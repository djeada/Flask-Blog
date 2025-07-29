#!/usr/bin/env bash
set -e

# Install dependencies for FastAPI Blog
INSTALL_TIMEOUT=30

echo "[INFO] Installing dependencies for FastAPI Blog..."

# Check if MySQL client tools are available
if ! command -v mysqladmin >/dev/null 2>&1; then
  echo "[INFO] MySQL client tools not found..."
  
  # Try to install system dependencies without sudo if possible
  if command -v apt-get >/dev/null 2>&1; then
    echo "[INFO] Attempting to install MySQL client tools..."
    
    # Try without sudo first (for CI environments)
    if timeout $INSTALL_TIMEOUT apt-get update >/dev/null 2>&1 && \
       timeout $INSTALL_TIMEOUT apt-get install -y mysql-client libmysqlclient-dev pkg-config >/dev/null 2>&1; then
      echo "[INFO] Successfully installed MySQL client tools"
    elif command -v sudo >/dev/null 2>&1; then
      # Fall back to sudo if available
      echo "[INFO] Trying with sudo..."
      timeout $INSTALL_TIMEOUT sudo apt-get update
      timeout $INSTALL_TIMEOUT sudo apt-get install -y mysql-client libmysqlclient-dev pkg-config
      echo "[INFO] Successfully installed MySQL client tools with sudo"
    else
      echo "[WARNING] Could not install MySQL client tools. They may need to be installed manually."
      echo "[WARNING] Continuing anyway - system may already have MySQL client available."
    fi
    
  elif command -v yum >/dev/null 2>&1; then
    echo "[INFO] Attempting to install MySQL client tools with yum..."
    if timeout $INSTALL_TIMEOUT yum install -y mysql mysql-devel pkgconfig >/dev/null 2>&1; then
      echo "[INFO] Successfully installed MySQL client tools"
    elif command -v sudo >/dev/null 2>&1; then
      timeout $INSTALL_TIMEOUT sudo yum install -y mysql mysql-devel pkgconfig
      echo "[INFO] Successfully installed MySQL client tools with sudo"
    else
      echo "[WARNING] Could not install MySQL client tools. They may need to be installed manually."
    fi
    
  else
    echo "[WARNING] Could not detect package manager. MySQL client tools may need to be installed manually."
    echo "[WARNING] Continuing anyway - system may already have MySQL client available."
  fi
else
  echo "[INFO] MySQL client tools already available"
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
