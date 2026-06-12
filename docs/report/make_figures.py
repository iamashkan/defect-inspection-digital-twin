"""Generate the figures used in the thesis report and the slide deck.

Outputs into docs/report/assets/:
    architecture_pipeline.png   system block diagram (4 stages)
    stage2_grading_bands.png    condition-score → decision bands w/ sample parts
    stage2_decision_dist.png    decision distribution from the digital twin
and copies the existing Stage 1 overlay + confusion matrix into assets/.
"""
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs" / "report" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

GREEN, AMBER, RED, BLUE, GREY = "#2ecc71", "#f1c40f", "#e74c3c", "#5aa2ff", "#5b6472"


def architecture():
    fig, ax = plt.subplots(figsize=(11, 3.4))
    ax.set_xlim(0, 11); ax.set_ylim(0, 3.4); ax.axis("off")
    boxes = [
        ("Camera\n(sim feed)", 0.4, BLUE, "Stage 3"),
        ("Inspection\nCV + ML  (Grad-CAM)", 3.0, "#7a5cff", "Stage 1"),
        ("Decision\ngrading → REUSE/\nREPAIR/RECYCLE", 5.9, "#e67e22", "Stage 2"),
        ("Digital Twin\nrecord + stats", 8.8, GREEN, "Stage 2/3"),
    ]
    w, h, y = 2.0, 1.4, 1.4
    centers = []
    for label, x, color, tag in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    linewidth=0, facecolor=color, alpha=0.92))
        ax.text(x + w / 2, y + h / 2 + 0.08, label, ha="center", va="center",
                color="white", fontsize=10.5, fontweight="bold")
        ax.text(x + w / 2, y - 0.28, tag, ha="center", va="center",
                color=GREY, fontsize=9, style="italic")
        centers.append((x, x + w))
    labels = ["image", "class+mask\n+confidence", "condition score\n+ decision"]
    for (l, r), lab in zip(zip([c[1] for c in centers[:-1]], [c[0] for c in centers[1:]]), labels):
        ax.add_patch(FancyArrowPatch((l + 0.05, y + h / 2), (r - 0.05, y + h / 2),
                                     arrowstyle="-|>", mutation_scale=18, lw=2, color=GREY))
        ax.text((l + r) / 2, y + h / 2 + 0.55, lab, ha="center", va="bottom",
                fontsize=8.5, color=GREY)
    ax.text(5.5, 3.15, "Defect Inspection Digital Twin — processing pipeline",
            ha="center", fontsize=12.5, fontweight="bold", color="#222")
    fig.tight_layout()
    fig.savefig(ASSETS / "architecture_pipeline.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def grading_bands():
    fig, ax = plt.subplots(figsize=(11, 2.7))
    ax.set_xlim(0, 100); ax.set_ylim(0, 1.6)
    # Decision bands.
    ax.axvspan(0, 50, color=RED, alpha=0.85)
    ax.axvspan(50, 80, color=AMBER, alpha=0.85)
    ax.axvspan(80, 100, color=GREEN, alpha=0.85)
    ax.text(25, 1.32, "RECYCLE", ha="center", color="white", fontweight="bold", fontsize=12)
    ax.text(65, 1.32, "REPAIR", ha="center", color="white", fontweight="bold", fontsize=12)
    ax.text(90, 1.32, "REUSE", ha="center", color="white", fontweight="bold", fontsize=12)
    # Sample parts (from the synthetic demo) plotted by condition score.
    samples = [("crack", 22, RED), ("scratch", 61, AMBER), ("good", 96, GREEN)]
    for name, score, _ in samples:
        ax.plot([score], [0.55], marker="v", markersize=14, color="#111", zorder=5)
        ax.text(score, 0.32, f"{name}\n{score}/100", ha="center", va="top",
                fontsize=9.5, color="#111", fontweight="bold")
    ax.set_yticks([])
    ax.set_xlabel("Condition score (0 = scrap … 100 = pristine)", fontsize=10.5)
    ax.set_title("Stage 2 — condition score → recovery decision (with demo parts)",
                 fontsize=12, fontweight="bold")
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(ASSETS / "stage2_grading_bands.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def decision_dist():
    store = ROOT / "outputs" / "digital_twin.jsonl"
    counts = {"REUSE": 0, "REPAIR": 0, "RECYCLE": 0}
    if store.exists():
        for line in store.read_text().splitlines():
            if line.strip():
                d = json.loads(line).get("decision")
                if d in counts:
                    counts[d] += 1
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    bars = ax.bar(list(counts.keys()), list(counts.values()),
                  color=[GREEN, AMBER, RED], width=0.62)
    for b, v in zip(bars, counts.values()):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.15, str(v),
                ha="center", fontsize=12, fontweight="bold")
    total = sum(counts.values()) or 1
    recovery = 100 * (counts["REUSE"] + counts["REPAIR"]) / total
    ax.set_title(f"Stage 2 — decisions over {total} parts\n"
                 f"recovery rate (REUSE+REPAIR) = {recovery:.0f}%",
                 fontsize=12, fontweight="bold")
    ax.set_ylabel("parts")
    ax.set_ylim(0, max(counts.values()) + 1.5)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(ASSETS / "stage2_decision_dist.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def copy_existing():
    src = ROOT / "docs" / "sample_results"
    shutil.copy(src / "crack_overlay.png", ASSETS / "stage1_overlay.png")
    shutil.copy(src / "confusion_matrix.png", ASSETS / "stage1_confusion.png")


if __name__ == "__main__":
    architecture()
    grading_bands()
    decision_dist()
    copy_existing()
    print("figures written to", ASSETS)
    for p in sorted(ASSETS.glob("*.png")):
        print("  ", p.name, f"({p.stat().st_size // 1024} KB)")
