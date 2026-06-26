#!/bin/bash
set -e
PROJ=/mnt/c/Users/keshav/Documents/mnit\(cyberhack\)

# start dockerd if not running
docker info &>/dev/null || { dockerd &>/tmp/dockerd.log & sleep 5; }

# sync project to native WSL fs for fast I/O
rsync -a --delete "$PROJ/" ~/mnit/ --exclude='env/' --exclude='node_modules/' --exclude='*.db' --exclude='.git/'
cd ~/mnit

# build qwen-base only if it doesn't exist yet (one-time ~800MB download)
if ! docker image inspect mnit-qwen-base:latest &>/dev/null; then
  echo "=== Building qwen-base (one-time download, will be cached) ==="
  docker build -f Dockerfile.qwen-base -t mnit-qwen-base:latest .
else
  echo "=== qwen-base already cached, skipping ==="
fi

echo "=== Building app images (fast) ==="
docker compose build --parallel

echo "=== Starting all services ==="
docker compose up -d

echo ""
echo "=== All services up ==="
docker compose ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}'
