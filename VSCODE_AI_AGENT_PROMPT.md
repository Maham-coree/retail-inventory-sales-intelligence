# MASTER PROMPT: Finish the "Retail Inventory and Sales Intelligence System" today

## 0. Role and goal
You are a senior full-stack engineer working inside this VS Code workspace (Windows, PowerShell, Python 3.13, virtual environment at `.venv` in the project root, PostgreSQL 18 running locally, pgAdmin installed).

This is a university DBMS project. Complete it **today**: finish the backend (FastAPI + SQLAlchemy + Alembic + PostgreSQL), build a **professional frontend**, add the pgAdmin SQL scripts, tests, backup scripts, Git setup and documentation. The instructor requires coverage of the 217 terms listed in section 12 ("database to local development"), so every one of them must be demonstrable somewhere in the project, and mapped in `docs/TERMS_MAPPING.md`.

Work autonomously. Ask the user only if you are blocked by something you cannot discover yourself (for example a missing password). Do not stop after each phase; continue until everything in section 11 passes.

## 1. ABSOLUTE RULES (read before touching anything)
1. **No duplication.** Before creating any file, class, route, migration, SQL object, test or seed row, check whether it already exists. If it exists, reuse or extend it. Never create a second copy, a "v2", or a parallel implementation. When refactoring, MOVE code and delete the old location.
2. **Never run `01_schema_and_data.sql`** (or any script that contains `DROP SCHEMA`). It would wipe the existing database and roles. Database changes go **only** through new Alembic migrations (revision 0003 and later). Never edit or delete migrations `0001_baseline` and `0002_add_barcode`.
3. **Everything must be idempotent and re-runnable.** Seed scripts use "insert if not exists". Migrations have working `upgrade()` and `downgrade()`. Running this prompt a second time must change nothing that is already done.
4. **Keep working things working.** Existing URLs listed in section 2 must keep their paths and response shapes (you may add fields).
5. **Secrets:** never print, log, hardcode or commit the database password or any secret. Read the database URL from `.env`. Do not hardcode the database name; take it from `DATABASE_URL`. Make sure `.env`, `.venv`, `__pycache__`, `*.dump`, `*.log` are in `.gitignore`.
6. Run Python tools as `python -m <tool>` (the PATH on this machine is unreliable). Use PowerShell-compatible commands only.
7. Leave the legacy `dashboard/` (Streamlit) folder untouched.
8. Lab and demo features may only touch their own `retail.lab_*` tables, never the real business tables, and must not leave junk data behind.

## 2. Known current state (VERIFY by inspecting the repo; do not assume)
**Database (local PostgreSQL, schema `retail`)**: 12 tables (categories, suppliers, products, stores, inventory, employees, customers, sales, sale_items, purchase_orders, purchase_order_items, stock_movements), 16 foreign keys, 12 indexes, 6 views (`v_stock_status`, `v_reorder_list`, `v_inventory_valuation`, `v_daily_sales`, `v_monthly_revenue`, `v_product_performance`), trigger `trg_sale_item_after_insert` (function `fn_apply_sale_item`, SECURITY DEFINER), function `receive_purchase_order(po_id)`, sample data, roles `role_admin`, `role_manager`, `role_cashier` and users `admin_user`, `manager_user`, `cashier_user` (privileges already granted).

