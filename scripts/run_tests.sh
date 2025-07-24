#!/usr/bin/env bash
set -e

# FastAPI Blog Test Runner
# Tests the modernized FastAPI version of the blog application

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."

# Default values
PORT=8000
TIMEOUT=120
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --port PORT        Port to run the FastAPI app on (default: 8000)"
            echo "  --timeout TIMEOUT  Test timeout in seconds (default: 120)"
            echo "  -v, --verbose      Enable verbose output"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=== FastAPI Blog Test Runner ==="
echo "Port: $PORT"
echo "Timeout: $TIMEOUT seconds"
echo "Verbose: $VERBOSE"
echo "==============================="

# Export configuration for tests
export BLOG_APP_PORT="$PORT"
export BLOG_TEST_TIMEOUT="$TIMEOUT"
export BLOG_VERBOSE="$VERBOSE"

# Run the tests
if [ "$VERBOSE" = "true" ]; then
    timeout $TIMEOUT pytest "$REPO_ROOT/tests/" -s -v --log-cli-level=INFO
else
    timeout $TIMEOUT pytest "$REPO_ROOT/tests/" -v
fi

echo "FastAPI tests completed successfully!"
