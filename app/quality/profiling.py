from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


def _build_histogram(series: pd.Series, bins: int = 20) -> List[Dict[str, Any]]:
    non_null = series.dropna()
    if non_null.empty:
        return []
    try:
        counts, edges = np.histogram(non_null.astype(float), bins=min(bins, max(5, non_null.nunique())))
    except Exception:
        return []
    hist = []
    for i in range(len(counts)):
        hist.append({
            "bin_start": round(float(edges[i]), 4),
            "bin_end": round(float(edges[i + 1]), 4),
            "count": int(counts[i]),
        })
    return hist


def _percentiles(series: pd.Series) -> Dict[str, float]:
    non_null = series.dropna()
    if non_null.empty:
        return {}
    qs = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
    labels = ["p1", "p5", "p10", "p25", "p50", "p75", "p90", "p95", "p99"]
    try:
        values = np.nanpercentile(non_null.astype(float), [q * 100 for q in qs])
        return {label: round(float(values[i]), 4) for i, label in enumerate(labels)}
    except Exception:
        return {}


def _outlier_counts(series: pd.Series) -> Dict[str, Any]:
    non_null = series.dropna()
    if len(non_null) < 4:
        return {"low_count": 0, "high_count": 0, "iqr": None, "lower_bound": None, "upper_bound": None}
    try:
        numeric = non_null.astype(float)
        q1, q3 = np.percentile(numeric, [25, 75])
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        return {
            "low_count": int((numeric < lower).sum()),
            "high_count": int((numeric > upper).sum()),
            "iqr": round(float(iqr), 4),
            "lower_bound": round(float(lower), 4),
            "upper_bound": round(float(upper), 4),
        }
    except Exception:
        return {"low_count": 0, "high_count": 0, "iqr": None, "lower_bound": None, "upper_bound": None}


def _segment_missing_rates(df: pd.DataFrame, target_column: str) -> List[Dict[str, Any]]:
    segment_cols: List[str] = [
        name for name in df.columns
        if name != target_column
        and not pd.api.types.is_numeric_dtype(df[name])
        and df[name].nunique(dropna=True) > 1
        and df[name].nunique(dropna=True) <= 20
    ]
    results: List[Dict[str, Any]] = []
    for seg in segment_cols:
        grouped = df.groupby(seg, dropna=False, observed=True)[target_column].agg(
            missing_count=lambda s: int(s.isna().sum()),
            total_count="count",
            missing_rate=lambda s: float(s.isna().mean()),
            median=lambda s: float(s.dropna().median()) if s.notna().any() else None,
            mean=lambda s: float(s.dropna().mean()) if s.notna().any() else None,
        )
        grouped = grouped.reset_index()
        grouped.columns = [seg, "missing_count", "total_count", "missing_rate", "median", "mean"]
        seg_rates = []
        for _, row in grouped.iterrows():
            seg_rates.append({
                "segment_value": str(row[seg]),
                "missing_count": int(row["missing_count"]),
                "total_count": int(row["total_count"]),
                "missing_percent": round(float(row["missing_rate"]) * 100, 2),
                "median": round(float(row["median"]), 2) if row["median"] is not None else None,
                "mean": round(float(row["mean"]), 2) if row["mean"] is not None else None,
            })
        rates = [s["missing_percent"] for s in seg_rates]
        spread = round(float(max(rates) - min(rates)), 2) if rates else 0.0
        results.append({
            "segment_column": seg,
            "spread_percent": spread,
            "correlated_with_missingness": spread >= 10.0,
            "segments": seg_rates,
        })
    return results


def profile_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute quality metrics for a dataset and produce a quality score."""
    profile: Dict[str, Any] = {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "column_profiles": {},
        "null_percent_by_column": {},
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_rate": float(df.duplicated().mean()) if not df.empty else 0.0,
        "quality_score": 100.0,
        "segment_analysis": {},
    }

    invalid_timestamp_count = 0
    for column in df.columns:
        series = df[column]
        null_percent = float(series.isna().mean()) if not df.empty else 0.0
        profile["null_percent_by_column"][column] = round(null_percent * 100, 2)
        column_profile: Dict[str, Any] = {
            "dtype": str(series.dtype),
            "missing_count": int(series.isna().sum()),
            "missing_percent": round(null_percent * 100, 2),
            "unique_count": int(series.nunique(dropna=True)),
            "sample_values": [str(value) for value in series.dropna().head(3).tolist()],
        }

        if pd.api.types.is_numeric_dtype(series):
            non_null = series.dropna()
            stats = {
                "min": float(series.min()) if not series.empty and pd.notna(series.min()) else None,
                "max": float(series.max()) if not series.empty and pd.notna(series.max()) else None,
                "mean": round(float(series.mean()), 4) if not series.empty else None,
                "std": round(float(series.std()), 4) if not series.empty else None,
            }
            profile[f"{column}_stats"] = stats
            column_profile["inferred_type"] = "numeric"
            column_profile["skew"] = round(float(non_null.skew()), 3) if len(non_null) > 2 else 0.0
            column_profile["kurtosis"] = round(float(non_null.kurtosis()), 3) if len(non_null) > 3 else 0.0
            column_profile["stats"] = stats
            column_profile["percentiles"] = _percentiles(series)
            column_profile["histogram"] = _build_histogram(series)
            column_profile["outliers"] = _outlier_counts(series)
            if column_profile["missing_percent"] > 0:
                profile["segment_analysis"][column] = _segment_missing_rates(df, column)
        elif any(token in column.lower() for token in ["time", "date", "timestamp", "created", "event"]):
            parsed = pd.to_datetime(series, utc=True, errors="coerce")
            column_profile["inferred_type"] = "timestamp"
            column_profile["parse_success_percent"] = round(float(parsed.notna().mean() * 100), 2) if not series.empty else 0.0
        else:
            is_cat = series.nunique(dropna=True) <= max(20, len(series) * 0.1)
            column_profile["inferred_type"] = "categorical" if is_cat else "string"
            value_counts = series.value_counts(dropna=True).head(10)
            column_profile["top_values"] = {str(key): int(value) for key, value in value_counts.items()}
            column_profile["category_count"] = int(series.nunique(dropna=True))

        profile["column_profiles"][column] = column_profile

        if any(token in column.lower() for token in ["time", "date", "timestamp", "created", "event"]):
            try:
                pd.to_datetime(series, utc=True, errors="raise")
            except Exception:
                invalid_timestamp_count += int(series.isna().sum())

    overall_null = float(df.isna().mean().mean()) if not df.empty else 0.0
    duplicate_penalty = profile["duplicate_rate"] * 60
    null_penalty = overall_null * 40
    invalid_ts_penalty = (invalid_timestamp_count / max(len(df), 1)) * 30
    score = max(0.0, 100.0 - duplicate_penalty - null_penalty - invalid_ts_penalty)
    profile["quality_score"] = round(score, 2)
    return profile