**Backend `fastapi_backend/`**:
- `.env` (user-created, contains `DATABASE_URL`), `.env.example`, `requirements.txt` (fastapi, uvicorn[standard], sqlalchemy, psycopg[binary], python-dotenv, alembic)
- `alembic.ini`, `alembic/env.py` (uses `DATABASE_URL`, `version_table_schema="retail"`), `alembic/script.py.mako`, `alembic/versions/0001_baseline.py` (empty baseline), `alembic/versions/0002_add_barcode.py` (adds `retail.products.barcode`, unique)
- `app/database.py` (engine, `SessionLocal`, `Base`, `get_db`), `app/models.py` (only `Category`, `Supplier`, `Product`), `app/schemas.py` (`ProductBase`, `ProductCreate`, `ProductUpdate`, `ProductOut`), `app/reports.py` (14 reports with relational algebra + SQL), `app/main.py`, `app/static/index.html` (single-file UI)
- **Existing endpoints:** `GET /` (serves the UI), `GET /health`, `GET/POST /products`, `GET/PUT/PATCH/DELETE /products/{product_id}`, `GET /reorder-alerts`, `GET /categories`, `GET /suppliers`, `GET /stock`, `GET /sales`, `GET /summary`, `GET /reports`, `GET /reports/{report_id}` (with `?explain=true`). A helper `db_error()` maps SQLSTATE 23505/23503/23514 to HTTP 409/409/400.

**Unknown, you must check:** whether Alembic has already been stamped/upgraded. Run `python -m alembic current`. If it shows nothing, run `python -m alembic stamp 0001_baseline`, then `python -m alembic upgrade head`. If it already shows `0002_add_barcode`, skip. Also check whether Git is already initialised and whether the `.gitignore` is complete.

## 3. Working method
1. Phase 0: inventory the repo, then create `PROJECT_STATUS.md` at the repo root with a checklist of every phase and task below, ticking only what you have verified as existing.
2. After finishing each task, tick it in `PROJECT_STATUS.md`. At the start of any later run, read this file first and skip ticked tasks (verify quickly, do not redo).
3. After each phase run the relevant checks (import the app, `python -m alembic current`, `python -m pytest -q`, `python -m ruff check .`) and fix problems before moving on.

## 4. Technology decisions (do not substitute)
- Backend: FastAPI, SQLAlchemy 2.0 (typed `Mapped`), psycopg 3, Alembic, Pydantic v2.
- Auth: password hashing with the `bcrypt` package; JWT with `PyJWT` (HS256); `OAuth2PasswordBearer` so the Swagger "Authorize" button works; `python-multipart` for the login form.
- Tests: `pytest`, `httpx` (FastAPI TestClient). Lint: `ruff`.
- Frontend: **no build step and no npm**. Plain HTML, CSS and ES-module JavaScript served by FastAPI from `app/static/`. Charts with Chart.js loaded from a pinned CDN URL (`https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js`).
- Add every new package to `requirements.txt` once (no duplicates) and install with `python -m pip install -r requirements.txt`.

## 5. Target backend structure (migrate toward this; move, do not copy)
```
fastapi_backend/
  app/
    main.py              # app creation, middleware (CORS, request logging), routers, static mount, exception handlers only
    config.py            # settings from env: DATABASE_URL, APP_ENV, JWT_SECRET, JWT_EXPIRE_MINUTES, CORS_ORIGINS
    database.py          # (exists) keep
    models.py            # (exists) add the missing models here
    schemas.py           # (exists) add the missing schemas here
    reports.py           # (exists) append only
    security.py          # password hashing, JWT create/verify
    deps.py              # get_current_user, require_roles(...)
    logging_config.py
    routers/             # products, categories, suppliers, stores, inventory, customers, employees,
                         # sales, purchase_orders, stock_movements, reports, dashboard, auth, users, labs
    services/            # business logic (service layer)
    repositories/        # database access (repository layer)
    scripts/seed_users.py
  alembic/versions/      # 0003 and later only
  tests/
  scripts/backup.ps1, scripts/restore.ps1
```
Routers call services; services call repositories; repositories use SQLAlchemy sessions. Move the existing product logic out of `main.py` into this structure while keeping every existing URL working. Leave no dead code.

## 6. Phases and tasks

