#!/usr/bin/env bash
# AgentNet — database backup script
# Usage: bash scripts/backup.sh [output_dir]
set -e

BACKUP_DIR="${1:-/home/agentuser/agentnet/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="agentnet_backup_${TIMESTAMP}.sql"
mkdir -p "$BACKUP_DIR"

echo "📦 Backing up AgentNet database..."
PGPASSWORD=changeme_dev_only pg_dump \
  -h localhost \
  -U agentnet \
  -d agentnet \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  --file="${BACKUP_DIR}/${FILENAME}"

# Compress
gzip -f "${BACKUP_DIR}/${FILENAME}"
echo "✅ Backup saved: ${BACKUP_DIR}/${FILENAME}.gz ($(du -h "${BACKUP_DIR}/${FILENAME}.gz" | cut -f1))"

# Keep only last 7 backups
ls -t "${BACKUP_DIR}"/agentnet_backup_*.gz 2>/dev/null | tail -n +8 | xargs rm -f 2>/dev/null || true
echo "🗑️  Pruned old backups (kept last 7)"
