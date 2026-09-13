import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "gigtrust")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "activity_logs")


def get_mongo_collection():
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=10000
    )

    database = client[MONGO_DATABASE]
    collection = database[MONGO_COLLECTION]

    return client, collection


def test_mongo_connection():
    client, collection = get_mongo_collection()

    try:
        client.admin.command("ping")

        return {
            "database": "Cosmos DB MongoDB",
            "status": "connected",
            "collection": collection.name
        }

    finally:
        client.close()


def log_activity(
    event_type: str,
    user_id: int,
    transaction_id: int | None = None,
    amount: float | None = None,
    details: dict | None = None
):
    client, collection = get_mongo_collection()

    try:
        event = {
            "event_type": event_type,
            "user_id": user_id,
            "transaction_id": transaction_id,
            "amount": amount,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc)
        }

        result = collection.insert_one(event)

        return {
            "status": "logged",
            "event_id": str(result.inserted_id)
        }

    finally:
        client.close()