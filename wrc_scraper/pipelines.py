# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from datetime import datetime

from shared.logging_config import get_events_logger
from shared.mongo import get_landing_collection
from wrc_scraper.items import WrcRecord

events_logger = get_events_logger()


class WrcScraperPipeline:
    def process_item(self, item: WrcRecord, spider):
        # convert dates into a Mongo-friendly datetime
        doc = item.model_dump()
        doc["published_date"] = datetime.combine(item.published_date, datetime.min.time())
        doc["partition_date"] = datetime.combine(item.partition_date, datetime.min.time())

        # upsert into Mongo
        collection = get_landing_collection()
        collection.update_one(
            {"body": item.body, "identifier": item.identifier},
            {"$set": doc},
            upsert=True,
        )

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
