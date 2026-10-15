# Deployment preparation

This document describes deployment only. No cloud resources have been created and
the application has not been deployed.

## Render backend

1. Create a Render Web Service for the `fastapi_backend` directory (or configure
   the repository root and set the service root to `fastapi_backend`).
2. Install using `pip install -r requirements.txt`.
3. Set the start command exactly to:

   ```sh
   python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

4. Configure `APP_ENV=production`, `DATABASE_URL`, a cryptographically random
   `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, and `CORS_ORIGINS` in Render's environment
   settings. Never deploy `.env` or place credentials in source.
5. Use a managed PostgreSQL database such as Neon. Its `DATABASE_URL` should use
   the psycopg driver form and include `sslmode=require`, for example
   `postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require`. Keep values in
   the provider's secret settings, not in logs or documentation.
6. Provision the approved base `retail` schema, then apply the additive Alembic
   revisions and seed/replace app users under an explicit production policy.

## Separate Vercel frontend

The current frontend is served by FastAPI at `/static/`. If a separate frontend
is later built/deployed on Vercel, configure its API base URL to the Render
service and set backend `CORS_ORIGINS` to the exact HTTPS Vercel origin(s). Avoid
wildcard origins when bearer credentials are used. The API wrapper uses a
same-origin base by default; a separately hosted version can set
`window.RETAIL_API_BASE` before the ES-module entrypoint.

## Cloudflare, DNS, and domain

Register or select a domain, configure DNS records to point the desired hostnames
to the frontend/backend providers, and optionally use Cloudflare for DNS and
proxying. Configure TLS at the providers and verify CORS, health checks, and
redirects after DNS propagation. DNS maps names to services; it does not host the
FastAPI code or PostgreSQL data.

## Environment separation

- **Development:** local `.env` and a non-production database; localhost CORS.
- **Testing:** isolated disposable data/database and test-only accounts; no
  production secrets.
- **Production:** provider-managed environment variables, production database,
  unique JWT secret, exact CORS origins, backups, and restricted DB privileges.

Do not reuse database passwords, JWT secrets, or mutable test data across these
environments. Rotate demo passwords and disable unused demo accounts before
production use.
