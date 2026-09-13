import sys, pyodbc, os, re
from dotenv import load_dotenv

load_dotenv()

if len(sys.argv) != 2:
    print("Usage: python run_sql_file.py <path-to-sql-file>")
    sys.exit(1)

sql_path = sys.argv[1]

conn_str = (
    f"Driver={{ODBC Driver 18 for SQL Server}};"
    f"Server=tcp:{os.getenv('SQL_SERVER')},1433;"
    f"Database={os.getenv('SQL_DATABASE')};"
    f"Uid={os.getenv('SQL_USERNAME')};"
    f"Pwd={os.getenv('SQL_PASSWORD')};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=no;"
)

with open(sql_path, "r", encoding="utf-8") as f:
    script = f.read()

# Split on explicit GO batch separators
go_batches = re.split(r"^\s*GO\s*$", script, flags=re.MULTILINE | re.IGNORECASE)

# Further split on CREATE PROCEDURE/FUNCTION boundaries AND on "-- ===...===" banner lines
split_pattern = r"(?=^\s*CREATE\s+(?:OR\s+ALTER\s+)?(?:PROCEDURE|PROC|FUNCTION)\s)|(?=^--\s*=+\s*$)"

batches = []
for gb in go_batches:
    parts = re.split(split_pattern, gb, flags=re.MULTILINE | re.IGNORECASE)
    batches.extend(parts)

conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()

for i, batch in enumerate(batches):
    batch = batch.strip()
    if not batch:
        continue
    try:
        cursor.execute(batch)
        print(f"Batch {i+1}: OK")
    except Exception as e:
        print(f"Batch {i+1}: FAILED — {e}")

conn.close()
print("Done.")