FROM python:3.8-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jdk \
    libssl-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

CMD flask run --host=0.0.0.0