# Database-to-local-development terms mapping

Every requested term is mapped below to a concrete schema, code location, endpoint,
UI page, demo script, or explanation. Conceptual terms that are not executable are
described in `ARCHITECTURE.md` or `DEPLOYMENT.md`.

## Database basics

| Term | Demonstrated at |
|---|---|
| DBMS | PostgreSQL setup and operation, `ARCHITECTURE.md` |
| RDBMS | `database/retail_inventory_sales_intelligence.sql`, 12 related tables |
| Database | Local connection from `fastapi_backend/.env` |
| Table/Relation | The 12 base tables in `database/retail_inventory_sales_intelligence.sql` |
| Row/Tuple/Record | `retail.products` records returned by `GET /products` |
| Column/Attribute/Field | Product fields in `app/models.py` and `/products` |
| Domain | SQL column types and Pydantic fields in `app/schemas.py` |
| Schema | PostgreSQL schema `retail` in the SQL setup and Alembic revisions |
| Entity | `docs/database_design_documentation.md`, Entity Sets |
| Entity Set | `docs/database_design_documentation.md`, Entity Sets table |
| Attribute | `docs/database_design_documentation.md`, Relational Model |
| Relationship | ER model and FK relationships in `docs/database_design_documentation.md` |
| Cardinality | ERD one-to-many and many-to-many links in `docs/database_design_documentation.md` |
| Participation Constraint | Required `NOT NULL` foreign keys in the schema SQL |
| ER Model | `docs/database_design_documentation.md`, ER Diagram |
| ERD | `docs/database_design_documentation.md`, Mermaid ER diagram |

## Keys and constraints

| Term | Demonstrated at |
|---|---|
| Primary Key | Primary key declarations in the 12 retail tables |
| Foreign Key | FK declarations in `database/retail_inventory_sales_intelligence.sql` |
| Candidate Key | Unique `sku`, `barcode`, username, and natural-name columns |
| Superkey | `product_id` plus any subset of product attributes, schema described in `docs/database_design_documentation.md` |
| Composite Key | `retail.inventory(store_id, product_id)` in the schema and `app/models.py` |
| Surrogate Key | Identity primary keys such as `product_id` and `sale_id` |
| Natural Key | `products.sku` and the unique username in `0003_app_users` |
| Referential Integrity | Foreign keys and `ON DELETE` rules in the base schema |
| Entity Integrity | Non-null primary keys in all tables |
| Constraint | CHECK/UNIQUE/FK definitions in base SQL and migration SQL |
| NOT NULL | Required columns throughout `database/retail_inventory_sales_intelligence.sql` |
| UNIQUE | SKU, category name, emails, lab item name, user name, and barcode |
| CHECK | Prices, quantities, role and status constraints in schema and `schemas.py` |
| DEFAULT | `now()`, generated identities, default quantities, and statuses in SQL |

## Dependencies and normalization

| Term | Demonstrated at |
|---|---|
| Functional Dependency | `docs/database_design_documentation.md`, keys and business entities |
| Partial Dependency | `docs/database_design_documentation.md`, normalization explanation |
| Transitive Dependency | `docs/database_design_documentation.md`, normalization explanation |
| Normalization | `docs/database_design_documentation.md`, table separation |
| 1NF | Atomic attributes and one value per cell in the retail tables |
| 2NF | `inventory` composite key and full-key dependency, `docs/database_design_documentation.md` |
| 3NF | Lookup entities separate category, supplier, store, and customer attributes |
| BCNF | Concept and key determinants explained in `docs/database_design_documentation.md` |
| Update Anomaly | Avoided by storing supplier/category/store facts in separate entities |
| Insertion Anomaly | Avoided by independent supplier/category/customer tables |
| Deletion Anomaly | Avoided by independent entities and explicit FK delete rules |
| Armstrong's Axioms | Conceptual dependency reasoning in `docs/ARCHITECTURE.md` and database design notes |
| Attribute Closure | Conceptual key derivation explained in `docs/ARCHITECTURE.md` |

## Relational algebra

