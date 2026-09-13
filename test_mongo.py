import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DATABASE")]
collection = db[os.getenv("MONGO_COLLECTION")]

collection.insert_one({"test": "connection check"})
print("Connected! Document count:", collection.count_documents({}))