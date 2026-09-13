import pyodbc, os
from dotenv import load_dotenv

load_dotenv()

conn_str = (
    f"Driver={{ODBC Driver 18 for SQL Server}};"
    f"Server=tcp:{os.getenv('SQL_SERVER')},1433;"
    f"Database={os.getenv('SQL_DATABASE')};"
    f"Uid={os.getenv('SQL_USERNAME')};"
    f"Pwd={os.getenv('SQL_PASSWORD')};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=no;"
)

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()
cursor.execute("SELECT full_name, email, balance FROM Users WHERE email IN ('alice@example.com', 'bob@example.com')")
for row in cursor.fetchall():
    print(row)
cursor.close()
conn.close()