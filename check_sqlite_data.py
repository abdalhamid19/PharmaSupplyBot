import sqlite3

conn = sqlite3.connect('data/manual_review/manual_review.sqlite3')
cur = conn.cursor()

print('Total records:', cur.execute('SELECT COUNT(*) FROM manual_review_decisions').fetchone()[0])
print('\nSample records:')
cur.execute('SELECT item_code, item_name, approved, correct_store_product_id, correct_product_name FROM manual_review_decisions LIMIT 5')
for row in cur.fetchall():
    print(row)

print('\nSchema:')
cur.execute('PRAGMA table_info(manual_review_decisions)')
for col in cur.fetchall():
    print(col)

conn.close()
