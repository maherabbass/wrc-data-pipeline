import calendar
from collections.abc import Iterator
from datetime import date, timedelta


def last_day_of_month(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def add_months(year: int, month: int, months: int) -> tuple[int, int]:
    zero_based = (month - 1) + months
    return year + zero_based // 12, zero_based % 12 + 1


def iter_partitions(start_date: date, end_date: date, size_months: int) -> Iterator[tuple[date, date, date]]:
    if size_months <= 0:
        raise ValueError(f"size_months must be a positive integer, got {size_months}")
    if start_date > end_date:
        raise ValueError(f"start_date ({start_date}) must not be after end_date ({end_date})")

    cursor = start_date
    while cursor <= end_date:
        partition_date = cursor.replace(day=1)

        last_year, last_month = add_months(cursor.year, cursor.month, size_months - 1)
        group_end = last_day_of_month(last_year, last_month)
        partition_end = min(group_end, end_date)

        yield cursor, partition_end, partition_date

        cursor = partition_end + timedelta(days=1)