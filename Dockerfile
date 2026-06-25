FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# torch CPU-only to keep image size sane — GPU passthrough not needed for 0.8B
RUN pip install --no-cache-dir torch==2.12.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

# CMD supplied per-service in docker-compose
