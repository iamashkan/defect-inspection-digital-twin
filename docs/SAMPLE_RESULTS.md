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

## Stage 2 — Grading + recovery decision + digital twin (planned)

- A **decision** per part: `REUSE` / `REPAIR` / `RECYCLE` with a confidence,
  derived from defect type, count, area% and severity (e.g. small cosmetic
  scratch → REPAIR; clean → REUSE; crack / large area → RECYCLE).
- A **digital-twin record** per part: condition score (0–100), defect heatmap,
  decision, timestamp — appended to a running store (JSON/SQLite).
- A **Streamlit dashboard** showing the image + heatmap overlay, the decision
  badge, and running statistics (decision counts, average condition score,
  throughput) updating as parts are inspected.

## Stage 3 — ROS 2 / Gazebo / RViz (planned)

- Separate ROS 2 Humble nodes: **camera** (publishes frames), **inspection**
  (runs the Stage 1 CV+ML), **decision** (Stage 2 grading), **digital-twin
  state** (maintains/serves part records).
- A minimal **Gazebo** inspection cell: a fixed camera over a table with a part.
- An **RViz** config visualizing the incoming image, the defect overlay, and the
  decision as an annotated marker.
- Demo: launch the cell, a part appears under the camera, and the decision +
  heatmap stream through the node graph into RViz in real time.
