# EquityTracker Backend

FastAPI backend for tracking leveraged fixed income fund portfolios with lot-based accounting,
historical prices, loan-rate history, and analytics focused on return on equity.

## Komplett API-dokumentasjon

Se [API.md](./API.md) for full dokumentasjon av alle endpoints, request/response-modeller,
valideringsregler, feilhåndtering og eksempler.

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

## Yahoo kursimport fra tiker.txt

Hent historiske sluttkurser fra Yahoo Finance for tickere i `tiker.txt` fra 2023-01-01:

```bash
uv run python -m app.scripts.fetch_yahoo_prices --start-date 2023-01-01
```

Standard output-mappe er `yahoo_prices/` (en JSON-fil per ticker).

## Migrations

```bash
uv run alembic upgrade head
```

## Docker

Build and run API with PostgreSQL-backed defaults:

```bash
docker compose up --build
```

Configure `DATABASE_URL` in `.env` as:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/equitytracker
```
