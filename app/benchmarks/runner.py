from __future__ import annotations

from typing import Any, Dict

from app.benchmarks import benchmark_suite
from app.benchmarks.report_writer import write_report


def run_benchmarks() -> Dict[str, Any]:
    report = benchmark_suite()
    write_report(report)
    return report
