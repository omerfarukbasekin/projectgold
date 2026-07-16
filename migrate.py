import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from decouple import config
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

SQLITE_DB = "/home/farukbasekin51/gold-ingestor/app.db"

def get_sqlite_connection():
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_postgres_connection():
    return psycopg2.connect(
        host=config("DB_HOST", default="localhost"), # Use localhost for direct local connection
        port=config("DB_PORT", default=5432, cast=int),
        database=config("DB_NAME", default="gold_db"),
        user=config("DB_USER", default="gold_user"),
        password=config("DB_PASSWORD", default="gold_password")
    )

def migrate_data():
    sqlite_conn = None
    postgres_conn = None
    try:
        sqlite_conn = get_sqlite_connection()
        sqlite_cursor = sqlite_conn.cursor()

        postgres_conn = get_postgres_connection()
        postgres_cursor = postgres_conn.cursor()

        # Fetch data from SQLite
        sqlite_cursor.execute("SELECT code, price_buy, price_sell, created_at FROM trades")
        rows = sqlite_cursor.fetchall()
        logging.info(f"Found {len(rows)} records in SQLite for migration.")

        inserted_count = 0
        for row in rows:
            try:
                # Assuming SQLite columns: code, price_buy, price_sell, created_at
                code = row["code"]
                price_buy = float(row["price_buy"])
                price_sell = float(row["price_sell"])
                created_at = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")

                # For 'description', we can use a placeholder or derive it if possible
                description = f"Gold {code}" # Placeholder
                source_updated_at = created_at # Assuming created_at is the source_updated_at for legacy data

                postgres_cursor.execute("""
                    INSERT INTO trades (
                        code, description, price_buy, price_sell,
                        source_updated_at, synced_to_firebase, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (code, source_updated_at) DO NOTHING;
                """, (
                    code, description, price_buy, price_sell,
                    source_updated_at, False, created_at
                ))

                if postgres_cursor.rowcount == 1:
                    inserted_count += 1

            except Exception as e:
                logging.error(f"Error migrating row {row.get('code')}: {e}")

        postgres_conn.commit()
        logging.info(f"Migration complete. {inserted_count} new records inserted into PostgreSQL.")

    except Exception as e:
        logging.error(f"Migration failed: {e}")
    finally:
        if sqlite_conn:
            sqlite_conn.close()
        if postgres_conn:
            postgres_conn.close()

if __name__ == "__main__":
    migrate_data()