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
cursor.execute("UPDATE Users SET balance = 10000 WHERE email = 'alice@example.com'")
conn.commit()
print("Balance updated. Rows affected:", cursor.rowcount)
cursor.close()
conn.close()