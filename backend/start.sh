#!/bin/bash
set -e

# Start Agent System with FastMCP Server
echo "Starting Reactive Agent System..."

# Activate the virtual environment if it exists
if [ -f /opt/venv/bin/activate ]; then
    source /opt/venv/bin/activate
fi

# Initialize Ray if not already running
if ! ray status > /dev/null 2>&1; then
    echo "Starting Ray..."
    ray start --head --port=6379 --dashboard-port=9998 &
    sleep 5
fi

# Start FastMCP server in background
echo "Starting FastMCP server..."
python mcp/mcp_server.py &
MCP_PID=$!

# Wait a moment for MCP server to start
sleep 3

# Start Flask application
echo "Starting Flask application with reactive agents..."
export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Set MCP server URL for the Flask app to communicate
export MCP_SERVER_URL="http://localhost:8000"

# Function to cleanup processes on exit
cleanup() {
    echo "Shutting down agent system..."
    kill $MCP_PID 2>/dev/null
    ray stop
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start Flask app
exec flask run --host=0.0.0.0 --port=5000 --no-reload
