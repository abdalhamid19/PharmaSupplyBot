import sys
import os
import csv
import psycopg2
from pathlib import Path

# Add project root to path so we can import src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.core.manual_review_hints import hint_key

DB_USER = "abdalhamid"
DB_PASS = "_wJpvGkeXrpD4_mD8jAhYg"
DB_HOST = "mahrousdb-27867.j77.aws-eu-central-1.cockroachlabs.cloud"
DB_PORT = 26257
DB_NAME = "defaultdb"

def create_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS manual_review_decisions (
                item_code_key TEXT NOT NULL,
                item_name_key TEXT NOT NULL,
                item_code TEXT NOT NULL,
                item_name TEXT NOT NULL,
                approved INT NOT NULL,
                manual_decision TEXT NOT NULL DEFAULT '',
                correct_store_product_id TEXT NOT NULL DEFAULT '',
                correct_product_name TEXT NOT NULL DEFAULT '',
                correct_product_name_ar TEXT NOT NULL DEFAULT '',
                correct_query TEXT NOT NULL DEFAULT '',
                run_id TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (item_code_key, item_name_key)
            )
        """)
        conn.commit()
        print("Table 'manual_review_decisions' created/verified.")

def import_csv(conn, csv_path):
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        
        insert_query = """
            INSERT INTO manual_review_decisions (
                item_code_key, item_name_key, item_code, item_name,
                approved, manual_decision, correct_product_name, correct_product_name_ar
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (item_code_key, item_name_key) DO UPDATE SET
                approved = EXCLUDED.approved,
                manual_decision = EXCLUDED.manual_decision,
                correct_product_name = EXCLUDED.correct_product_name,
                correct_product_name_ar = EXCLUDED.correct_product_name_ar,
                updated_at = CURRENT_TIMESTAMP
        """
        
        count = 0
        with conn.cursor() as cur:
            for row in reader:
                code = row["item_code"]
                name = row["item_name"]
                code_key, name_key = hint_key(code, name)
                
                decision = row["decision"]
                approved = 1 if decision in ("approved_match", "auto_matched") else 0
                
                cur.execute(insert_query, (
                    code_key, name_key, code, name,
                    approved, decision, row.get("correct_product_name", ""), row.get("correct_product_name_ar", "")
                ))
                count += 1
            conn.commit()
        print(f"Successfully imported {count} rows.")

if __name__ == "__main__":
    conn_str = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
    try:
        conn = psycopg2.connect(conn_str)
        create_table(conn)
        import_csv(conn, "saved_corrected_items(2).csv")
        conn.close()
    except Exception as e:
        print(f"Failed to connect or import: {e}")
