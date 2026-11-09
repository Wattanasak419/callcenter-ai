# Cloud deployment guide

The production entry point is `backend.main:app`.

## Runtime

Run the service with:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Required production configuration should be supplied through environment variables rather than committed files. Start from `.env.example`.

- `CALLCENTER_AUTH_SECRET`: use a long random secret.
- `CALLCENTER_COOKIE_SECURE=1`: enable when the site is served over HTTPS.
- `DATABASE_URL`: local development can use SQLite. For a real cloud deployment, use a managed PostgreSQL database or another persistent SQL service.
- `PORT`: normally injected by the hosting platform.

## Persistent data

SQLite (`callcenter.db`) is suitable for local development only unless the cloud host provides a persistent volume. Ephemeral containers can lose local files during deploys/restarts. A managed PostgreSQL database is recommended for production.

Uploaded call audio is currently stored under `backend/uploads`. Cloud deployment therefore also requires persistent storage for that directory, or a future object-storage adapter (for example S3). Do not rely on an ephemeral container filesystem for production recordings.

## Health checks

The application exposes:

- `GET /healthz` — process health.
- `GET /readyz` — database readiness.

Configure the cloud platform to use these endpoints for health/readiness checks.

## Data migration behavior

On startup, the review migration adds reversible `is_active` flags to records and employee accounts when an older SQLite database is detected. Legacy `deleted`, `pending_delete`, and `disabled` case states are migrated to inactive records instead of physically deleting data. AI processing status (`processing`, `done`, `failed`) remains separate from Enable/Disable state.

Back up the database before the first production migration.

## Security checklist

Use HTTPS, set `CALLCENTER_COOKIE_SECURE=1`, rotate the authentication secret, keep `.env` and database backups out of Git, restrict database network access, and use the Permission Matrix for least-privilege access. IT is intended to administer accounts/permissions/system settings; customer operations remain with Staff and Supervisor unless permissions are deliberately changed.
