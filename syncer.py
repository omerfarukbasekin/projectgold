from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import firebase_admin
from firebase_admin import credentials, firestore
import logging
import time
import os
from decouple import config

LOG_FILE = "syncer.log"

# -------- LOG CONFIG --------
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# -------- FIREBASE INITIALIZATION --------
db_fs = None
try:
    # Use Certificate file if available, otherwise fallback to project ID (ADC)
    service_account_path = "service-account.json"
    project_id = config("FIREBASE_PROJECT_ID", default="projectgold-6b3bf")
    
    if os.path.exists(service_account_path):
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, options={"projectId": project_id})
        logging.info("Firebase Admin Service Account ile başlatıldı.")
        print("Firebase Admin Service Account ile başlatıldı.")
    else:
        firebase_admin.initialize_app(options={"projectId": project_id})
        logging.info("Firebase Admin default/environment credentials ile başlatıldı.")
        print("Firebase Admin default credentials ile başlatıldı.")
        
    db_fs = firestore.client()
    logging.info("Firebase Firestore bağlantısı başarıyla kuruldu.")
    print("Firebase Firestore bağlantısı kuruldu.")
except Exception as e:
    logging.error(f"Firebase Firestore başlatılamadı: {e}")
    print(f"Hata: Firebase Firestore başlatılamadı: {e}")

# -------- DB CONNECTION --------
def get_db_connection():
    return psycopg2.connect(
        host=config("DB_HOST", default="db"),
        port=config("DB_PORT", default=5432, cast=int),
        database=config("DB_NAME", default="gold_db"),
        user=config("DB_USER", default="gold_user"),
        password=config("DB_PASSWORD", default="gold_password")
    )

# -------- SYNC LOGIC --------
def sync_to_firebase():
    if db_fs is None:
        logging.error("Firebase Firestore bağlantısı mevcut değil. Senkronizasyon iptal edildi.")
        print("Hata: Firebase bağlantısı bulunmadığından senkronizasyon yapılamıyor.")
        return

    logging.info("Senkronizasyon işlemi başlatıldı...")
    print("Postgresql'den yeni veriler okunuyor...")

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Select unsynced trades
        cur.execute("""
            SELECT id, code, description, price_buy, price_sell, source_updated_at 
            FROM trades 
            WHERE synced_to_firebase = FALSE
            ORDER BY source_updated_at ASC
        """)
        unsynced_trades = cur.fetchall()
        
        if not unsynced_trades:
            logging.info("Senkronize edilecek yeni veri bulunamadı.")
            print("Senkronize edilecek yeni veri yok.")
            cur.close()
            conn.close()
            return

        print(f"{len(unsynced_trades)} adet yeni kayıt Firestore'a senkronize ediliyor...")
        logging.info(f"{len(unsynced_trades)} yeni kayıt Firestore'a senkronize ediliyor.")

        synced_ids = []

        # Process each trade and write to Firestore
        for trade in unsynced_trades:
            try:
                code = trade["code"]
                source_time_dt = trade["source_updated_at"]
                
                # Document ID format for history (e.g. 2026-07-08_14-30-00)
                doc_id = source_time_dt.strftime("%Y-%m-%d_%H-%M-%S")

                # 1. Update the latest price document for this code
                latest_ref = db_fs.collection("gold_prices").document(code)
                latest_ref.set({
                    "code": code,
                    "description": trade.get("description") or "",
                    "price_buy": float(trade["price_buy"]),
                    "price_sell": float(trade["price_sell"]),
                    "source_updated_at": source_time_dt,
                    "updated_at": firestore.SERVER_TIMESTAMP
                })

                # 2. Add to history subcollection
                history_ref = latest_ref.collection("history").document(doc_id)
                history_ref.set({
                    "price_buy": float(trade["price_buy"]),
                    "price_sell": float(trade["price_sell"]),
                    "source_updated_at": source_time_dt,
                    "created_at": firestore.SERVER_TIMESTAMP
                })

                synced_ids.append(trade["id"])
            except Exception as fe:
                logging.error(f"Firestore yazma hatası (ID: {trade['id']}): {fe}")
                print(f"Firestore yazma hatası (ID: {trade['id']}): {fe}")

        # Batch update PostgreSQL rows as synced_to_firebase = TRUE
        if synced_ids:
            cur.execute("""
                UPDATE trades 
                SET synced_to_firebase = TRUE 
                WHERE id = ANY(%s)
            """, (synced_ids,))
            conn.commit()
            logging.info(f"{len(synced_ids)} adet kayıt Postgres'te 'synced_to_firebase = TRUE' olarak güncellendi.")
            print(f"{len(synced_ids)} adet kayıt başarıyla Firestore'a senkronize edildi ve işaretlendi.")

        cur.close()
        conn.close()

    except Exception as e:
        logging.error(f"Senkronizasyon sırasında genel hata: {e}")
        print(f"Senkronizasyon hatası: {e}")

if __name__ == "__main__":
    # Run once when called
    sync_to_firebase()
