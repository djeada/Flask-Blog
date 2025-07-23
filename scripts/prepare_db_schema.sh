#!/usr/bin/env bash
set -e

# Prepare DB schema
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."
SCHEMA_PATH="$REPO_ROOT/tests/schema.sql"
TIMEOUT=15
timeout $TIMEOUT mysql -h 127.0.0.1 -uroot -proot flask_db < "$SCHEMA_PATH"
