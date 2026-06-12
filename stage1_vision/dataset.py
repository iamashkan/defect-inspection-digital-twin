"""Dataset loading for Stage 1.

The loader is intentionally generic: it consumes any **ImageFolder-style**
classification layout, which is exactly how the recommended public surface-defect
datasets are organized (NEU-DET classes, casting `def_front`/`ok_front`, etc.):

    data/<name>/
    ├── train/<class>/*.jpg
    └── test/ <class>/*.jpg

Key functions:
    build_transforms(...)  -> train/eval torchvision transforms
    build_dataloaders(cfg) -> (train_loader, val_loader, test_loader, class_names)

Run directly to generate a tiny offline synthetic dataset so the whole pipeline
works with zero downloads:

    python -m stage1_vision.dataset --make-synthetic
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, random_split
from torchvision import transforms
from torchvision.datasets import ImageFolder

from . import config


# --- Transforms --------------------------------------------------------------
def build_transforms(image_size: int, train: bool, augment: bool):
    """Build torchvision transforms.

    Augmentation is kept gentle on purpose — surface defects are subtle texture
    cues, so aggressive color/crop jitter can destroy the very signal we want.
    """
    norm = transforms.Normalize(config.IMAGENET_MEAN, config.IMAGENET_STD)

    if train and augment:
        return transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.1, contrast=0.1),
            transforms.ToTensor(),
            norm,
        ])

    return transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        norm,
    ])


# --- Dataloaders -------------------------------------------------------------
def build_dataloaders(cfg: config.TrainConfig):
    """Construct train / val / test dataloaders from an ImageFolder root.

    Behavior:
      * Requires `<data_dir>/train`. Carves a validation split from it
        (`cfg.val_split`) unless a `<data_dir>/val` directory exists.
      * Uses `<data_dir>/test` for the test loader if present, else falls back
        to the val split.

    Returns (train_loader, val_loader, test_loader, class_names).
    """
    data_dir = Path(cfg.data_dir)
    train_dir = data_dir / "train"
    if not train_dir.exists():
        raise FileNotFoundError(
            f"No train/ directory under {data_dir}. Arrange data as "
            f"ImageFolder (data/<name>/train/<class>/*.jpg) or run "
            f"`python -m stage1_vision.dataset --make-synthetic`."
        )

    train_tf = build_transforms(cfg.image_size, train=True, augment=cfg.augment)
    eval_tf = build_transforms(cfg.image_size, train=False, augment=False)

    full_train = ImageFolder(str(train_dir), transform=train_tf)
    class_names = full_train.classes

    # Validation: dedicated val/ dir if present, else split off the train set.
    val_dir = data_dir / "val"
    if val_dir.exists():
        train_ds = full_train
        val_ds = ImageFolder(str(val_dir), transform=eval_tf)
    else:
        n_val = max(1, int(len(full_train) * cfg.val_split))
        n_train = len(full_train) - n_val
        gen = torch.Generator().manual_seed(cfg.seed)
        train_ds, val_subset = random_split(full_train, [n_train, n_val], generator=gen)
        # val should use eval transforms — wrap with a transform-swapping view.
        val_ds = _EvalView(val_subset, eval_tf)

    # Test: dedicated test/ dir if present, else reuse val.
    test_dir = data_dir / "test"
    if test_dir.exists():
        test_ds = ImageFolder(str(test_dir), transform=eval_tf)
    else:
        print("[dataset] no test/ dir found — using validation split as test set.")
        test_ds = val_ds

    common = dict(batch_size=cfg.batch_size, num_workers=cfg.num_workers, pin_memory=True)
    train_loader = DataLoader(train_ds, shuffle=True, **common)
    val_loader = DataLoader(val_ds, shuffle=False, **common)
    test_loader = DataLoader(test_ds, shuffle=False, **common)

    print(
        f"[dataset] classes={class_names} | "
        f"train={len(train_ds)} val={len(val_ds)} test={len(test_ds)}"
    )
    return train_loader, val_loader, test_loader, class_names


class _EvalView(torch.utils.data.Dataset):
    """Wrap a random_split Subset so it applies eval transforms.

    `random_split` returns a Subset that shares the parent's (train) transform.
    For validation we want deterministic eval transforms instead; this view
    re-loads each sample's raw image and applies the eval transform.
    """

    def __init__(self, subset, eval_tf):
        self.subset = subset
        self.eval_tf = eval_tf
        self.base = subset.dataset  # the underlying ImageFolder

    def __len__(self):
        return len(self.subset)

    def __getitem__(self, idx):
        real_idx = self.subset.indices[idx]
        path, target = self.base.samples[real_idx]
        img = self.base.loader(path)
        return self.eval_tf(img), target


# --- Synthetic dataset (offline smoke test) ---------------------------------
def make_synthetic_dataset(root: Path | None = None, per_class: int = 60, seed: int = 42):
    """Generate a tiny labelled dataset of synthetic "parts" with painted defects.

    Three classes mimicking a recovery (reuse/repair/recycle) inspection story:
      * good     — clean part surface (→ would map to REUSE)
      * scratch  — thin bright/dark linear marks (→ REPAIR)
      * crack    — jagged dark fracture lines (→ RECYCLE)

    Images are procedurally drawn with OpenCV so the entire pipeline runs with no
    downloads and no internet. Not a substitute for a real dataset — just enough
    to prove train/inference/visualization end-to-end.
    """
    import cv2

    rng = np.random.default_rng(seed)
    root = Path(root) if root else config.DATA_DIR / "synthetic"
    classes = ["good", "scratch", "crack"]
    size = 256

    def base_surface() -> np.ndarray:
        # Metallic-grey surface with mild noise + brightness gradient.
        gray = rng.integers(110, 150)
        img = np.full((size, size, 3), gray, dtype=np.uint8)
        noise = rng.normal(0, 8, (size, size, 3))
        grad = np.linspace(-15, 15, size).reshape(1, size, 1)
        img = np.clip(img.astype(float) + noise + grad, 0, 255).astype(np.uint8)
        return img

    for split, n in (("train", per_class), ("test", max(8, per_class // 4))):
        for cls in classes:
            out_dir = root / split / cls
            out_dir.mkdir(parents=True, exist_ok=True)
            for i in range(n):
                img = base_surface()

                if cls == "scratch":
                    for _ in range(rng.integers(1, 3)):
                        p1 = (int(rng.integers(0, size)), int(rng.integers(0, size)))
                        p2 = (int(rng.integers(0, size)), int(rng.integers(0, size)))
                        shade = int(rng.choice([40, 220]))
                        cv2.line(img, p1, p2, (shade, shade, shade),
                                 int(rng.integers(1, 3)))

                elif cls == "crack":
                    # Jagged dark polyline = fracture.
                    x, y = int(rng.integers(20, size - 20)), int(rng.integers(0, 30))
                    pts = [(x, y)]
                    for _ in range(rng.integers(6, 12)):
                        x += int(rng.integers(-25, 25))
                        y += int(rng.integers(10, 30))
                        pts.append((np.clip(x, 0, size - 1), np.clip(y, 0, size - 1)))
                    for a, b in zip(pts, pts[1:]):
                        cv2.line(img, a, b, (20, 20, 20), int(rng.integers(2, 4)))

                cv2.imwrite(str(out_dir / f"{cls}_{i:04d}.jpg"), img)

    print(f"[dataset] synthetic dataset written to {root} "
          f"(classes={classes}, ~{per_class}/class train).")
    return root


def _cli():
    p = argparse.ArgumentParser(description="Stage 1 dataset utilities.")
    p.add_argument("--make-synthetic", action="store_true",
                   help="Generate an offline synthetic dataset under data/synthetic.")
    p.add_argument("--root", type=str, default=None,
                   help="Override output root for the synthetic dataset.")
    p.add_argument("--per-class", type=int, default=60,
                   help="Training images per class to generate.")
    args = p.parse_args()

    if args.make_synthetic:
        make_synthetic_dataset(root=args.root, per_class=args.per_class)
    else:
        p.print_help()


if __name__ == "__main__":
    _cli()
