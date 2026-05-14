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

## Always-On Local App

If you want one local URL and a server that keeps running in the background, use Docker from the repo root:

```powershell
docker compose up -d --build
```

Then open:

```text
http://localhost:8000
```

The container is configured with `restart: unless-stopped`, so it will come back automatically after Docker restarts.

Useful commands:

```powershell
docker compose logs -f
docker compose down
```

For this mode, the frontend is built into the app image and served by FastAPI on the same URL as the API.

## Test Backend

```bash
cd backend
uv run pytest
```

## Notes

- The backend supports lot-based transactions, historical prices, and loan rate history.
- Database settings are environment-driven, with PostgreSQL as the default database.
