# WRC Data Pipeline

Scrapes decisions and determinations from [workplacerelations.ie](https://www.workplacerelations.ie) (Equality Tribunal, Employment Appeals Tribunal, Labour Court, and the Workplace Relations Commission), lands the raw documents and metadata in MongoDB/MinIO, then transforms the HTML documents down to their actual case content in a separate zone.

## Prerequisites

- Python 3.10+
- Docker Desktop (for MongoDB and MinIO)

## Setup

1. Copy `.env.example` to `.env` and adjust values if needed (the defaults work out of the box for local use):
   ```
   cp .env.example .env
   ```
2. Start MongoDB and MinIO:
   ```
   docker compose up -d
   docker compose ps   # both should show "healthy"
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the scraper

```
scrapy crawl wrc -a start_date=2024-01-01 -a end_date=2024-01-31 -L INFO
```

`start_date`/`end_date` accept any range; the crawl internally chunks it into monthly partitions (configurable via `PARTITION_SIZE_MONTHS`). Logs are structured JSON, one event per line. Running the same range twice is safe — already-saved, unchanged records are skipped rather than duplicated.

Scraped documents land in the `wrc-landing-docs` MinIO bucket and their metadata in the `landing_metadata` MongoDB collection (both names configurable in `.env`).

## Running the transform step

```
python -m transform.transform --start-date 2024-01-01 --end-date 2024-01-31
```

Reads matching records from the landing collection for that date range, leaves PDF/DOC files untouched, and cleans HTML files down to just the case content (stripping the site's navigation/header/footer). Results land in a separate `wrc-transformed-docs` bucket and `transformed_metadata` collection — the original landing data is never modified. Also safe to re-run; unchanged content is skipped.

## Running both together with Dagster

The scraper and transform step can also be run as a pair of dependent, orchestrated assets instead of two manual commands:

```
.\run_dagster.ps1     # Windows
./run_dagster.sh      # macOS/Linux
```

Both scripts set `DAGSTER_HOME` to an absolute path computed from the project's own location — Dagster requires it to be absolute, so it can't be portably hardcoded in a shared `.env.example`. Without it, Dagster falls back to a fresh temporary instance on every run (losing history between runs). The Windows script additionally sets `PYTHONLEGACYWINDOWSSTDIO`, which has to be set before Python starts and so can't be loaded from `.env` at all — without it, Dagster's run logs aren't captured for the UI to display (a Windows-only console I/O limitation; macOS/Linux don't need this).

Open `http://localhost:3000`. You'll see two assets, `landing_zone` and `transformed_zone` (the latter depends on the former), partitioned by month. Pick a month and materialize `landing_zone`; once it succeeds, `transformed_zone` becomes materializable for that same month. Selecting both together and materializing runs them in the correct order automatically.

## Running tests

```
pytest
```

Covers the pure logic that's cheapest and most valuable to pin down: date partitioning, the hash-normalization fix, identifier sanitization, and search URL building. Doesn't cover the Scrapy/Dagster pipeline itself, which was instead verified through live crawls against real Mongo/MinIO — these are unit tests for the standalone helper functions, not integration tests.

## Where things are configured

Every connection string, bucket/collection name, partition size, and scraping parameter (selectors, retry/throttle settings, user agents, etc.) lives in `.env` — see `.env.example` for the full list with comments. Nothing is hardcoded in the source.

## Project layout

```
shared/           config, Mongo/S3 clients, hashing, logging -- used by both the scraper and transform step
wrc_scraper/      the Scrapy project (spider, item model, pipeline, settings)
transform/        the standalone transform script
orchestration/    Dagster assets wiring the scraper and transform step together
tests/            unit tests for the standalone helper functions in shared/ and wrc_scraper/search_url.py
```

See `ARCHITECTURE.md` for the higher-level design decisions.
