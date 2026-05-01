# EquityTracker

EquityTracker is a portfolio analytics platform for leveraged fixed income funds.

## Project Structure

- backend: FastAPI service, database models, analytics logic, tests, and migrations.
- frontend: Reserved for the future React application (not implemented yet).

## Quick Start (Backend)

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

## Test Backend

```bash
cd backend
uv run pytest
```

## Notes

- The backend supports lot-based transactions, historical prices, and loan rate history.
- Database settings are environment-driven for SQLite (dev) and PostgreSQL (production).
