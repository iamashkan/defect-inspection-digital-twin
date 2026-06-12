# Final graded result (Stage 2): a detection plus the recovery decision.
# Published on /inspection/result by the decision node and consumed by the
# digital-twin node.
std_msgs/Header header

# Unique id assigned to the inspected part by the decision node.
string part_id

# Identifier carried from the camera (demo: source image filename).
string source_id

# --- detection (echoed from DetectionResult) ---
string pred_class
float32 confidence
float32 defect_area_pct

# --- grading (Stage 2) ---
float32 severity              # class severity weight used, 0..1
float32 condition_score       # 0..100
string decision               # "REUSE" | "REPAIR" | "RECYCLE"
float32 decision_confidence   # 0..1
