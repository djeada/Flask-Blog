#!/usr/bin/env bash
set -e

# Install dependencies for FastAPI Blog
INSTALL_TIMEOUT=30

echo "[INFO] Installing dependencies for FastAPI Blog..."

# Install system dependencies
if ! command -v mysqladmin >/dev/null 2>&1; then
  echo "[INFO] Installing MySQL client tools..."
  if command -v apt-get >/dev/null 2>&1; then
    timeout $INSTALL_TIMEOUT sudo apt-get update
    timeout $INSTALL_TIMEOUT sudo apt-get install -y mysql-client libmysqlclient-dev pkg-config
  elif command -v yum >/dev/null 2>&1; then
    timeout $INSTALL_TIMEOUT sudo yum install -y mysql mysql-devel pkgconfig
  else
    echo "[ERROR] Could not detect package manager. Please install MySQL client manually."
    exit 1
  fi
fi

# Install Python dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."
REQ_PATH="$REPO_ROOT/requirements.txt"

# Check if requirements file exists
if [ ! -f "$REQ_PATH" ]; then
    echo "[ERROR] Requirements file not found: $REQ_PATH"
    exit 1
fi

echo "[INFO] Installing FastAPI dependencies..."
timeout $INSTALL_TIMEOUT python -m pip install --upgrade pip
timeout $INSTALL_TIMEOUT pip install -r "$REQ_PATH"

# Install test dependencies if available
REQ_TEST_PATH="$REPO_ROOT/requirements-test.txt"
if [ -f "$REQ_TEST_PATH" ]; then
  echo "[INFO] Installing test dependencies..."
  timeout $INSTALL_TIMEOUT pip install -r "$REQ_TEST_PATH"
fi

echo "[INFO] Dependencies installation completed successfully!"
