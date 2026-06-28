FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ curl && rm -rf /var/lib/apt/lists/*
COPY requirements-base.txt .
# torch CPU in separate layer — cached by Docker, only downloads once (~800MB)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements-base.txt
COPY . .
ENV PYTHONUNBUFFERED=1
