import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime
import sys
import time

DB_FILE = "app.db"

FETCH_LIMIT = 4000
BATCH_SIZE = 10 

print("Firebase bağlantısı test ediliyor...")
try:
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "projectgold-6b3bf")
    service_account_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "service-account.json")
    
    if os.path.exists(service_account_path) and os.path.isfile(service_account_path):
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, options={"projectId": project_id})
        print("Service Account ile bağlanıldı.")
    else:
        firebase_admin.initialize_app(options={"projectId": project_id})
        print("Default Credentials (ADC) ile bağlanıldı.")
        
    db_fs = firestore.client()
except Exception as e:
    print(f"BAĞLANTI HATASI: {e}")
    sys.exit(1)

print(f"\n'{DB_FILE}' dosyasından veriler okunuyor...")
if not os.path.exists(DB_FILE):
    print("HATA: app.db dosyası bulunamadı!")
    sys.exit(1)

conn = sqlite3.connect(DB_FILE)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

total_synced = 0
print("Güvenli aktarım başladı (Sondan max 200 veri alınacak, 10'ar 10'ar yollanacak).")

cur.execute(f"""
    SELECT id, code, description, price_buy, price_sell, source_updated_at 
    FROM trades 
    WHERE synced_to_firebase = 0
    ORDER BY source_updated_at DESC
    LIMIT {FETCH_LIMIT}
""")
trades = cur.fetchall()

trades = trades[::-1]

if not trades:
    print("\nSQLite üzerinde aktarılacak (synced=0) başka kayıt kalmadı!")
    conn.close()
    sys.exit(0)

for i in range(0, len(trades), BATCH_SIZE):
    chunk = trades[i:i + BATCH_SIZE]
    batch = db_fs.batch()
    synced_ids = []

    for trade in chunk:
        try:
            code = trade["code"]
            source_time_str = trade["source_updated_at"]
            
            doc_id = source_time_str.replace(" ", "_").replace(":", "-")
            source_time_dt = datetime.strptime(source_time_str, "%Y-%m-%d %H:%M:%S")

            latest_ref = db_fs.collection("gold_prices").document(code)
            batch.set(latest_ref, {
                "code": code,
                "description": trade["description"] or "",
                "price_buy": float(trade["price_buy"]),
                "price_sell": float(trade["price_sell"]),
                "source_updated_at": source_time_dt,
                "updated_at": firestore.SERVER_TIMESTAMP
            })

            history_ref = latest_ref.collection("history").document(doc_id)
            batch.set(history_ref, {
                "price_buy": float(trade["price_buy"]),
                "price_sell": float(trade["price_sell"]),
                "source_updated_at": source_time_dt,
                "created_at": firestore.SERVER_TIMESTAMP
            })

            synced_ids.append(trade["id"])
        except Exception as fe:
            print(f"Hazırlama hatası (ID: {trade['id']}): {fe}")

    try:
        batch.commit()
        if synced_ids:
            placeholders = ",".join("?" for _ in synced_ids)
            cur.execute(f"UPDATE trades SET synced_to_firebase = 1 WHERE id IN ({placeholders})", synced_ids)
            conn.commit()
            
        total_synced += len(synced_ids)
        print(f"... 10'luk paket gitti. Toplam {total_synced}/{len(trades)} kayıt başarıyla aktarıldı.")
    except Exception as commit_error:
        print(f"Firebase Yazma Hatası: {commit_error}. İşlem durduruluyor.")
        break

    time.sleep(5)

conn.close()
print(f"\nİŞLEM TAMAMLANDI. Bu partide toplam {total_synced} adet kayıt Firebase'e aktarıldı.")
