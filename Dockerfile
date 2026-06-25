FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ curl && rm -rf /var/lib/apt/lists/*
COPY requirements-base.txt .
RUN pip install --no-cache-dir -r requirements-base.txt
COPY . .
ENV PYTHONUNBUFFERED=1
