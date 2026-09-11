from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo import MongoClient
from pymongo.collection import Collection

from shared.config import get_settings


@lru_cache
def get_mongo_client() -> MongoClient:
    return MongoClient(get_settings().mongo_uri)


def get_landing_collection() -> Collection:
    settings = get_settings()
    return get_mongo_client()[settings.mongo_db_name][settings.mongo_landing_collection]


def get_transformed_collection() -> Collection:
    settings = get_settings()
    return get_mongo_client()[settings.mongo_db_name][settings.mongo_transformed_collection]


# Async counterparts (motor) used by the Scrapy spider/pipeline
@lru_cache
def get_async_mongo_client() -> AsyncIOMotorClient:
    return AsyncIOMotorClient(get_settings().mongo_uri)


def get_async_landing_collection() -> AsyncIOMotorCollection:
    settings = get_settings()
    return get_async_mongo_client()[settings.mongo_db_name][settings.mongo_landing_collection]