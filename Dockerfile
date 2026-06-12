# Reproducible environment for Re-X Inspection Digital Twin (Stages 1 & 2).
#
# Default base is CPU-friendly so it builds anywhere. For GPU, swap the base
# image for an NVIDIA CUDA runtime and install the matching torch wheel, e.g.:
#   FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04
#   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
# then run with:  docker run --gpus all ...
#
# Stage 3 (ROS 2 Humble / Gazebo / RViz) uses a separate ROS base image and is
# documented in the Stage 3 README rather than baked in here.

FROM python:3.10-slim

# OpenCV runtime libs (libGL / glib) for cv2 in headless containers.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first to leverage Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Headless matplotlib backend by default.
ENV MPLBACKEND=Agg

# Smoke-test entrypoint: build a synthetic dataset, train briefly, run inference.
CMD ["bash", "-lc", "\
    python -m stage1_vision.dataset --make-synthetic && \
    python -m stage1_vision.train --data data/synthetic --epochs 2 && \
    python -m stage1_vision.inference --weights outputs/best_model.pt \
        --images data/synthetic/test --out outputs/predictions"]
