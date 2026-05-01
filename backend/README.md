# Fundtracker Backend

FastAPI backend for tracking leveraged fixed income fund portfolios with lot-based accounting,
historical prices, loan-rate history, and analytics focused on return on equity.

## Quick start

```bash
uv sync
uv run uvicorn app.main:app --reload
```

## Tests

```bash
uv run pytest
```

## Migrations

```bash
uv run alembic upgrade head
```
