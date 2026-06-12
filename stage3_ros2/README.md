# Stage 3 — ROS 2 (Humble) + Gazebo + RViz

Wraps the Stage 1 CV model and Stage 2 grading/digital-twin into a ROS 2 node
graph, with a minimal Gazebo inspection-cell world and an RViz config.

```
 camera_node ──/inspection/image_raw──▶ inspection_node ──/inspection/detection──▶ decision_node
 (dataset feed)                          (Stage 1 CV+ML)        (DetectionResult)    (Stage 2 grade)
                                              │                                          │
                                   /inspection/overlay                          /inspection/result
                                       (Image → RViz)                          (InspectionResult)
                                                                                          │
                                                                                          ▼
                                                                                  digital_twin_node
                                                                          records part + /inspection/
                                                                          decision_marker (→ RViz)
```

> **Platform note:** ROS 2 + Gazebo run on **Linux (Ubuntu 22.04)**, not macOS.
> Use the provided Docker image for the headless node graph, or a native Ubuntu
> 22.04 + ROS 2 Humble machine for the full RViz/Gazebo GUI experience.

---

## Nodes & topics

| Node | Subscribes | Publishes | Role |
|------|------------|-----------|------|
| `camera_node` | — | `/inspection/image_raw` (Image) | Streams recovered-part images from a folder (simulated camera). |
| `inspection_node` | `/inspection/image_raw` | `/inspection/overlay` (Image), `/inspection/detection` (DetectionResult) | Runs the Stage 1 model + Grad-CAM. |
| `decision_node` | `/inspection/detection` | `/inspection/result` (InspectionResult) | Stage 2 grading → REUSE/REPAIR/RECYCLE. |
| `digital_twin_node` | `/inspection/result` | `/inspection/decision_marker` (MarkerArray) | Records the part in the twin; RViz decision markers. |

Custom interfaces live in the `defect_inspection_interfaces` package
(`DetectionResult`, `InspectionResult`).

---

## Quick start — headless, in Docker (recommended on macOS/Windows)

From the **repo root**:

```bash
docker build -f stage3_ros2/Dockerfile.ros2 -t defect-twin-ros2 .
docker run --rm -it defect-twin-ros2
```

The default command trains a tiny Stage 1 model and launches the four nodes; you
will see decisions stream through the graph, e.g.:

```
[inspection_node] detected crack (conf 0.97, area 21.1%) on crack_0001.jpg
[decision_node]  crack_0001.jpg: crack → RECYCLE (condition 22/100, conf 0.79)
[digital_twin_node] recorded PART-9C0D1E2F (crack_0001.jpg) → RECYCLE | twin now holds 7 parts, recovery rate 57%
```

---

## Full run with RViz + Gazebo (native Ubuntu 22.04 + ROS 2 Humble)

**1. Install** ROS 2 Humble (desktop-full) and the extras:

```bash
sudo apt install ros-humble-desktop-full ros-humble-cv-bridge ros-humble-gazebo-ros-pkgs
```

**2. Make the Stage 1/2 code importable and train a model** (from the repo root):

```bash
pip install -e .
python3 -m stage1_vision.dataset --make-synthetic
python3 -m stage1_vision.train --data data/synthetic --epochs 5
```

**3. Build the workspace:**

```bash
cd stage3_ros2/ros2_ws
colcon build
source install/setup.bash
```

**4. Launch the inspection cell** (back at the repo root):

```bash
ros2 launch defect_inspection inspection_cell.launch.py \
    repo_root:=$PWD \
    weights:=$PWD/outputs/best_model.pt \
    image_dir:=$PWD/data/synthetic/test \
    use_rviz:=true use_gazebo:=true
```

What you should see:
- **RViz**: the live `original | heatmap | overlay` image, and a colored text
  marker showing the current decision (green REUSE / amber REPAIR / red RECYCLE)
  plus running statistics (parts inspected, decision mix, recovery rate).
- **Gazebo**: the inspection cell — a table with a part and a fixed downward
  camera.
- **Terminal**: per-part detection → decision → twin-record logs.

Inspect topics live:

```bash
ros2 topic echo /inspection/result
ros2 topic hz /inspection/overlay
```

---

## Launch arguments

| Arg | Default | Meaning |
|-----|---------|---------|
| `repo_root` | `""` | Repo path (lets nodes import stage1/stage2 if not `pip install -e`’d). |
| `weights` | `""` | Stage 1 checkpoint path. |
| `image_dir` | `""` | Folder of part images for `camera_node`. |
| `store` | `""` | Digital-twin JSONL (default `outputs/digital_twin.jsonl`). |
| `device` | `cpu` | `cpu` / `cuda` / `auto`. |
| `publish_rate` | `0.5` | Camera Hz. |
| `reuse_min` / `repair_min` | `80` / `50` | Decision thresholds. |
| `use_rviz` | `true` | Start RViz with the bundled config. |
| `use_gazebo` | `false` | Bring up the Gazebo inspection-cell world. |

---

## Notes

- The dataset `camera_node` provides the defect imagery the CV model actually
  grades; the Gazebo camera (`/inspection/gz_camera/image_raw`) is the cell’s
  visual feed. Keeping them separate means the pipeline runs with or without
  Gazebo, and the CV always sees real surface-defect textures.
- The nodes reuse the **exact** Stage 1 model and Stage 2 grader — no logic is
  duplicated, so a better-trained model or retuned thresholds flow straight
  through to the ROS graph.
