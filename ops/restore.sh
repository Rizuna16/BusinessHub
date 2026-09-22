#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:-}"
DB_URL="${DATABASE_URL:-}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Error: No backup file specified." >&2
    echo "Usage: ./ops/restore.sh <path_to_backup.sql.gz>" >&2
    exit 1
fi

if [ -z "$DB_URL" ]; then
    echo "Error: DATABASE_URL environment variable is not set." >&2
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file '$BACKUP_FILE' not found." >&2
    exit 1
fi

echo "WARNING: This will restore database content into the target database."
read -p "Are you sure you want to proceed? (yes/NO): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore aborted."
    exit 0
fi

echo "Starting BusinessHub database restore..."
gunzip < "$BACKUP_FILE" | psql "$DB_URL"

echo "Database restore completed successfully."
