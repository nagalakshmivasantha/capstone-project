# AI Data Quality Gateway

A production-like offline feature-data quality platform for CSV, Parquet and MinIO/S3-style tabular data.

## What this project includes
- canonical feature schema and validation contract
- point-in-time retrieval with independent oracle baseline
- leakage detection and validation
- schema inference, drift detection, and repair recommendation logic
- quality profiling and rule evaluation
- format conversion and partition-pruning diagnostics
- deterministic cache and lineage manifests
- MinIO-compatible local simulation adapter
- FastAPI service and CLI
- benchmark, acceptance, and evidence reporting

## Supported formats
- Local CSV
- Local Parquet
- MinIO/S3-compatible CSV
- MinIO/S3-compatible Parquet
- Any additional format remains explicitly TBD

## Quick start

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m app.cli --help
```

## CLI examples

```bash
python -m app.cli ingest tests/fixtures/events.csv
python -m app.cli infer-schema tests/fixtures/features.csv
python -m app.cli profile tests/fixtures/features.csv
python -m app.cli validate tests/fixtures/features.csv
python -m app.cli retrieve tests/fixtures/events.csv tests/fixtures/features.csv
python -m app.cli detect-leakage tests/fixtures/events.csv tests/fixtures/features.csv
python -m app.cli benchmark
python -m app.cli acceptance
python -m scripts.generate_parquet_fixtures
python -m scripts.minio_setup
```

## API

```bash
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8001
```

## Dashboard

The dashboard uses React, Vite, and Chart.js. Install Node.js 22.12+ with npm, then build the frontend before starting FastAPI:

```bash
cd app/frontend
npm ci
npm run build
cd ../..
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8001
```

Open [the dashboard](http://127.0.0.1:8001/dashboard) for dataset uploads, inspection and repairs, quality trends, alerts, lineage, governance checks, and MinIO inventory.

For frontend development, keep the API running on port 8001. Run `npm run dev` from `app/frontend` and open the URL Vite prints. The development server proxies dashboard requests to FastAPI. Set `DASHBOARD_API_URL` before starting Vite to use another backend URL.

## Docker

```bash
docker compose -f docker/docker-compose.yml up --build
```

## S3 / MinIO integration

The gateway uses the S3 API through `boto3`. It defaults to `MINIO_MODE=auto`: it connects to the configured endpoint when available and falls back to the local `app/minio_data` simulator for offline development.

For a real MinIO or S3-compatible deployment:

```text
MINIO_MODE=real
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

Storage API routes:

- `GET /storage/minio`
- `GET /storage/minio/objects`
- `POST /storage/minio/buckets`
- `POST /storage/minio/upload`
- `POST /storage/minio/download`

Example upload payload:

```json
{
  "bucket": "features",
  "file_path": "tests/fixtures/features.parquet",
  "object_name": "daily/features.parquet"
}
```

## Production operations

The gateway now includes:

- durable SQLite metadata and audit events (`QUALITY_DB_PATH`), with a clean seam for PostgreSQL
- optional API-key authentication using `QUALITY_API_KEY`
- asynchronous validation jobs with bounded retries
- webhook notification testing through `QUALITY_WEBHOOK_URL`
- Prometheus-compatible metrics at `/metrics/prometheus`
- Kubernetes deployment and readiness/liveness probes in `docker/kubernetes.yaml`
- Prometheus scrape configuration in `docker/prometheus.yml`

Operational endpoints:

- `GET /audit`
- `POST /jobs/validate`
- `GET /jobs/{job_id}`
- `POST /notifications/test`
- `GET /metrics/prometheus`

Enable authentication in a deployment:

```text
QUALITY_API_KEY=replace-with-a-secret
QUALITY_DB_PATH=/var/lib/quality-gateway/platform.db
QUALITY_JOB_WORKERS=4
QUALITY_JOB_MAX_ATTEMPTS=3
QUALITY_WEBHOOK_URL=https://example.invalid/quality-events
```

Protected requests must send `X-API-Key`. Health, metrics, and the dashboard shell remain available for probes and operations discovery.

## MySQL connection

The platform can inspect the MySQL database configured through environment variables:

```text
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=capstone
MYSQL_USER=root
MYSQL_PASSWORD=<set-locally>
```

Do not commit `MYSQL_PASSWORD` or send it in chat. On Windows PowerShell, set it only in your local process/session:

```powershell
$env:MYSQL_PASSWORD = "your-local-password"
```

Alternatively, copy `.env.example` to `.env` and fill in `MYSQL_PASSWORD` locally. The `.env` file is ignored by Git and is loaded automatically when the API starts.

For a hidden password prompt on Windows PowerShell, run:

```powershell
.\scripts\configure_mysql.ps1
```

To create the `capstone` database, create the project-owned tables, and load the repository fixtures, run:

```powershell
.\scripts\setup_mysql.ps1
```

The setup is idempotent for the project-owned fixture tables (`events` and `features`) and does not drop unrelated tables.

After setup, sync registered dataset metadata and quality results into MySQL:

```powershell
.\.venv\Scripts\python.exe .\scripts\sync_mysql_platform.py
```

The dashboard supports a real file-upload workflow. In **Connect a dataset**, select a CSV or Parquet file and optionally provide a dataset ID. The gateway stores the upload in configured object storage, evaluates it, writes `platform_datasets`, `quality_runs`, and an audit event to MySQL, then refreshes the inventory. The legacy JSON endpoint `POST /dashboard/datasets/register` remains available for integrations that already have a server-side file path.

Database verification endpoints:

- `GET /database/health`
- `GET /database/tables`
- `GET /database/snapshot`
