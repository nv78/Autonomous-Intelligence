FROM python:3.8-slim 

ENV FLASK_APP=app.py \
    FLASK_ENV=development \
    FLASK_DEBUG=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
    
# Set up application directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose ports
EXPOSE 5000 6379

# Use the start script as the entrypoint
CMD ["bash", "-c", "ray start --head --port=6379 --dashboard-port=9998 && flask run --host=0.0.0.0 --port=5000 --no-reload"]

