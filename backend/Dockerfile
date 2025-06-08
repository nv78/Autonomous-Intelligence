
# Development stage
FROM python:3.8-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    default-jdk \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Install tokenizers and anthropic separately
RUN pip install --no-cache-dir tokenizers==0.13.3 anthropic==0.7.4

# Set up application directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make start script executable
RUN chmod +x /app/start.sh

# Set environment variables for development
ENV FLASK_APP=app.py \
    FLASK_ENV=development \
    FLASK_DEBUG=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose ports
EXPOSE 5000 6379 9998

# Use the start script as the entrypoint
ENTRYPOINT ["/bin/bash", "/app/start.sh"]
