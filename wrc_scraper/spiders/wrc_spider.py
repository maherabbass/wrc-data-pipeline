from datetime import date, datetime
from pathlib import PurePosixPath

import scrapy

from shared.config import get_settings
from shared.hashing import sha256_hex
from shared.partitioning import iter_partitions
from wrc_scraper.items import WrcRecord
from wrc_scraper.search_url import build_search_url


class WrcSpider(scrapy.Spider):
    name = "wrc"

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
                url = build_search_url(
                    base_url, settings.wrc_search_path, body_id, partition_start, partition_end, page_number=1
                )
                yield scrapy.Request(
                    url,
                    callback=self.parse_search_results,
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
            self.logger.info(f"{body_name}: no more results after page {page_number - 1}")
            return

        for row in rows:
            identifier = row.css(settings.wrc_identifier_selector).get(default="").strip()
            description = row.css(settings.wrc_description_selector).get(default="").strip()
            date_text = row.css(settings.wrc_date_selector).get(default="").strip()
            href = row.css(settings.wrc_link_selector).get()

            if not (identifier and date_text and href):
                self.logger.warning(f"Skipping unparseable row for {body_name}")
                continue

            published_date = datetime.strptime(date_text, settings.wrc_date_format).date()
            link = response.urljoin(href)
            content_type, file_extension = self.infer_content_type(link)

            yield scrapy.Request(
                link,
                callback=self.parse_document,
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

        next_url = build_search_url(
            base_url, settings.wrc_search_path, body_id, partition_start, partition_end, page_number=page_number + 1
        )
        yield scrapy.Request(
            next_url,
            callback=self.parse_search_results,
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

    def parse_document(self, response, identifier, description, published_date, body_name, partition_date, content_type, file_extension):
        file_hash = sha256_hex(response.body)

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
        )
        self.logger.info(f"{record.identifier} | {content_type} | hash={file_hash[:12]}...")
        yield record