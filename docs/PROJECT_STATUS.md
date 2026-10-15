# Project Status

This checklist tracks verified completion of the requested work. Checked boxes indicate that the complete task was verified, not merely that a related file exists.

## Phase 0 — Inventory
- [x] Inspected the existing workspace folders and files.
- [x] Confirmed the existing FastAPI app, partial product models/schemas, reports, static page, requirements, SQL setup script, and database design document.
- [x] Confirmed the requested Alembic setup, tests, structured frontend, deployment docs, and pgAdmin demo script are not present in the inventory.
- [x] Scope changes to the existing `fastapi_backend/`, `database/`, and `docs/` folders.

## Phase A — Environment, config, logging
- [ ] A1. Alembic revision state and migration setup.
- [ ] A2. Environment configuration and example environment files.
- [ ] A3. CORS configuration.
- [ ] A4. Logging, request middleware, and exception handlers.
- [ ] A5. Health and database health endpoints.

## Phase B — Models, schemas, repositories, services, CRUD
- [ ] B1. SQLAlchemy models and barcode field.
- [ ] B2. Validated request/response schemas.
- [ ] B3. CRUD for categories, suppliers, stores, customers, employees, and products.
- [ ] B4. Inventory listing and stock adjustment.
- [ ] B5. Sales creation, detail, and list behavior.
- [ ] B6. Purchase orders and reorder-based PO creation.
- [ ] B7. Stock movement ledger.
- [ ] B8. Paginated/searchable list endpoints.
- [ ] B9. Extended reports.
- [ ] B10. Dashboard summary.

## Phase C — Authentication and authorization
- [ ] C1. `0003_app_users` migration and grants.
- [ ] C2. Password/JWT security, authentication, and user administration.
- [ ] C3. Idempotent demo-user seeding.
- [ ] C4. Route authentication and role authorization.

## Phase D — Database objects
- [ ] D1. Monthly sales materialized view and refresh endpoint.
- [ ] D2. Stock adjustment stored procedure.
- [ ] D3. Isolated lab tables and seed rows.
- [ ] D4. Additional-index naming and duplication checks.

## Phase E — Labs
- [ ] E1. Commit lab.
- [ ] E2. Rollback lab.
- [ ] E3. Savepoint lab.
- [ ] E4. Isolation-level lab.
- [ ] E5. Lock lab.
- [ ] E6. Deadlock lab.
- [ ] E7. Unique-violation lab.
- [ ] E8. Query optimization lab.

## Phase F — Tests and lint
- [ ] F1. Ruff configuration and clean lint run.
- [ ] F2. Unit tests.
- [ ] F3. Integration tests with automatic database-unavailable skip.
- [ ] F4. Full pytest run.

## Phase G — Backup, restore, Git, deployment preparation
- [ ] G1. Safe backup and restore PowerShell scripts.
- [ ] G2. Ignore rules and documented Git workflow.
- [ ] G3. Render/Vercel/Neon/Cloudflare and environment deployment guide.

## Phase H — pgAdmin deliverables
- [ ] H. Safe, re-runnable pgAdmin demonstration SQL.

## Phase 7 — Frontend
- [ ] Structured HTML/CSS/ES-module SPA and shared API/UI modules.
- [ ] Login, dashboard, management, sales, purchase-order, inventory, ledger, reports, labs, design, and user pages.
- [ ] Role-aware navigation, accessible/responsive styling, loading/error/empty states, and printable receipts.

## Documentation and final verification
- [ ] README and architecture documentation.
- [ ] Map every section 12 term in `TERMS_MAPPING.md`.
- [ ] Verify migrations, lint, tests, app startup, role smoke tests, and frontend behavior.
- [ ] Record remaining manual steps and final outcome.