### Phase A: Environment, config, logging
- A1. Finish Alembic as described in section 2 (stamp/upgrade only if needed).
- A2. Create `app/config.py`. Support `APP_ENV` (`development`, `production`) and load `.env.development` / `.env.production` if present, otherwise `.env`. Append only the **missing** keys to `.env.example` (`APP_ENV`, `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `CORS_ORIGINS`) and add them to the user's `.env` if missing, generating a random `JWT_SECRET` (do not print it). Create `.env.development.example` and `.env.production.example` (templates, no real secrets).
- A3. Add `CORSMiddleware` configured from `CORS_ORIGINS` (default `http://127.0.0.1:8000,http://localhost:8000`).
- A4. `logging_config.py`: console + rotating file `logs/app.log`, a request-logging middleware (method, path, status, duration), and global exception handlers (SQLAlchemy `IntegrityError` and others mapped to clean JSON using the existing `db_error()` logic; unexpected errors logged with stack trace and returned as a generic 500).
- A5. Extend the existing `GET /health` (keep it) and add `GET /health/db` that runs `SELECT 1` and returns the PostgreSQL version.

### Phase B: Models, schemas, repositories, services, CRUD
- B1. Add the missing SQLAlchemy models, matching the real tables and constraints exactly: Store, Inventory (composite key), Employee, Customer, Sale, SaleItem (`line_total` is a generated column, read-only), PurchaseOrder, PurchaseOrderItem, StockMovement. Add `barcode` to `Product` and the product schemas (optional, unique) now that migration 0002 exists.
- B2. Pydantic schemas (Create / Update / Out) with validation: positive quantities, non-negative prices, price >= cost, allowed values for `role`, `payment_method`, PO `status`.
- B3. Full CRUD (with proper status codes 200/201/204/404/409/422) for: categories, suppliers, stores, customers, employees (read + create + update), products (exists, refactor). Delete must return a clear 409 when a foreign key blocks it.
- B4. **Inventory:** `GET /inventory` (filters: store, product, status), `POST /inventory/adjust` which calls the stored procedure from Phase D (`CALL retail.sp_adjust_stock(...)`).
- B5. **Sales:** `POST /sales` with body `{store_id, customer_id?, employee_id?, payment_method, items:[{product_id, quantity, discount?}]}`. Use each product's current `unit_price`. Insert the sale and its items in **one transaction**; the existing trigger reduces stock and updates the total. On insufficient stock (CHECK violation) roll back everything and return 409 naming the product. `GET /sales/{id}` returns the sale with its lines (for the receipt). Keep the existing `GET /sales` list shape.
- B6. **Purchase orders:** create (with items), list, get, change status (Draft, Ordered, Cancelled), and `POST /purchase-orders/{id}/receive` which calls `retail.receive_purchase_order(po_id)`. Add `POST /purchase-orders/from-reorder-alerts` that creates one Draft PO per supplier from the current reorder list (`suggested_order_qty` and `unit_cost`), skipping products already on an open PO.
- B7. `GET /stock-movements` (ledger, filters by product, store, type, date range, pagination).
- B8. Add list-query support (`search`, `page`, `page_size`, `sort`) to products, customers, sales and stock movements, returning `{items, total, page, page_size}`. Keep the existing `GET /products` working for current callers (plain list when no pagination params are given).
- B9. Extend `app/reports.py` by **appending** (check ids first, no duplicates): a RIGHT JOIN report, a FULL JOIN report, a "materialized view" report (Phase D), and a "stock movements by type" aggregate.
- B10. `GET /dashboard/summary` extends the existing `/summary` data with: sales per day (last 30 days), top 5 products, stock status counts, revenue per store. Keep `/summary` as it is.

### Phase C: Authentication and authorization
- C1. Alembic migration `0003_app_users`: table `retail.app_users` (`user_id` identity PK, `public_id UUID` default `gen_random_uuid()` unique, `username` unique not null, `password_hash` not null, `role` CHECK in (`admin`,`manager`,`cashier`), `employee_id` nullable FK to `retail.employees`, `is_active` default true, `created_at`). Grant privileges to the existing database roles in a guarded `DO` block. Full downgrade.
- C2. `security.py`, `deps.py`, router `auth`: `POST /auth/login` (OAuth2 form, returns JWT access token and user info), `GET /auth/me`. Router `users` (admin only): list, create, deactivate, reset password. Passwords are always hashed with bcrypt, never returned.
- C3. `app/scripts/seed_users.py` (idempotent, run with `python -m app.scripts.seed_users`): creates `admin` (Admin@123), `manager` (Manager@123, employee 1), `cashier` (Cashier@123, employee 2) only if they do not exist. These demo credentials go in the README.
- C4. Protect **every** route except `/`, `/static/*`, `/health`, `/health/db`, `/auth/login`, `/docs`, `/openapi.json`. Authorization matrix:

| Capability | admin | manager | cashier |
|---|---|---|---|
| Read products, stock, customers, sales, reports | yes | yes | products, stock, own sales only |
| Create or edit products, suppliers, categories, stores | yes | yes | no |
| Delete anything | yes | no | no |
| Create sales and customers | yes | yes | yes |
| Adjust stock, purchase orders, receive PO | yes | yes | no |
| Users, labs, backups | yes | no | no |

Return 401 when unauthenticated and 403 when the role is not allowed.

### Phase D: Database objects (one new migration `0004_db_objects`, with grants and full downgrade)
- D1. Materialized view `retail.mv_monthly_sales` (month, store, invoices, revenue) with a unique index so it can be refreshed concurrently. Endpoint `POST /reports/materialized/refresh` (admin, manager) runs `REFRESH MATERIALIZED VIEW`.
- D2. Stored procedure `retail.sp_adjust_stock(p_store_id int, p_product_id int, p_delta int, p_reason text)`: upserts the inventory row, writes an `ADJUSTMENT` row in `stock_movements`, raises a clear exception if the result would be negative. Called with `CALL`.
- D3. Lab tables `retail.lab_demo(item_id identity, item_name, qty)` seeded with a few rows and `retail.lab_orders(id, customer_ref, amount, created_at)` (empty; filled on demand).
- D4. Any additional index you add must be a normal B-tree with a clear name; do not recreate the 12 existing indexes.

### Phase E: Labs (admin only; all work stays inside `retail.lab_*` tables)
Implement router `labs` returning a step-by-step log (list of `{step, sql, result}`) so the frontend can display what happened:
- E1. **COMMIT**: insert, commit, show the row is visible.
- E2. **ROLLBACK**: insert, rollback, show the row is gone.
- E3. **SAVEPOINT**: insert A, `SAVEPOINT s1`, insert B, `ROLLBACK TO s1`, commit, show only A persisted.
- E4. **Isolation levels**: show `SHOW transaction_isolation`; with two connections demonstrate that READ COMMITTED sees another transaction's committed change in a second read while REPEATABLE READ does not.
- E5. **Locks**: connection A does `SELECT ... FOR UPDATE` on a lab row; connection B tries `FOR UPDATE NOWAIT` and the lab reports the lock error (SQLSTATE 55P03).
- E6. **Deadlock**: two threads with separate connections update two lab rows in opposite order; report that PostgreSQL aborted one with SQLSTATE 40P01, then roll both back.
- E7. **Unique violation (23505)**: try to insert a duplicate and show the error code and how the API turns it into 409.
- E8. **Optimization lab**: `POST /labs/optimization/seed` (fill `lab_orders` with 200,000 rows using `generate_series`, only if empty), `POST /labs/optimization/run` which runs `EXPLAIN (ANALYZE, BUFFERS)` for `WHERE customer_ref = <value>`, creates a B-tree index, runs `ANALYZE`, explains again, drops the index, and returns both plans and timings.

### Phase F: Tests and lint
- F1. `pyproject.toml` with ruff configuration; `python -m ruff check .` must pass (fix findings).
- F2. Unit tests (no database): schema validation (price below cost fails), password hashing and verification, JWT create/verify, status-code mapping in `db_error()`.
- F3. Integration tests (real local database, marked `integration`, skipped automatically if the database is unreachable): login for each role, products create/read/update/delete (use SKU prefix `TEST-` and clean up), a sale that reduces stock (and is cleaned up or rolled back), insufficient-stock rejection, authorization (cashier cannot delete, 401 without a token), duplicate SKU returns 409.
- F4. `python -m pytest -q` must pass.

### Phase G: Backup, restore, Git, deployment preparation
- G1. `scripts/backup.ps1` and `scripts/restore.ps1`: locate `pg_dump`/`pg_restore`/`psql` automatically under `C:\Program Files\PostgreSQL\*\bin` (the PATH is unreliable), read connection details from `.env`, create a custom-format backup (`-Fc`) and a plain SQL dump (`--format=plain`) in `backups/` with timestamped names, and restore into a **new** database name given as a parameter. Never overwrite the live database.
- G2. Git: if no repository exists run `git init -b main`; make sure `.gitignore` is complete; create a clean first commit (never include `.env`, `.venv`, `logs/`, `backups/`). Do not push. Document the exact push commands for GitHub in the README, and branching (`feature/...`), commit, push, pull, clone.
- G3. `docs/DEPLOYMENT.md`: how to deploy the backend to Render (start command `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`, environment variables, Neon `DATABASE_URL` with `sslmode=require`), how a separate frontend on Vercel would work (CORS origins), where Cloudflare/DNS/domain fit, and environment separation (development/testing/production). Documentation only; do not deploy.

### Phase H: pgAdmin deliverables
Create `database/pgadmin_demos.sql` (clearly sectioned, every section safe and re-runnable, touching only `retail.lab_*` or wrapped in `ROLLBACK`): DCL demo (`GRANT`/`REVOKE`/`SET ROLE`), TCL (`BEGIN`/`COMMIT`/`ROLLBACK`/`SAVEPOINT`), isolation levels (two-tab instructions in comments), locks (`FOR UPDATE`, `NOWAIT`), a deadlock script for two query tabs, `EXPLAIN ANALYZE` before/after an index, the 23505 demo, `REFRESH MATERIALIZED VIEW`, `CALL retail.sp_adjust_stock(...)`, RIGHT/FULL JOIN examples, `pg_roles` listing, and verification queries (counts of tables, views, indexes, constraints, triggers from `information_schema`/`pg_catalog`). Add a short header comment on how to run it in pgAdmin's Query Tool and how to open **Tools > PSQL Tool**. Do not duplicate schema creation or data from earlier scripts.

## 7. Frontend specification (replace `app/static/index.html` with a structured SPA; no duplicate or leftover old files)
**Structure:** `static/index.html` (shell), `static/css/styles.css` (design tokens, components), `static/js/main.js` (hash router, auth guard), `js/api.js` (fetch wrapper: base URL, JWT header, JSON, error normalisation to toasts, 401 redirects to login), `js/ui.js` (table, modal, toast, badge, confirm dialog, form helpers, skeleton loaders, empty states), `js/pages/*.js` one module per page.

**Look and feel:** professional enterprise dashboard. Dark navy sidebar with grouped navigation (OVERVIEW, MANAGEMENT, SALES, ANALYTICS, ADMIN, DEVELOPER), light content area, top bar with page title, current user, role badge and Logout. Consistent spacing and type scale, subtle shadows, colour-coded status badges (OK green, REORDER amber, CRITICAL orange, OUT OF STOCK red), responsive layout (collapsible sidebar on mobile), accessible labels and focus states, print stylesheet for receipts. No emoji icons; use a consistent inline SVG icon set.

**Pages (hide menu items and buttons the role may not use):**
1. **Login** (username, password, demo-credentials hint, error state).
2. **Dashboard**: KPI cards (total sales, invoices, stock value, items to reorder, out of stock) and charts (sales per day line, top products bar, stock-status doughnut, revenue per store), plus a reorder preview table.
3. **Products**: searchable, sortable, paginated table; add/edit in a modal with validation; delete with confirm; barcode field; category and supplier dropdowns.
4. **Categories, Suppliers, Stores, Customers, Employees**: same table + modal pattern.
5. **Inventory**: per-store stock with status badges, filters, and an "Adjust stock" dialog (uses `/inventory/adjust`).
6. **Sales**: list with filters; **New Sale (POS style)**: pick store and customer, search and add products, quantity and discount, live totals, submit; clear error on insufficient stock; **Receipt** view (printable).
7. **Purchase Orders**: list, create, view lines, change status, **Receive** button, and "Create POs from reorder alerts".
8. **Reorder Alerts**: priority badges, supplier, suggested quantity, estimated cost, CSV export, button to create POs.
9. **Stock Ledger**: movements with filters and pagination.
10. **Reports & SQL Query Portfolio**: keep the current behaviour (dropdown grouped by category, relational algebra box, SQL box, result table, "Show EXPLAIN") for all reports including the new ones, plus a "Refresh materialized view" button.
11. **Transactions Lab** and **Optimization Lab** (admin): run each scenario and display the step log, SQL, results and the before/after query plans with timings.
12. **Database Design** page (read-only): ER overview, the 12 tables with keys, the functional dependencies and normal form per table, and the business rules (reuse the content of `docs/database_design_documentation.md`; do not retype it differently).
13. **Users** (admin): list, create, deactivate, reset password.
14. **API Docs** link to `/docs`.

Handle loading, empty and error states on every page; never show raw JSON errors to the user.

## 8. Documentation
- `README.md`: project summary, architecture diagram (browser, FastAPI, SQLAlchemy, psycopg, PostgreSQL), setup from zero, running (`python -m uvicorn app.main:app --reload`), migrations (`alembic upgrade head`, `downgrade -1`), seeding users, demo credentials, tests, lint, backup/restore, Git workflow, deployment pointer, troubleshooting (password authentication failed, PATH, `psql` not recognized, port in use).
- `docs/ARCHITECTURE.md`: layers (router, service, repository, model), request flow, transaction handling, auth flow.
- `docs/TERMS_MAPPING.md`: for **every** term in section 12, one line saying where it is demonstrated (file, endpoint, page or script). Terms that are concepts only must say how they are shown (e.g. in `pgadmin_demos.sql`).

## 9. Quality bar
Typed code, small functions, docstrings only where useful, consistent naming, no commented-out code, no unused imports, no hardcoded secrets, clear error messages, every endpoint with tags, summary and response models so Swagger UI is clean.

## 10. Database naming and safety checks
Read the database name from `DATABASE_URL` (it may contain spaces or capitals). Before any migration, print only the database name and current Alembic revision, not the URL. Never drop or recreate the schema.

## 11. Final verification (all must pass, then report)
1. `python -m alembic current` shows the latest revision (head); `upgrade head`, `downgrade -1`, `upgrade head` all work.
2. `python -m ruff check .` and `python -m pytest -q` pass.
3. App starts with `python -m uvicorn app.main:app --reload`; smoke-test login for the three roles and at least one endpoint per router, plus 401/403 cases.
4. Frontend: every page loads without console errors for the appropriate role.
5. `PROJECT_STATUS.md` fully ticked; `git status` clean after the first commit.
6. **Final report** (concise): files created or changed, migrations added, endpoint count, test results, how to run, demo credentials, what the user must still do manually (push to GitHub, optional deployment), and any assumption you made.

## 12. Terms to map in `docs/TERMS_MAPPING.md` (217)
**Database basics:** DBMS, RDBMS, Database, Table/Relation, Row/Tuple/Record, Column/Attribute/Field, Domain, Schema, Entity, Entity Set, Attribute, Relationship, Cardinality, Participation Constraint, ER Model, ERD.
**Keys and constraints:** Primary Key, Foreign Key, Candidate Key, Superkey, Composite Key, Surrogate Key, Natural Key, Referential Integrity, Entity Integrity, Constraint, NOT NULL, UNIQUE, CHECK, DEFAULT.
**Dependencies and normalization:** Functional Dependency, Partial Dependency, Transitive Dependency, Normalization, 1NF, 2NF, 3NF, BCNF, Update Anomaly, Insertion Anomaly, Deletion Anomaly, Armstrong's Axioms, Attribute Closure.
**Relational algebra:** Relational Algebra, Selection, Projection, Join, Union, Intersection, Difference, Cartesian Product.
**SQL:** DDL, DML, DQL, DCL, TCL, SQL, Query, Subquery, Join Types, Aggregate Function, GROUP BY, HAVING, CTE, View, Materialized View, Index, B-tree Index, Query Optimization, Query Plan, EXPLAIN.
**Transactions and database logic:** Transaction, ACID, Atomicity, Consistency, Isolation, Durability, COMMIT, ROLLBACK, SAVEPOINT, Concurrency, Lock, Deadlock, Isolation Level, Trigger, Stored Procedure, Function, Sequence, UUID.
**PostgreSQL and access control:** PostgreSQL, pgAdmin, psql, PostgreSQL Server, Database Instance, Role, User, RBAC, Privilege, Search Path, Public Schema, Error 23505.
**Connecting app to database:** Database Driver, psycopg/psycopg2, Connection String/Database URL, localhost, Port, Host, Client-Server Architecture, Backend, Frontend, API.
**REST and HTTP:** REST, REST API, HTTP, HTTP Request, HTTP Response, GET, POST, PUT, PATCH, DELETE, Endpoint, Route, Request Body, Response Body, JSON, Status Code.
**FastAPI, ORM, migrations:** FastAPI, REST vs FastAPI, Pydantic, Validation, Schema Model, ORM, SQLAlchemy, Model, Session, Alembic, Migration, Revision, Upgrade Migration, Downgrade Migration, First Migration, Bootstrapping, First Vertical Slice.
**Application layers and business rules:** Business Logic, Business Rule, Service Layer, Repository Layer, CRUD.
**Authentication and security:** Authentication, Authorization, Password Hashing, Token, JWT.
**Configuration and Python environment:** Environment Variable, .env File, .env.example, Secret, Virtual Environment, venv, Dependency, requirements.txt, Package Manager, pip.
**Servers and execution:** Uvicorn, ASGI, WSGI, Synchronous Execution, Asynchronous Execution, Server Process, Backend Server, Database Server, Frontend Server.
**Local development setup:** Local Development, Development Environment, Production Environment, VS Code, PowerShell, Terminal, PATH Environment Variable, psql not recognized, Local Architecture, Localhost API URL.
**API documentation and browser security:** Swagger UI, OpenAPI, API Schema, CORS.
**Git and GitHub:** Git, Repository, GitHub, Commit, Branch, Push, Pull, Clone, .gitignore.
**Quality and troubleshooting:** Linting, Testing, Unit Test, Integration Test, Health Check Endpoint, Logging, Stack Trace, Exception.
**Backup and restore:** Database Backup, Restore, SQL Dump, PostgreSQL Backup Format.
**Deployment and environments:** Deployment, Cloud Database, Neon PostgreSQL, Render, Vercel, Cloudflare, Domain Name, DNS, Environment Separation.

For concepts that cannot be a running feature (WSGI, Asynchronous Execution, Cloudflare, Vercel, Render, DNS, Domain Name, Deadlock as a theory), document them in `docs/ARCHITECTURE.md` or `docs/DEPLOYMENT.md` and point to that location in the mapping.

**Begin with Phase 0 now: inspect the repository, create `PROJECT_STATUS.md`, then proceed phase by phase without waiting for confirmation.**
