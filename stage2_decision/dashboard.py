"""Streamlit dashboard for the Defect Inspection Digital Twin.

Two views:
  * Inspect    — upload (or pick a sample) part image, run the Stage 1 CV model
                 live, grade it, show the image + heatmap overlay + decision, and
                 record the part in the digital twin.
  * Statistics — running stats over every inspected part: decision mix, average
                 condition score, recovery rate, and the recent record table.

Run it (from the repo root, with deps installed and a trained checkpoint):

    streamlit run stage2_decision/dashboard.py

Configure the checkpoint path and digital-twin store in the sidebar.
"""
from __future__ import annotations

import sys
from pathlib import Path

# `streamlit run stage2_decision/dashboard.py` puts the *script's* directory on
# sys.path, not the repo root — so the stage1_vision / stage2_decision packages
# aren't importable by default. Add the repo root (one level up) to fix that.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np
import streamlit as st
import torch
from PIL import Image

from stage1_vision import config, model as model_lib
from stage1_vision.dataset import build_transforms
from stage1_vision.gradcam import GradCAM
from stage1_vision.inference import _softmax_probs, defect_mask_and_area, make_overlay
from stage2_decision.digital_twin import DigitalTwin
from stage2_decision.grading import (
    DECISION_COLORS,
    DECISIONS,
    GradingConfig,
    grade_record,
)

DEFAULT_WEIGHTS = config.OUTPUT_DIR / "best_model.pt"
SAMPLE_DIR = config.DATA_DIR / "synthetic" / "test"


# --- cached model loading -----------------------------------------------------
@st.cache_resource(show_spinner="Loading model…")
def load_model(weights_path: str):
    """Load the Stage 1 checkpoint once and cache it across reruns."""
    model, ckpt = model_lib.load_checkpoint(weights_path, map_location="cpu")
    target = model_lib.last_conv_layer(model, ckpt["backbone"])
    return model, ckpt, target


def infer_one(pil: Image.Image, model, ckpt, target):
    """Run defect inference on one PIL image → (record, overlay_rgb, heatmap)."""
    size = ckpt["image_size"]
    tf = build_transforms(size, train=False, augment=False)
    tensor = tf(pil).unsqueeze(0)

    cam = GradCAM(model, target)
    heatmap, class_idx, conf = cam(tensor)          # Grad-CAM needs gradients
    probs = _softmax_probs(model, tensor, torch.device("cpu"))
    cam.remove_hooks()

    pred_class = ckpt["class_names"][class_idx]
    mask, area_pct = defect_mask_and_area(heatmap)

    rgb_vis = np.array(pil.resize((size, size)))
    label = f"{pred_class}  {conf*100:.1f}%  area={area_pct:.1f}%"
    panel_bgr = make_overlay(rgb_vis, heatmap, label)
    panel_rgb = cv2.cvtColor(panel_bgr, cv2.COLOR_BGR2RGB)

    record = {
        "pred_class": pred_class,
        "confidence": float(conf),
        "defect_area_pct": float(area_pct),
        "probabilities": {c: float(p) for c, p in zip(ckpt["class_names"], probs)},
    }
    return record, panel_rgb, heatmap


def decision_badge(decision: str, confidence: float) -> str:
    """Return HTML for a colored decision badge."""
    color = DECISION_COLORS.get(decision, "#888")
    return (
        f"<div style='display:inline-block;padding:10px 22px;border-radius:10px;"
        f"background:{color};color:#111;font-weight:700;font-size:1.4rem;'>"
        f"{decision}</div>"
        f"<span style='margin-left:12px;color:#aaa;'>decision confidence "
        f"{confidence*100:.0f}%</span>"
    )


def sidebar_config():
    st.sidebar.header("Configuration")
    weights = st.sidebar.text_input("Model checkpoint", value=str(DEFAULT_WEIGHTS))
    store = st.sidebar.text_input(
        "Digital-twin store",
        value=str(config.OUTPUT_DIR / "digital_twin.jsonl"),
    )

    st.sidebar.subheader("Decision thresholds")
    reuse_min = st.sidebar.slider("REUSE if condition ≥", 50, 100, 80)
    repair_min = st.sidebar.slider("REPAIR if condition ≥", 0, reuse_min, 50)
    cfg = GradingConfig(reuse_min=float(reuse_min), repair_min=float(repair_min))

    return weights, store, cfg


