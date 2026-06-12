# Stage 2 — Grading, Recovery Decision & Digital Twin

Turns the Stage 1 defect features (class, confidence, defect-area %) into a
**condition score (0–100)**, a **REUSE / REPAIR / RECYCLE** decision with a
**decision confidence**, records every part in a persistent **digital twin**, and
visualizes it all in a **Streamlit dashboard**.

Depends on Stage 1's `predictions` contract — it does **not** require Stage 3.

---

## Files

| File | Role |
|------|------|
| `grading.py` | Transparent, rule-based grader: features → condition score → decision + confidence. Per-class severity map (synthetic / NEU / casting), tunable thresholds. |
| `digital_twin.py` | Append-only JSONL record store + running statistics (pandas-friendly). |
| `pipeline.py` | Glue CLI: Stage 1 inference → grade → record in the twin. |
| `dashboard.py` | Streamlit app (Inspect + Statistics views). |

---

## How the decision is made (and why it's a rule, not a black box)

In a real inspection/quality setting an unexplained "RECYCLE" is a hard sell, so
grading is a **transparent rule** every step of which is inspectable:

```
condition = 100 × (1 − penalty)
penalty   = severity_weight · severity(class) + area_weight · (area% / area_full)

score ≥ 80  → REUSE        # near-pristine
50 ≤ score < 80 → REPAIR   # cosmetic / recoverable
score < 50  → RECYCLE      # structural / heavily damaged
```

- **severity(class)** — 0 (cosmetic, e.g. *scratch*) … 1 (structural, e.g.
  *crack*, *inclusion*). Defaults cover the synthetic, NEU-DET and casting class
  names; override via `GradingConfig.severity_by_class`.
- **decision confidence** blends the model's confidence with how far the score
  sits from a decision threshold (calls near a boundary are reported as less
  certain).

Thresholds and weights live in `GradingConfig` and are adjustable live from the
dashboard sidebar.

---

## Run it

**1. Headless pipeline** (inference → grade → digital twin) over a folder:

```bash
python -m stage2_decision.pipeline \
    --weights outputs/best_model.pt \
    --images data/synthetic/test \
    --out outputs/predictions \
    --reset-twin
```

Prints a per-part decision table and the running twin statistics, and writes
records to `outputs/digital_twin.jsonl`.

**2. Streamlit dashboard:**

```bash
streamlit run stage2_decision/dashboard.py
```

- **Inspect** tab: upload (or pick a sample) part image → live CV inference →
  decision badge, condition score, defect-area %, and the
  `original | heatmap | overlay` panel → one click records the part in the twin.
- **Statistics** tab: parts inspected, average condition score, **recovery rate**
  (REUSE + REPAIR share), decision-mix bar chart, and the recent record table.

**Quick checks** (no dashboard, no GPU):

```bash
python -m stage2_decision.grading        # grades 3 sample records
python -m stage2_decision.digital_twin   # writes a temp twin + prints stats
```

---

## The digital-twin record

One JSON object per inspected part, appended to `outputs/digital_twin.jsonl`:

```json
{
  "part_id": "PART-9F3A1C7B",
  "timestamp": "2026-06-13T09:12:44+00:00",
  "image": "data/synthetic/test/crack/crack_0001.jpg",
  "pred_class": "crack",
  "model_confidence": 0.974,
  "defect_area_pct": 21.1,
  "severity": 0.95,
  "condition_score": 22.0,
  "decision": "RECYCLE",
  "decision_confidence": 0.79,
  "overlay_path": "outputs/predictions/crack_0001_overlay.png",
  "heatmap_mask_path": "outputs/predictions/crack_0001_mask.png"
}
```

This is the live virtual record of the physical part — condition, defect
heatmap, decision and timestamp — and the data Stage 3's ROS 2 *digital-twin
state* node will serve.
