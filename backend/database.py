import os
import time
import pyodbc
from dotenv import load_dotenv

load_dotenv()


def get_db_connection(retries: int = 3, delay: float = 2.0):
    server = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DATABASE")
    username = os.getenv("SQL_USERNAME")
    password = os.getenv("SQL_PASSWORD")

    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{server},1433;"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return pyodbc.connect(connection_string)
        except pyodbc.OperationalError as e:
            last_error = e
            if attempt < retries:
                time.sleep(delay)

    raise last_error