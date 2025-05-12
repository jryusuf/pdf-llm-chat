import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_settings

settings = get_settings()

MONGO_URL = settings.MONGO_URL
DATABASE_NAME = "appdb"

_mongo_client: AsyncIOMotorClient = None


async def connect_to_mongo():
    """Connects to MongoDB."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(MONGO_URL)


async def close_mongo_connection():
    """Closes the MongoDB connection."""
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None


async def get_mongo_db() -> AsyncIOMotorDatabase:
    """
    MongoDB database dependency.

    Provides an active MongoDB database connection.
    """
    global _mongo_client
    if _mongo_client is None:
        await connect_to_mongo()
    return _mongo_client[DATABASE_NAME]
