# CockroachDB Cloud Database Setup

## Overview
This project now uses **CockroachDB Cloud** as a shared, synchronized database for manual review corrections. All team members connect to the same cloud database, ensuring data consistency and enabling real-time collaboration.

## Cloud Database Details

- **Cluster Name:** mahrousdb
- **Host:** mahrousdb-27867.j77.aws-eu-central-1.cockroachlabs.cloud
- **Port:** 26257
- **Database:** defaultdb
- **Region:** AWS EU (Central Frankfurt)
- **Version:** CockroachDB CCL v25.4.10

## Connection Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and update with your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
DB_HOST=mahrousdb-27867.j77.aws-eu-central-1.cockroachlabs.cloud
DB_PORT=26257
DB_NAME=defaultdb
DB_USER=abdalhamid
DB_PASSWORD=_wJpvGkeXrpD4_mD8jAhYg
DB_SSLMODE=allow
```

### 3. Test Connection

```python
from src.core.database import init_db

# Initialize database
db_manager = init_db()

# Test connection
if db_manager.test_connection():
    print("✓ Connected to CockroachDB Cloud")
else:
    print("✗ Connection failed")
```

## Usage in Code

### Initialize on Startup

```python
from src.core.database import init_db, close_db

# Application startup
db = init_db(password="your-password")

# ... application code ...

# Application shutdown
close_db()
```

### Query Database

```python
from src.core.database import get_db_manager

db = get_db_manager()

# Execute SELECT query
results = db.execute_query(
    "SELECT * FROM manual_review_corrections WHERE status = %s",
    ("pending",)
)

# Execute INSERT/UPDATE/DELETE
affected_rows = db.execute_update(
    "INSERT INTO manual_review_corrections (item_id, correction) VALUES (%s, %s)",
    (123, "Updated value")
)
```

### Using Context Manager

```python
from src.core.database import get_db_manager

db = get_db_manager()

with db.get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM manual_review_corrections")
    count = cur.fetchone()[0]
    cur.close()
    print(f"Total corrections: {count}")
```

## Benefits of Cloud Database

✅ **Centralized:** Single source of truth for all team members  
✅ **Real-time Sync:** Changes visible immediately to everyone  
✅ **Automatic Backup:** CockroachDB handles replication & redundancy  
✅ **Scalable:** Handles growing data without local performance impact  
✅ **Accessible:** Team members can access from anywhere  
✅ **Secure:** SSL encrypted connections  

## Migration from SQLite

Previous manual review data was stored in `manual_review.sqlite3` locally. This has been migrated to the cloud:

1. **Local SQLite** (`manual_review.sqlite3`): Kept for backward compatibility
2. **Cloud PostgreSQL** (CockroachDB): New primary storage for collaborative corrections

To migrate existing SQLite data to CockroachDB:

```python
import sqlite3
import psycopg2
from src.core.database import get_db_manager

# Read from local SQLite
sqlite_conn = sqlite3.connect("manual_review.sqlite3")
sqlite_cur = sqlite_conn.cursor()
sqlite_cur.execute("SELECT * FROM corrections")
rows = sqlite_cur.fetchall()

# Write to cloud database
db = get_db_manager()
for row in rows:
    db.execute_update(
        "INSERT INTO corrections (col1, col2, ...) VALUES (%s, %s, ...)",
        row
    )
```

## Security Notes

⚠️ **Never commit `.env` file with real credentials to Git**  
- `.env` is in `.gitignore`
- Use `.env.example` as template with placeholder values
- Team members should get credentials from secure channel (password manager, etc.)

## Troubleshooting

### Connection Refused
```
psycopg2.OperationalError: connection to server ... failed
```
- Check internet connection
- Verify DB_HOST and DB_PORT are correct
- Ensure IP address is whitelisted (if applicable)

### SSL Certificate Error
```
SSL error: certificate verify failed
```
- Ensure `DB_SSLMODE=allow` in .env (or use `sslmode=verify-full` with proper certs)
- This is handled by default in the `database.py` module

### Authentication Failed
```
FATAL: password authentication failed for user "abdalhamid"
```
- Verify DB_PASSWORD is correct
- Check DB_USER is "abdalhamid"

## Useful SQL Commands

```sql
-- List all tables
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Check database size
SELECT pg_database.datname, pg_size_pretty(pg_database.pg_database_size(pg_database.datname)) 
FROM pg_database;

-- View active connections
SELECT * FROM crdb_internal.node_runtime_info;
```

## Next Steps

1. **Create Schema:** Define tables for `manual_review_corrections`, `candidates`, etc.
2. **Set Up ORM:** Consider using SQLAlchemy for easier database interaction
3. **Add Migrations:** Use Alembic for schema version control
4. **Monitor Performance:** Use CockroachDB console for metrics and insights
