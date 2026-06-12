"""Model definition for Stage 1.

A lightweight, pretrained CNN backbone (ResNet18 or MobileNetV3-Small) with a
fresh classification head sized to the dataset. Pretrained ImageNet weights make
fine-tuning fast on a mid-range GPU / Colab free tier.

We also expose the name of the last convolutional layer so Grad-CAM
(`gradcam.py`) can hook it to produce a defect-localization heatmap — that is
the "mask" output for Stage 1 without requiring pixel-level annotations.
"""
from __future__ import annotations

import torch
import torch.nn as nn
from torchvision import models


SUPPORTED_BACKBONES = ("resnet18", "mobilenet_v3_small")


def build_model(backbone: str, num_classes: int, pretrained: bool = True,
                freeze_backbone: bool = False) -> nn.Module:
    """Create a classifier with a pretrained backbone and a new head.

    Args:
        backbone: "resnet18" or "mobilenet_v3_small".
        num_classes: number of defect classes.
        pretrained: load ImageNet weights (recommended for fast fine-tuning).
        freeze_backbone: if True, only the new head is trained (fastest, but
            usually a few points lower accuracy).
    """
    if backbone not in SUPPORTED_BACKBONES:
        raise ValueError(f"Unsupported backbone {backbone!r}; choose from {SUPPORTED_BACKBONES}.")

    if backbone == "resnet18":
        weights = models.ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
        model = models.resnet18(weights=weights)
        in_features = model.fc.in_features
        model.fc = nn.Linear(in_features, num_classes)

    else:  # mobilenet_v3_small
        weights = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
        model = models.mobilenet_v3_small(weights=weights)
        in_features = model.classifier[-1].in_features
        model.classifier[-1] = nn.Linear(in_features, num_classes)

    if freeze_backbone:
        _freeze_all_but_head(model, backbone)

    return model


def _freeze_all_but_head(model: nn.Module, backbone: str) -> None:
    """Freeze every parameter except the final classification layer."""
    for p in model.parameters():
        p.requires_grad = False
    head = model.fc if backbone == "resnet18" else model.classifier[-1]
    for p in head.parameters():
        p.requires_grad = True


def last_conv_layer(model: nn.Module, backbone: str) -> nn.Module:
    """Return the last conv layer used as the Grad-CAM target.

    For ResNet18 this is the final residual block's last conv; for
    MobileNetV3-Small it is the last module in `features`.
    """
    if backbone == "resnet18":
        return model.layer4[-1].conv2
    return model.features[-1]


def save_checkpoint(model: nn.Module, path, *, backbone: str, class_names, image_size: int):
    """Persist weights plus the metadata inference needs to reconstruct the model."""
    torch.save(
        {
            "state_dict": model.state_dict(),
            "backbone": backbone,
            "class_names": list(class_names),
            "image_size": image_size,
        },
        path,
    )


def load_checkpoint(path, map_location="cpu"):
    """Rebuild a model from a checkpoint produced by `save_checkpoint`.

    Returns (model, metadata_dict).
    """
    ckpt = torch.load(path, map_location=map_location)
    model = build_model(
        backbone=ckpt["backbone"],
        num_classes=len(ckpt["class_names"]),
        pretrained=False,
    )
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model, ckpt
