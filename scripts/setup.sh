#!/usr/bin/env bash
set -e

# FastAPI Blog Setup Script
# Comprehensive setup for the modernized blog application

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."
SRC_DIR="$REPO_ROOT/src"

echo "==============================================="
echo "       FastAPI Blog Setup Script"
echo "==============================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Python dependencies
install_dependencies() {
    echo "Installing Python dependencies..."
    
    if [ -f "$SCRIPT_DIR/install_dependencies.sh" ]; then
        bash "$SCRIPT_DIR/install_dependencies.sh"
        echo "✓ Dependencies installed successfully"
    else
        echo "❌ Install dependencies script not found"
        exit 1
    fi
}

# Function to setup environment variables
setup_environment() {
    echo "Setting up environment variables..."
    
    # Environment variables are now managed by set_env_vars.sh script
    # No .env file needed as the application uses environment variables directly
    echo "✓ Using environment variables from set_env_vars.sh script"
}

# Function to check database connection
check_database() {
    echo "Checking database connection..."
    
    # Use set_env_vars.sh for environment configuration
    source "$REPO_ROOT/scripts/set_env_vars.sh"
    
    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-3306}"
    DB_USER="${DB_USER:-root}"
    DB_PASSWORD="${DB_PASSWORD:-secret_pass}"
    
    if command_exists mysql; then
        # Create MySQL configuration file for secure authentication
        MYSQL_CONFIG_FILE="$HOME/.my.cnf"
        if [ ! -f "$MYSQL_CONFIG_FILE" ]; then
            echo "[client]" > "$MYSQL_CONFIG_FILE"
            echo "host=$DB_HOST" >> "$MYSQL_CONFIG_FILE"
            echo "port=$DB_PORT" >> "$MYSQL_CONFIG_FILE"
            echo "user=$DB_USER" >> "$MYSQL_CONFIG_FILE"
            echo "password=$DB_PASSWORD" >> "$MYSQL_CONFIG_FILE"
            chmod 600 "$MYSQL_CONFIG_FILE"
            echo "✓ Created MySQL configuration file at $MYSQL_CONFIG_FILE"
        fi
        
        if mysql --defaults-file="$MYSQL_CONFIG_FILE" -e "SELECT 1;" >/dev/null 2>&1; then
            echo "✓ Database connection successful"
            return 0
        else
            echo "❌ Database connection failed"
            echo "Please ensure MySQL is running and credentials are correct"
            return 1
        fi
    else
        echo "⚠️  MySQL client not found, skipping connection test"
        return 0
    fi
}

# Function to setup database schema
setup_database() {
    echo "Setting up database schema..."
    
    if [ -f "$SCRIPT_DIR/prepare_db_schema.sh" ]; then
        bash "$SCRIPT_DIR/prepare_db_schema.sh"
        echo "✓ Database schema setup completed"
    else
        echo "❌ Database schema script not found"
        exit 1
    fi
}

# Function to run tests
run_tests() {
    echo "Running application tests..."
    
    if [ -f "$SCRIPT_DIR/run_tests.sh" ]; then
        bash "$SCRIPT_DIR/run_tests.sh" --timeout 60
        echo "✓ All tests passed"
    else
        echo "❌ Test script not found"
        exit 1
    fi
}

# Main setup process
main() {
    echo "Starting FastAPI Blog setup..."
    
    # Check prerequisites
    echo "Checking prerequisites..."
    
    if ! command_exists python3; then
        echo "❌ Python 3 is required but not installed"
        exit 1
    fi
    
    if ! command_exists pip; then
        echo "❌ pip is required but not installed"
        exit 1
    fi
    
    echo "✓ Python and pip are available"
    
    # Setup steps
    install_dependencies
    setup_environment
    
    # Optional steps (can continue if they fail)
    if check_database; then
        setup_database
    else
        echo "⚠️  Skipping database setup due to connection issues"
        echo "   You can run 'scripts/prepare_db_schema.sh' manually later"
    fi
    
    echo ""
    echo "==============================================="
    echo "           Setup Complete!"
    echo "==============================================="
    echo ""
    echo "Next steps:"
    echo "1. Ensure MySQL is running"
    echo "2. Run: cd src && python init_app.py"
    echo "3. Start the app: cd src && uvicorn main:app --reload"
    echo "4. Visit: http://localhost:8000"
    echo ""
    echo "Available commands:"
    echo "- Run tests: scripts/run_tests.sh"
    echo "- Setup DB: scripts/prepare_db_schema.sh"
    echo "- Set env vars: source scripts/set_env_vars.sh"
    echo ""
}

# Parse command line options
SKIP_TESTS=false
SKIP_DB=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --skip-tests  Skip running tests"
            echo "  --skip-db     Skip database setup"
            echo "  -h, --help    Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main setup
main

# Optional test run
if [ "$SKIP_TESTS" = "false" ]; then
    echo "Running tests to verify setup..."
    if run_tests; then
        echo "🎉 Setup verification successful!"
    else
        echo "⚠️  Tests failed, but setup may still be functional"
        echo "   Check the error messages above"
    fi
fi
