from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongo_uri: str
    mongo_db_name: str
    mongo_landing_collection: str = "landing_metadata"
    mongo_transformed_collection: str = "transformed_metadata"

    minio_endpoint: str
    minio_root_user: str
    minio_root_password: str
    minio_use_ssl: bool = False
    minio_landing_bucket: str
    minio_transformed_bucket: str

    partition_size_months: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()

