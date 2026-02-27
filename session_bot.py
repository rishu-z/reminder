"""
Session Mention Bot — Improved
Fixes: persistent users, correct scheduler context, race conditions,
       error handling, flood protection, duplicate-trigger guard.
"""

import os
import json
import asyncio
import logging
import pytz
from datetime import datetime, timedelta, time
from pathlib import Path

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ─── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ─── Config ─────────────────────────────────────────────────────────────────

TOKEN    = os.getenv("BOT_TOKEN")
CHAT_ID  = int(os.getenv("CHAT_ID", "-1003800205030"))
TOPIC_ID = int(os.getenv("TOPIC_ID", "1799"))

IST = pytz.timezone("Asia/Kolkata")

SESSION_TIMES = [
    time(11,  0),
    time(16,  0),
    time(20,  0),
    time( 0,  0),
]

BATCH_SIZE     = 5      # users per message
BATCH_DELAY    = 5      # seconds between batches
LOOP_DELAY     = 30     # seconds between full loops
TRIGGER_BEFORE = 10     # minutes before session to start mentioning
USERS_FILE     = Path(os.getenv("USERS_FILE", "/app/data/active_users.json"))

# ─── Persistent user store ──────────────────────────────────────────────────

def load_users() -> set:
    if USERS_FILE.exists():
        try:
            return set(json.loads(USERS_FILE.read_text()))
        except Exception:
            pass
    return set()

def save_users(users: set) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(list(users)))

active_users: set = load_users()

# ─── State ──────────────────────────────────────────────────────────────────

mention_task: asyncio.Task = None
stop_flag = False
last_triggered: datetime = None

# ─── Helpers ────────────────────────────────────────────────────────────────

def get_next_session() -> datetime:
    now   = datetime.now(IST)
    today = now.date()
    for s in SESSION_TIMES:
        dt = IST.localize(datetime.combine(today, s))
        if dt > now:
            return dt
    tomorrow = today + timedelta(days=1)
    return IST.localize(datetime.combine(tomorrow, SESSION_TIMES[0]))


async def is_admin(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        admins = await context.bot.get_chat_administrators(CHAT_ID)
        return user_id in {a.user.id for a in admins}
    except Exception as e:
        log.warning("is_admin error: %s", e)
        return False


def in_session_topic(update: Update) -> bool:
    return (
        update.effective_chat.id == CHAT_ID
        and update.message.message_thread_id == TOPIC_ID
    )

# ─── Handlers ───────────────────────────────────────────────────────────────

async def track_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silently track every user who writes in the group."""
    if update.effective_chat.id != CHAT_ID:
        return
    user = update.effective_user
    if user and not user.is_bot:
        if user.id not in active_users:
            active_users.add(user.id)
            save_users(active_users)


async def cmd_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: /all [optional note] — manually trigger mentions."""
    global mention_task
    if not in_session_topic(update):
        return
    if not await is_admin(update.effective_user.id, context):
        await update.message.reply_text("⛔ Admins only.")
        return
    if mention_task and not mention_task.done():
        await update.message.reply_text("⚠️ Already running. Use /stop first.")
        return

    note       = " ".join(context.args).strip() or None
    session_dt = get_next_session()
    mention_task = asyncio.create_task(run_mentions(context, session_dt, note))
    log.info("Manual /all triggered for session at %s", session_dt)


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: /stop — stop the current mention loop."""
    global stop_flag
    if not in_session_topic(update):
        return
    if not await is_admin(update.effective_user.id, context):
        return
    stop_flag = True
    await update.message.reply_text("⛔ Mentions stopped.")
    log.info("Mentions stopped by admin %s", update.effective_user.id)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: /stats — show tracked user count & next session."""
    if not in_session_topic(update):
        return
    if not await is_admin(update.effective_user.id, context):
        return
    next_s  = get_next_session()
    running = mention_task and not mention_task.done()
    await update.message.reply_text(
        f"👥 Tracked users: {len(active_users)}\n"
        f"⏰ Next session: {next_s.strftime('%H:%M')} IST\n"
        f"🔄 Mentions running: {'Yes ✅' if running else 'No ❌'}"
    )

# ─── Core mention loop ───────────────────────────────────────────────────────

async def run_mentions(context, session_dt: datetime, manual_note: str = None):
    global mention_task, stop_flag
    stop_flag = False

    users = list(active_users)
    total = len(users)

    if total == 0:
        log.info("No active users to mention.")
        mention_task = None
        return

    log.info("Starting mentions for %d users, session at %s", total, session_dt)

    try:
        while datetime.now(IST) < session_dt and not stop_flag:
            remaining = int((session_dt - datetime.now(IST)).total_seconds() / 60)
            mentioned = 0

            for i in range(0, total, BATCH_SIZE):
                if stop_flag:
                    break

                batch      = users[i : i + BATCH_SIZE]
                mentioned += len(batch)

                mentions  = " ".join(
                    f"<a href='tg://user?id={uid}'>👤</a>" for uid in batch
                )
                note_line = f"\n📝 {manual_note}\n" if manual_note else ""
                text = (
                    f"🚀 <b>Session in {remaining} min</b>{note_line}\n"
                    f"📊 {mentioned}/{total} notified\n\n"
                    f"{mentions}"
                )

                try:
                    await context.bot.send_message(
                        chat_id=CHAT_ID,
                        text=text,
                        parse_mode="HTML",
                        message_thread_id=TOPIC_ID,
                    )
                except Exception as e:
                    log.error("send_message failed: %s", e)

                await asyncio.sleep(BATCH_DELAY)

            await asyncio.sleep(LOOP_DELAY)

    except asyncio.CancelledError:
        log.info("Mention task cancelled.")
    finally:
        mention_task = None
        log.info("Mention loop ended.")

# ─── Auto-scheduler ──────────────────────────────────────────────────────────

async def scheduler_check(bot):
    global mention_task, last_triggered

    now          = datetime.now(IST)
    next_session = get_next_session()
    trigger_time = next_session - timedelta(minutes=TRIGGER_BEFORE)

    already_triggered = (
        last_triggered is not None
        and abs((last_triggered - next_session).total_seconds()) < 60
    )

    should_trigger = (
        now >= trigger_time
        and now < next_session
        and not already_triggered
        and (mention_task is None or mention_task.done())
    )

    if not should_trigger:
        return

    last_triggered = next_session
    log.info("Auto-trigger: session at %s", next_session)

    class _BotCtx:
        def __init__(self, b):
            self.bot = b

    mention_task = asyncio.create_task(
        run_mentions(_BotCtx(bot), next_session)
    )

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set!")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, track_users))
    app.add_handler(CommandHandler("all",   cmd_all))
    app.add_handler(CommandHandler("stop",  cmd_stop))
    app.add_handler(CommandHandler("stats", cmd_stats))

    scheduler = AsyncIOScheduler(timezone=IST)
    scheduler.add_job(
        scheduler_check,
        "interval",
        minutes=1,
        args=[app.bot],
    )
    scheduler.start()

    log.info("🔥 Session Bot running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
