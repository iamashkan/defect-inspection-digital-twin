"""Stage 1 — surface-defect computer vision for the Defect Inspection Digital Twin.

Public surface: train a lightweight pretrained backbone on a surface-defect
dataset, then run inference that yields, per image:
    * a defect class
    * a localization heatmap ("mask") via Grad-CAM
    * a confidence score

Each module is runnable on its own as `python -m stage1_vision.<module>`.
"""

__all__ = ["config", "dataset", "model", "gradcam", "utils", "train", "inference"]
