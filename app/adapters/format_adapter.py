from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd

SUPPORTED_FORMATS = {"csv", "parquet"}


def detect_format(path: str) -> str:
    suffix = Path(path).suffix.lower().replace(".", "")
    if suffix in SUPPORTED_FORMATS:
        return suffix
    if "s3://" in path or "minio://" in path:
        suffix = path.split("?")[0].split(".")[-1].lower()
        if suffix in SUPPORTED_FORMATS:
            return suffix
    raise ValueError(f"Unsupported format for '{path}'. Supported formats: {sorted(SUPPORTED_FORMATS)}")


def read_dataset(path: str) -> pd.DataFrame:
    file_format = detect_format(path)
    if file_format == "csv":
        return pd.read_csv(path)
    if file_format == "parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file format: {file_format}")


def convert_dataset(input_path: str, output_path: str, file_format: str = "parquet") -> Dict[str, Any]:
    if file_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported conversion target '{file_format}'")
    df = read_dataset(input_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if file_format == "csv":
        df.to_csv(output, index=False)
    else:
        df.to_parquet(output, index=False)
    return {
        "source": input_path,
        "target": str(output),
        "rows": int(len(df)),
        "columns": len(df.columns),
        "format": file_format,
    }


def partition_pruning(total_partitions: int, relevant_partitions: int) -> Dict[str, Any]:
    considered = max(total_partitions, 1)
    scanned = max(relevant_partitions, 0)
    pruned = max(considered - scanned, 0)
    ratio = 0.0 if considered == 0 else round(pruned / considered, 4)
    return {
        "partitions_considered": considered,
        "partitions_scanned": scanned,
        "partitions_pruned": pruned,
        "pruning_ratio": ratio,
    }
