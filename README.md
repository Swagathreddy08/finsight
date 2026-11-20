# FinSight

FinSight is a personal financial intelligence workspace. Its goal is to help people
bring transactions together, understand where money is going, and ask useful
questions about their own financial activity.

> This repository is under active development. The local release includes
> accounts, transaction imports and analytics, budgets, category rules, and
> rotating authentication sessions. A production Compose deployment is
> configured, but a real deployment still requires a public domain, DNS, VM
> firewall setup, and backup/recovery verification.

## What is included today

- A Next.js welcome and product-preview screen
- A FastAPI backend with authentication, finance APIs, and interactive API docs
- Account registration, sign-in, user-scoped transactions, and CSV imports
- PostgreSQL and Redis services in the local application stack
- Docker Compose for running the local stack
- Shared environment settings for the frontend and backend

## Start FinSight locally

From the project root, prepare your local settings:

**Windows PowerShell**
```powershell
Copy-Item .env.example .env
docker compose up --build
```

**macOS or Linux**
```bash
cp .env.example .env
docker compose up --build
```

Then open:

| Service | Address |
| --- | --- |
| Web app | http://localhost:3000 |
| API | http://localhost:8000 |
| Interactive API docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

Registration and sign-in return a short-lived access token and set an HttpOnly
refresh cookie. The browser keeps the access token in memory, rotates the
refresh cookie automatically, and revokes the current session on sign-out.
Cookie-based API clients should send credentials to `POST /api/v1/auth/refresh`
and `POST /api/v1/auth/logout`; the refresh token is never returned in JSON.
Production auth mutations validate the request origin. Each session expires
after seven days, and access tokens are checked against the active session on
every request. Use the access token as a bearer token for the transaction endpoints:
`POST /api/v1/transactions`, `GET /api/v1/transactions`, and
`GET /api/v1/transactions/{transaction_id}`. Transaction amounts are signed:
expenses are negative and income is positive.

To import a CSV, send it as multipart form field `file` to
`POST /api/v1/transactions/import`. Include `date`, `description`, and `amount`
columns; `merchant`, `currency`, and `category` are optional. Dates use
`YYYY-MM-DD`; amounts use at most two decimal places. Uploads are limited to
5 MB and 5,000 rows. The response includes import counts and row-level errors.
Import history and saved row errors are available at
`GET /api/v1/transactions/imports` and
`GET /api/v1/transactions/imports/{import_id}`.
You can also sign in to the web app and open http://localhost:3000/import to
upload a file and review its import summary.

The signed-in overview is at http://localhost:3000/dashboard. It summarizes the
last 30 days by currency, rather than adding different currencies together.
Transactions without a category receive a best-effort category from local
merchant and description rules; an explicit category is left unchanged.
Add personal keyword rules with `GET /api/v1/categorization/rules`,
`POST /api/v1/categorization/rules`, and
`DELETE /api/v1/categorization/rules/{rule_id}`. Rules are applied to new
transactions and CSV imports in priority order. Correct an existing transaction
with `PATCH /api/v1/transactions/{transaction_id}/category`; your correction is
kept as a manual category.

The dashboard also supports monthly category budgets through
`POST /api/v1/budgets`, `GET /api/v1/budgets`, and
`PUT /api/v1/budgets/{budget_id}`. Budget progress compares a category's
spending in that calendar month and currency with its limit. Possible recurring
charges are available at `GET /api/v1/analytics/recurring?months=6`. This is a
best-effort estimate: it looks for at least three expenses spaced roughly a
month apart with similar amounts, so review suggestions before acting on them.

You can also run the first health check directly:

```text
GET http://localhost:8000/health
```

## Run individual services

### Backend

```powershell
cd backend
python -m pip install -e ".[test]"
python -m pytest -q
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Before a frontend release, run:

```powershell
npm run lint
npm run build
npm audit --audit-level=low
```

## How the application is organized

```text
backend/
  app/
    core/          Shared configuration and infrastructure
    api/v1/        HTTP routes for versioned API endpoints
    models/        Database entities
    schemas/       Validated API request and response shapes
    repositories/  Database access
    services/      Financial workflows and business rules
    ai/            Classification and language-query integrations
  tests/           Backend tests

frontend/
  app/             Next.js pages and styles
  components/      Reusable interface components
  lib/             Frontend utilities and API clients
```

The intended backend structure keeps HTTP routes thin. Pydantic validates data,
repositories handle database access, and services implement financial workflows.
AI features should classify or explain information; they should not directly
control transaction amounts, dates, database credentials, or unrestricted SQL.

## Keeping financial data private

User-owned PostgreSQL tables use row-level security in production. Each
authenticated database transaction sets its user context, and the production
Compose setup runs the API as a restricted database role. A separate migration
role owns schema changes and is not used by the API.

LLM provider calls will not receive database credentials. Natural-language
questions should be converted into strict, validated query specifications before
any allowlisted repository or SQLAlchemy operation runs.

## Configuration

Copy `.env.example` to `.env`, then replace every local placeholder with values
appropriate for your environment.

Do not commit real database passwords, JWT secrets, API keys, AWS credentials,
or `.env` files. The example file is intentionally non-secret and safe to share.

## Production VM deployment

The production Compose file serves the web app and API behind Caddy, which
obtains and renews HTTPS certificates. PostgreSQL and Redis have no host-published
ports; only Caddy's HTTP/HTTPS ports are exposed. The deployment uses separate
database migration and runtime roles, PostgreSQL row-level security, secure
HttpOnly refresh cookies, and non-root application containers.

On a Linux VM with Docker Compose installed:

1. Point the domain's DNS A/AAAA records to the VM and allow inbound TCP ports
   80 and 443 in the VM/network firewall.
2. Copy `.env.production.example` to `.env.production`. Set `PUBLIC_DOMAIN` to
   the real domain and generate unique values for each password and
   `JWT_SECRET_KEY` (for example, `openssl rand -hex 32`). Keep this file
   private and outside version control.
3. Start the stack:

   ```bash
   docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
   ```

4. Check service health and visit `https://<your-domain>`. The first boot creates
   database roles and data volumes; the role-init script only runs for a fresh
   PostgreSQL volume.

This is a single-VM deployment, not a high-availability setup. Back up PostgreSQL
regularly to encrypted storage outside the VM and test restores before relying on
the system. For example, on the VM:

```bash
mkdir -p backups
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U finsight_admin -d finsight -Fc > "backups/finsight-$(date +%F).dump"
```

Before calling a deployment production-ready, verify DNS/TLS renewal, backup
retention and restore, monitoring/alerts, and a clean-VM migration. The public
domain and off-VM recovery target are not configured in this workspace.

## Project status

The current implementation state and verification record are maintained in
[DEVELOPMENT_PROGRESS.md](DEVELOPMENT_PROGRESS.md).

"# finsight" 
