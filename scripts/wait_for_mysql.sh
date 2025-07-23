#!/usr/bin/env bash
set -e

# Wait for MySQL to be ready
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."
TIMEOUT=15
START=$(date +%s)
while true; do
  if mysqladmin ping -h 127.0.0.1 -uroot -proot --silent; then
    break
  fi
  NOW=$(date +%s)
  if [ $((NOW-START)) -ge $TIMEOUT ]; then
    echo "[ERROR] MySQL did not become ready within $TIMEOUT seconds."
    exit 1
  fi
  sleep 2
done
