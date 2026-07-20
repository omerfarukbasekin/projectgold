import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime
import sys

DB_FILE = "app.db"

# 1. Firebase Başlatma
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

# 2. SQLite'dan Veri Çekme
print(f"\n'{DB_FILE}' dosyasından veriler okunuyor...")
if not os.path.exists(DB_FILE):
    print("HATA: app.db dosyası bulunamadı!")
    sys.exit(1)

conn = sqlite3.connect(DB_FILE)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# TÜM dataları çek
cur.execute("""
    SELECT id, code, description, price_buy, price_sell, source_updated_at 
    FROM trades 
    ORDER BY source_updated_at ASC
""")
all_trades = cur.fetchall()

if not all_trades:
    print("Veritabanında hiç kayıt bulunamadı.")
    conn.close()
    sys.exit(0)

print(f"Toplam {len(all_trades)} adet kayıt bulundu. Firebase'e aktarım başlıyor...")

# 3. Batch ile Firebase'e Gönderme
batch = db_fs.batch()
ops_count = 0
total_synced = 0

for trade in all_trades:
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

        ops_count += 2
        total_synced += 1

        if ops_count >= 490:
            batch.commit()
            print(f"... {total_synced} kayıt işlendi (Batch commit edildi).")
            batch = db_fs.batch()
            ops_count = 0

    except Exception as fe:
        print(f"Hazırlama hatası (ID: {trade['id']}): {fe}")

if ops_count > 0:
    batch.commit()

print("\nFirebase aktarımı bitti. SQLite güncelleniyor...")
cur.execute("UPDATE trades SET synced_to_firebase = 1")
conn.commit()
conn.close()

print(f"\nBAŞARILI: Toplam {total_synced} kayıt Firebase'e gönderildi ve SQLite'ta işaretlendi.")
