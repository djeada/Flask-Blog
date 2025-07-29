#!/usr/bin/env bash
set -e

# Prepare DB schema for FastAPI Blog
# Uses environment variables for database configuration

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."
SCHEMA_PATH="$REPO_ROOT/tests/schema.sql"
TIMEOUT=15

# Use environment variables with defaults
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-secret_pass}"
DB_NAME="${DB_NAME:-blog_db}"

echo "Preparing database schema for FastAPI Blog..."
echo "Host: $DB_HOST:$DB_PORT"
echo "Database: $DB_NAME"
echo "User: $DB_USER"

# Check if schema file exists
if [ ! -f "$SCHEMA_PATH" ]; then
    echo "Error: Schema file not found at $SCHEMA_PATH"
    exit 1
fi

# Create database if it doesn't exist
echo "Creating database if it doesn't exist..."
timeout $TIMEOUT mysql -h "$DB_HOST" -P "$DB_PORT" --protocol=TCP -u"$DB_USER" -p"$DB_PASSWORD" \
    -e "CREATE DATABASE IF NOT EXISTS $DB_NAME;"

# Apply schema
echo "Applying database schema..."
timeout $TIMEOUT mysql -h "$DB_HOST" -P "$DB_PORT" --protocol=TCP -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < "$SCHEMA_PATH"

echo "Database schema preparation completed successfully!"
