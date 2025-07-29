#!/bin/bash

# FastAPI Blog Startup Script

echo "Starting FastAPI Blog Application..."

# Set the working directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r ../requirements.txt

# Source environment variables
echo "Setting up environment variables..."
source ../scripts/set_env_vars.sh

# Initialize database tables
echo "Initializing database..."
python init_app.py

# Start the application
echo "Starting FastAPI server..."
echo "🚀 Application will be available at: http://localhost:8000"
echo "📚 API documentation will be available at: http://localhost:8000/docs"
echo "🔄 Interactive API explorer at: http://localhost:8000/redoc"

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
