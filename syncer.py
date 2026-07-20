import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore
import logging
import os
from datetime import datetime

LOG_FILE = "syncer.log"
DB_FILE = "app.db" # Eski sisteme uyumlu path

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

db_fs = None
try:
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "projectgold-6b3bf")
    service_account_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "service-account.json")
    if os.path.exists(service_account_path):
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, options={"projectId": project_id})
        logging.info("Firebase Service Account ile başlatıldı.")
    else:
        firebase_admin.initialize_app(options={"projectId": project_id})
        logging.info("Firebase default credentials (ADC) ile başlatıldı.")
    db_fs = firestore.client()
except Exception as e:
    logging.error(f"Firebase başlatılamadı: {e}")
    print(f"Firebase başlatılamadı (HATA): {e}")

def sync_to_firebase():
    if db_fs is None:
        print("Firebase bağlantısı yok, çıkılıyor.")
        return

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT id, code, description, price_buy, price_sell, source_updated_at 
        FROM trades 
        WHERE synced_to_firebase = 0
        ORDER BY source_updated_at ASC
    """)
    unsynced_trades = cur.fetchall()

    if not unsynced_trades:
        conn.close()
        return

    # Firestore yazmalarını atomik yapmak için Batch kullanıyoruz (Maks 500 işlem)
    batch = db_fs.batch()
    synced_ids = []
    ops_count = 0

    for trade in unsynced_trades:
        try:
            code = trade["code"]
            source_time_str = trade["source_updated_at"]
            
            # Idempotent doküman IDsi: aynı veri tekrar gelse bile çift kayıt oluşmaz.
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
            ops_count += 2

            # Batch limiti 500dür. Sınır aşılırsa batchi commit edip yenisini açıyoruz.
            if ops_count >= 490:
                batch.commit()
                batch = db_fs.batch()
                ops_count = 0

        except Exception as fe:
            logging.error(f"Firestore hazırlama hatası (ID: {trade["id"]}): {fe}")

    # Kalan son batchi gönder
    if ops_count > 0:
        try:
            batch.commit()
            logging.info(f"{len(synced_ids)} adet kayıt başarıyla Firestorea yazıldı (Batch Commit).")
        except Exception as e:
            logging.error(f"Batch yazma sırasında hata: {e}")
            conn.close()
            return

    # Sadece Firebasee başarıyla (hata fırlatmadan) yazılanları SQLite ta işaretle
    if synced_ids:
        # SQLite IN clause sınırı (999 değişken) aşılmasın diye 500 lük gruplar yapıyoruz
        chunk_size = 500
        for i in range(0, len(synced_ids), chunk_size):
            chunk = synced_ids[i:i + chunk_size]
            placeholders = ",".join("?" for _ in chunk)
            cur.execute(f"""
                UPDATE trades 
                SET synced_to_firebase = 1 
                WHERE id IN ({placeholders})
            """, chunk)
        conn.commit()
        print(f"{len(synced_ids)} kayıt başarıyla Firestorea yazıldı ve SQLite üzerinde işaretlendi.")

    conn.close()

if __name__ == "__main__":
    sync_to_firebase()
