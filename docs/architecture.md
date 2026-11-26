# Architecture overview

## Gateway pipeline

CSV / Parquet / Object Store
  -> Source / Format Adapter
  -> Schema + Semantics Inference
  -> Quality Gateway
  -> Format Conversion / Optimization
  -> Partition Pruning + Cache
  -> Point-in-Time Feature Retrieval
  -> Leakage Detection / Validation
  -> Features for Downstream ML
  -> Lineage + Telemetry + Reconciliation

## Key design choices

- Supported format matrix is deliberately frozen to local CSV/Parquet and MinIO/S3 CSV/Parquet.
- The point-in-time retrieval engine and the independent oracle are separated by implementation and tests.
- Schema inference produces confidence and routes ambiguous fields to quarantine or explicit human intervention.
- Quality assertions are versioned and partition aware, preventing globally healthy averages from hiding defective data partitions.
- Every result carries lineage metadata and a reproducible request identifier.
