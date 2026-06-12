"""Stage 1 training: fine-tune a pretrained backbone on a surface-defect dataset.

Outputs (under cfg.output_dir, default repo `outputs/`):
    best_model.pt          checkpoint (weights + backbone + class names + size)
    metrics.json           final test accuracy + per-class precision/recall/F1
    confusion_matrix.png   row-normalized confusion matrix
    training_log.json      per-epoch train/val loss & accuracy

Example:
    python -m stage1_vision.train --data data/synthetic --epochs 5
    python -m stage1_vision.train --data data/NEU-DET --backbone mobilenet_v3_small
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import torch
import torch.nn as nn
from tqdm import tqdm

from . import config, model as model_lib, utils
from .dataset import build_dataloaders


def parse_args() -> config.TrainConfig:
    """Build a TrainConfig from CLI flags layered over config defaults."""
    cfg = config.TrainConfig()
    p = argparse.ArgumentParser(description="Stage 1 — train surface-defect classifier.")
    p.add_argument("--data", type=str, default=str(cfg.data_dir),
                   help="ImageFolder root (contains train/ and optionally test/).")
    p.add_argument("--backbone", type=str, default=cfg.backbone,
                   choices=model_lib.SUPPORTED_BACKBONES)
    p.add_argument("--epochs", type=int, default=cfg.epochs)
    p.add_argument("--batch-size", type=int, default=cfg.batch_size)
    p.add_argument("--lr", type=float, default=cfg.lr)
    p.add_argument("--image-size", type=int, default=cfg.image_size)
    p.add_argument("--freeze-backbone", action="store_true", default=cfg.freeze_backbone,
                   help="Train only the new head (fastest).")
    p.add_argument("--no-augment", dest="augment", action="store_false", default=cfg.augment)
    p.add_argument("--device", type=str, default=cfg.device, choices=["auto", "cuda", "cpu"])
    p.add_argument("--output-dir", type=str, default=str(cfg.output_dir))
    p.add_argument("--num-workers", type=int, default=cfg.num_workers)
    p.add_argument("--seed", type=int, default=cfg.seed)
    args = p.parse_args()

    cfg.data_dir = Path(args.data)
    cfg.backbone = args.backbone
    cfg.epochs = args.epochs
    cfg.batch_size = args.batch_size
    cfg.lr = args.lr
    cfg.image_size = args.image_size
    cfg.freeze_backbone = args.freeze_backbone
    cfg.augment = args.augment
    cfg.device = args.device
    cfg.output_dir = Path(args.output_dir)
    cfg.num_workers = args.num_workers
    cfg.seed = args.seed
    return cfg


def run_epoch(model, loader, criterion, device, optimizer=None) -> tuple[float, float]:
    """One pass over `loader`. Train if optimizer given, else evaluate.

    Returns (mean_loss, accuracy).
    """
    is_train = optimizer is not None
    model.train(is_train)

    total_loss, total_correct, total = 0.0, 0, 0
    ctx = torch.enable_grad() if is_train else torch.no_grad()
    with ctx:
        for images, targets in tqdm(loader, leave=False,
                                    desc="train" if is_train else "eval"):
            images, targets = images.to(device), targets.to(device)
            logits = model(images)
            loss = criterion(logits, targets)

            if is_train:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()

            total_loss += loss.item() * images.size(0)
            total_correct += (logits.argmax(1) == targets).sum().item()
            total += images.size(0)

    return total_loss / total, total_correct / total


@torch.no_grad()
def collect_predictions(model, loader, device):
    """Return (y_true, y_pred) lists over a loader for metric computation."""
    model.eval()
    y_true, y_pred = [], []
    for images, targets in tqdm(loader, leave=False, desc="predict"):
        logits = model(images.to(device))
        y_pred.extend(logits.argmax(1).cpu().tolist())
        y_true.extend(targets.tolist())
    return y_true, y_pred


def main():
    cfg = parse_args()
    utils.seed_everything(cfg.seed)
    device = utils.resolve_device(cfg.device)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[train] device={device} backbone={cfg.backbone} data={cfg.data_dir}")

    # --- Data ---
    train_loader, val_loader, test_loader, class_names = build_dataloaders(cfg)
    cfg.class_names = class_names

    # --- Model ---
    model = model_lib.build_model(
        backbone=cfg.backbone,
        num_classes=len(class_names),
        pretrained=cfg.pretrained,
        freeze_backbone=cfg.freeze_backbone,
    ).to(device)

    criterion = nn.CrossEntropyLoss(label_smoothing=cfg.label_smoothing)
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=cfg.lr, weight_decay=cfg.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cfg.epochs)

    # --- Train loop with best-on-val checkpointing ---
    best_val_acc, best_path = -1.0, cfg.output_dir / "best_model.pt"
    history = []
    t0 = time.time()
    for epoch in range(1, cfg.epochs + 1):
        tr_loss, tr_acc = run_epoch(model, train_loader, criterion, device, optimizer)
        va_loss, va_acc = run_epoch(model, val_loader, criterion, device)
        scheduler.step()

        history.append({"epoch": epoch, "train_loss": tr_loss, "train_acc": tr_acc,
                        "val_loss": va_loss, "val_acc": va_acc})
        print(f"[train] epoch {epoch:02d}/{cfg.epochs} | "
              f"train loss {tr_loss:.3f} acc {tr_acc:.3f} | "
              f"val loss {va_loss:.3f} acc {va_acc:.3f}")

        if va_acc > best_val_acc:
            best_val_acc = va_acc
            model_lib.save_checkpoint(
                model, best_path, backbone=cfg.backbone,
                class_names=class_names, image_size=cfg.image_size,
            )
            print(f"[train]   ↳ new best val acc {va_acc:.3f} → saved {best_path}")

    print(f"[train] done in {time.time() - t0:.1f}s, best val acc {best_val_acc:.3f}")

    # --- Final test-set evaluation using the best checkpoint ---
    best_model, _ = model_lib.load_checkpoint(best_path, map_location=device)
    best_model.to(device)
    y_true, y_pred = collect_predictions(best_model, test_loader, device)

    metrics = utils.compute_metrics(y_true, y_pred, class_names)
    metrics["best_val_accuracy"] = best_val_acc
    metrics["backbone"] = cfg.backbone
    metrics["class_names"] = class_names
    print(f"[train] TEST accuracy = {metrics['accuracy']:.3f}")

    utils.save_json(metrics, cfg.output_dir / "metrics.json")
    utils.save_json({"history": history}, cfg.output_dir / "training_log.json")
    utils.plot_confusion_matrix(y_true, y_pred, class_names,
                                cfg.output_dir / "confusion_matrix.png")
    print(f"[train] artifacts in {cfg.output_dir}")


if __name__ == "__main__":
    main()
