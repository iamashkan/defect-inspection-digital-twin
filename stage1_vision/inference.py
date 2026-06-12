"""Stage 1 inference + visualization.

For each input image, produces:
    * defect class       (argmax of softmax)
    * confidence         (top-1 softmax probability)
    * full probability vector over all classes
    * a Grad-CAM heatmap ("mask") localizing the defect
    * a binary defect mask + defect-area % (heatmap thresholded)

and writes a side-by-side overlay PNG: [original | heatmap | overlay+label].

A `predictions.json` summarizes every image — this is exactly the structured
record Stage 2's grading/decision module and the digital twin will consume
(class, confidence, defect_area_pct), so Stage 1 already speaks the downstream
contract.

Examples:
    python -m stage1_vision.inference --weights outputs/best_model.pt \
        --images data/synthetic/test --out outputs/predictions
    python -m stage1_vision.inference --weights outputs/best_model.pt \
        --images path/to/single.jpg
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from . import config, model as model_lib, utils
from .dataset import build_transforms
from .gradcam import GradCAM

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def gather_images(path: Path) -> list[Path]:
    """Collect image paths from a single file or a directory tree."""
    path = Path(path)
    if path.is_file():
        return [path]
    files = sorted(p for p in path.rglob("*") if p.suffix.lower() in IMAGE_EXTS)
    if not files:
        raise FileNotFoundError(f"No images found under {path}.")
    return files


def heatmap_to_color(heatmap: np.ndarray) -> np.ndarray:
    """Map a [0,1] heatmap to a BGR JET colormap image (uint8)."""
    hm = np.clip(heatmap * 255, 0, 255).astype(np.uint8)
    return cv2.applyColorMap(hm, cv2.COLORMAP_JET)


def defect_mask_and_area(heatmap: np.ndarray, threshold: float = 0.5):
    """Threshold the heatmap into a binary defect mask + percentage area.

    Returns (binary_mask uint8 {0,255}, defect_area_pct float).
    The area % is a simple, explainable severity proxy that Stage 2 turns into a
    recovery decision.
    """
    mask = (heatmap >= threshold).astype(np.uint8) * 255
    area_pct = float((mask > 0).mean() * 100.0)
    return mask, area_pct


def make_overlay(rgb_uint8: np.ndarray, heatmap: np.ndarray, label: str,
                 alpha: float = 0.45) -> np.ndarray:
    """Build the [original | heatmap | overlay] BGR panel with a label banner."""
    h, w = rgb_uint8.shape[:2]
    bgr = cv2.cvtColor(rgb_uint8, cv2.COLOR_RGB2BGR)
    color_hm = heatmap_to_color(heatmap)
    overlay = cv2.addWeighted(bgr, 1 - alpha, color_hm, alpha, 0)

    # Label banner across the overlay panel.
    banner_h = max(24, h // 10)
    cv2.rectangle(overlay, (0, 0), (w, banner_h), (0, 0, 0), -1)
    cv2.putText(overlay, label, (6, int(banner_h * 0.7)),
                cv2.FONT_HERSHEY_SIMPLEX, max(0.4, w / 600), (255, 255, 255),
                1, cv2.LINE_AA)

    panel = np.hstack([bgr, color_hm, overlay])
    return panel


@torch.no_grad()
def _softmax_probs(model, tensor, device):
    logits = model(tensor.to(device))
    return F.softmax(logits, dim=1)[0].cpu().numpy()


def run_inference(weights: Path, images_path: Path, out_dir: Path | None,
                  device_choice: str = "auto", mask_threshold: float = 0.5):
    """Run the full predict + visualize loop; return a list of record dicts."""
    device = utils.resolve_device(device_choice)
    model, ckpt = model_lib.load_checkpoint(weights, map_location=device)
    model.to(device)
    class_names = ckpt["class_names"]
    image_size = ckpt["image_size"]
    backbone = ckpt["backbone"]
    print(f"[infer] loaded {backbone} | classes={class_names} | size={image_size}")

    eval_tf = build_transforms(image_size, train=False, augment=False)
    target_layer = model_lib.last_conv_layer(model, backbone)
    cam = GradCAM(model, target_layer)

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for img_path in gather_images(images_path):
        pil = Image.open(img_path).convert("RGB")
        tensor = eval_tf(pil).unsqueeze(0).to(device)

        # Grad-CAM also returns the predicted class + confidence in one pass.
        heatmap, class_idx, confidence = cam(tensor)
        probs = _softmax_probs(model, tensor, device)
        pred_class = class_names[class_idx]

        mask, area_pct = defect_mask_and_area(heatmap, mask_threshold)

        record = {
            "image": str(img_path),
            "pred_class": pred_class,
            "confidence": round(confidence, 4),
            "defect_area_pct": round(area_pct, 2),
            "probabilities": {c: round(float(p), 4) for c, p in zip(class_names, probs)},
        }
        records.append(record)

        if out_dir is not None:
            rgb_vis = np.array(pil.resize((image_size, image_size)))
            label = f"{pred_class}  {confidence*100:.1f}%  area={area_pct:.1f}%"
            panel = make_overlay(rgb_vis, heatmap, label)
            cv2.imwrite(str(out_dir / f"{img_path.stem}_overlay.png"), panel)
            cv2.imwrite(str(out_dir / f"{img_path.stem}_mask.png"), mask)

        print(f"[infer] {img_path.name:30s} → {pred_class:10s} "
              f"conf={confidence:.3f} area={area_pct:.1f}%")

    cam.remove_hooks()

    if out_dir is not None:
        with open(out_dir / "predictions.json", "w") as f:
            json.dump(records, f, indent=2)
        print(f"[infer] wrote {len(records)} records + overlays to {out_dir}")

    return records


def parse_args():
    cfg = config.TrainConfig()
    p = argparse.ArgumentParser(description="Stage 1 — defect inference + overlays.")
    p.add_argument("--weights", type=str, default=str(cfg.output_dir / "best_model.pt"),
                   help="Path to a checkpoint from train.py.")
    p.add_argument("--images", type=str, required=True,
                   help="Image file or directory of images.")
    p.add_argument("--out", type=str, default=str(cfg.output_dir / "predictions"),
                   help="Output directory for overlays + predictions.json. "
                        "Pass empty string to skip writing files.")
    p.add_argument("--device", type=str, default="auto", choices=["auto", "cuda", "cpu"])
    p.add_argument("--mask-threshold", type=float, default=0.5,
                   help="Heatmap threshold for the binary defect mask / area %%.")
    return p.parse_args()


def main():
    args = parse_args()
    out_dir = args.out if args.out else None
    run_inference(
        weights=Path(args.weights),
        images_path=Path(args.images),
        out_dir=out_dir,
        device_choice=args.device,
        mask_threshold=args.mask_threshold,
    )


if __name__ == "__main__":
    main()
