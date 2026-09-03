from datetime import date
from urllib.parse import urlencode

SEARCH_PATH = "/en/search/"


def build_search_url(
    base_url: str, body_id: int, from_date: date, to_date: date, page_number: int
) -> str:
    """Return the absolute search-results URL for one body, one date range, one page.
    """

    query = {
        "decisions": 1,
        "from": from_date.strftime("%d/%m/%Y"),
        "to": to_date.strftime("%d/%m/%Y"),
        "legislationsub": "",
        "body": body_id,
        "pageNumber": page_number,
    }
    return f"{base_url.rstrip('/')}{SEARCH_PATH}?{urlencode(query)}"
