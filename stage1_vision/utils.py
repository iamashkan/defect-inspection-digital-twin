"""Shared helpers for Stage 1: seeding, device selection, metrics, plotting.

Kept dependency-light (numpy, matplotlib, scikit-learn) so the training and
inference scripts read cleanly.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import torch


# --- Reproducibility ---------------------------------------------------------
def seed_everything(seed: int) -> None:
    """Seed Python, NumPy and PyTorch for reproducible runs."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    # Favor reproducibility over the last few % of speed.
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def resolve_device(choice: str = "auto") -> torch.device:
    """Map a config string to a torch.device, falling back to CPU."""
    if choice == "auto":
        choice = "cuda" if torch.cuda.is_available() else "cpu"
    if choice == "cuda" and not torch.cuda.is_available():
        print("[utils] CUDA requested but not available — using CPU.")
        choice = "cpu"
    return torch.device(choice)


# --- Metrics -----------------------------------------------------------------
def accuracy_from_logits(logits: torch.Tensor, targets: torch.Tensor) -> float:
    """Top-1 accuracy for a batch of logits."""
    preds = logits.argmax(dim=1)
    return (preds == targets).float().mean().item()


def compute_metrics(y_true, y_pred, class_names) -> dict:
    """Build an accuracy / per-class report dict using scikit-learn."""
    from sklearn.metrics import accuracy_score, classification_report

    report = classification_report(
        y_true,
        y_pred,
        labels=list(range(len(class_names))),
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "per_class": report,
    }


def save_json(obj: dict, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
    print(f"[utils] wrote {path}")


# --- Plotting ----------------------------------------------------------------
def plot_confusion_matrix(y_true, y_pred, class_names, out_path: Path) -> None:
    """Render and save a normalized confusion matrix."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import confusion_matrix

    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(class_names))))
    cm_norm = cm.astype(float) / np.clip(cm.sum(axis=1, keepdims=True), 1, None)

    fig, ax = plt.subplots(figsize=(1.4 * len(class_names) + 2, 1.4 * len(class_names) + 2))
    im = ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax.set_xticks(range(len(class_names)))
    ax.set_yticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=45, ha="right")
    ax.set_yticklabels(class_names)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("Confusion matrix (row-normalized)")

    # Annotate each cell with count and normalized value.
    for i in range(len(class_names)):
        for j in range(len(class_names)):
            ax.text(
                j, i, f"{cm[i, j]}\n{cm_norm[i, j]:.2f}",
                ha="center", va="center",
                color="white" if cm_norm[i, j] > 0.5 else "black",
                fontsize=8,
            )

    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"[utils] wrote {out_path}")


def denormalize(img_tensor: torch.Tensor, mean, std) -> np.ndarray:
    """Undo ImageNet normalization → HxWx3 uint8 RGB array for visualization."""
    img = img_tensor.detach().cpu().numpy().transpose(1, 2, 0)
    img = img * np.array(std) + np.array(mean)
    img = np.clip(img, 0, 1)
    return (img * 255).astype(np.uint8)
