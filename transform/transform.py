"""Standalone transform step -- cleans/copies scraped documents from the landing zone
into the transformed zone. Runs on its own, separate from the spider:

    python -m transform.transform --start-date 2024-01-01 --end-date 2024-01-31
"""

import argparse
import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from shared.config import get_settings
from shared.hashing import sha256_hex
from shared.logging_config import configure_json_logging, get_events_logger
from shared.mongo import get_landing_collection, get_transformed_collection
from shared.storage import ensure_bucket, get_s3_client, sanitize_identifier

events_logger = get_events_logger()

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_description(text: str) -> str:
    # source descriptions carry raw \r\n and repeated whitespace from the site's markup
    return _WHITESPACE_RE.sub(" ", text).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transform scraped WRC documents for a date range.")
    parser.add_argument("--start-date", required=True, type=date.fromisoformat)
    parser.add_argument("--end-date", required=True, type=date.fromisoformat)
    return parser.parse_args()


def clean_html(raw_html: bytes, content_selector: str) -> bytes:
    # keep only the actual case content, dropping the site's nav/header/footer chrome
    soup = BeautifulSoup(raw_html, "html.parser")
    content = soup.select_one(content_selector)
    if content is None:
        events_logger.warning("content selector matched nothing", extra={"event": "content_selector_no_match"})
        return raw_html
    return str(content).encode("utf-8")


def main() -> None:
    configure_json_logging()
    args = parse_args()
    settings = get_settings()

    landing_collection = get_landing_collection()
    transformed_collection = get_transformed_collection()
    s3_client = get_s3_client()
    ensure_bucket(s3_client, settings.minio_transformed_bucket)

    start = datetime.combine(args.start_date, datetime.min.time())
    end = datetime.combine(args.end_date, datetime.min.time())
    records = landing_collection.find({"published_date": {"$gte": start, "$lte": end}})

    saved = 0
    skipped = 0
    failed = 0
    for record in records:
        try:
            raw_bytes = s3_client.get_object(
                Bucket=settings.minio_landing_bucket, Key=record["file_path"]
            )["Body"].read()

            # pdf/doc are left untouched; html is cleaned down to just the case content
            if record["content_type"] == "html":
                content = clean_html(raw_bytes, settings.wrc_content_selector)
            else:
                content = raw_bytes

            content_hash = sha256_hex(content)

            # skip if this exact content was already transformed
            existing_record = transformed_collection.find_one({"body": record["body"], "identifier": record["identifier"]})
            if existing_record and existing_record.get("file_hash") == content_hash:
                skipped += 1
                events_logger.info(
                    "skipped -- unchanged",
                    extra={"event": "skipped_unchanged", "body": record["body"], "identifier": record["identifier"]},
                )
                continue

            # flat filename, no folders
            file_path = f"{sanitize_identifier(record['identifier'])}.{record['file_extension']}"
            s3_client.put_object(Bucket=settings.minio_transformed_bucket, Key=file_path, Body=content)

            doc = dict(record)
            doc.pop("_id", None)
            doc["file_path"] = file_path
            doc["file_hash"] = content_hash
            doc["description"] = normalize_description(doc["description"])
            transformed_collection.update_one(
                {"body": record["body"], "identifier": record["identifier"]},
                {"$set": doc},
                upsert=True,
            )
        except Exception as exc:
            failed += 1
            events_logger.error(
                "save failed",
                extra={
                    "event": "save_failed",
                    "body": record.get("body"),
                    "identifier": record.get("identifier"),
                    "error": str(exc),
                },
            )
            continue

        saved += 1
        events_logger.info(
            "document_transformed",
            extra={
                "event": "transformed",
                "body": record["body"],
                "identifier": record["identifier"],
                "file_path": file_path,
            },
        )

    events_logger.info(
        "run summary",
        extra={
            "event": "run_summary",
            "records_found": saved + skipped + failed,
            "records_saved": saved,
            "records_skipped": skipped,
            "records_failed": failed,
        },
    )


if __name__ == "__main__":
    main()
