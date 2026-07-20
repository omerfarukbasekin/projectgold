#!/bin/bash

# Sanal ortam (venv) varsa aktif et
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Zamanlanmış Direkt Syncer başlatılıyor..."

# Terminal kapansa dahi arka planda (nohup ile) her 30 dakikada bir manual_push_all.py çalıştıracak sonsuz döngü
nohup bash -c '
while true; do
  echo "-----------------------------------" >> direct_syncer.log
  echo "[$(date)] manual_push_all.py tetikleniyor..." >> direct_syncer.log
  python3 manual_push_all.py >> direct_syncer.log 2>&1
  echo "[$(date)] 30 Dakika bekleniyor..." >> direct_syncer.log
  sleep 1800
done
' > /dev/null 2>&1 &

echo "Sistem arka planda başarıyla kuruldu ve çalıştırıldı!"
echo "Çalışmasını izlemek için: tail -f direct_syncer.log"
