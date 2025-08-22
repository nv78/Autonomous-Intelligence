#!/bin/bash
set -e

# Activate the virtual environment
source /opt/venv/bin/activate

# Start Flask
echo "Starting Flask application..."
exec flask run --host=0.0.0.0 --port=5000
