# ENTSO-E European Power Flow Monitor

Hourly European electricity flow monitor built on the ENTSO-E Transparency Platform.

## MVP

The first vertical slice tracks cross-border physical flows for the Baltic/Nordic region:

- Finland
- Sweden bidding zones SE1-SE4
- Estonia
- Latvia
- Lithuania

The dashboard will show selected-hour flow arrows, border-pair trends, top importers/exporters, and ingestion health.
The next layer adds border infrastructure, reference capacities, ENTSO-E transfer capacities where
available, and utilization percentages.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Add your ENTSO-E token to `.env`:

```text
ENTSOE_API_TOKEN=your-token-here
```

For hosted Supabase/Postgres storage, also set:

```text
DATABASE_URL=postgresql://...
```

## Run

Initialize the local DuckDB schema:

```powershell
python -m entsoe_power_flow.db
```

Run the dashboard:

```powershell
streamlit run app/streamlit_app.py
```

Backfill flow data once the API token is available:

```powershell
entsoe-backfill-flows --days 7
```

The backfill command initializes the database if needed, requests each configured border pair,
parses ENTSO-E XML points, upserts hourly rows, and records the run in `ingestion_runs`.

Run checks:

```powershell
python -m pytest
python -m ruff check .
```

## Supabase

Create a Supabase project, open the SQL editor, and run `sql/supabase_schema.sql`.

Use the project's Postgres connection string as `DATABASE_URL` for backend ingestion and for
Streamlit reads. Keep that value in GitHub Actions secrets and Streamlit secrets; do not commit it.

Backfill into Supabase locally:

```powershell
entsoe-backfill-flows --days 3 --storage postgres
entsoe-backfill-capacities --days 14 --storage postgres
```

## Scheduled Ingestion

The workflow at `.github/workflows/ingest-flows.yml` runs once per week and can also be started
manually from GitHub Actions. Each run refetches the last 14 days so late or revised ENTSO-E
records are upserted without pretending the MVP needs daily monitoring.

Required GitHub repository secrets:

- `ENTSOE_API_TOKEN`
- `DATABASE_URL`

The job writes to Supabase/Postgres.

## Streamlit Cloud

Deploy `app/streamlit_app.py` from the GitHub repository. Add `DATABASE_URL` to Streamlit secrets so
the dashboard reads from Supabase. If `DATABASE_URL` is not set, the app falls back to local DuckDB.

## Data Design

The pipeline uses a rolling backfill window because ENTSO-E data can arrive late or be revised after first publication. Each run should refetch recent periods and upsert by natural key.

Core tables:

- `zones`
- `border_pairs`
- `power_flows_hourly`
- `generation_hourly`
- `prices_hourly`
- `ingestion_runs`

## ENTSO-E Access

REST API access requires a Transparency Platform account, a request for RESTful API access, and a generated security token. See `docs/entsoe-access-email.md` for a draft email.
