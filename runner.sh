#!/bin/sh

MODE=$1

if [ "$MODE" = "syncer" ]; then
  echo "Firebase Syncer Loop başlatıldı..."
  while true; do
    echo "[$(date)] Syncer çalışıyor..."
    python -u syncer.py
    echo "Bekleniyor: 30 dakika..."
    sleep 1800 # Sync data every 30 minutes (1800 seconds)
  done
else
  echo "Gold Collector Loop başlatıldı..."
  while true; do
    echo "[$(date)] Collector çalışıyor..."
    python -u collector.py
    echo "Bekleniyor: 5 dakika..."
    sleep 300 # Collect data every 5 minutes (300 seconds)
  done
fi