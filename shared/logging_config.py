"""Shared JSON log formatting, wired in via WrcSpider.from_crawler"""

import json
import logging

# LogRecord's own attributes, so the formatter below only picks up extra={...} fields
_RESERVED_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {
    "message",
    "asctime",
}


class JsonFormatter(logging.Formatter):
    """Renders one JSON object per log line, merging any `extra={...}` fields straight in."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_json_logging(level: str = "INFO") -> None:
    """Point the root logger at a single JSON-formatted handler."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.setLevel(level)  # since Scrapy hardcodes its own loggers to DEBUG
    logging.basicConfig(level=level, handlers=[handler], force=True)


def get_events_logger() -> logging.Logger:
    """Plain logger for structured events -- Scrapy's self.logger drops extra= fields."""
    return logging.getLogger("wrc_scraper.events")
