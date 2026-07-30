#!/usr/bin/env bash
# Automated daily backup
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/agentnet"
mkdir -p "$BACKUP_DIR"

docker compose exec -T db pg_dump -U agentnet agentnet | gzip > "${BACKUP_DIR}/agentnet_${TIMESTAMP}.sql.gz"
echo "Backup saved: ${BACKUP_DIR}/agentnet_${TIMESTAMP}.sql.gz"

# Keep last 7 days
find "$BACKUP_DIR" -name 'agentnet_*.sql.gz' -mtime +7 -delete
