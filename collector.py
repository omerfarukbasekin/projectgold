import requests
import sqlite3
import logging
import time
from datetime import datetime

URL = "https://static.altinkaynak.com/public/Gold"
LOG_FILE = "collector.log"
DB_FILE = "data/app.db"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def parse_price(val: str) -> float:
    return float(val.replace(".", "").replace(",", "."))

def parse_datetime(val: str) -> str:
    dt = datetime.strptime(val, "%d.%m.%Y %H:%M:%S")
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
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
    conn.close()
    logging.info("SQLite tablosu doğrulandı.")

def collect_data():
    logging.info("Data collection script başlatıldı")

    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        logging.info(f"{len(data)} adet veri alındı")
    except Exception as e:
        logging.error(f"Veri çekilemedi: {e}")
        print(f"API Hatası: {e}")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    inserted = 0

    for item in data:
        try:
            code = item["Kod"]
            source_time = parse_datetime(item["GuncellenmeZamani"])

            cur.execute("""
                INSERT OR IGNORE INTO trades (
                    code, description, price_buy, price_sell, source_updated_at
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
                logging.info(f"KAYIT | code={code} | DB'ye yazıldı")

        except Exception as e:
            logging.error(f"HATA | code={item.get('Kod')} | {e}")

    conn.commit()
    conn.close()
    print(f"Bitti. {inserted} yeni kayıt SQLite'a eklendi.")

if __name__ == "__main__":
    init_db()
    collect_data()
