# Project Status

This checklist tracks verified completion of the requested work. Checked boxes indicate that the complete task was verified, not merely that a related file exists.

## Phase 0 — Inventory
- [x] Inspected the existing workspace folders and files.
- [x] Confirmed the existing FastAPI app, partial product models/schemas, reports, static page, requirements, SQL setup script, and database design document.
- [x] Confirmed the requested Alembic setup, tests, structured frontend, deployment docs, and pgAdmin demo script are not present in the inventory.
- [x] Scope changes to the existing `fastapi_backend/`, `database/`, and `docs/` folders.

## Phase A — Environment, config, logging
- [x] A1. Alembic revision state and migration setup.
- [x] A2. Environment configuration and example environment files.
- [x] A3. CORS configuration.
- [x] A4. Logging, request middleware, and exception handlers.
- [x] A5. Health and database health endpoints.

## Phase B — Models, schemas, repositories, services, CRUD
- [x] B1. SQLAlchemy models and barcode field.
- [x] B2. Validated request/response schemas.
- [x] B3. CRUD for categories, suppliers, stores, customers, employees, and products.
- [x] B4. Inventory listing and stock adjustment.
- [x] B5. Sales creation, detail, and list behavior.
- [x] B6. Purchase orders and reorder-based PO creation.
- [x] B7. Stock movement ledger.
- [x] B8. Paginated/searchable list endpoints.
- [x] B9. Extended reports.
- [x] B10. Dashboard summary.

## Phase C — Authentication and authorization
- [x] C1. `0003_app_users` migration and grants.
- [x] C2. Password/JWT security, authentication, and user administration.
- [x] C3. Idempotent demo-user seeding.
- [x] C4. Route authentication and role authorization.

## Phase D — Database objects
- [x] D1. Monthly sales materialized view and refresh endpoint.
- [x] D2. Stock adjustment stored procedure.
- [x] D3. Isolated lab tables and seed rows.
- [x] D4. Additional-index naming and duplication checks.

## Phase E — Labs
- [x] E1. Commit lab.
- [x] E2. Rollback lab.
- [x] E3. Savepoint lab.
- [x] E4. Isolation-level lab.
- [x] E5. Lock lab.
- [x] E6. Deadlock lab.
- [x] E7. Unique-violation lab.
- [x] E8. Query optimization lab.

## Phase F — Tests and lint
- [x] F1. Ruff configuration and clean lint run.
- [x] F2. Unit tests.
- [x] F3. Integration tests with automatic database-unavailable skip.
- [x] F4. Full pytest run.

## Phase G — Backup, restore, Git, deployment preparation
- [x] G1. Safe backup and restore PowerShell scripts.
- [x] G2. Ignore rules and documented Git workflow.
- [x] G3. Render/Vercel/Neon/Cloudflare and environment deployment guide.

## Phase H — pgAdmin deliverables
- [x] H. Safe, re-runnable pgAdmin demonstration SQL.

## Phase 7 — Frontend
- [x] Structured HTML/CSS/ES-module SPA and shared API/UI modules.
- [x] Login, dashboard, management, sales, purchase-order, inventory, ledger, reports, labs, design, and user pages.
- [x] Role-aware navigation, accessible/responsive styling, loading/error/empty states, and printable receipts.

## Documentation and final verification
- [x] README and architecture documentation.
- [x] Map every section 12 term in `TERMS_MAPPING.md`.
- [x] Verify migrations, lint, tests, app startup, role smoke tests, and frontend behavior.
- [x] Record remaining manual steps and final outcome.
