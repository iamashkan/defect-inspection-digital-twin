"""Digital-twin data layer.

A lightweight, append-only store that holds a live virtual record of every part
the system inspects. Each record captures the part's condition score, the defect
heatmap/overlay path, the decision, and a timestamp — the "digital twin" of the
physical part.

Storage is a JSON-Lines file (`outputs/digital_twin.jsonl`): one JSON object per
line, append-only, trivially inspectable and pandas-friendly. No database server,
no paid services.

    twin = DigitalTwin()                      # defaults to outputs/digital_twin.jsonl
    rec = twin.add(image=..., grading=..., overlay_path=...)
    df = twin.to_dataframe()
    stats = twin.stats()
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Repo root = two levels up from this file (<repo>/stage2_decision/digital_twin.py).
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = REPO_ROOT / "outputs" / "digital_twin.jsonl"

# Columns, in display order, for the dashboard / DataFrame export.
RECORD_FIELDS = [
    "part_id", "timestamp", "image", "pred_class", "model_confidence",
    "defect_area_pct", "severity", "condition_score", "decision",
    "decision_confidence", "overlay_path", "heatmap_mask_path",
]


class DigitalTwin:
    """Append-only digital-twin store backed by a JSONL file."""

    def __init__(self, store_path: str | Path | None = None):
        self.store_path = Path(store_path) if store_path else DEFAULT_STORE
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    # --- writing ---
    def add(self, *, image: str, grading: dict, overlay_path: str | None = None,
            heatmap_mask_path: str | None = None, part_id: str | None = None,
            timestamp: str | None = None) -> dict:
        """Append one inspected part to the twin and return the stored record.

        Args:
            image: path to the inspected image.
            grading: the dict returned by `stage2_decision.grading.grade_record`.
            overlay_path / heatmap_mask_path: optional visualization artifact paths.
            part_id / timestamp: optional overrides (auto-generated otherwise).
        """
        record = {
            "part_id": part_id or f"PART-{uuid.uuid4().hex[:8].upper()}",
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "image": image,
            "pred_class": grading.get("pred_class"),
            "model_confidence": grading.get("model_confidence"),
            "defect_area_pct": grading.get("defect_area_pct"),
            "severity": grading.get("severity"),
            "condition_score": grading.get("condition_score"),
            "decision": grading.get("decision"),
            "decision_confidence": grading.get("decision_confidence"),
            "overlay_path": overlay_path,
            "heatmap_mask_path": heatmap_mask_path,
        }
        with open(self.store_path, "a") as f:
            f.write(json.dumps(record) + "\n")
        return record

    # --- reading ---
    def records(self) -> list[dict]:
        """Return all records (empty list if the store doesn't exist yet)."""
        if not self.store_path.exists():
            return []
        out = []
        with open(self.store_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def to_dataframe(self):
        """Return all records as a pandas DataFrame (ordered columns)."""
        import pandas as pd

        rows = self.records()
        if not rows:
            return pd.DataFrame(columns=RECORD_FIELDS)
        df = pd.DataFrame(rows)
        # Keep a stable column order; tolerate missing optional columns.
        cols = [c for c in RECORD_FIELDS if c in df.columns]
        return df[cols]

    def stats(self) -> dict:
        """Running statistics over all inspected parts.

        Returns counts per decision, average condition score, average decision
        confidence, and total throughput.
        """
        from .grading import DECISIONS

        rows = self.records()
        n = len(rows)
        counts = {d: 0 for d in DECISIONS}
        for r in rows:
            d = r.get("decision")
            if d in counts:
                counts[d] += 1

        def _avg(key):
            vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
            return round(sum(vals) / len(vals), 1) if vals else 0.0

        return {
            "total_parts": n,
            "decision_counts": counts,
            "avg_condition_score": _avg("condition_score"),
            "avg_decision_confidence": _avg("decision_confidence"),
            # Share of parts kept in service (reused or repaired) vs recycled.
            "recovery_rate_pct": round(
                100.0 * (counts["REUSE"] + counts["REPAIR"]) / n, 1) if n else 0.0,
        }

    def clear(self) -> None:
        """Delete the store (used by tests / 'reset' in the dashboard)."""
        if self.store_path.exists():
            self.store_path.unlink()


if __name__ == "__main__":
    # Smoke test: write a couple of records to a temp store and print stats.
    import tempfile

    from .grading import grade_record

    tmp = Path(tempfile.mkdtemp()) / "twin.jsonl"
    twin = DigitalTwin(tmp)
    for s in [
        {"pred_class": "good", "confidence": 0.74, "defect_area_pct": 14.4},
        {"pred_class": "crack", "confidence": 0.97, "defect_area_pct": 21.1},
    ]:
        twin.add(image=f"demo/{s['pred_class']}.jpg", grading=grade_record(s))
    print("records:", len(twin.records()))
    print("stats:", json.dumps(twin.stats(), indent=2))