| Term | Demonstrated at |
|---|---|
| Relational Algebra | Report portfolio (`GET /reports`, Reports page) |
| Selection | `selection` and `cheap` reports, `app/reports.py` |
| Projection | `projection` report, `app/reports.py` |
| Join | `join` and `leftjoin` reports |
| Union | `union` report |
| Intersection | `intersection` report |
| Difference | `difference` report |
| Cartesian Product | `cartesian` report |

## SQL

| Term | Demonstrated at |
|---|---|
| DDL | Alembic `0003_app_users.py` and `0004_db_objects.py` |
| DML | Product, customer, sale, and purchase-order API mutations |
| DQL | `/reports/{report_id}` and `app/reports.py` |
| DCL | `database/pgadmin_demos.sql`, DCL section |
| TCL | Transactions Lab and `database/pgadmin_demos.sql`, TCL section |
| SQL | Reports page SQL panel and `app/reports.py` |
| Query | `GET /reports/{report_id}` |
| Subquery | `subquery` report in `app/reports.py` |
| Join Types | `leftjoin`, `rightjoin`, `fulljoin`, and `cartesian` reports |
| Aggregate Function | `COUNT`, `SUM`, and `AVG` in report queries |
| GROUP BY | `groupby`, dashboard, and `movement_types` report |
| HAVING | `having` report in `app/reports.py` |
| CTE | `cte` report in `app/reports.py` |
| View | `retail.v_reorder_list` and `retail.v_stock_status` |
| Materialized View | `retail.mv_monthly_sales`, `POST /reports/materialized/refresh` |
| Index | The 12 base indexes and `0004_db_objects.py` unique index |
| B-tree Index | Optimization Lab temporary B-tree on `lab_orders.customer_ref` |
| Query Optimization | Optimization Lab page and `/labs/optimization/run` |
| Query Plan | Reports EXPLAIN action and Optimization Lab |
| EXPLAIN | `/reports/{report_id}?explain=true` and EXPLAIN ANALYZE lab |

## Transactions and database logic

| Term | Demonstrated at |
|---|---|
| Transaction | Sales API transaction and Transactions Lab |
| ACID | `docs/ARCHITECTURE.md`, transaction explanation |
| Atomicity | Sale header/lines committed or rolled back as one transaction |
| Consistency | Database constraints plus sale trigger |
| Isolation | `/labs/transactions/isolation` and two-tab pgAdmin instructions |
| Durability | Transactions Lab COMMIT scenario |
| COMMIT | `/labs/transactions/commit` |
| ROLLBACK | `/labs/transactions/rollback` |
| SAVEPOINT | `/labs/transactions/savepoint` |
| Concurrency | Isolation and lock demos with multiple database connections |
| Lock | `/labs/transactions/locks`, `FOR UPDATE` / `NOWAIT` |
| Deadlock | `/labs/transactions/deadlock`, SQLSTATE 40P01 |
| Isolation Level | `SHOW transaction_isolation` and isolation Lab |
| Trigger | Existing `trg_sale_item_after_insert` and sale flow |
| Stored Procedure | `retail.sp_adjust_stock` and `/inventory/adjust` |
| Function | Existing `retail.receive_purchase_order` and PO receive route |
| Sequence | Identity columns and sequence grants in Alembic migration |
| UUID | `app_users.public_id` default in `0003_app_users.py` |

## PostgreSQL and access control

| Term | Demonstrated at |
|---|---|
| PostgreSQL | Configured backend connection and `GET /health/db` |
| pgAdmin | `database/pgadmin_demos.sql` header run instructions |
| psql | Backup/restore scripts and `Tools > PSQL Tool` instructions |
| PostgreSQL Server | `GET /health/db` reports the connected server version |
| Database Instance | Local PostgreSQL server connection in `fastapi_backend/.env` |
| Role | `role_admin`, `role_manager`, and `role_cashier` grants |
| User | `retail.app_users` and Users admin page |
| RBAC | `app/deps.py` and role-specific SPA navigation |
| Privilege | Guarded grants in migrations and DCL demo |
| Search Path | `SET search_path` in the provided base schema SQL |
| Public Schema | `docs/ARCHITECTURE.md` describes application objects scoped to `retail` |
| Error 23505 | `/labs/transactions/unique-violation` and HTTP 409 duplicate response |

## Connecting app to database

