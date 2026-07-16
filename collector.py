from datetime import datetime
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import os
import time
from decouple import config

URL = "https://static.altinkaynak.com/public/Gold"
LOG_FILE = "collector.log"

# -------- LOG CONFIG --------
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# -------- HELPERS --------
def parse_price(val: str) -> float:
    return float(val.replace(".", "").replace(",", "."))

def parse_datetime(val: str) -> datetime:
    return datetime.strptime(val, "%d.%m.%Y %H:%M:%S")

def get_db_connection():
    return psycopg2.connect(
        host=config("DB_HOST", default="localhost"), # Use localhost for direct local connection
        port=config("DB_PORT", default=5432, cast=int),
        database=config("DB_NAME", default="gold_db"),
        user=config("DB_USER", default="gold_user"),
        password=config("DB_PASSWORD", default="gold_password")
    )

def init_db():
    retries = 5
    while retries > 0:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(50) NOT NULL,
                    description VARCHAR(255),
                    price_buy NUMERIC(15, 4) NOT NULL,
                    price_sell NUMERIC(15, 4) NOT NULL,
                    source_updated_at TIMESTAMP NOT NULL,
                    synced_to_firebase BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_code_updated UNIQUE (code, source_updated_at)
                );
            """)
            conn.commit()
            cur.close()
            conn.close()
            logging.info("PostgreSQL tablosu başarıyla doğrulandı/oluşturuldu.")
            print("PostgreSQL tablosu doğrulandı.")
            break
        except Exception as e:
            retries -= 1
            logging.warning(f"PostgreSQL bağlantı hatası, tekrar deneniyor ({retries} deneme kaldı): {e}")
            print(f"Bağlantı hatası, tekrar deneniyor ({retries} deneme kaldı): {e}")
            time.sleep(5)

# -------- DATA COLLECTION --------
def collect_data():
    logging.info("Data collection script başlatıldı")
    print("Veriler çekiliyor...")

    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        logging.info(f"{len(data)} adet veri alındı")
        print(f"Altınkaynak API'den {len(data)} adet veri çekildi.")
    except Exception as e:
        logging.error(f"Veri çekilemedi: {e}")
        print(f"Hata: Veri çekilemedi: {e}")
        return

    try:
        conn = get_db_connection()
        cur = conn.cursor()
    except Exception as e:
        logging.error(f"Veritabanına bağlanılamadı: {e}")
        print(f"Veritabanı bağlantı hatası: {e}")
        return

    inserted = 0

    for item in data:
        try:
            code = item["Kod"]
            source_time = parse_datetime(item["GuncellenmeZamani"])

            cur.execute("""
                INSERT INTO trades (
                    code,
                    description,
                    price_buy,
                    price_sell,
                    source_updated_at
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (code, source_updated_at) DO NOTHING
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
                    f"KAYIT | code={code} | source_time={source_time} | Postgres'e yazıldı"
                )

        except Exception as e:
            logging.error(
                f"HATA | code={item.get('Kod')} | {e}"
            )

    conn.commit()
    cur.close()
    conn.close()

    logging.info(f"Script tamamlandı | {inserted} yeni kayıt eklendi")
    print(f"Bitti. {inserted} yeni kayıt Postgres'e eklendi.")

if __name__ == "__main__":
    init_db()
    collect_data()