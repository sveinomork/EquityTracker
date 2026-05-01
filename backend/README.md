# EquityTracker Backend

FastAPI backend for tracking leveraged fixed income fund portfolios with lot-based accounting,
historical prices, loan-rate history, and analytics focused on return on equity.

## Local development

```bash
uv sync
uv run uvicorn app.main:app --reload
```

## API endpoints

- `POST /api/v1/funds`
- `GET /api/v1/funds`
- `POST /api/v1/transactions`
- `POST /api/v1/funds/{fund_id}/prices`
- `GET /api/v1/funds/{fund_id}/prices`
- `POST /api/v1/funds/{fund_id}/rates`
- `GET /api/v1/funds/{fund_id}/rates`
- `GET /api/v1/funds/{fund_id}/summary`
- `GET /api/v1/funds/{fund_id}/lots`
- `GET /api/v1/portfolio/summary`

## Query filters for read endpoints

`GET /api/v1/funds/{fund_id}/prices` and `GET /api/v1/funds/{fund_id}/rates` support:

- `from_date` (optional, `YYYY-MM-DD`)
- `to_date` (optional, `YYYY-MM-DD`)
- `limit` (optional, `1-5000`)

## Tests

```bash
uv run pytest
```

## Migrations

```bash
uv run alembic upgrade head
```

## Docker

Build and run API with SQLite-backed defaults:

```bash
docker compose up --build api
```

Run API with PostgreSQL profile:

```bash
docker compose --profile postgres up --build
```

When using PostgreSQL profile, configure `DATABASE_URL` in `.env` as:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/equitytracker
```
