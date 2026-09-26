"""MongoDB database client and connection lifecycle manager."""

from typing import Any, Optional
from .config import settings

# Global client and db placeholders
_mongo_client: Optional[Any] = None
_database: Optional[Any] = None


async def connect_to_database() -> None:
    """Initialize async MongoDB client connection."""
    global _mongo_client, _database
    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        _mongo_client = AsyncIOMotorClient(settings.mongodb_uri)
        _database = _mongo_client[settings.mongodb_db_name]
    except ImportError:
        # Dependency not yet installed in local environment
        pass


async def close_database_connection() -> None:
    """Close async MongoDB client connection."""
    global _mongo_client
    if _mongo_client is not None:
        try:
            _mongo_client.close()
        except Exception:
            pass


def get_database() -> Optional[Any]:
    """Dependency helper to retrieve the active MongoDB database instance."""
    return _database
