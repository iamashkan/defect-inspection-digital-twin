# Stage 1 — Surface-Defect Computer Vision

Fine-tunes a lightweight pretrained backbone (ResNet18 / MobileNetV3-Small) on a
surface-defect dataset and, per image, outputs a **defect class**, a
**Grad-CAM localization mask**, and a **confidence score** — plus accuracy
metrics, a confusion matrix, and side-by-side overlay visualizations.

This stage is fully self-contained: it has no dependency on Stages 2–3, and its
`predictions.json` already matches the contract the later grading/decision and
digital-twin layers will consume.

---

## Files

| File | Role |
|------|------|
| `config.py` | All paths + hyperparameters (`TrainConfig`). |
| `dataset.py` | ImageFolder loader + offline synthetic-data generator. |
| `model.py` | Pretrained backbone + new head; checkpoint save/load; Grad-CAM target layer. |
| `gradcam.py` | Minimal Grad-CAM (defect heatmap = our "mask"). |
| `train.py` | Fine-tuning loop, best-on-val checkpoint, metrics, confusion matrix. |
| `inference.py` | Class + heatmap + confidence + defect-area% + overlay panels. |
| `utils.py` | Seeding, device, metrics, plotting. |

---

## 1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # run from the repo root
```

## 2. Get data

Stage 1 reads any **ImageFolder** layout:

```
data/<name>/train/<class>/*.jpg
data/<name>/test/<class>/*.jpg
```

**Option A — zero-download smoke test (recommended first run).**
Generates labelled synthetic "parts" (`good` / `scratch` / `crack`) so every
script runs offline end-to-end:

```bash
python -m stage1_vision.dataset --make-synthetic
```

**Option B — a real public dataset.**

- **NEU-DET** (6 steel-surface defect classes). Download from the NEU surface
  defect database, arrange the class folders under `data/NEU-DET/train` and
  `data/NEU-DET/test`.
- **Casting product defects** (Kaggle, binary `def_front`/`ok_front`):
  ```bash
  # with the Kaggle CLI configured (free account):
  kaggle datasets download -d ravirajsinh45/real-life-industrial-dataset-of-casting-product
  # unzip so you end up with data/casting/train/<class> and data/casting/test/<class>
  ```

No dataset present? The scripts point you to `--make-synthetic`.

## 3. Train

```bash
# Synthetic smoke test (CPU-OK, a couple of minutes):
python -m stage1_vision.train --data data/synthetic --epochs 5

# A real dataset on a mid-range GPU:
python -m stage1_vision.train --data data/NEU-DET --backbone resnet18 --epochs 15
# Fastest fine-tune (head only) / smallest model:
python -m stage1_vision.train --data data/casting --backbone mobilenet_v3_small --freeze-backbone
```

Writes to `outputs/`: `best_model.pt`, `metrics.json`, `confusion_matrix.png`,
`training_log.json`.

## 4. Inference + visual overlays

```bash
python -m stage1_vision.inference \
    --weights outputs/best_model.pt \
    --images data/synthetic/test \
    --out outputs/predictions
```

For each image you get:
- `<name>_overlay.png` — `[ original | heatmap | overlay+label ]`
- `<name>_mask.png` — binary defect mask
- one row in `outputs/predictions/predictions.json`:
  ```json
  {
    "image": ".../crack_0003.jpg",
    "pred_class": "crack",
    "confidence": 0.974,
    "defect_area_pct": 6.1,
    "probabilities": {"good": 0.01, "scratch": 0.02, "crack": 0.97}
  }
  ```

---

## <a name="colab"></a>Run it in Google Colab (free GPU)

1. Go to <https://colab.research.google.com> → **Runtime → Change runtime type →
   T4 GPU**.
2. In a cell, clone the repo (or upload it) and install deps:
   ```python
   !git clone <your-repo-url> rex && cd rex && pip install -q -r requirements.txt
   %cd rex
   ```
3. Build the synthetic dataset (or upload a real one to `data/`):
   ```python
   !python -m stage1_vision.dataset --make-synthetic
   ```
4. Train on the free GPU:
   ```python
   !python -m stage1_vision.train --data data/synthetic --epochs 10 --device cuda
   ```
5. Run inference and display an overlay inline:
   ```python
   !python -m stage1_vision.inference --weights outputs/best_model.pt \
       --images data/synthetic/test --out outputs/predictions --device cuda

   from IPython.display import Image as Show
   import glob
   Show(sorted(glob.glob("outputs/predictions/*_overlay.png"))[0])
   ```

The ready-made notebook `notebooks/colab_stage1.ipynb` runs all of the above.

> **Tip:** for a real dataset in Colab, either `kaggle datasets download ...`
> (upload your `kaggle.json` first) or mount Google Drive and point `--data` at
> the folder. Everything stays free — no paid services.

---

## Notes on design choices

- **Why classification + Grad-CAM instead of segmentation?** It needs only
  image-level labels (which NEU/casting provide), trains in minutes, and still
  yields a defect *location* heatmap and a defect-area% severity proxy. If you
  later have pixel masks (e.g. MVTec AD), this stage can be swapped for a U-Net
  without changing the downstream `predictions.json` contract.
- **Why ResNet18 / MobileNetV3-Small?** Small, pretrained, fast to fine-tune on a
  mid-range GPU; MobileNet is the lighter option for edge/throughput.
- **Reproducibility:** fixed seeds, deterministic cuDNN, no paid services.
