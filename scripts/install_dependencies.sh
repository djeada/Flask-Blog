#!/usr/bin/env bash
set -e

# Install system dependencies
INSTALL_TIMEOUT=30
if ! command -v mysqladmin >/dev/null 2>&1; then
  echo "[INFO] Installing MySQL client tools..."
  if command -v apt-get >/dev/null 2>&1; then
    timeout $INSTALL_TIMEOUT sudo apt-get update
    timeout $INSTALL_TIMEOUT sudo apt-get install -y mysql-client
  elif command -v yum >/dev/null 2>&1; then
    timeout $INSTALL_TIMEOUT sudo yum install -y mysql
  else
    echo "[ERROR] Could not detect package manager. Please install MySQL client manually."
    exit 1
  fi
fi

# Install Python dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."
REQ_PATH="$REPO_ROOT/requirements.txt"
REQ_TEST_PATH="$REPO_ROOT/requirements-test.txt"
timeout $INSTALL_TIMEOUT python -m pip install --upgrade pip
timeout $INSTALL_TIMEOUT pip install -r "$REQ_PATH"
if [ -f "$REQ_TEST_PATH" ]; then
  timeout $INSTALL_TIMEOUT pip install -r "$REQ_TEST_PATH"
fi
