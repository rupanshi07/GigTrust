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

print("--- Gigs ---")
for row in cursor.execute("SELECT gig_id, client_id, title, budget, status FROM Gigs"):
    print(row)

print("\n--- Bids ---")
for row in cursor.execute("SELECT bid_id, gig_id, freelancer_id, bid_amount, status FROM Bids"):
    print(row)

print("\n--- Transactions ---")
for row in cursor.execute("SELECT transaction_id, escrow_id, sender_id, receiver_id, amount, transaction_type, created_at FROM Transactions"):
    print(row)

cursor.close()
conn.close()