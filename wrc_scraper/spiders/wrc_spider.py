from datetime import date, datetime
from pathlib import PurePosixPath

import scrapy
from scrapy import signals
from scrapy.spidermiddlewares.httperror import HttpError

from shared.config import get_settings
from shared.hashing import sha256_hex, normalize_for_hash
from shared.logging_config import configure_json_logging, get_events_logger
from shared.mongo import get_landing_collection
from shared.partitioning import iter_partitions
from shared.storage import ensure_bucket, get_s3_client, sanitize_identifier
from wrc_scraper.items import WrcRecord
from wrc_scraper.search_url import build_search_url

events_logger = get_events_logger()


class WrcSpider(scrapy.Spider):
    name = "wrc"

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        # Scrapy re-installs its own logging handler right after this returns, so JSON
        # logging is configured on spider_opened instead, which fires after that happens.
        crawler.signals.connect(spider.setup_logging, signal=signals.spider_opened)
        return spider

    def setup_logging(self, spider):
        configure_json_logging(self.settings.get("LOG_LEVEL", "INFO"))

    def __init__(self, *args, **kwargs):
        self.start_date = date.fromisoformat(kwargs.pop("start_date"))
        self.end_date = date.fromisoformat(kwargs.pop("end_date"))
        super().__init__(*args, **kwargs)

    async def start(self):
        settings = get_settings()
        base_url = settings.wrc_base_url
        size_months = settings.partition_size_months

        for body_name, body_id in settings.wrc_body_ids.items():
            for partition_start, partition_end, partition_date in iter_partitions(
                self.start_date, self.end_date, size_months
            ):
                events_logger.info(
                    "partition started",
                    extra={
                        "event": "crawl_partition_started",
                        "body": body_name,
                        "partition_start": partition_start.isoformat(),
                        "partition_end": partition_end.isoformat(),
                    },
                )
                url = build_search_url(
                    base_url, settings.wrc_search_path, body_id, partition_start, partition_end, page_number=1
                )
                yield scrapy.Request(
                    url,
                    callback=self.parse_search_results,
                    errback=self.handle_error,
                    cb_kwargs={
                        "base_url": base_url,
                        "body_id": body_id,
                        "body_name": body_name,
                        "partition_start": partition_start,
                        "partition_end": partition_end,
                        "partition_date": partition_date,
                        "page_number": 1,
                    },
                )

    def parse_search_results(self, response, base_url, body_id, body_name, partition_start, partition_end, partition_date, page_number):
        settings = get_settings()
        rows = response.css(settings.wrc_result_row_selector)
        if not rows:
            events_logger.info(
                "no more results",
                extra={
                    "event": "search_page_empty",
                    "body": body_name,
                    "partition_start": partition_start.isoformat(),
                    "partition_end": partition_end.isoformat(),
                    "page_number": page_number,
                },
            )
            return

        records_valid = 0
        for row in rows:
            identifier = row.css(settings.wrc_identifier_selector).get(default="").strip()
            description = row.css(settings.wrc_description_selector).get(default="").strip()
            date_text = row.css(settings.wrc_date_selector).get(default="").strip()
            href = row.css(settings.wrc_link_selector).get()

            if not (identifier and date_text and href):
                self.crawler.stats.inc_value("wrc/unparseable_rows")
                events_logger.warning(
                    "unparseable row",
                    extra={"event": "unparseable_row", "body": body_name, "page_number": page_number},
                )
                continue

            records_valid += 1
            published_date = datetime.strptime(date_text, settings.wrc_date_format).date()
            link = response.urljoin(href)
            content_type, file_extension = self.infer_content_type(link)

            yield scrapy.Request(
                link,
                callback=self.parse_document,
                errback=self.handle_error,
                cb_kwargs={
                    "identifier": identifier,
                    "description": description,
                    "published_date": published_date,
                    "body_name": body_name,
                    "partition_date": partition_date,
                    "content_type": content_type,
                    "file_extension": file_extension,
                },
            )

        events_logger.info(
            "search page processed",
            extra={
                "event": "search_page_scraped",
                "body": body_name,
                "partition_start": partition_start.isoformat(),
                "partition_end": partition_end.isoformat(),
                "page_number": page_number,
                "records_found": len(rows),
                "records_valid": records_valid,
            },
        )

        next_url = build_search_url(
            base_url, settings.wrc_search_path, body_id, partition_start, partition_end, page_number=page_number + 1
        )
        yield scrapy.Request(
            next_url,
            callback=self.parse_search_results,
            errback=self.handle_error,
            cb_kwargs={
                "base_url": base_url,
                "body_id": body_id,
                "body_name": body_name,
                "partition_start": partition_start,
                "partition_end": partition_end,
                "partition_date": partition_date,
                "page_number": page_number + 1,
            },
        )

    @staticmethod
    def infer_content_type(link: str) -> tuple[str, str]:
        suffix = PurePosixPath(link).suffix.lower().lstrip(".")
        if suffix == "pdf":
            return "pdf", suffix
        if suffix in ("doc", "docx"):
            return "doc", suffix
        return "html", "html"

    def handle_error(self, failure):
        request = failure.request
        status = failure.value.response.status if failure.check(HttpError) else None
        self.crawler.stats.inc_value("wrc/failed_downloads")
        events_logger.error(
            "download failed",
            extra={
                "event": "download_failed",
                "url": request.url,
                "status": status,
                "error": failure.getErrorMessage().strip(),
            },
        )

    def parse_document(self, response, identifier, description, published_date, body_name, partition_date, content_type, file_extension):
        file_hash = sha256_hex(normalize_for_hash(response.body, content_type))
        settings = get_settings()

        # skip unchanged records
        existing_record = get_landing_collection().find_one({"body": body_name, "identifier": identifier})
        if existing_record and existing_record.get("file_hash") == file_hash:
            self.crawler.stats.inc_value("wrc/skipped_unchanged")
            events_logger.info(
                "skipped -- unchanged",
                extra={"event": "skipped_unchanged", "body": body_name, "identifier": identifier},
            )
            return

        # build the storage key
        file_path = f"{body_name}/{partition_date.isoformat()}/{sanitize_identifier(identifier)}.{file_extension}"

        # upload the raw document bytes to MinIO at that key
        s3_client = get_s3_client()
        ensure_bucket(s3_client, settings.minio_landing_bucket)
        s3_client.put_object(Bucket=settings.minio_landing_bucket, Key=file_path, Body=response.body)

        # build the metadata record
        record = WrcRecord(
            identifier=identifier,
            description=description,
            published_date=published_date,
            link=response.url,
            body=body_name,
            partition_date=partition_date,
            content_type=content_type,
            file_extension=file_extension,
            file_hash=file_hash,
            file_path=file_path,
        )
        events_logger.info(
            "fetched",
            extra={
                "event": "document_uploaded",
                "body": body_name,
                "identifier": record.identifier,
                "content_type": content_type,
                "file_hash": file_hash,
            },
        )
        yield record

    def closed(self, reason):
        stats = self.crawler.stats.get_stats()
        saved = stats.get("item_scraped_count", 0)
        skipped = stats.get("wrc/skipped_unchanged", 0)
        failed = stats.get("wrc/failed_downloads", 0)
        unparseable = stats.get("wrc/unparseable_rows", 0)
        found = saved + skipped + failed + unparseable

        events_logger.info(
            "run summary",
            extra={
                "event": "run_summary",
                "reason": reason,
                "records_found": found,
                "records_saved": saved,
                "records_skipped": skipped,
                "records_failed": failed,
                "records_unparseable": unparseable,
            },
        )
