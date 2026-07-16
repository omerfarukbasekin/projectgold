  GNU nano 7.2                                                                            runner.sh                                                                                     
#!/bin/sh

while true; do
  echo "[$(date)] collector çalışıyor..."
  python app.py
  sleep 600
done




from datetime import datetime
import requests
import sqlite3
import logging
import os

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

# -------- HELPERS --------
def parse_price(val: str) -> float:
    return float(val.replace(".", "").replace(",", "."))

def parse_datetime(val: str) -> str:
    return datetime.strptime(
        val, "%d.%m.%Y %H:%M:%S"
    ).strftime("%Y-%m-%d %H:%M:%S")

# -------- MAIN --------
def main():
    logging.info("Script başlatıldı")

    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        logging.info(f"{len(data)} adet veri alındı")
    except Exception as e:
        logging.error(f"Veri çekilemedi: {e}")
        return

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    inserted = 0

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
    conn.close()

    logging.info(f"Script tamamlandı | {inserted} yeni kayıt eklendi")

if __name__ == "__main__":
    main()


    bunlar eskiden çalışanlar stabele çalışıyordu bunlar gibi yapamazmıyız