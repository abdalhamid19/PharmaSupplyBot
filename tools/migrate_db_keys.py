import sqlite3
from pathlib import Path
from src.core.manual_review_hints import _clean_name

def migrate():
    db_path = Path("data") / "manual_review" / "manual_review.sqlite3"
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
        
    print("Migrating manual review decisions keys...")
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT item_code_key, item_name_key, item_name FROM manual_review_decisions").fetchall()
        
        updated_count = 0
        for item_code_key, old_item_name_key, item_name in rows:
            new_item_name_key = _clean_name(item_name).upper()
            if old_item_name_key != new_item_name_key:
                try:
                    conn.execute(
                        "UPDATE manual_review_decisions SET item_name_key = ? WHERE item_code_key = ? AND item_name_key = ?",
                        (new_item_name_key, item_code_key, old_item_name_key)
                    )
                    updated_count += 1
                except sqlite3.IntegrityError:
                    print(f"Integrity error migrating {item_code_key}. Likely duplicate. Deleting old row.")
                    conn.execute("DELETE FROM manual_review_decisions WHERE item_code_key = ? AND item_name_key = ?", 
                                 (item_code_key, old_item_name_key))
                    
        conn.commit()
        print(f"Successfully migrated {updated_count} rows.")

if __name__ == "__main__":
    migrate()
