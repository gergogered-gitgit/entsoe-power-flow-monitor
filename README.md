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

