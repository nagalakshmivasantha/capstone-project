from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def write_evidence_manifest(payload: Dict[str, Any]) -> Dict[str, Any]:
    path = Path(__file__).resolve().parent.parent / "artifacts" / "evidence_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"path": str(path), **payload}
