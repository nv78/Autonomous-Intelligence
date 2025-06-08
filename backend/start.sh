#!/bin/bash
set -e

# Activate the virtual environment
source /opt/venv/bin/activate

# Run database initialization
cd /app
echo "Running database initialization script..."
python3 database/init_db_dev.py

# Start Flask
echo "Starting Flask application..."
exec flask run --host=0.0.0.0 --port=5000
