# Retail Inventory and Sales Intelligence System

A web application and PostgreSQL database for a small chain of shops. It keeps track of how much of each product is in each store, records sales, and tells the owner which products need to be reordered, from which supplier, how many, and at what cost.

I built it as a Database Management Systems course project. The goal was to take the theory (ER design, keys, normalization, relational algebra, SQL, transactions) and turn it into something that actually runs on a laptop: a real database, a REST API, a login system and a browser interface.

## The problem it solves

Small shops usually track stock in a notebook or a spreadsheet, and two things go wrong. Either an item runs out while customers are still asking for it (a stock-out), or an item sits on the shelf for months and ties up money (dead stock).

This system keeps one live record of stock per store and works out the rest from it. Every sale reduces stock automatically, every stock change is written to a ledger, and a reorder report lists what is running low, how urgent it is, and what a restock would cost.

## What it does

- Tracks stock per product and per store, with status labels (OK, REORDER, CRITICAL, OUT OF STOCK).
- Records sales from a point-of-sale style screen. Stock and the invoice total update automatically inside one transaction, and a sale that would push stock below zero is rejected.
- Manages products, categories, suppliers, stores, customers and employees.
- Creates purchase orders (including one per supplier straight from the reorder list) and receives them into stock.
- Keeps a stock ledger of every movement: sale, purchase, adjustment.
- Shows a dashboard with sales, stock value, top products and what needs reordering.
- Has a Reports page where each query is shown as relational algebra, as SQL, with its result and its `EXPLAIN` plan.
- Includes two labs for demonstrating transactions (commit, rollback, savepoints, locks, deadlocks, isolation levels) and query optimization (before and after an index).
- Login with role-based access for admin, manager and cashier.

## Tech stack

| Layer | Technology |
|---|---|
| Database | PostgreSQL (developed on version 18), schema `retail` |
| Backend | Python, FastAPI, Uvicorn |
| Data access | SQLAlchemy 2.0 (ORM), psycopg 3 |
| Migrations | Alembic |
| Validation | Pydantic |
| Security | bcrypt password hashing, JWT tokens |
| Frontend | HTML, CSS and JavaScript (no build step), served by FastAPI |
| Tests and linting | pytest, Ruff |
| Tools | pgAdmin, VS Code, Git |

## How it fits together

```
Browser (HTML / CSS / JS)
        |  HTTP requests, JSON
        v
FastAPI  (routers -> services -> repositories)
        |  SQLAlchemy ORM
        v
psycopg driver
        |
        v
PostgreSQL  (schema "retail": tables, views, trigger, function, procedure)
```

Routers only handle HTTP, services hold the business rules, and repositories are the only place that talks to the database.

## Database design

The business data lives in 12 tables: `categories`, `suppliers`, `products`, `stores`, `inventory`, `employees`, `customers`, `sales`, `sale_items`, `purchase_orders`, `purchase_order_items` and `stock_movements`. On top of those there are a few support tables (application users and the lab tables), six SQL views and one materialized view.

A few design decisions worth knowing:

- **Stock per store.** `inventory` has a composite primary key `(store_id, product_id)`, because stock depends on both the store and the product. It is the link table of a many-to-many relationship.
- **Normalization.** The tables were designed from the business rules and functional dependencies and are in BCNF. There are two deliberate exceptions for speed and convenience: `sales.total_amount` (kept up to date by the trigger) and `sale_items.line_total` (a generated column).
- **Price at the time of sale.** `sale_items.unit_price` is copied from the product when the sale happens, so old invoices do not change when prices change.
- **Rules live in the database.** Stock cannot go negative (`CHECK`), selling price cannot be below cost, SKUs and emails are unique, and every relationship is a foreign key.
- **Automation in the database.** A trigger reduces stock and updates the invoice total after each sale line. A function receives purchase orders into stock. A stored procedure adjusts stock and logs the movement.

The longer write-up with the ER diagram, keys and dependencies is in [`docs/database_design_documentation.md`](docs/database_design_documentation.md).

## Getting started (Windows)

You need Python 3.11 or newer (developed on 3.13), PostgreSQL, Git, and optionally pgAdmin.

**1. Get the code and create a virtual environment**

```powershell
git clone https://github.com/<your-username>/retail-inventory-sales-intelligence.git
cd retail-inventory-sales-intelligence
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r fastapi_backend\requirements.txt
```

**2. Create the database and load the base schema**

