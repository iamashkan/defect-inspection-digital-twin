# Output of the inspection node (Stage 1 CV+ML): a per-frame defect detection,
# before grading. Published on /inspection/detection.
std_msgs/Header header

# Identifier of the inspected part/frame (carried from the camera; for the demo
# this is the source image filename).
string source_id

# Predicted defect class (e.g. "good", "scratch", "crack").
string pred_class

# Top-1 softmax probability for pred_class, in [0, 1].
float32 confidence

# Percentage of the surface flagged as defective (thresholded Grad-CAM mask).
float32 defect_area_pct
