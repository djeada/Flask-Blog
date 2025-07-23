#!/usr/bin/env bash
set -e

# Set environment variables for CI and local runs

export BLOG_DB_HOST="localhost"
export BLOG_DB_USER="root"
export BLOG_DB_PASSWORD="root"
export BLOG_DB_NAME="flask_db"
export BLOG_DB_CURSOR="DictCursor"

# Also set MySQL client variables for compatibility
export MYSQL_USER="$BLOG_DB_USER"
export MYSQL_PASSWORD="$BLOG_DB_PASSWORD"

# Optionally print for diagnostics
printenv | grep BLOG_DB_