In pgAdmin, create an empty database (for example `retail_inventory`), open its Query Tool, load `database/retail_inventory_sales_intelligence.sql`, select everything and run it. This creates the schema, the 12 tables, the views, the trigger, the function and the sample data.

> The script drops and recreates the `retail` schema. Run it only on a fresh database, never on one that already holds data you want to keep.

**3. Configure the environment**

```powershell
Copy-Item fastapi_backend\.env.example fastapi_backend\.env
```

Open `fastapi_backend\.env` and set `DATABASE_URL` to your own details, for example:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/retail_inventory
```

If your password contains `@` write `%40`, and if it contains `#` write `%23`. The `.env` file is ignored by Git, so your password is never committed.

**4. Apply the migrations and create the demo users**

```powershell
cd fastapi_backend
python -m alembic upgrade head
python -m app.scripts.seed_users
```

**5. Run the app**

```powershell
python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000> for the web interface and <http://127.0.0.1:8000/docs> for the interactive API documentation.

## Demo accounts

These are created by `seed_users` for local testing only. Change them before using the system for anything real.

| Username | Password | Role |
|---|---|---|
| `admin` | `Admin@123` | admin |
| `manager` | `Manager@123` | manager |
| `cashier` | `Cashier@123` | cashier |

## Who can do what

| Action | admin | manager | cashier |
|---|:---:|:---:|:---:|
| View products, stock and reports | yes | yes | products and stock only |
| Add or edit products, suppliers, categories, stores | yes | yes | no |
| Delete records | yes | no | no |
| Record sales and add customers | yes | yes | yes |
| Adjust stock, create and receive purchase orders | yes | yes | no |
| Manage users, use the labs | yes | no | no |

A request without a token gets `401`. A valid token without permission gets `403`. In the interface, menu items and buttons a role cannot use are hidden.

## Using the API

The API is documented automatically by FastAPI. On `/docs`, click **Authorize** and sign in with a demo account, then try any endpoint with **Try it out**. Typical status codes are `200` and `201` for success, `204` for a delete, `401` and `403` for access problems, `404` for a missing record, `409` for a conflict (for example a duplicate SKU) and `422` for invalid input.

## Tests, linting and migrations

From the `fastapi_backend` folder:

```powershell
python -m pytest -q          # unit and integration tests (integration tests need the local database)
python -m ruff check .       # lint
python -m alembic current    # which migration the database is on
python -m alembic downgrade -1
python -m alembic upgrade head
```

## Backup and restore

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup.ps1
```

This writes a timestamped custom-format backup (`.dump`) and a plain SQL dump (`.sql`) into `backups/`. `scripts\restore.ps1` restores a backup into a new database name, so a restore can never overwrite the live one. Backups are ignored by Git.

## Project structure

```
.
├── fastapi_backend/
│   ├── app/            routers, services, repositories, models, schemas, static frontend
│   ├── alembic/        database migrations
│   ├── scripts/        backup and restore scripts (PowerShell)
│   └── tests/          unit and integration tests
├── database/           base schema with sample data, and pgAdmin demo queries
├── docs/               architecture, deployment notes, design write-up, terminology mapping
└── dashboard/          an earlier Streamlit prototype
```

## More documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): layers, request flow, transactions and authentication
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md): notes on deploying (Neon, Render, Vercel) and on keeping development and production separate
- [`docs/TERMS_MAPPING.md`](docs/TERMS_MAPPING.md): where each course term is demonstrated in the project
- [`database/pgadmin_demos.sql`](database/pgadmin_demos.sql): queries for demonstrating transactions, locks, `EXPLAIN` and more directly in pgAdmin

<!--
Screenshots: save images in docs/screenshots/ and delete these comment markers to show them.

![Dashboard](docs/screenshots/dashboard.png)
![New sale](docs/screenshots/new-sale.png)
![Reports and SQL](docs/screenshots/reports.png)
![API docs](docs/screenshots/api-docs.png)
-->

## Limitations and ideas

This is a course project, so some things are intentionally simple: each product has one supplier, there is no returns workflow, prices are in a single currency (PKR), and there are no email or SMS alerts. The application has been run and tested locally; the deployment notes are documentation and the project is not deployed.

Possible next steps are multi-supplier pricing, returns, batch and expiry tracking, automatic purchase orders from the reorder list, and low-stock notifications.

## Author

Built by **[MAHAM WASEEM]** for the Database Management Systems course.
