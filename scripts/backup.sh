#!/bin/bash

# Backup script for VPN Bot database
# Runs daily via cron

set -e

# Configuration
BACKUP_DIR="/app/backups"
DATA_DIR="/app/data"
DB_FILE="$DATA_DIR/vpn_bot.db"
RETENTION_DAYS=30

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/vpn_bot_$TIMESTAMP.db"

echo "Starting database backup..."

# Copy database file
if [ -f "$DB_FILE" ]; then
    cp "$DB_FILE" "$BACKUP_FILE"

    # Compress backup
    gzip "$BACKUP_FILE"

    echo "Backup created: ${BACKUP_FILE}.gz"

    # Remove old backups
    find "$BACKUP_DIR" -name "vpn_bot_*.db.gz" -type f -mtime +$RETENTION_DAYS -delete
    echo "Cleaned up backups older than $RETENTION_DAYS days"
else
    echo "Database file not found: $DB_FILE"
    exit 1
fi

echo "Backup completed successfully"
