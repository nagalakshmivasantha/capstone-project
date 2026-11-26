from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from app.adapters.format_adapter import read_dataset
from app.quality.inference import infer_schema
from app.quality.profiling import profile_dataset
from app.quality.rules import assess_ml_safety, evaluate_quality_rules


def apply_repair(
    dataset_path: str,
    column: str,
    method: str,
    segment_column: Optional[str] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Apply a repair strategy to a dataset and return the repaired quality summary."""
    df = read_dataset(dataset_path)
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in dataset")

    original_missing = int(df[column].isna().sum())
    before_quality = profile_dataset(df)

    repaired = df.copy()

    if method == "mean":
        if not pd.api.types.is_numeric_dtype(repaired[column]):
            raise ValueError("Mean imputation requires a numeric column")
        mean_val = repaired[column].mean()
        repaired[column] = repaired[column].fillna(mean_val)
        details = {"imputed_value": float(mean_val), "rows_imputed": original_missing}

    elif method == "median":
        if not pd.api.types.is_numeric_dtype(repaired[column]):
            raise ValueError("Median imputation requires a numeric column")
        median_val = repaired[column].median()
        repaired[column] = repaired[column].fillna(median_val)
        details = {"imputed_value": float(median_val), "rows_imputed": original_missing}

    elif method == "segment_median":
        if not segment_column:
            candidates = [
                name for name in repaired.columns
                if name != column and not pd.api.types.is_numeric_dtype(repaired[name])
            ]
            if not candidates:
                raise ValueError("No segment column available for segment-level imputation")
            segment_column = candidates[0]
        if segment_column not in repaired.columns:
            raise ValueError(f"Segment column '{segment_column}' not found")
        if not pd.api.types.is_numeric_dtype(repaired[column]):
            raise ValueError("Segment median imputation requires a numeric column")

        segment_medians: Dict[Any, float] = {}
        per_segment: List[Dict[str, Any]] = []
        for seg_value, group in repaired.groupby(segment_column, dropna=False, observed=True):
            med = group[column].median()
            if pd.notna(med):
                segment_medians[seg_value] = float(med)
            per_segment.append({
                "segment": str(seg_value),
                "group_median": float(med) if pd.notna(med) else None,
                "missing_in_group": int(group[column].isna().sum()),
                "group_size": int(len(group)),
            })

        def _fill(seg_value: Any, value: Any) -> Any:
            if pd.notna(value):
                return value
            return segment_medians.get(seg_value, repaired[column].median())

        repaired[column] = [
            _fill(seg, val) for seg, val in zip(repaired[segment_column], repaired[column])
        ]
        details = {
            "segment_column": segment_column,
            "per_segment": per_segment,
            "rows_imputed": original_missing,
        }

    elif method == "drop":
        before = len(repaired)
        repaired = repaired.dropna(subset=[column]).reset_index(drop=True)
        details = {"rows_dropped": before - len(repaired), "remaining_rows": len(repaired)}

    else:
        raise ValueError(f"Unknown repair method: {method}")

    after_profile = profile_dataset(repaired)
    after_schema = infer_schema(repaired)
    after_rules = evaluate_quality_rules(repaired, after_schema)
    after_safety = assess_ml_safety(repaired, after_profile, after_rules)

    repaired_path: Optional[str] = None
    if output_path is None:
        src = Path(dataset_path)
        repaired_path = str(src.with_name(f"{src.stem}_repaired{src.suffix}"))
    else:
        repaired_path = output_path
    out = Path(repaired_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() == ".parquet":
        repaired.to_parquet(out, index=False)
    else:
        repaired.to_csv(out, index=False)

    return {
        "dataset_path": dataset_path,
        "repaired_path": repaired_path,
        "column": column,
        "method": method,
        "details": details,
        "before": {
            "missing_count": original_missing,
            "missing_percent": round(original_missing / max(len(df), 1) * 100, 2),
            "quality_score": before_quality["quality_score"],
            "rows": len(df),
        },
        "after": {
            "missing_count": int(repaired[column].isna().sum()),
            "missing_percent": round(repaired[column].isna().mean() * 100, 2),
            "quality_score": after_profile["quality_score"],
            "rows": len(repaired),
            "safe_for_feature_retrieval": after_safety["safe_for_feature_retrieval"],
            "decision": after_safety["decision"],
            "issue_count": after_safety["issue_count"],
        },
        "profile": after_profile,
        "schema": after_schema,
        "rules": after_rules,
        "ml_safety": after_safety,
    }
