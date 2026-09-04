# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from datetime import datetime

from shared.mongo import get_landing_collection
from wrc_scraper.items import WrcRecord


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

        spider.logger.info(f"Saved {item.body}/{item.identifier} -> {item.file_path}")
        return item
