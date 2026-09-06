from datetime import date

import pytest

from shared.partitioning import add_months, iter_partitions, last_day_of_month


def test_last_day_of_month_handles_leap_year():
    assert last_day_of_month(2024, 2) == date(2024, 2, 29)
    assert last_day_of_month(2023, 2) == date(2023, 2, 28)


def test_add_months_rolls_over_year():
    assert add_months(2024, 11, 2) == (2025, 1)


def test_iter_partitions_two_month_windows():
    partitions = list(iter_partitions(date(2024, 1, 15), date(2024, 6, 10), 2))
    assert partitions == [
        (date(2024, 1, 15), date(2024, 2, 29), date(2024, 1, 1)),
        (date(2024, 3, 1), date(2024, 4, 30), date(2024, 3, 1)),
        (date(2024, 5, 1), date(2024, 6, 10), date(2024, 5, 1)),
    ]


def test_iter_partitions_one_month_windows_truncate_at_end_date():
    partitions = list(iter_partitions(date(2024, 1, 15), date(2024, 2, 10), 1))
    assert partitions == [
        (date(2024, 1, 15), date(2024, 1, 31), date(2024, 1, 1)),
        (date(2024, 2, 1), date(2024, 2, 10), date(2024, 2, 1)),
    ]


def test_iter_partitions_rejects_non_positive_size():
    with pytest.raises(ValueError):
        list(iter_partitions(date(2024, 1, 1), date(2024, 1, 1), 0))


def test_iter_partitions_rejects_start_after_end():
    with pytest.raises(ValueError):
        list(iter_partitions(date(2024, 2, 1), date(2024, 1, 1), 1))
