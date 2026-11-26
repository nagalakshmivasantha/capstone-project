# Evidence manifest

Each query result should include the following lineage metadata:

- dataset_id
- source
- source_version
- schema_version
- configuration_version
- query_id
- software_version
- retrieval_timestamp
- transformation
- result_hash

This repository includes a basic lineage manifest creator in `app/lineage/lineage.py`.