| Term | Demonstrated at |
|---|---|
| Database Driver | psycopg 3 configured in `app/database.py` |
| psycopg/psycopg2 | `requirements.txt` uses `psycopg[binary]` (psycopg 3) |
| Connection String/Database URL | `DATABASE_URL` setting in `.env.example` |
| localhost | Local development URL examples in `.env.example` |
| Port | Database URL and Uvicorn port in README setup |
| Host | Database URL and `GET /health/db` connection |
| Client-Server Architecture | `docs/ARCHITECTURE.md` |
| Backend | FastAPI application in `app/main.py` |
| Frontend | Structured SPA in `app/static/` |
| API | Swagger/OpenAPI at `/docs` |

## REST and HTTP

| Term | Demonstrated at |
|---|---|
| REST | API resource paths and HTTP verbs |
| REST API | FastAPI endpoints listed in Swagger |
| HTTP | Browser-to-FastAPI calls in `static/js/api.js` |
| HTTP Request | JSON and OAuth2 form submissions in `static/js/api.js` |
| HTTP Response | API response body handling in `static/js/api.js` |
| GET | Read/list routes such as `GET /products` |
| POST | Create routes such as `POST /sales` |
| PUT | Replace routes such as `PUT /products/{product_id}` |
| PATCH | Partial product and PO status updates |
| DELETE | Product and directory delete routes |
| Endpoint | Named route functions in `app/routers/` |
| Route | Hash route registry in `static/js/main.js` |
| Request Body | Pydantic payloads in `app/schemas.py` |
| Response Body | Router response models and mapped result objects |
| JSON | API wrapper request/response normalization |
| Status Code | Explicit 201/204/401/403/404/409/422 responses |

## FastAPI, ORM, migrations

| Term | Demonstrated at |
|---|---|
| FastAPI | App construction in `app/main.py` |
| REST vs FastAPI | `docs/ARCHITECTURE.md`, HTTP framework and REST API roles |
| Pydantic | Validation models in `app/schemas.py` |
| Validation | Constrained fields and price/cost validator in `schemas.py` |
| Schema Model | Product and request schemas in `app/schemas.py` |
| ORM | SQLAlchemy models in `app/models.py` |
| SQLAlchemy | Engine, session, Base, and models |
| Model | `Product`, `Sale`, and other classes in `app/models.py` |
| Session | Request-scoped `get_db` in `app/database.py` |
| Alembic | `fastapi_backend/alembic/` |
| Migration | Revisions `0003_app_users` and `0004_db_objects` |
| Revision | `revision` declarations in migration files |
| Upgrade Migration | `upgrade()` in the two additive revisions |
| Downgrade Migration | `downgrade()` in the two additive revisions |
| First Migration | Historical migration was absent; caveat and safe add-only history in `docs/README.md` |
| Bootstrapping | Setup sequence in `docs/README.md` |
| First Vertical Slice | Existing Products endpoints and CRUD in `app/routers/resources.py` |

## Application layers and business rules

| Term | Demonstrated at |
|---|---|
| Business Logic | Sale, PO, and stock routes in `app/routers/operations.py` |
| Business Rule | Price/cost, stock, PO status, and role validations |
| Service Layer | Business operation modules under `app/services/` and transaction flow |
| Repository Layer | Parameterized query helpers in `app/repositories/queries.py` |
| CRUD | Product and directory routers in `app/routers/resources.py` |

## Authentication and security

| Term | Demonstrated at |
|---|---|
| Authentication | Login route and login page |
| Authorization | `get_current_user`, `require_roles`, and access matrix |
| Password Hashing | bcrypt helpers in `app/security.py` |
| Token | OAuth2 bearer token response from `/auth/login` |
| JWT | HS256 token creation and validation in `app/security.py` |

## Configuration and Python environment

| Term | Demonstrated at |
|---|---|
| Environment Variable | `app/config.py` settings |
| .env File | Private local `fastapi_backend/.env` |
| .env.example | `fastapi_backend/.env.example` |
| Secret | `JWT_SECRET`; private and excluded from version control |
| Virtual Environment | Workspace `.venv` in README setup |
| venv | PowerShell Python executable in `docs/README.md` |
| Dependency | `fastapi_backend/requirements.txt` |
| requirements.txt | Dependency manifest under `fastapi_backend/` |
| Package Manager | pip commands in `docs/README.md` |
| pip | `python -m pip install -r requirements.txt` |

