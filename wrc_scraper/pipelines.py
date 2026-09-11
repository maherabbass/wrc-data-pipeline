# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from datetime import datetime

from scrapy.exceptions import DropItem

from shared.logging_config import get_events_logger
from shared.mongo import get_async_landing_collection
from wrc_scraper.items import WrcRecord

events_logger = get_events_logger()


class WrcScraperPipeline:
    def __init__(self, stats):
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.stats)

    async def process_item(self, item: WrcRecord, spider):
        # convert dates into a Mongo-friendly datetime
        doc = item.model_dump()
        doc["published_date"] = datetime.combine(item.published_date, datetime.min.time())
        doc["partition_date"] = datetime.combine(item.partition_date, datetime.min.time())

        try:
            # upsert into Mongo
            collection = get_async_landing_collection()
            await collection.update_one(
                {"body": item.body, "identifier": item.identifier},
                {"$set": doc},
                upsert=True,
            )
        except Exception as exc:
            self.stats.inc_value("wrc/save_failed")
            events_logger.error(
                "save failed",
                extra={
                    "event": "save_failed",
                    "stage": "mongo_upsert",
                    "body": item.body,
                    "identifier": item.identifier,
                    "error": str(exc),
                },
            )
            raise DropItem(f"Failed to save {item.body}/{item.identifier} to Mongo") from exc

        events_logger.info(
            "saved",
            extra={
                "event": "saved_to_mongo",
                "body": item.body,
                "identifier": item.identifier,
                "file_path": item.file_path,
            },
        )
        return item
