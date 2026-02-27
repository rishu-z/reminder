# 🚀 Session Mention Bot

Telegram bot jo automatically group members ko session se pehle mention karta hai.

---

## 📁 File Structure

```
session-bot/
├── session_bot.py     # Main bot code
├── requirements.txt   # Python dependencies
├── Dockerfile         # Railway deployment
├── railway.toml       # Railway config
└── .gitignore
```

---

## ⚙️ Environment Variables

Railway pe ye variables set karne hain:

| Variable     | Description                        | Example                  |
|--------------|------------------------------------|--------------------------|
| `BOT_TOKEN`  | BotFather se mila token ✅ Required | `123456:ABC-DEF...`      |
| `CHAT_ID`    | Group ka ID (optional)             | `-1003800205030`         |
| `TOPIC_ID`   | Topic/Thread ka ID (optional)      | `1799`                   |
| `USERS_FILE` | JSON file path (optional)          | `/app/data/active_users.json` |

> `CHAT_ID` aur `TOPIC_ID` default values `session_bot.py` mein hain, sirf change karna ho toh env var set karo.

---

## 🚂 Railway Deployment Steps

### 1. GitHub pe push karo

```bash
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/apna-username/session-bot.git
git push -u origin main
```

### 2. Railway pe project banao

1. [railway.app](https://railway.app) → GitHub se login
2. **New Project** → **Deploy from GitHub repo**
3. Apna repo select karo
4. Railway Dockerfile automatically detect karega ✅

### 3. Environment variable add karo

Railway Dashboard → Apna project → **Variables** tab:

```
BOT_TOKEN = apna_token_yahan_paste_karo
```

### 4. Volume add karo (Persistent Storage)

Bina Volume ke `active_users.json` restart pe delete ho jaayegi!

1. Railway Dashboard → **New** → **Volume**
2. Volume ko apne bot service se connect karo
3. Mount Path: `/app/data`

### 5. Deploy!

Railway automatically build aur deploy karega.  
**Logs** tab mein dikhega: `🔥 Session Bot running...`

---

## 🛠️ Admin Commands

Sirf group admins use kar sakte hain, aur sirf configured topic mein:

| Command         | Kya karta hai                              |
|-----------------|--------------------------------------------|
| `/all`          | Abhi mention loop shuru karo               |
| `/all note xyz` | Mention ke saath custom note bhejo         |
| `/stop`         | Chal rahe mentions band karo               |
| `/stats`        | Users count, next session, status dekho    |

---

## ⏰ Session Times (IST)

- 11:00 AM
- 4:00 PM  
- 8:00 PM  
- 12:00 AM (Midnight)

Bot session se **10 minutes pehle** automatically mentions shuru karta hai.

---

## 💡 Tips

- **Free plan**: 500 hrs/month — 24/7 ke liye **Hobby ($5/month)** lo
- Bot crash kare toh Railway **auto-restart** karta hai (`restartPolicyType = "always"`)
- Logs real-time dekhne ke liye: Railway Dashboard → **Logs** tab
