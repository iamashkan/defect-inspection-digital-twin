"""End-to-end pipeline: Stage 1 inference → Stage 2 grading → digital twin.

Runs the Stage 1 CV model over one or more images, grades each result into a
REUSE / REPAIR / RECYCLE decision, and records every part in the digital twin.
This is the headless counterpart to the Streamlit dashboard.

Example:
    python -m stage2_decision.pipeline \
        --weights outputs/best_model.pt \
        --images data/synthetic/test \
        --out outputs/predictions
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from stage1_vision import config
from stage1_vision.inference import run_inference

from .digital_twin import DigitalTwin
from .grading import GradingConfig, grade_record


def _overlay_paths(image_path: str, out_dir: Path | None):
    """Derive the overlay/mask paths run_inference writes for an image."""
    if out_dir is None:
        return None, None
    stem = Path(image_path).stem
    overlay = out_dir / f"{stem}_overlay.png"
    mask = out_dir / f"{stem}_mask.png"
    return (str(overlay) if overlay.exists() else None,
            str(mask) if mask.exists() else None)


def run_pipeline(weights: Path, images: Path, out_dir: Path | None,
                 store_path: Path | None = None,
                 grading_cfg: GradingConfig | None = None,
                 device: str = "auto", reset_twin: bool = False) -> dict:
    """Run Stage 1 → grade → record. Returns the twin's running stats."""
    grading_cfg = grading_cfg or GradingConfig()
    twin = DigitalTwin(store_path)
    if reset_twin:
        twin.clear()
        print(f"[pipeline] cleared digital-twin store at {twin.store_path}")

    # Stage 1: defect class + Grad-CAM mask + confidence + defect-area% per image.
    records = run_inference(
        weights=weights, images_path=images, out_dir=out_dir, device_choice=device
    )

    print("\n[pipeline] grading + recording in digital twin:")
    for rec in records:
        grading = grade_record(rec, grading_cfg)
        overlay, mask = _overlay_paths(rec["image"], out_dir)
        stored = twin.add(
            image=rec["image"], grading=grading,
            overlay_path=overlay, heatmap_mask_path=mask,
        )
        print(f"  {Path(rec['image']).name:28s} {grading['pred_class']:10s} "
              f"cond={grading['condition_score']:5.1f} "
              f"→ {grading['decision']:8s} (conf {grading['decision_confidence']:.2f}) "
              f"[{stored['part_id']}]")

    stats = twin.stats()
    print("\n[pipeline] digital-twin stats:")
    print(json.dumps(stats, indent=2))
    print(f"[pipeline] store: {twin.store_path}")
    return stats


def parse_args():
    out_default = config.OUTPUT_DIR / "predictions"
    p = argparse.ArgumentParser(description="Stage 2 — inference → grade → digital twin.")
    p.add_argument("--weights", type=str,
                   default=str(config.OUTPUT_DIR / "best_model.pt"),
                   help="Stage 1 checkpoint.")
    p.add_argument("--images", type=str, required=True,
                   help="Image file or directory.")
    p.add_argument("--out", type=str, default=str(out_default),
                   help="Where overlays/masks are written (also linked in the twin).")
    p.add_argument("--store", type=str, default=None,
                   help="Digital-twin JSONL path (default outputs/digital_twin.jsonl).")
    p.add_argument("--device", type=str, default="auto", choices=["auto", "cuda", "cpu"])
    p.add_argument("--reset-twin", action="store_true",
                   help="Clear the digital-twin store before running.")
    return p.parse_args()


def main():
    args = parse_args()
    run_pipeline(
        weights=Path(args.weights),
        images=Path(args.images),
        out_dir=Path(args.out) if args.out else None,
        store_path=Path(args.store) if args.store else None,
        device=args.device,
        reset_twin=args.reset_twin,
    )


if __name__ == "__main__":
    main()
