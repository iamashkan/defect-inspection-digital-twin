"""Central configuration for Stage 1.

Everything tunable — paths, image size, backbone, hyperparameters — lives here so
the training and inference scripts stay declarative and reproducible. CLI flags
on the scripts override these defaults.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# --- Repo-relative paths -----------------------------------------------------
# config.py is at <repo>/stage1_vision/config.py, so the repo root is two up.
REPO_ROOT: Path = Path(__file__).resolve().parents[1]
DATA_DIR: Path = REPO_ROOT / "data"
OUTPUT_DIR: Path = REPO_ROOT / "outputs"

# --- Reproducibility ---------------------------------------------------------
SEED: int = 42

# ImageNet normalization stats (the pretrained backbones expect these).
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


@dataclass
class TrainConfig:
    """Hyperparameters for fine-tuning the defect classifier.

    Defaults are deliberately small/fast for a mid-range GPU and Colab's free
    tier. They are enough to fine-tune a pretrained backbone to good accuracy on
    the recommended surface-defect datasets.
    """

    # Data
    data_dir: Path = DATA_DIR / "synthetic"   # ImageFolder root with train/ test/
    image_size: int = 224                      # square input fed to the backbone
    batch_size: int = 32
    num_workers: int = 2
    val_split: float = 0.15                    # carved from train/ when no val/ dir

    # Model
    backbone: str = "resnet18"                 # "resnet18" | "mobilenet_v3_small"
    pretrained: bool = True                    # ImageNet weights → fast fine-tune
    freeze_backbone: bool = False              # True = train only the new head

    # Optimization
    epochs: int = 10
    lr: float = 3e-4
    weight_decay: float = 1e-4
    label_smoothing: float = 0.05

    # Runtime
    device: str = "auto"                       # "auto" | "cuda" | "cpu"
    output_dir: Path = OUTPUT_DIR
    seed: int = SEED

    # Light data augmentation (kept gentle: defects are subtle texture cues).
    augment: bool = True

    # Derived at runtime; filled in by train.py after reading the dataset.
    class_names: list[str] = field(default_factory=list)
