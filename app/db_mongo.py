# db_mongo.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DB", "Microservicio3")
COLL_NAME = os.getenv("MONGODB_COLLECTION", "UserTiktokMetrics")

client: AsyncIOMotorClient | None = None

def get_client() -> AsyncIOMotorClient:
    global client
    if client is None:
        client = AsyncIOMotorClient(MONGO_URI)
    return client

def get_collection_by(name: str):
    cli = get_client()
    return cli[DB_NAME][name]

def get_collection():
    cli = get_client()
    return cli[DB_NAME][COLL_NAME]

async def ensure_indexes():
    pass
