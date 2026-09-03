# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from datetime import date
from typing import Literal

from pydantic import BaseModel


class WrcRecord(BaseModel):
    identifier: str
    description: str
    published_date: date
    link: str
    body: str
    partition_date: date
    content_type: Literal["pdf", "doc", "html"]
    file_extension: str

    file_path: str | None = None
    file_hash: str | None = None
