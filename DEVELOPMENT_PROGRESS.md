# FinSight Development Progress

## Current phase

**Phase 8: production deployment hardening**

The browser now keeps access tokens in memory and uses an HttpOnly refresh
cookie. PostgreSQL RLS, separate migration/runtime roles, non-root containers,
and a Caddy-backed production Compose configuration are being validated.

## What is working

- FastAPI application with `/health`
- User registration, login, session-bound JWTs, and `/auth/me`
- Hashed refresh-token rotation, replay detection, and per-session logout
- HttpOnly refresh cookie, memory-only access token, and sign-out controls
- Production auth-origin validation and secure-cookie configuration
- PostgreSQL row-level security migration for user-owned records
- Dedicated restricted runtime database role in production Compose
- Caddy HTTPS reverse proxy and production health checks
- Non-root backend and frontend containers
- PostgreSQL user table managed by Alembic
- User-scoped transaction creation, listing, and detail endpoints
- PostgreSQL transaction table managed by Alembic
- CSV upload with per-row validation, duplicate detection, and persisted import errors
- User-scoped import history and row-error detail endpoints
- Browser CSV upload page with import summary and invalid-row feedback
- Local rule-based categories for uncategorized transactions
- Authenticated spending summaries grouped by currency
- Signed-in dashboard with recent transactions and category breakdowns
- Monthly budgets with actual spending, remaining amount, and over-budget progress
- Heuristic recurring-charge estimates based on monthly cadence and stable amounts
- User-owned keyword rules applied to new transactions and CSV imports
- Manual transaction category correction with category-source tracking
- Rule management and category correction controls on the dashboard
- Browser registration and sign-in pages
- Backend settings loaded from environment variables
- Frontend and API CORS alignment
- Next.js welcome and product-preview page
- PostgreSQL and Redis in Docker Compose
- Docker build and ignore configuration
- Backend and frontend local verification

## Remaining before production release

These deployment requirements still need real-environment verification:

1. Set the public domain and DNS records, then validate Caddy certificate issuance and renewal.
2. Deploy to a clean VM and verify migrations, runtime DB grants, and cross-user RLS isolation.
3. Configure encrypted off-VM backups and perform a restore test.
4. Add deployment monitoring/alerting and a CI/CD release pipeline.
5. Decide whether the bundled PostgreSQL is acceptable or use a managed database.

## Verified locally

The following checks were run successfully:

- Backend dependencies install
- 31 backend tests pass, including production settings, cookie rotation, replay revocation, and finance workflows
- Frontend production build passes
- Frontend TypeScript validation passes
- npm audit reports zero vulnerabilities
- Development and production Docker Compose configurations validate
- The complete Docker stack starts
- PostgreSQL and Redis report healthy
- Local PostgreSQL is at migration `20261120_0007`
- A fresh PostgreSQL instance initialized the separate roles, ran all migrations, and passed an API auth smoke test using the restricted runtime role
- PostgreSQL row-level-security isolation was verified for reads and cross-user writes
- Transaction creation and listing work against PostgreSQL
- CSV imports reject malformed files and report invalid rows
- `GET /health` returns `{"status":"ok"}`
- The frontend root page returns HTTP 200

The production Compose configuration and isolated role/migration/auth path have
been verified, but a live-domain deployment, clean-VM operational run, and
off-VM backup/restore test have not. Do not treat the application as ready for a
real production launch until those environment-specific checks are complete.
