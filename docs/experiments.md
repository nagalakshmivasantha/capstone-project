# AI Data Quality Gateway

## End-to-end workflow

1. Register a dataset.
2. Infer and validate schema.
3. Profile quality and run rules.
4. Run leakage and point-in-time retrieval checks.
5. Generate benchmark and acceptance evidence.
6. Reproduce with CLI or Docker.

## Supported formats
- Local CSV
- Local Parquet
- MinIO/S3-style object-store CSV
- MinIO/S3-style object-store Parquet
- Any additional format remains explicitly TBD

## Commands

```bash
python -m app.cli ingest tests/fixtures/events.csv
python -m app.cli infer-schema tests/fixtures/features.csv
python -m app.cli profile tests/fixtures/features.csv
python -m app.cli validate tests/fixtures/features.csv
python -m app.cli retrieve tests/fixtures/events.csv tests/fixtures/features.csv
python -m app.cli detect-leakage tests/fixtures/events.csv tests/fixtures/features.csv
python -m app.cli benchmark
python -m app.cli acceptance
```

## API endpoints

```bash
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8001
```

Then call:
- GET /health
- GET /metrics
- POST /datasets/register
- POST /datasets/profile
- POST /datasets/validate
- POST /retrieve
- POST /validate/leakage
- POST /validate/schema
- POST /recovery/replay
- POST /recovery/quarantine
