#!/usr/bin/env bash
set -e

# FastAPI Blog Test Runner
# Tests the modernized FastAPI version of the blog application

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."

echo "=== FastAPI Blog Test Runner ==="

# Run the tests
pytest "$REPO_ROOT/tests/" -s -v --log-cli-level=INFO --tb=short

echo "FastAPI tests completed successfully!"
