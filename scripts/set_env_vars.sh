#!/usr/bin/env bash
set -e

# Set environment variables for FastAPI Blog application

# FastAPI Database Configuration
export DB_HOST="localhost"
export DB_PORT="3306"
export DB_USER="root"
export DB_PASSWORD="secret_pass"
export DB_NAME="blog_db"

# Security Configuration
export SECRET_KEY="your-secret-key-here-change-this-in-production"
export ALGORITHM="HS256"
export ACCESS_TOKEN_EXPIRE_MINUTES="30"

# Application Configuration
export DEBUG="True"
export APP_NAME="FastAPI Blog"
export APP_VERSION="1.0.0"

# CORS Configuration
export ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8000"

# Test Configuration
export BLOG_APP_PORT="8000"
export BLOG_TEST_TIMEOUT="120"
export BLOG_VERBOSE="false"

# Optionally print for diagnostics
echo "FastAPI Blog Environment Variables Set:"
printenv | grep -E "(DB_|SECRET_|APP_|BLOG_)" | sort
