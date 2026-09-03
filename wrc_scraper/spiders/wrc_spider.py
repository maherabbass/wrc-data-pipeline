from datetime import date

import scrapy

from shared.config import get_settings
from shared.partitioning import iter_partitions
from shared.body_ids import BODY_IDS
from wrc_scraper.search_url import build_search_url

RESULT_ROW_SELECTOR = "li.each-item"


class WrcSpider(scrapy.Spider):
    name = "wrc"

    def __init__(self, *args, **kwargs):
        self.start_date = date.fromisoformat(kwargs.pop("start_date"))
        self.end_date = date.fromisoformat(kwargs.pop("end_date"))
        super().__init__(*args, **kwargs)

    async def start(self):
        base_url = "https://www.workplacerelations.ie"
        size_months = get_settings().partition_size_months

        for body_name, body_id in BODY_IDS.items():
            for partition_start, partition_end, partition_date in iter_partitions(
                self.start_date, self.end_date, size_months
            ):
                url = build_search_url(base_url, body_id, partition_start, partition_end, page_number=1)
                yield scrapy.Request(
                    url,
                    callback=self.parse_search_results,
                    cb_kwargs={
                        "base_url": base_url,
                        "body_id": body_id,
                        "body_name": body_name,
                        "partition_start": partition_start,
                        "partition_end": partition_end,
                        "page_number": 1,
                    },
                )

    def parse_search_results(self, response, base_url, body_id, body_name, partition_start, partition_end, page_number):
        rows = response.css(RESULT_ROW_SELECTOR)
        if not rows:
            self.logger.info(f"{body_name}: no more results after page {page_number - 1}")
            return

        for row in rows:
            identifier = row.css(".refNO::text").get(default="").strip()
            description = row.css("p.description::text").get(default="").strip()
            date_text = row.css("span.date::text").get(default="").strip()
            self.logger.info(f"{body_name} | {identifier} | {date_text} | {description}")

        next_url = build_search_url(base_url, body_id, partition_start, partition_end, page_number=page_number + 1)
        yield scrapy.Request(
            next_url,
            callback=self.parse_search_results,
            cb_kwargs={
                "base_url": base_url,
                "body_id": body_id,
                "body_name": body_name,
                "partition_start": partition_start,
                "partition_end": partition_end,
                "page_number": page_number + 1,
            },
        )
