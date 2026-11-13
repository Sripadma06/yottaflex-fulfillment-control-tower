# YottaFlex Fulfillment Control Tower

A professional React/Vite + FastAPI + PostgreSQL implementation of an Order Fulfillment & Delivery Promise Optimization control tower.

## UI

The dashboard has been rebuilt to closely match the supplied YottaFlex reference UI.

- Google OAuth / OpenID Connect login
- Navy enterprise sidebar and compact white workspace
- Fulfillment Control Tower overview with live KPI cards
- Allocation health and order-status visualization
- Orders search, status filtering, pagination, and drill-down
- Order details with allocation decision and shipment summary
- Shipment search and tracking timeline
- Exceptions review workspace
- Data Quality and operational integrity checks
- Authenticated user menu and sign out

The visual reference and implementation notes are under `docs/ui/`.

## Important data rule

The UI does not invent customer, item, carrier, or promise fields that are not present in the current operational schema. Those fields display `—` until the underlying schema/data model provides them.

The dashboard uses live FastAPI/PostgreSQL data for operational metrics. Ground-truth anomaly records remain isolated from operational decision endpoints.

## Backend quick start

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -e "[dev]"
cp .env.example .env
docker compose up -d
alembic upgrade head
uvicorn fulfillment.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## Google OAuth

Create a Google OAuth Web Application and configure this authorized redirect URI:

```text
http://127.0.0.1:8000/auth/callback
```

Set the following in `.env`:

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SESSION_SECRET=replace-with-a-long-random-secret
FRONTEND_URL=http://localhost:5173
COOKIE_SECURE=false
```

Do not commit `.env`.

## Dashboard quick start

```bash
cd dashboard
npm install
npm run dev
```

Open http://localhost:5173.

## Validation

```bash
fulfillment validate --root data
fulfillment verify-anomalies --root data
fulfillment detect-anomalies --root data
python -m pytest -q
```

## Production notes

- Use HTTPS and `COOKIE_SECURE=true` in production.
- Restrict Google redirect URIs to the deployed host.
- Replace development CORS origins with the deployed frontend origin.
- Use a strong random session secret.
- Add persistent identity/role tables if role-based authorization is required.
