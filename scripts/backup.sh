#!/bin/bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_NAME="${DB_NAME:-lostitem}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump"

export PGPASSWORD="$DB_PASSWORD"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -F c -f "$FILENAME"

# Encrypt the backup with GPG if a key is provided
if [ -n "${GPG_RECIPIENT:-}" ]; then
    gpg --batch --yes --trust-model always \
        --recipient "$GPG_RECIPIENT" \
        --encrypt "$FILENAME"
    rm -f "$FILENAME"
    FILENAME="${FILENAME}.gpg"
fi

echo "Backup saved: $FILENAME ($(du -h "$FILENAME" | cut -f1))"

# Rotate old backups
find "$BACKUP_DIR" -name "${DB_NAME}_*.dump*" -mtime +"$RETENTION_DAYS" -delete
echo "Removed backups older than $RETENTION_DAYS days"
