from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

DEFAULT_RULES = {
    "null_rate": {"max": 0.05, "severity": "WARNING"},
    "duplicate_rate": {"max": 0.01, "severity": "WARNING"},
    "timezone_required": {"required": True, "severity": "CRITICAL"},
    "entity_nullable": {"nullable": False, "severity": "CRITICAL"},
    "numeric_required": {"required": True, "severity": "CRITICAL"},
}


def evaluate_quality_rules(df: pd.DataFrame, inferred_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    columns = {entry["column"]: entry for entry in inferred_schema.get("columns", [])}

    for column, meta in columns.items():
        series = df[column] if column in df.columns else pd.Series([], dtype="object")
        null_rate = float(series.isna().mean()) if not series.empty else 0.0
        if null_rate > DEFAULT_RULES["null_rate"]["max"]:
            results.append(
                {
                    "rule_id": f"null_rate:{column}",
                    "dataset": "dataset",
                    "column": column,
                    "observed": round(null_rate, 4),
                    "threshold": DEFAULT_RULES["null_rate"]["max"],
                    "severity": DEFAULT_RULES["null_rate"]["severity"],
                    "status": "fail",
                    "recommendation": f"{column} has a null-rate above threshold; quarantine or repair incomplete rows before use.",
                }
            )

        duplicate_rate = float(df.duplicated().mean()) if not df.empty else 0.0
        if duplicate_rate > DEFAULT_RULES["duplicate_rate"]["max"]:
            results.append(
                {
                    "rule_id": "duplicate_rate:global",
                    "dataset": "dataset",
                    "column": column,
                    "observed": round(duplicate_rate, 4),
                    "threshold": DEFAULT_RULES["duplicate_rate"]["max"],
                    "severity": DEFAULT_RULES["duplicate_rate"]["severity"],
                    "status": "fail",
                    "recommendation": "Duplicate rows were detected; deduplicate only after confirming business semantics.",
                }
            )

        if "time" in str(column).lower() or "date" in str(column).lower():
            parsed = pd.to_datetime(series, errors="coerce", utc=True)
            if parsed.notna().sum() and parsed.notna().sum() < len(series):
                results.append(
                    {
                        "rule_id": f"timezone_required:{column}",
                        "dataset": "dataset",
                        "column": column,
                        "observed": float(parsed.isna().mean()),
                        "threshold": 0.0,
                        "severity": DEFAULT_RULES["timezone_required"]["severity"],
                        "status": "fail",
                        "recommendation": "Require timezone-aware timestamps or normalize before ingestion to avoid hidden temporal drift.",
                    }
                )

        if pd.api.types.is_numeric_dtype(series):
            lowered = str(column).lower()
            invalid_values = pd.Series(False, index=series.index)
            if any(token in lowered for token in ["age", "years"]):
                invalid_values = (series < 0) | (series > 120)
            elif any(token in lowered for token in ["income", "amount", "price", "cost"]):
                invalid_values = series < 0
            if invalid_values.any():
                results.append(
                    {
                        "rule_id": f"valid_range:{column}",
                        "dataset": "dataset",
                        "column": column,
                        "observed": int(invalid_values.sum()),
                        "threshold": 0,
                        "severity": "WARNING",
                        "status": "fail",
                        "recommendation": f"Validate {column} against its business range and quarantine or correct impossible values.",
                    }
                )

        if "entity" in str(column).lower() and meta.get("semantic_type") == "entity_id":
            if series.isna().any() and not DEFAULT_RULES["entity_nullable"]["nullable"]:
                results.append(
                    {
                        "rule_id": f"entity_nullable:{column}",
                        "dataset": "dataset",
                        "column": column,
                        "observed": float(series.isna().mean()),
                        "threshold": 0.0,
                        "severity": DEFAULT_RULES["entity_nullable"]["severity"],
                        "status": "fail",
                        "recommendation": "Entity identifiers must be present; rows with null IDs should be quarantined.",
                    }
                )

        if meta.get("semantic_type") in {"numeric", "feature_value"} and pd.api.types.is_numeric_dtype(series):
            pass

    return results


def build_recommendation(failure: Dict[str, Any]) -> Dict[str, Any]:
    kind = failure.get("kind") or failure.get("rule_id") or "unknown"
    return {
        "what_failed": kind,
        "why_it_matters": "The dataset may silently contaminate historical feature retrieval or downstream training data.",
        "severity": failure.get("severity", "WARNING"),
        "automatic_repair_safe": False,
        "suggested_action": failure.get("recommendation", "Review the upstream transformation and quarantine affected rows."),
    }


def assess_ml_safety(df: pd.DataFrame, profile: Dict[str, Any], rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize whether the dataset is safe for downstream feature retrieval."""
    issues = []
    profile_issues = {rule.get("column") for rule in rules}
    column_profiles = profile.get("column_profiles", {})
    segment_analysis = profile.get("segment_analysis", {})
    for rule in rules:
        if rule.get("rule_id", "").startswith("null_rate:"):
            column = rule["column"]
            missing_percent = round(float(rule["observed"]) * 100, 2)
            series = df[column]
            col_profile = column_profiles.get(column, {})
            if pd.api.types.is_numeric_dtype(series):
                skew = float(col_profile.get("skew", series.dropna().skew() if series.dropna().size > 2 else 0.0))
                characteristics = ["Numerical"]
                if abs(skew) >= 1:
                    characteristics.append("Right-skewed" if skew > 0 else "Left-skewed")
                characteristics.append(f"{missing_percent:g}% missing")
                options = [
                    {"name": "Mean imputation", "risk": "HIGH", "detail": "Can distort a skewed distribution"},
                    {"name": "Median imputation", "risk": "MEDIUM", "detail": "Preserves a typical value but ignores segments"},
                    {"name": "Drop records", "risk": "HIGH", "detail": "Loses rows and may bias retrieval"},
                ]
                recommendation = "Median imputation"
                reason = "Median is more robust than mean for a skewed numeric feature."
                segment_info = segment_analysis.get(column, [])
                best_segment = None
                for seg in segment_info:
                    if seg.get("correlated_with_missingness"):
                        best_segment = seg
                        break
                if best_segment is None and segment_info:
                    rates_dict = {}
                    for seg in segment_info:
                        for s in seg.get("segments", []):
                            rates_dict.setdefault(seg["segment_column"], []).append(s["missing_percent"])
                    for seg_col, rates in rates_dict.items():
                        if len(rates) > 1 and (max(rates) - min(rates)) >= 10.0:
                            for seg in segment_info:
                                if seg["segment_column"] == seg_col:
                                    best_segment = seg
                                    break
                        if best_segment:
                            break
                if best_segment:
                    segment = best_segment["segment_column"]
                    characteristics.insert(-1, "Missingness correlated with segment")
                    options.insert(2, {"name": "Segment median", "risk": "LOW", "detail": f"Impute within {segment} groups"})
                    recommendation = "Segment-level median"
                    reason = "Distribution is skewed and missingness varies by segment; within-segment medians preserve group differences."
                    segment_values_data = []
                    for s in best_segment.get("segments", []):
                        segment_values_data.append({
                            "segment": s["segment_value"],
                            "missing_percent": s["missing_percent"],
                            "median": s["median"],
                            "mean": s["mean"],
                            "total": s["total_count"],
                            "missing_count": s["missing_count"],
                        })
                else:
                    segment_values_data = None
                dist = col_profile.get("percentiles", {})
                hist = col_profile.get("histogram", [])
                issues.append({
                    "column": column,
                    "missing_percent": missing_percent,
                    "impact_percent": missing_percent,
                    "severity": "HIGH" if missing_percent >= 20 else "MEDIUM",
                    "characteristics": characteristics,
                    "options": options,
                    "recommended": recommendation,
                    "reason": reason,
                    "distribution": {
                        "skew": skew,
                        "kurtosis": col_profile.get("kurtosis"),
                        "min": col_profile.get("stats", {}).get("min"),
                        "max": col_profile.get("stats", {}).get("max"),
                        "mean": col_profile.get("stats", {}).get("mean"),
                        "median": dist.get("p50"),
                        "p25": dist.get("p25"),
                        "p75": dist.get("p75"),
                        "outliers": col_profile.get("outliers", {}),
                        "histogram": hist,
                    },
                    "segment_analysis": {
                        "segment_column": best_segment["segment_column"] if best_segment else None,
                        "spread_percent": best_segment["spread_percent"] if best_segment else 0.0,
                        "segments": segment_values_data,
                    },
                })
            else:
                issues.append({
                    "column": column,
                    "missing_percent": missing_percent,
                    "impact_percent": missing_percent,
                    "severity": "HIGH" if missing_percent >= 20 else "MEDIUM",
                    "characteristics": ["Missing values"],
                    "options": [{"name": "Quarantine incomplete rows", "risk": "MEDIUM", "detail": "Prevent unknown values reaching retrieval"}],
                    "recommended": "Review upstream data",
                    "reason": "Non-numeric missing values require domain-specific handling.",
                    "distribution": {},
                    "segment_analysis": {"segment_column": None, "spread_percent": 0.0, "segments": None},
                })

    for rule in rules:
        if rule.get("rule_id", "").startswith("valid_range:") and rule.get("column") not in profile_issues:
            continue
        if rule.get("rule_id", "").startswith("valid_range:"):
            column = rule["column"]
            impact = round(float(rule["observed"]) / max(len(df), 1) * 100, 2)
            issues.append({
                "column": column,
                "missing_percent": 0,
                "impact_percent": impact,
                "severity": rule.get("severity", "WARNING"),
                "characteristics": ["Invalid values", f"{impact:g}% of rows affected"],
                "options": [
                    {"name": "Quarantine invalid rows", "risk": "MEDIUM", "detail": "Keep impossible values out of feature retrieval"},
                    {"name": "Correct from source", "risk": "LOW", "detail": "Preferred when the upstream value can be recovered"},
                ],
                "recommended": "Correct from source or quarantine",
                "reason": f"{impact:g}% of records contain values outside the expected {column} range.",
                "distribution": {},
                "segment_analysis": {"segment_column": None, "spread_percent": 0.0, "segments": None},
            })

    return {
        "safe_for_feature_retrieval": not rules,
        "decision": "ALLOW" if not rules else "BLOCK_PENDING_REPAIR",
        "issue_count": len(rules),
        "issues": issues,
        "profiling": {
            "columns_profiled": len(profile.get("column_profiles", {})),
            "rows_affected_percent": round(sum(float(issue.get("impact_percent", 0)) for issue in issues), 2),
        },
    }
