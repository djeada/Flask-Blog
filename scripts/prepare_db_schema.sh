#!/usr/bin/env bash
set -e

# Prepare DB schema
# Requires the following environment variables:
#   DB_USER - The database username
#   DB_PASS - The database password
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."
SCHEMA_PATH="$REPO_ROOT/tests/schema.sql"
TIMEOUT=15
# Ensure required environment variables are set
if [ -z "$DB_USER" ] || [ -z "$DB_PASS" ]; then
    echo "Error: DB_USER and DB_PASS environment variables must be set."
    exit 1
fi

timeout $TIMEOUT mysql -h 127.0.0.1 -u"$DB_USER" -p"$DB_PASS" flask_db < "$SCHEMA_PATH"