## Servers and execution

| Term | Demonstrated at |
|---|---|
| Uvicorn | README launch command |
| ASGI | FastAPI/Uvicorn runtime described in `docs/ARCHITECTURE.md` |
| WSGI | Difference noted in `docs/ARCHITECTURE.md` |
| Synchronous Execution | Synchronous SQLAlchemy endpoints, `docs/ARCHITECTURE.md` |
| Asynchronous Execution | Async request logging middleware in `app/main.py`; execution concepts in `docs/ARCHITECTURE.md` |
| Server Process | Uvicorn process in README setup |
| Backend Server | FastAPI deployment instructions in `docs/DEPLOYMENT.md` |
| Database Server | PostgreSQL health check and architecture diagram |
| Frontend Server | FastAPI static serving or separate Vercel arrangement in `docs/DEPLOYMENT.md` |

## Local development setup

| Term | Demonstrated at |
|---|---|
| Local Development | README setup instructions |
| Development Environment | `.env.development.example` and deployment guide |
| Production Environment | `.env.production.example` and deployment guide |
| VS Code | Project workflow and integrated terminal setup in README |
| PowerShell | All setup, test, migration, and backup command examples |
| Terminal | Command-line setup in README |
| PATH Environment Variable | PostgreSQL tool troubleshooting in README |
| psql not recognized | Troubleshooting guidance in README |
| Local Architecture | `docs/ARCHITECTURE.md` |
| Localhost API URL | `http://127.0.0.1:8000/` in README |

## API documentation and browser security

| Term | Demonstrated at |
|---|---|
| Swagger UI | `/docs` and sidebar API Documentation link |
| OpenAPI | FastAPI-generated schema at `/openapi.json` |
| API Schema | Pydantic schemas and OpenAPI docs |
| CORS | `CORSMiddleware` and `CORS_ORIGINS` configuration |

## Git and GitHub

| Term | Demonstrated at |
|---|---|
| Git | Git workflow section in `docs/README.md` |
| Repository | Repository setup instructions in `docs/README.md` |
| GitHub | Remote URL and workflow examples in `docs/README.md` |
| Commit | `git commit` example in README |
| Branch | `feature/<short-name>` workflow in README |
| Push | `git push` examples in README |
| Pull | `git pull --rebase` example in README |
| Clone | `git clone` example in README |
| .gitignore | `fastapi_backend/.gitignore` |

## Quality and troubleshooting

| Term | Demonstrated at |
|---|---|
| Linting | Ruff configuration and command in README |
| Testing | pytest command and `tests/` suite |
| Unit Test | `tests/test_unit.py` |
| Integration Test | `tests/test_integration.py` |
| Health Check Endpoint | `/health` and `/health/db` |
| Logging | `app/logging_config.py` and request middleware |
| Stack Trace | Logged unexpected exception handler in `app/main.py` |
| Exception | Global clean JSON error handling in `app/main.py` |

## Backup and restore

| Term | Demonstrated at |
|---|---|
| Database Backup | `fastapi_backend/scripts/backup.ps1` |
| Restore | `fastapi_backend/scripts/restore.ps1` creates a new DB |
| SQL Dump | Timestamped plain SQL dump from `backup.ps1` |
| PostgreSQL Backup Format | Timestamped custom-format `-Fc` dump from `backup.ps1` |

## Deployment and environments

| Term | Demonstrated at |
|---|---|
| Deployment | `docs/DEPLOYMENT.md` |
| Cloud Database | Managed database guidance in `docs/DEPLOYMENT.md` |
| Neon PostgreSQL | Neon connection setup and SSL requirement in `docs/DEPLOYMENT.md` |
| Render | Backend deployment instructions in `docs/DEPLOYMENT.md` |
| Vercel | Separate frontend instructions in `docs/DEPLOYMENT.md` |
| Cloudflare | DNS/proxy discussion in `docs/DEPLOYMENT.md` |
| Domain Name | Domain setup in `docs/DEPLOYMENT.md` |
| DNS | DNS routing explanation in `docs/DEPLOYMENT.md` |
| Environment Separation | Development/testing/production table in `docs/DEPLOYMENT.md` |
