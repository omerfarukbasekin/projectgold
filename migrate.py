import sqlite3
import csv
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

SQLITE_DB_PATH = "/home/farukbasekin51/gold-ingestor/app.db"
OUTPUT_CSV_FILE = "/home/farukbasekin51/gold-ingestor/trades_export.csv"

def export_to_csv():
    sqlite_conn = None
    try:
        if not os.path.exists(SQLITE_DB_PATH):
            logging.error(f"SQLite database not found at {SQLITE_DB_PATH}")
            print(f"Error: SQLite database not found at {SQLITE_DB_PATH}")
            return

        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_conn.row_factory = sqlite3.Row # Allows access by column name
        sqlite_cursor = sqlite_conn.cursor()

        sqlite_cursor.execute("SELECT created_at, source_updated_at, code, description, price_buy, price_sell FROM trades")
        rows = sqlite_cursor.fetchall()

        if not rows:
            logging.info("No data found in SQLite 'trades' table to export.")
            print("No data found in SQLite 'trades' table to export.")
            return

        # Get column names for CSV header
        column_names = rows[0].keys()

        with open(OUTPUT_CSV_FILE, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(column_names) # Write header
            for row in rows:
                csv_writer.writerow(list(row)) # Write row data
        
        logging.info(f"Successfully exported {len(rows)} records to {OUTPUT_CSV_FILE}")
        print(f"Success: Exported {len(rows)} records to {OUTPUT_CSV_FILE}")

    except Exception as e:
        logging.error(f"Error during CSV export: {e}")
        print(f"Error during CSV export: {e}")
    finally:
        if sqlite_conn:
            sqlite_conn.close()

if __name__ == "__main__":
    export_to_csv()
