# YottaFlex AI — Fulfillment Control Tower

A full-stack **Fulfillment Control Tower** built as part of the YottaFlex AI Candidate Project.

The system provides visibility into orders, shipments, fulfillment nodes, inventory, allocation decisions, tracking events, and operational exceptions through a web-based dashboard.

---

## 1. Project Overview

The goal of this project is to build a working fulfillment operations system that can:

- Generate realistic fulfillment data at scale
- Store and manage fulfillment data in PostgreSQL
- Track orders and shipments
- Monitor fulfillment and delivery activity
- Identify operational exceptions
- Display key fulfillment metrics through a dashboard
- Provide authenticated access using Google OAuth
- Support reproducible local development and production deployment

The project uses synthetic data and does not depend on confidential or proprietary business data.

---

## 2. Key Features

### Fulfillment Data

The system supports:

- Orders
- Shipments
- Split shipments
- Fulfillment nodes
- Carriers
- Inventory records
- Allocation decisions
- Tracking events
- Holidays
- Ground-truth validation cases

### Dashboard

The dashboard provides operational visibility into:

- Total orders
- Shipments
- Exceptions
- Fulfillment activity
- Shipment and order status
- Operational trends

### Authentication

- Google OAuth authentication
- Session-based authentication
- Protected API endpoints
- Secure production cookies

### Data Generation and Validation

The project includes CLI workflows for:

- Generating synthetic fulfillment datasets
- Validating generated data
- Loading data into PostgreSQL
- Running database migrations

---

## 3. Technology Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic / Pydantic Settings
- PostgreSQL
- Psycopg

### Frontend

- React
- Vite
- JavaScript
- HTML / CSS

### Authentication

- Google OAuth
- Starlette SessionMiddleware

### Deployment

- Render — Backend
- Vercel — Frontend
- Supabase PostgreSQL — Database
- GitHub — Source control

---

## 4. Architecture

```text
                    ┌──────────────────────┐
                    │       Browser        │
                    │    React / Vite      │
                    └──────────┬───────────┘
                               │
                               │ HTTPS / REST API
                               ▼
                    ┌──────────────────────┐
                    │      FastAPI         │
                    │      Backend         │
                    └──────────┬───────────┘
                               │
                 ┌─────────────┼─────────────┐
                 │             │             │
                 ▼             ▼             ▼
          Authentication    Services     Data Access
          Google OAuth      API Logic     SQLAlchemy
                                             │
                                             ▼
                                   ┌──────────────────┐
                                   │    PostgreSQL    │
                                   │     Supabase     │
                                   └──────────────────┘
```

---

## 5. Repository Structure

```text
.
├── data/
│   └── output/
│
├── migrations/
│   ├── versions/
│   └── env.py
│
├── src/
│   └── fulfillment/
│       ├── api.py
│       ├── auth.py
│       ├── config.py
│       ├── db.py
│       ├── generator.py
│       ├── loader.py
│       ├── models.py
│       └── ...
│
├── frontend/
│   └── ...
│
├── config/
│   └── business_rules.yaml
│
├── README.md
├── requirements.txt
├── alembic.ini
└── ...
```

---

## 6. Prerequisites

Install the following before running the project:

- Python 3.11+
- Node.js and npm
- PostgreSQL
- Git

For production deployment, a PostgreSQL-compatible hosted database can be used.

---

## 7. Backend Setup

Clone the repository:

```bash
git clone https://github.com/Sripadma06/yottaflex-fulfillment-control-tower.git
cd yottaflex-fulfillment-control-tower
```

Create and activate a virtual environment.

### Windows Git Bash

```bash
python -m venv .venv
source .venv/Scripts/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 8. Environment Configuration

Create a `.env` file in the project root.

Example:

```env
DATABASE_URL=postgresql+psycopg://<username>:<password>@<host>:<port>/<database>

GENERATOR_SEED=20261022

GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>

SESSION_SECRET=<your-random-session-secret>

FRONTEND_URL=http://localhost:5173
COOKIE_SECURE=false
```

### Important

Do not commit `.env` files, passwords, OAuth secrets, API keys, or other credentials to GitHub.

Use environment variables for all secrets.

---

## 9. Database Setup

After configuring `DATABASE_URL`, run the migrations:

```bash
alembic upgrade head
```

Check the current migration:

```bash
alembic current
```

The database should be at the latest migration revision.

---

## 10. Generate Fulfillment Data

The project includes a synthetic data generator.

Generate the full dataset:

```bash
fulfillment generate --scale full --out data/output
```

The full generated dataset used for validation contains approximately:

- 50,000 orders
- 20 fulfillment nodes
- 10 carriers
- 200 inventory records
- 50,000 allocation decisions
- 53,429 shipments
- 3,429 split orders
- 8,598 delayed shipments
- 1,499 exception orders
- 296,551 tracking events
- Ground-truth validation cases

The generated data is deterministic through the configured random seed.

---

## 11. Validate the Dataset

Run:

```bash
fulfillment validate --root data/output
```

The validation workflow checks fulfillment relationships and known anomaly cases.

The generated dataset intentionally contains ground-truth anomalies for validation. These include cases involving:

- Promise timestamps
- Allocation exceeding stock
- Unsupported carrier/service/zone combinations
- Shipment and tracking chronology
- Split-shipment status rollups

These cases are retained intentionally to demonstrate validation and exception handling.

---

## 12. Load Data into PostgreSQL

After generating and validating the dataset:

```bash
fulfillment load --root data/output
```

This loads the generated fulfillment data into PostgreSQL.

The loading process uses PostgreSQL bulk loading for the generated datasets.

---

## 13. Run the Backend

Start the FastAPI application:

```bash
uvicorn src.fulfillment.api:app --reload
```

The backend will normally be available at:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

---

## 14. Run the Frontend

Open a second terminal and navigate to the frontend:

```bash
cd frontend
npm install
npm run dev
```

The Vite development server will normally run at:

```text
http://localhost:5173
```

---

## 15. Authentication Flow

The application uses Google OAuth.

The general authentication flow is:

```text
User
  │
  ▼
