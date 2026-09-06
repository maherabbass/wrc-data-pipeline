from datetime import date

from wrc_scraper.search_url import build_search_url


def test_build_search_url_shape():
    url = build_search_url(
        "https://www.workplacerelations.ie", "/en/search/", 15376, date(2024, 1, 1), date(2024, 1, 31), 1
    )
    assert url == (
        "https://www.workplacerelations.ie/en/search/"
        "?decisions=1&from=01%2F01%2F2024&to=31%2F01%2F2024&legislationsub=&body=15376&pageNumber=1"
    )


def test_build_search_url_strips_trailing_slash_from_base_url():
    url = build_search_url("https://example.com/", "/en/search/", 1, date(2024, 1, 1), date(2024, 1, 1), 1)
    assert url.startswith("https://example.com/en/search/")
    assert "//en/search" not in url


def test_build_search_url_increments_page_number():
    url = build_search_url("https://example.com", "/en/search/", 1, date(2024, 1, 1), date(2024, 1, 31), 3)
    assert "pageNumber=3" in url
