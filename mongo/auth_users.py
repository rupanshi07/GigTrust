import os
import base64
import hashlib
import hmac
import jwt
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError

from backend.database import get_db_connection

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "gigtrust")
AUTH_COLLECTION = os.getenv("MONGO_AUTH_COLLECTION", "users")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@gigtrust.com").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

# Maps the public-facing role names used at signup to the SQL Users.role
# CHECK constraint values ('CLIENT', 'FREELANCER', 'ADMIN').
ROLE_TO_SQL = {
    "user": "CLIENT",
    "freelancer": "FREELANCER",
}


def _get_collection():
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI is not configured.")

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")

    collection = client[MONGO_DATABASE][AUTH_COLLECTION]
    collection.create_index([("email", ASCENDING)], unique=True)
    return client, collection


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    iterations = 200_000
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )

    return "$".join(
        [
            "pbkdf2_sha256",
            str(iterations),
            base64.b64encode(salt).decode("utf-8"),
            base64.b64encode(derived).decode("utf-8"),
        ]
    )


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_b64, hash_b64 = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False

        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )

        return hmac.compare_digest(actual, expected)

    except Exception:
        return False


def _create_sql_user(full_name: str, email: str, role_sql: str) -> int:
    """Creates a matching row in the SQL Users table and returns its user_id.
    The SQL row does not store a usable password hash (auth is via Mongo),
    so we store a placeholder — SQL login is not a supported path."""
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO Users (full_name, email, password_hash, role, balance)
        OUTPUT INSERTED.user_id
        VALUES (?, ?, ?, ?, 0)
        """,
        (full_name, email, "MANAGED_VIA_MONGO_AUTH", role_sql),
    )
    row = cursor.fetchone()
    connection.commit()

    user_id = row[0]

    cursor.close()
    connection.close()

    return user_id


def _create_token(sql_user_id: int, email: str, role: str) -> str:
    payload = {
        "sub": str(sql_user_id),
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Raises jwt.PyJWTError on invalid/expired tokens."""
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


def register_account(name: str, email: str, password: str, role: str):
    role = role.strip().lower()
    email = email.strip().lower()
    name = name.strip()

    if role not in {"user", "freelancer"}:
        return {
            "status": "failed",
            "message": "Only user and freelancer accounts can self-register.",
        }

    if not name:
        return {"status": "failed", "message": "Name is required."}

    if "@" not in email:
        return {"status": "failed", "message": "Enter a valid email address."}

    if len(password) < 6:
        return {
            "status": "failed",
            "message": "Password must contain at least 6 characters.",
        }

    client = None

    try:
        client, collection = _get_collection()

        # Create the SQL-side identity first, since Gigs/Bids/Contracts/
        # Transactions all reference Users(user_id).
        sql_user_id = _create_sql_user(
            full_name=name,
            email=email,
            role_sql=ROLE_TO_SQL[role],
        )

        document = {
            "name": name,
            "email": email,
            "password_hash": _hash_password(password),
            "role": role,
            "sql_user_id": sql_user_id,
            "created_at": datetime.now(timezone.utc),
            "account_status": "active",
        }

        result = collection.insert_one(document)

        return {
            "status": "success",
            "message": f"{role.capitalize()} account created.",
            "user": {
                "id": str(result.inserted_id),
                "sql_user_id": sql_user_id,
                "name": name,
                "email": email,
                "role": role,
            },
        }

    except DuplicateKeyError:
        return {
            "status": "failed",
            "message": "An account with this email already exists.",
        }

    finally:
        if client:
            client.close()


def login_account(email: str, password: str, role: str):
    role = role.strip().lower()
    email = email.strip().lower()

    # Admin credentials are fixed and are NOT stored in MongoDB or SQL.
    if role == "admin":
        if email == ADMIN_EMAIL and hmac.compare_digest(password, ADMIN_PASSWORD):
            token = _create_token(sql_user_id=0, email=ADMIN_EMAIL, role="ADMIN")
            return {
                "status": "success",
                "message": "Admin login successful.",
                "token": token,
                "user": {
                    "name": "Administrator",
                    "email": ADMIN_EMAIL,
                    "role": "admin",
                },
            }

        return {
            "status": "failed",
            "message": "Invalid admin credentials.",
        }

    if role not in {"user", "freelancer"}:
        return {"status": "failed", "message": "Invalid role."}

    client = None

    try:
        client, collection = _get_collection()
        account = collection.find_one({"email": email, "role": role})

        if not account:
            return {
                "status": "failed",
                "message": f"No {role} account was found for this email.",
            }

        if not _verify_password(password, account.get("password_hash", "")):
            return {
                "status": "failed",
                "message": "Invalid email or password.",
            }

        token = _create_token(
            sql_user_id=account["sql_user_id"],
            email=account["email"],
            role=ROLE_TO_SQL[account["role"]],
        )

        return {
            "status": "success",
            "message": "Login successful.",
            "token": token,
            "user": {
                "id": str(account["_id"]),
                "sql_user_id": account["sql_user_id"],
                "name": account.get("name", ""),
                "email": account["email"],
                "role": account["role"],
            },
        }

    finally:
        if client:
            client.close()
