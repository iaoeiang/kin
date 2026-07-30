#!/usr/bin/env bash
# AgentNet — database restore script
# Usage: bash scripts/restore.sh <backup_file>
set -e

if [ -z "$1" ]; then
  echo "❌ Usage: bash scripts/restore.sh <backup_file>"
  echo "   Supports .sql or .sql.gz files"
  exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "❌ File not found: $BACKUP_FILE"
  exit 1
fi

echo "⚠️  WARNING: This will DROP all tables in the agentnet database!"
read -p "Type 'RESTORE' to confirm: " CONFIRM
if [ "$CONFIRM" != "RESTORE" ]; then
  echo "Canceled."
  exit 0
fi

echo "🔄 Restoring AgentNet database from $BACKUP_FILE..."

if [[ "$BACKUP_FILE" == *.gz ]]; then
  gunzip -c "$BACKUP_FILE" | PGPASSWORD=changeme_dev_only psql -h localhost -U agentnet -d agentnet
else
  PGPASSWORD=changeme_dev_only psql -h localhost -U agentnet -d agentnet -f "$BACKUP_FILE"
fi

echo "✅ Restore complete. Restart the API server: sudo systemctl restart agentnet-api"
