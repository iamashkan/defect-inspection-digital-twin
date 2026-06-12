"""Stage 2 — grading, recovery decision, and the digital-twin data layer.

Turns the per-image defect features produced by Stage 1 (defect class,
confidence, defect-area %) into:
    * a condition score (0-100)
    * a recovery decision: REUSE / REPAIR / RECYCLE
    * a decision confidence

and records every inspected part in a persistent digital twin (condition score,
defect heatmap path, decision, timestamp). A Streamlit dashboard visualizes the
image + heatmap overlay, the decision, and running statistics.

Modules:
    grading       rule-based, explainable grader (features -> decision)
    digital_twin  append-only record store + statistics (JSONL + pandas)
    pipeline      glue: Stage 1 inference -> grade -> record in the twin
    dashboard     Streamlit app (run with `streamlit run`)
"""

__all__ = ["grading", "digital_twin", "pipeline"]