def view_inspect(weights, store, grading_cfg):
    st.subheader("Inspect a part")

    if not Path(weights).exists():
        st.warning(
            f"No checkpoint at `{weights}`. Train Stage 1 first:\n\n"
            "```\npython -m stage1_vision.train --data data/synthetic --epochs 5\n```"
        )
        return

    # Input: upload, or pick a bundled sample.
    col_a, col_b = st.columns(2)
    uploaded = col_a.file_uploader("Upload a part image", type=["jpg", "jpeg", "png", "bmp"])
    sample = None
    if SAMPLE_DIR.exists():
        samples = sorted(str(p) for p in SAMPLE_DIR.rglob("*.jpg"))[:60]
        if samples:
            sample = col_b.selectbox("…or pick a sample", ["(none)"] + samples)
            if sample == "(none)":
                sample = None

    pil = None
    src_name = None
    if uploaded is not None:
        pil = Image.open(uploaded).convert("RGB")
        src_name = uploaded.name
    elif sample:
        pil = Image.open(sample).convert("RGB")
        src_name = sample

    if pil is None:
        st.info("Upload an image or pick a sample to inspect.")
        return

    model, ckpt, target = load_model(weights)
    record, overlay_rgb, _ = infer_one(pil, model, ckpt, target)
    grading = grade_record(record, grading_cfg)

    st.markdown(decision_badge(grading["decision"], grading["decision_confidence"]),
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Predicted defect", grading["pred_class"])
    c2.metric("Condition score", f"{grading['condition_score']:.0f}/100")
    c3.metric("Defect area", f"{grading['defect_area_pct']:.1f}%")

    st.image(overlay_rgb, caption="original | Grad-CAM heatmap | overlay",
             use_container_width=True)
    st.caption(grading["rationale"])

    # Record into the digital twin (one click → one part).
    if st.button("✓ Record this part in the digital twin", type="primary"):
        twin = DigitalTwin(store)
        stored = twin.add(image=src_name or "uploaded", grading=grading)
        st.success(f"Recorded {stored['part_id']} → {grading['decision']}")


def view_statistics(store):
    st.subheader("Digital-twin statistics")
    twin = DigitalTwin(store)
    stats = twin.stats()

    if stats["total_parts"] == 0:
        st.info("No parts recorded yet. Inspect some parts (or run "
                "`python -m stage2_decision.pipeline …`) to populate the twin.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Parts inspected", stats["total_parts"])
    c2.metric("Avg condition", f"{stats['avg_condition_score']:.0f}/100")
    c3.metric("Recovery rate", f"{stats['recovery_rate_pct']:.0f}%",
              help="Share kept in service (REUSE + REPAIR) vs RECYCLE")
    c4.metric("Avg decision conf", f"{stats['avg_decision_confidence']*100:.0f}%")

    st.markdown("**Decision mix**")
    counts = stats["decision_counts"]
    import pandas as pd

    chart_df = pd.DataFrame({"count": [counts[d] for d in DECISIONS]}, index=list(DECISIONS))
    st.bar_chart(chart_df, color="#5aa2ff")

    st.markdown("**Recent parts**")
    df = twin.to_dataframe()
    show_cols = ["part_id", "timestamp", "pred_class", "condition_score",
                 "decision", "decision_confidence", "image"]
    show_cols = [c for c in show_cols if c in df.columns]
    st.dataframe(df[show_cols].iloc[::-1].head(25), use_container_width=True)

    if st.button("Reset digital twin", help="Delete all recorded parts"):
        twin.clear()
        st.rerun()


def main():
    st.set_page_config(page_title="Defect Inspection Digital Twin",
                       page_icon="🔧", layout="wide")
    st.title("🔧 Defect Inspection Digital Twin")
    st.caption("Surface-defect CV → condition grading → REUSE / REPAIR / RECYCLE "
               "→ live digital-twin record.")

    weights, store, grading_cfg = sidebar_config()
    tab_inspect, tab_stats = st.tabs(["🔍 Inspect", "📊 Statistics"])
    with tab_inspect:
        view_inspect(weights, store, grading_cfg)
    with tab_stats:
        view_statistics(store)


if __name__ == "__main__":
    main()
