FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY session_bot.py .

# Data folder for persistent storage (mount a Railway Volume here)
RUN mkdir -p /app/data

CMD ["python", "session_bot.py"]
