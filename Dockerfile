FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    cron \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/data /app/backups

# Make backup script executable
RUN chmod +x /app/scripts/backup.sh

# Setup cron job for daily backup at 02:00
RUN echo "0 2 * * * cd /app && /app/scripts/backup.sh >> /var/log/backup.log 2>&1" > /etc/cron.d/backup \
    && crontab /etc/cron.d/backup

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite+aiosqlite:///./data/vpn_bot.db

# Start cron and bot
CMD ["sh", "-c", "cron && python bot.py"]
