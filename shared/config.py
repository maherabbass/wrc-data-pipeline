from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongo_uri: str
    mongo_db_name: str
    mongo_landing_collection: str = "landing_metadata"
    mongo_transformed_collection: str = "transformed_metadata"

    minio_endpoint: str
    minio_root_user: str
    minio_root_password: str
    minio_use_ssl: bool = False
    minio_landing_bucket: str
    minio_transformed_bucket: str

    partition_size_months: int = 1

    wrc_base_url: str = "https://www.workplacerelations.ie"
    wrc_search_path: str = "/en/search/"
    wrc_body_ids: dict[str, int] = {
        "equality_tribunal": 1,
        "employment_appeals_tribunal": 2,
        "labour_court": 3,
        "workplace_relations_commission": 15376,
    }

    # CSS selectors for parsing search-result rows, and the date format they display.
    wrc_result_row_selector: str = "li.each-item"
    wrc_identifier_selector: str = "h2.title a::text"
    wrc_description_selector: str = "p.description::text"
    wrc_date_selector: str = "span.date::text"
    wrc_link_selector: str = "div.link a::attr(href)"
    wrc_date_format: str = "%d/%m/%Y"

    # CSS selector isolating a case page's actual content
    wrc_content_selector: str = "div.content"

    # Pool of desktop browser user agents RandomUserAgentMiddleware picks from per request.
    wrc_user_agents: list[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/26.4 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
