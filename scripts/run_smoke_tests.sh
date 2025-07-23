#!/usr/bin/env bash
set -e

# Run smoke tests
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."
TIMEOUT=120
timeout $TIMEOUT pytest "$REPO_ROOT/tests/" -s -v --log-cli-level=INFO
