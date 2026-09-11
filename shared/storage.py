from functools import lru_cache

import aioboto3
import boto3
from botocore.exceptions import ClientError

from shared.config import get_settings


@lru_cache
def get_s3_client():
    settings = get_settings()
    scheme = "https" if settings.minio_use_ssl else "http"
    return boto3.client(
        "s3",
        endpoint_url=f"{scheme}://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_root_user,
        aws_secret_access_key=settings.minio_root_password,
    )


def ensure_bucket(client, bucket: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code not in ("404", "NoSuchBucket"):
            raise
        client.create_bucket(Bucket=bucket)


# Async counterpart (aioboto3) used by the Scrapy spider
def async_s3_client(session: aioboto3.Session):
    settings = get_settings()
    scheme = "https" if settings.minio_use_ssl else "http"
    return session.client(
        "s3",
        endpoint_url=f"{scheme}://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_root_user,
        aws_secret_access_key=settings.minio_root_password,
    )


async def ensure_bucket_async(client, bucket: str) -> None:
    try:
        await client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code not in ("404", "NoSuchBucket"):
            raise
        await client.create_bucket(Bucket=bucket)


def sanitize_identifier(identifier: str) -> str:
    # identifiers are inconsistently formatted on-site (stray spaces, mixed separators);
    # collapse whitespace so the result is a safe, consistent storage key/filename
    return "_".join(identifier.split())