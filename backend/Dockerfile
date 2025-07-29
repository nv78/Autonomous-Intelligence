
# Development stage
FROM python:3.8-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-jdk \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set up application directory
WORKDIR /app

COPY ./database/schema.sql /docker-entrypoint-initdb.d/init.sql

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables for development
ENV FLASK_APP=app.py \
    FLASK_ENV=development \
    FLASK_DEBUG=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose ports
EXPOSE 5000 6379 9998

# Use the start script as the entrypoint
CMD ["bash", "-c", "ray start --head --port=6379 --dashboard-port=9998 && flask run --host=0.0.0.0 --port=5000 --no-reload"]
