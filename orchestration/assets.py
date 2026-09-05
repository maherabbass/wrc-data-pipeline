import subprocess
import sys
from datetime import timedelta
from pathlib import Path

from dagster import AssetExecutionContext, MonthlyPartitionsDefinition, asset

from shared.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Same monthly granularity the scraper itself uses (partition_size_months=1)
monthly_partitions = MonthlyPartitionsDefinition(start_date=get_settings().wrc_partition_start_date)


def _partition_date_range(context: AssetExecutionContext) -> tuple[str, str]:
    window = context.partition_time_window
    start_date = window.start.date()
    end_date = (window.end - timedelta(days=1)).date()
    return start_date.isoformat(), end_date.isoformat()


@asset(partitions_def=monthly_partitions)
def landing_zone(context: AssetExecutionContext) -> None:
    """Runs the scraper for one month, landing raw documents and metadata."""
    start_date, end_date = _partition_date_range(context)
    subprocess.run(
        [sys.executable, "-m", "scrapy", "crawl", "wrc", "-a", f"start_date={start_date}", "-a", f"end_date={end_date}"],
        cwd=PROJECT_ROOT,
        check=True,
    )


@asset(partitions_def=monthly_partitions, deps=[landing_zone])
def transformed_zone(context: AssetExecutionContext) -> None:
    """Runs the transform script for the same month, once landing_zone has succeeded."""
    start_date, end_date = _partition_date_range(context)
    subprocess.run(
        [sys.executable, "-m", "transform.transform", "--start-date", start_date, "--end-date", end_date],
        cwd=PROJECT_ROOT,
        check=True,
    )
