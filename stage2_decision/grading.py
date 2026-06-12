"""Grading + recovery decision.

Converts the defect features from Stage 1 into a **condition score (0-100)**, a
**decision** (REUSE / REPAIR / RECYCLE) and a **decision confidence** — using a
transparent, rule-based model so every decision is explainable (important for an
inspection/quality context, where a black-box "RECYCLE" is a hard sell).

Inputs are exactly the per-image records Stage 1 emits, e.g.:
    {"pred_class": "crack", "confidence": 0.974, "defect_area_pct": 21.1, ...}

The grader is dataset-agnostic: each defect class carries a *severity* weight
(0 = cosmetic, 1 = structural/critical). Defaults cover the synthetic classes
plus the common NEU-DET and casting class names; pass your own map for other
datasets.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Decisions (kept as plain constants so other modules / the dashboard share them).
REUSE = "REUSE"
REPAIR = "REPAIR"
RECYCLE = "RECYCLE"
DECISIONS = (REUSE, REPAIR, RECYCLE)

# UI color per decision (used by the dashboard; defined here so it stays in one place).
DECISION_COLORS = {REUSE: "#2ecc71", REPAIR: "#f1c40f", RECYCLE: "#e74c3c"}


def default_severity_map() -> dict[str, float]:
    """Severity (0=cosmetic .. 1=structural) for common defect class names.

    Keys are lower-cased. Unknown classes fall back to GradingConfig.default_severity.
    """
    return {
        # --- synthetic demo classes ---
        "good": 0.0,
        "scratch": 0.35,
        "crack": 0.95,
        # --- NEU-DET steel surface defects ---
        "crazing": 0.60,
        "inclusion": 0.80,
        "patches": 0.40,
        "pitted_surface": 0.70,
        "rolled-in_scale": 0.50,
        "scratches": 0.35,
        # --- casting product dataset ---
        "ok_front": 0.0,
        "def_front": 0.85,
        # --- generic "no defect" aliases ---
        "ok": 0.0,
        "normal": 0.0,
        "none": 0.0,
    }


@dataclass
class GradingConfig:
    """Tunable, transparent grading parameters."""

    severity_by_class: dict[str, float] = field(default_factory=default_severity_map)
    default_severity: float = 0.5            # for unseen defect classes

    # A defect covering >= area_full_pct of the surface is treated as "fully damaged".
    area_full_pct: float = 40.0

    # How the condition penalty splits between severity (type) and area (extent).
    severity_weight: float = 0.6
    area_weight: float = 0.4

    # Condition-score thresholds that map to decisions.
    reuse_min: float = 80.0                  # score >= reuse_min  -> REUSE
    repair_min: float = 50.0                 # repair_min <= score < reuse_min -> REPAIR
    #                                          score < repair_min -> RECYCLE

    # Class names that mean "no real defect" (forces a clean condition score).
    good_classes: tuple[str, ...] = ("good", "ok", "ok_front", "normal", "none")


def _severity_for(pred_class: str, cfg: GradingConfig) -> float:
    return cfg.severity_by_class.get(pred_class.lower(), cfg.default_severity)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def condition_score(pred_class: str, defect_area_pct: float, confidence: float,
                    cfg: GradingConfig) -> tuple[float, float]:
    """Return (condition_score 0-100, penalty 0-1).

    For a "good"-class part the detected heatmap area is spurious, so we ignore
    area and only lightly penalize low model confidence — a clean part should
    score near 100.
    """
    pred_class_l = pred_class.lower()

    if pred_class_l in cfg.good_classes:
        # Clean part: condition driven by how *sure* we are it is clean.
        score = 100.0 - 15.0 * (1.0 - _clamp(confidence))
        return round(score, 1), round(1.0 - score / 100.0, 3)

    severity = _severity_for(pred_class_l, cfg)
    area_frac = _clamp(defect_area_pct / cfg.area_full_pct)
    penalty = _clamp(cfg.severity_weight * severity + cfg.area_weight * area_frac)
    score = 100.0 * (1.0 - penalty)
    return round(score, 1), round(penalty, 3)


def _decision_from_score(score: float, cfg: GradingConfig) -> str:
    if score >= cfg.reuse_min:
        return REUSE
    if score >= cfg.repair_min:
        return REPAIR
    return RECYCLE


def _decision_confidence(score: float, model_conf: float, cfg: GradingConfig) -> float:
    """Blend model confidence with the margin to the nearest decision boundary.

    A score sitting right on a threshold (e.g. 80.0 between REPAIR/REUSE) is an
    inherently shakier call than one deep inside a band — so we down-weight
    confidence near boundaries.
    """
    boundaries = [cfg.reuse_min, cfg.repair_min]
    margin = min(abs(score - b) for b in boundaries)
    # Normalize margin by the width of a typical band; cap at 1.0.
    band = max(1.0, (cfg.reuse_min - cfg.repair_min))
    margin_norm = _clamp(margin / band)
    conf = 0.6 * _clamp(model_conf) + 0.4 * margin_norm
    return round(conf, 3)


def grade_record(record: dict, cfg: GradingConfig | None = None) -> dict:
    """Grade a single Stage 1 record.

    Args:
        record: dict with at least `pred_class`, `confidence`, `defect_area_pct`.
        cfg: grading parameters (defaults if None).

    Returns a dict with condition_score, decision, decision_confidence and a
    human-readable rationale, plus the input features echoed for traceability.
    """
    cfg = cfg or GradingConfig()
    pred_class = str(record.get("pred_class", "unknown"))
    model_conf = float(record.get("confidence", 0.0))
    area_pct = float(record.get("defect_area_pct", 0.0))

    score, penalty = condition_score(pred_class, area_pct, model_conf, cfg)
    decision = _decision_from_score(score, cfg)
    dconf = _decision_confidence(score, model_conf, cfg)
    severity = 0.0 if pred_class.lower() in cfg.good_classes else _severity_for(pred_class, cfg)

    rationale = (
        f"class='{pred_class}' (severity {severity:.2f}), "
        f"defect area {area_pct:.1f}% → condition {score:.1f}/100 → {decision} "
        f"(thresholds: REUSE≥{cfg.reuse_min:.0f}, REPAIR≥{cfg.repair_min:.0f})"
    )

    return {
        "pred_class": pred_class,
        "model_confidence": round(model_conf, 4),
        "defect_area_pct": round(area_pct, 2),
        "severity": round(severity, 3),
        "condition_score": score,
        "decision": decision,
        "decision_confidence": dconf,
        "rationale": rationale,
    }


if __name__ == "__main__":
    # Tiny self-check across the three synthetic classes.
    cfg = GradingConfig()
    samples = [
        {"pred_class": "good", "confidence": 0.74, "defect_area_pct": 14.4},
        {"pred_class": "scratch", "confidence": 0.83, "defect_area_pct": 18.0},
        {"pred_class": "crack", "confidence": 0.97, "defect_area_pct": 21.1},
    ]
    for s in samples:
        g = grade_record(s, cfg)
        print(f"{s['pred_class']:8s} -> {g['decision']:8s} "
              f"score={g['condition_score']:5.1f} conf={g['decision_confidence']:.2f}")
