# Architecture

## Request and data flow

```text
Browser SPA
  → CORS / request logging / exception handling
  → FastAPI router and OAuth2 bearer dependency
  → validation and business service
  → repository query helper / SQLAlchemy session
  → psycopg 3 connection
  → PostgreSQL `retail` schema
```

The frontend uses HTML, CSS, and ES modules with a hash-based route. It makes
same-origin JSON requests by default, attaches the JWT bearer token, normalizes
API errors into toasts, and sends unauthenticated users to login. For a separately
hosted frontend, configure its API base URL and the backend `CORS_ORIGINS`.

## Python layers

- **Routers** in `fastapi_backend/app/routers/` define URLs, HTTP status codes,
  dependency injection, and role checks.
- **Services** in `fastapi_backend/app/services/` hold business behavior; schema
  constraints and PostgreSQL's trigger/procedures enforce data invariants.
- **Repositories** in `fastapi_backend/app/repositories/` contain database query
  helpers; SQL parameters are bound rather than interpolated from user values.
- **Models and schemas** in `app/models.py` and `app/schemas.py` describe the
  existing database records and validate API request/response data.
- **Alembic** owns additive application changes. `0003_app_users` and
  `0004_db_objects` have working upgrades and downgrades.

The starting workspace did not include historic revisions `0001_baseline` or
`0002_add_barcode`. The available 12-table business schema was inspected and left
untouched; the additive migration chain begins at `0003_app_users` rather than
creating inaccurate legacy revisions. `0005_add_barcode` supplies the barcode
column missing from the verified live schema.

## Transactions and business rules

Each request receives a SQLAlchemy session that is closed after response handling.
Sale header and line inserts share one transaction. PostgreSQL's existing
`trg_sale_item_after_insert` trigger reduces inventory, writes a stock movement,
and updates the invoice total. Any check-constraint failure rolls back the
complete sale. Purchase receipt is delegated to the existing
`retail.receive_purchase_order` function; manual adjustment uses the new
`retail.sp_adjust_stock` procedure.

The isolated labs write only to `retail.lab_demo` and `retail.lab_orders`. Their
transaction examples either roll back or remove demo rows after capturing the
result. The optimization seed intentionally persists its generated lab-only data.

## Authentication and authorization

`POST /auth/login` accepts OAuth2 form credentials and returns an HS256 JWT.
Passwords are verified with bcrypt. The current-user dependency decodes the token
and checks that the associated account remains active. Role dependencies enforce
admin, manager, and cashier route access. The token is never treated as proof
that a user is still active without checking the database.

## Local and server concepts

The local app is a client-server system: the browser is the frontend client,
FastAPI/Uvicorn is the HTTP backend, and PostgreSQL is a separate database server
on a host and port. FastAPI runs synchronous SQLAlchemy handlers using synchronous
execution; it is not a WSGI application. A database URL is a connection string,
not an API URL. Environment variables separate local configuration from deployed
configuration; `.env` is private and `.env.example` is a template.

Atomicity, consistency, isolation, durability, savepoints, locks, and deadlocks
are demonstrated by the admin Transaction Lab and `database/pgadmin_demos.sql`.
`EXPLAIN (ANALYZE, BUFFERS)` and a temporary B-tree index are demonstrated in the
Optimization Lab. Concepts such as attribute closure and Armstrong's axioms are
mapped in `TERMS_MAPPING.md` and explained alongside the database design.