Frontend
  │
  ▼
Backend /auth/login
  │
  ▼
Google OAuth
  │
  ▼
/auth/callback
  │
  ▼
Authenticated Session
  │
  ▼
Protected Dashboard APIs
```

Google OAuth credentials must be configured through environment variables.

---

## 16. Production Deployment

The submitted application is deployed using:

### Frontend

Vercel

```text
https://yottaflex-fulfillment-control-tower.vercel.app
```

### Backend

Render

```text
https://yottaflex-fulfillment-control-tower.onrender.com
```

### Database

Supabase PostgreSQL

Production secrets and database credentials are configured through deployment environment variables and are not stored in the repository.

---

## 17. Verification

The following checks were used to verify the system:

### Backend Health

```bash
curl https://yottaflex-fulfillment-control-tower.onrender.com/health
```

Expected:

```json
{
  "status": "ok"
}
```

### Database

Database migrations were applied successfully using:

```bash
alembic upgrade head
```

### Data Generation

Full-scale synthetic fulfillment data was successfully generated.

### Data Validation

The validation command was executed against the generated dataset.

### Data Loading

The generated dataset was successfully loaded into PostgreSQL.

### Authentication

Google OAuth login was tested successfully.

### Dashboard

The production dashboard was tested after authentication and verified against the populated production database.

---

## 18. Design Decisions

### PostgreSQL

PostgreSQL was selected because the project contains relational fulfillment entities with relationships between orders, shipments, inventory, allocation decisions, nodes, carriers, and tracking events.

### FastAPI

FastAPI provides a lightweight API layer with clear request/response handling and is suitable for building the backend services required by the dashboard.

### SQLAlchemy

SQLAlchemy provides structured database access and ORM-based models while keeping the database layer maintainable.

### Alembic

Alembic is used to version and apply database schema migrations consistently across environments.

### Synthetic Data

Synthetic data was used to avoid exposing confidential or personal information while still allowing realistic fulfillment scenarios and anomaly cases to be tested.

### Google OAuth

Google OAuth provides a straightforward authentication mechanism without requiring the application to store user passwords.

---

## 19. Validation and Exception Handling

The generated dataset intentionally includes specific anomaly cases.

These cases are useful for verifying that the system can identify unusual fulfillment conditions instead of assuming every record is valid.

Examples include:

- Invalid chronological relationships
- Allocation exceeding available inventory
- Unsupported carrier/service/zone combinations
- Shipment/tracking inconsistencies
- Split-order status inconsistencies

The validation results are treated as expected test/ground-truth cases rather than silently removing the anomalies.

---

## 20. AI Usage Disclosure

AI tools were used during development as permitted by the YottaFlex AI project guidelines.

AI assistance was primarily used for:

- Understanding implementation requirements
- Debugging errors
- Exploring implementation approaches
- Reviewing code and configuration
- Improving documentation
- Troubleshooting deployment issues

AI-generated suggestions were reviewed, tested, and adapted during implementation.

The final implementation, integration decisions, configuration, testing, debugging, and deployment were personally reviewed and validated.

A record of prompts used during development is included in the repository:

```text
docs/prompt-history.md
```

The prompt history is provided to make AI usage transparent.

---

## 21. Limitations

- The application uses synthetic fulfillment data rather than live enterprise data.
- Google OAuth requires valid OAuth credentials and correctly configured redirect URLs.
- Production deployment depends on the availability of the configured hosting and database services.
- The current system focuses on fulfillment visibility, validation, and operational monitoring rather than complete enterprise logistics management.
- The generated dataset is intended for demonstration and evaluation rather than production forecasting.

---

## 22. Future Improvements

Potential future improvements include:

- Role-based access control
- More detailed operational analytics
- Advanced shipment ETA prediction
- Automated exception resolution workflows
- Carrier performance analytics
- Inventory forecasting
- Real-time tracking updates
- Automated alerting
- More extensive automated test coverage
- CI/CD pipeline
- More granular audit logging

---

## 23. Reproducibility

The project uses a fixed generator seed to make generated data reproducible.

A fresh environment can reproduce the core workflow using:

```bash
pip install -r requirements.txt
alembic upgrade head
fulfillment generate --scale full --out data/output
fulfillment validate --root data/output
fulfillment load --root data/output
```

Then start the backend and frontend using the instructions above.

---

## 24. Project Status

**Status: Completed**

The application has been:

- Built
- Migrated
- Populated with full-scale synthetic data
- Validated
- Loaded into PostgreSQL
- Deployed
- Authenticated with Google OAuth
- Verified through the production dashboard

---

## 25. Author

**Sripadma Kulkarni**

GitHub:  
https://github.com/Sripadma06

LinkedIn:  
https://www.linkedin.com/in/sripadma-kulkarni-a76764299/
