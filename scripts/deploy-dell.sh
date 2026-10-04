#!/usr/bin/env bash
set -euo pipefail

remote_host="${AEGIS_REMOTE_HOST:-dell-ts}"
remote_path="${AEGIS_REMOTE_PATH:-/home/hari/aegispr}"

rsync -az --delete \
  --exclude .git \
  --exclude .env \
  --exclude node_modules \
  --exclude .venv \
  --exclude .next \
  ./ "${remote_host}:${remote_path}/"

ssh "$remote_host" "cd '$remote_path' && docker compose build && docker compose up -d && docker compose ps"
