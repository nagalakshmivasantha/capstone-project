from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def write_report(report: Dict[str, Any], file_name: str = "benchmark_report.json") -> Path:
    output = Path(__file__).resolve().parent.parent / "app" / "benchmarks" / file_name
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output
