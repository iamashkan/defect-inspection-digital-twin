"""Minimal, dependency-free Grad-CAM for defect localization.

Grad-CAM produces a class-discriminative heatmap by weighting a target conv
layer's activation maps by the gradient of the predicted class score w.r.t. those
activations. In Stage 1 this heatmap is our defect "mask" — it shows *where* on
the part the model is looking, without needing pixel-level annotations.

Reference: Selvaraju et al., "Grad-CAM: Visual Explanations from Deep Networks
via Gradient-based Localization" (ICCV 2017).
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F


class GradCAM:
    """Compute Grad-CAM heatmaps for a single target conv layer.

    Usage:
        cam = GradCAM(model, target_layer)
        heatmap, class_idx, confidence = cam(input_tensor)   # input: 1x3xHxW
        cam.remove_hooks()
    """

    def __init__(self, model: torch.nn.Module, target_layer: torch.nn.Module):
        self.model = model.eval()
        self.target_layer = target_layer
        self._activations: torch.Tensor | None = None
        self._gradients: torch.Tensor | None = None

        # Forward hook captures activations; full backward hook captures grads.
        self._fwd = target_layer.register_forward_hook(self._save_activations)
        self._bwd = target_layer.register_full_backward_hook(self._save_gradients)

    def _save_activations(self, module, inputs, output):
        self._activations = output.detach()

    def _save_gradients(self, module, grad_input, grad_output):
        self._gradients = grad_output[0].detach()

    def __call__(self, input_tensor: torch.Tensor, class_idx: int | None = None):
        """Return (heatmap[H,W] in [0,1], class_idx, confidence).

        Args:
            input_tensor: 1x3xHxW normalized image tensor on the model's device.
            class_idx: target class; defaults to the model's top prediction.
        """
        if input_tensor.dim() != 4 or input_tensor.size(0) != 1:
            raise ValueError("GradCAM expects a single image batch of shape 1x3xHxW.")

        logits = self.model(input_tensor)
        probs = F.softmax(logits, dim=1)

        if class_idx is None:
            class_idx = int(probs.argmax(dim=1).item())
        confidence = float(probs[0, class_idx].item())

        # Backprop the target class score to the target layer.
        self.model.zero_grad(set_to_none=True)
        logits[0, class_idx].backward(retain_graph=False)

        acts = self._activations[0]      # C x h x w
        grads = self._gradients[0]       # C x h x w

        # Channel weights = global-average-pooled gradients.
        weights = grads.mean(dim=(1, 2))                 # C
        cam = torch.relu((weights[:, None, None] * acts).sum(dim=0))  # h x w

        # Upsample to the input resolution and normalize to [0, 1].
        cam = cam[None, None]
        cam = F.interpolate(
            cam, size=input_tensor.shape[2:], mode="bilinear", align_corners=False
        )[0, 0]
        cam -= cam.min()
        denom = cam.max()
        if denom > 0:
            cam /= denom
        return cam.cpu().numpy().astype(np.float32), class_idx, confidence

    def remove_hooks(self):
        self._fwd.remove()
        self._bwd.remove()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.remove_hooks()
