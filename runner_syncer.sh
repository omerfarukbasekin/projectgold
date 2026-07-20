#!/bin/sh

while true; do
  echo "[$(date)] Syncer çalışıyor..."
  python syncer.py
  echo "[$(date)] Bekleniyor: 30 dakika..."
  sleep 1800
done
