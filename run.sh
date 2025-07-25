#!/bin/bash

# Exit on error
set -e

# Check if running the backend refactored version or the original
if [ "$1" == "backend" ]; then
    echo "Running refactored backend..."
    # Navigate to backend directory
    cd backend
    
    # Create and activate virtual environment for Python
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    source venv/bin/activate
    
    # Install backend dependencies
    echo "Installing backend dependencies..."
    pip install -r requirements.txt
    
    # Set PYTHONPATH to include the backend directory
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    
    # Run the application
    echo "Starting application on http://localhost:3000"
    uvicorn main:app --port 3000 --reload
else
    echo "Running original app.py..."
    # Run the original app.py
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    source venv/bin/activate
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt
    
    # Run the application
    echo "Starting application on http://localhost:3000"
    uvicorn app:app --port 3000 --reload
fi 