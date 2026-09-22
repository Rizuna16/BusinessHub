#!/usr/bin/env bash
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_URL="${DATABASE_URL:-}"

if [ -z "$DB_URL" ]; then
    echo "Error: DATABASE_URL environment variable is not set." >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/businesshub_backup_$TIMESTAMP.sql.gz"

echo "Starting BusinessHub database backup..."
pg_dump "$DB_URL" | gzip > "$BACKUP_FILE"

echo "Backup completed successfully: $BACKUP_FILE"
