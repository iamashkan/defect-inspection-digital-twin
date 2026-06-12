# SAMPLE RESULTS — what each demo should show

This document describes the expected output of each stage's demo so you can tell
at a glance whether a run "worked." Stage 1 is implemented now; Stages 2–3 are
described for when they're built.

---

## Stage 1 — Surface-defect CV

After `train.py` then `inference.py` on the synthetic dataset (or a real one):

**Console (training):**
```
[dataset] classes=['crack', 'good', 'scratch'] | train=153 val=27 test=24
[train] epoch 01/5 | train loss 1.02 acc 0.61 | val loss 0.74 acc 0.81
...
[train] epoch 05/5 | train loss 0.34 acc 0.97 | val loss 0.29 acc 0.96
[train] TEST accuracy = 0.958
```

**Artifacts in `outputs/`:**
- `best_model.pt` — the checkpoint (weights + class names + backbone + image size).
- `metrics.json` — overall test accuracy plus per-class precision / recall / F1.
- `confusion_matrix.png` — row-normalized; a strong diagonal = good separation.
- `training_log.json` — per-epoch loss/accuracy curves.

**Artifacts in `outputs/predictions/`:**
- `*_overlay.png` — three panels per image: **original | Grad-CAM heatmap |
  overlay** with a banner reading e.g. `crack  97.4%  area=6.1%`. On a `crack`
  image the hot (red) region should sit on the fracture line; on a `good` image
  the heatmap should be cool/diffuse with a low defect area %.
- `*_mask.png` — binary mask of the thresholded heatmap.
- `predictions.json` — one structured record per image (class, confidence,
  defect_area_pct, full probability vector).

**What "good" looks like:** test accuracy comfortably above chance (≥ ~0.9 on the
synthetic set and on NEU/casting after a few epochs), heatmaps that land on the
actual defect, and clearly higher `defect_area_pct` for defective vs. clean parts.

> The synthetic dataset is a smoke test, not a benchmark — its job is to prove
> the full train → infer → visualize loop runs offline. Swap in NEU-DET or the
> casting dataset for meaningful accuracy numbers.

---

## Stage 2 — Grading + recovery decision + digital twin

After `python -m stage2_decision.pipeline --images data/synthetic/test --reset-twin`:

**Console (per-part decisions + running stats):**
```
[pipeline] grading + recording in digital twin:
  good_0000.jpg     good       cond= 96.0 → REUSE    (conf 0.85) [PART-1A2B3C4D]
  scratch_0003.jpg  scratch    cond= 61.0 → REPAIR   (conf 0.71) [PART-5E6F7A8B]
  crack_0001.jpg    crack      cond= 22.0 → RECYCLE  (conf 0.79) [PART-9C0D1E2F]
...
[pipeline] digital-twin stats:
{ "total_parts": 24, "decision_counts": {"REUSE": 8, "REPAIR": 8, "RECYCLE": 8},
  "avg_condition_score": 59.7, "recovery_rate_pct": 66.7, ... }
```

**What "good" looks like:** clean parts → high condition → `REUSE`; cosmetic
defects (scratch) → mid condition → `REPAIR`; structural defects (crack) → low
condition → `RECYCLE`. Each part is appended to `outputs/digital_twin.jsonl` with
its condition score, decision, heatmap path and timestamp.

**Streamlit dashboard** (`streamlit run stage2_decision/dashboard.py`):
- **Inspect** — pick/upload a part, see the color-coded decision badge, condition
  score, defect-area %, and the `original | heatmap | overlay` panel; one click
  records the part in the twin.
- **Statistics** — parts inspected, average condition score, **recovery rate**
  (REUSE + REPAIR share), a decision-mix bar chart, and the recent record table,
  all updating as parts are inspected.

## Stage 3 — ROS 2 / Gazebo / RViz (planned)

- Separate ROS 2 Humble nodes: **camera** (publishes frames), **inspection**
  (runs the Stage 1 CV+ML), **decision** (Stage 2 grading), **digital-twin
  state** (maintains/serves part records).
- A minimal **Gazebo** inspection cell: a fixed camera over a table with a part.
- An **RViz** config visualizing the incoming image, the defect overlay, and the
  decision as an annotated marker.
- Demo: launch the cell, a part appears under the camera, and the decision +
  heatmap stream through the node graph into RViz in real time.
