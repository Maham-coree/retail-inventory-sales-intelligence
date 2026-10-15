# Retail Inventory and Sales Intelligence System

FastAPI application for a PostgreSQL retail inventory database, with authenticated
operations, reporting, and isolated database labs.

## Architecture

```text
Browser (HTML/CSS/ES modules) → FastAPI routers → services/repositories → SQLAlchemy
                                                                  ↓ psycopg 3
                                                           PostgreSQL / retail
```

The existing relational schema has 12 retail tables, six reporting views, a sale
trigger, and a purchase-receiving function. The browser dashboard is served from
`fastapi_backend/app/static/`; Chart.js is loaded from its pinned CDN build.

## Setup and run

1. Install PostgreSQL and provision the existing `retail` business schema in a
   development database. The supplied SQL setup file contains `DROP SCHEMA` and is
   intentionally not part of the migration workflow. Never run it against a
   database that contains data.
2. Copy `fastapi_backend/.env.example` to `fastapi_backend/.env` and set
   `DATABASE_URL`. The local `.env` is ignored and must not be committed.
3. Install Python dependencies in the workspace virtual environment:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r fastapi_backend\requirements.txt
   ```

4. From `fastapi_backend`, apply the additive application migrations and create
   demo accounts:

   ```powershell
   ..\.venv\Scripts\python.exe -m alembic upgrade head
   ..\.venv\Scripts\python.exe -m app.scripts.seed_users
   ..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
   ```

5. Open `http://127.0.0.1:8000/`. Swagger UI is at `/docs`.

The current workspace did not contain the historical `0001_baseline` and
`0002_add_barcode` migration files. To avoid inventing or editing those forbidden
revisions, `0003_app_users` is a root revision and creates only the additive
application objects. Inspection also showed that the supplied live schema did not
have `products.barcode`; `0005_add_barcode` adds that missing column without
rewriting the unavailable historical revisions. The chain assumes the existing
12-table `retail` schema is already present. On a clean database,
restore/provision that approved base schema before running these additions.

## Demo sign-in accounts

Run the idempotent seed command above, then use:

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin@123` |
| Manager | `manager` | `Manager@123` |
| Cashier | `cashier` | `Cashier@123` |

These are classroom demo credentials, not production credentials. Replace or
deactivate them before deployment. Passwords are stored as bcrypt hashes.

## Database migrations

From `fastapi_backend`:

```powershell
..\.venv\Scripts\python.exe -m alembic current
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic downgrade -1
..\.venv\Scripts\python.exe -m alembic upgrade head
```

`0003_app_users` adds the app-user table; `0004_db_objects` adds the materialized
view, stock procedure, and lab tables; `0005_add_barcode` adds a nullable unique
barcode to products. Downgrading one revision removes only objects from that
revision.

## Tests and lint

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m ruff check .
```

Unit tests do not need PostgreSQL. Integration tests are marked `integration` and
skip when the configured database cannot be reached. They use `TEST-` product
SKUs and clean up their sale/product test records.

## Backup and restore

From `fastapi_backend`:

```powershell
.\scripts\backup.ps1
.\scripts\restore.ps1 -NewDatabaseName RetailRestoreTest -BackupFile .\backups\retail-<timestamp>.dump
```

The backup script produces custom and plain SQL dumps in the ignored `backups/`
folder. Restore always creates a new database; it never targets the source
database for restoration. Verify a restored backup before relying on it.

## Git workflow

The workspace did not have a Git repository, and this implementation is scoped to
`fastapi_backend/`, `database/`, and `docs/`; therefore no root `.git` metadata or
commit was created. When the project owner initializes the repository, use:

```powershell
git init -b main
git add fastapi_backend database docs
git commit -m "Complete retail inventory application"
git remote add origin https://github.com/<owner>/<repository>.git
git push -u origin main
git switch -c feature/<short-name>
git add .
git commit -m "Describe the change"
git push -u origin feature/<short-name>
git pull --rebase origin main
git clone https://github.com/<owner>/<repository>.git
```

Do not add `.env`, `.venv`, `logs/`, or `backups/` to Git. The backend
`.gitignore` covers these paths and generated Python/test artifacts.

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for Render, Neon, a separate Vercel frontend,
Cloudflare/DNS, CORS, and environment separation.

## Troubleshooting

- **Password authentication failed:** check the local `DATABASE_URL` username,
  password, host, port, and database with your local PostgreSQL administrator.
  Do not paste credentials into issue reports or logs.
- **`psql` is not recognized:** the backup scripts locate PostgreSQL executables
  under `C:\Program Files\PostgreSQL\<version>\bin`; for manual use, invoke the
  executable by its full path or add that `bin` directory to the current
  PowerShell `PATH`.
- **Port already in use:** run Uvicorn with another port, for example
  `--port 8001`, and update the local CORS origin if needed.
- **401 or 403 response:** authenticate in the app or Swagger's Authorize dialog,
  and verify the account role has permission for that route.
- **Migration reports missing base objects:** the two historical migrations
  were absent from this workspace. Ensure the approved base schema has been
  provisioned before applying `0003` and `0004`.
