from datetime import datetime
import requests
import sqlite3
import logging
import os
import firebase_admin
from firebase_admin import credentials, firestore
from decouple import config

URL = "https://static.altinkaynak.com/public/Gold"
DB = "app.db"
LOG_FILE = "collector.log"

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
    service_account_path = "./service-account.json"
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

# -------- HELPERS --------
def parse_price(val: str) -> float:
    return float(val.replace(".", "").replace(",", "."))

def parse_datetime(val: str) -> str:
    return datetime.strptime(
        val, "%d.%m.%Y %H:%M:%S"
    ).strftime("%Y-%m-%d %H:%M:%S")

# -------- DATA COLLECTION & SYNC --------
def collect_and_sync():
    logging.info("Script başlatıldı")
    print("Veriler çekiliyor ve senkronize ediliyor...")

    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        logging.info(f"{len(data)} adet veri alındı")
    except Exception as e:
        logging.error(f"Veri çekilemedi: {e}")
        print(f"Hata: Veri çekilemedi: {e}")
        return

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Ensure trades table exists in SQLite with synced_to_firebase column
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            description TEXT,
            price_buy REAL NOT NULL,
            price_sell REAL NOT NULL,
            source_updated_at TEXT NOT NULL,
            synced_to_firebase INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_code_updated UNIQUE (code, source_updated_at)
        );
    """)
    conn.commit()

    inserted = 0
    synced = 0

    # 1. Insert new data into SQLite
    for item in data:
        try:
            code = item["Kod"]
            source_time = parse_datetime(item["GuncellenmeZamani"])

            cur.execute("""
                INSERT OR IGNORE INTO trades (
                    code,
                    description,
                    price_buy,
                    price_sell,
                    source_updated_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                code,
                item.get("Aciklama"),
                parse_price(item["Alis"]),
                parse_price(item["Satis"]),
                source_time
            ))

            if cur.rowcount == 1:
                inserted += 1
                logging.info(
                    f"KAYIT | code={code} | source_time={source_time} | DB'ye yazıldı"
                )

        except Exception as e:
            logging.error(
                f"HATA | code={item.get('Kod')} | {e}"
            )

    conn.commit()
    print(f"SQLite'a {inserted} yeni kayıt eklendi.")

    # 2. Sync unsynced data from SQLite to Firebase Firestore
    if db_fs is not None:
        try:
            # Select unsynced trades
            cur.execute("""
                SELECT id, code, description, price_buy, price_sell, source_updated_at 
                FROM trades 
                WHERE synced_to_firebase = 0
                ORDER BY source_updated_at ASC
            """)
            unsynced_trades = cur.fetchall()

            if unsynced_trades:
                print(f"{len(unsynced_trades)} adet yeni kayıt Firestore'a senkronize ediliyor...")
                logging.info(f"{len(unsynced_trades)} yeni kayıt Firestore'a senkronize ediliyor.")

                synced_ids = []

                for trade in unsynced_trades:
                    try:
                        trade_id = trade[0]
                        code = trade[1]
                        description = trade[2]
                        price_buy = trade[3]
                        price_sell = trade[4]
                        source_time_str = trade[5]

                        # Document ID format for history (e.g. 2026-07-08_14-30-00)
                        doc_id = source_time_str.replace(" ", "_").replace(":", "-")

                        # Parse source_time_str to datetime for Firestore
                        source_time_dt = datetime.strptime(source_time_str, "%Y-%m-%d %H:%M:%S")

                        # 1. Update the latest price document for this code
                        latest_ref = db_fs.collection("gold_prices").document(code)
                        latest_ref.set({
                            "code": code,
                            "description": description or "",
                            "price_buy": float(price_buy),
                            "price_sell": float(price_sell),
                            "source_updated_at": source_time_dt,
                            "updated_at": firestore.SERVER_TIMESTAMP
                        })

                        # 2. Add to history subcollection
                        history_ref = latest_ref.collection("history").document(doc_id)
                        history_ref.set({
                            "price_buy": float(price_buy),
                            "price_sell": float(price_sell),
                            "source_updated_at": source_time_dt,
                            "created_at": firestore.SERVER_TIMESTAMP
                        })

                        synced_ids.append(trade_id)
                    except Exception as fe:
                        logging.error(f"Firestore yazma hatası (ID: {trade[0]}): {fe}")
                        print(f"Firestore yazma hatası (ID: {trade[0]}): {fe}")

                # Batch update SQLite rows as synced_to_firebase = 1
                if synced_ids:
                    # SQLite doesn't support ANY(%s) with tuple parameter binding easily, so we use a loop or in clause
                    placeholders = ','.join('?' for _ in synced_ids)
                    cur.execute(f"""
                        UPDATE trades 
                        SET synced_to_firebase = 1 
                        WHERE id IN ({placeholders})
                    """, synced_ids)
                    conn.commit()
                    synced = len(synced_ids)
                    logging.info(f"{synced} adet kayıt SQLite'ta 'synced_to_firebase = 1' olarak güncellendi.")
                    print(f"{synced} adet kayıt başarıyla Firestore'a senkronize edildi.")
            else:
                print("Senkronize edilecek yeni veri yok.")
        except Exception as e:
            logging.error(f"Senkronizasyon sırasında genel hata: {e}")
            print(f"Senkronizasyon hatası: {e}")
    else:
        logging.warning("Firebase Firestore bağlantısı olmadığı için senkronizasyon atlandı.")

    conn.close()
    logging.info(f"Script tamamlandı | {inserted} yeni kayıt eklendi, {synced} senkronize edildi")
    print("İşlem tamamlandı.")

if __name__ == "__main__":
    collect_and_sync()
