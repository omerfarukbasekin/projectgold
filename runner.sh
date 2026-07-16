#!/bin/sh

# Source environment variables from .env
if [ -f ./.env ]; then
    export $(grep -v '^#' ./.env | xargs)
fi

# Activate Python virtual environment
if [ -f ./venv/bin/activate ]; then
    . ./venv/bin/activate
fi

echo "Gold Tracker Backend pipeline başlatıldı (SQLite & Firebase Sync)..."

while true; do
  echo "[$(date)] collector & syncer çalışıyor..."
  python main.py
  echo "[$(date)] Bekleniyor: 10 dakika..."
  sleep 600
done


