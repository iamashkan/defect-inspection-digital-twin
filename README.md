# Defect Inspection Digital Twin

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](...)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white)](...)
[![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?logo=opencv&logoColor=white)](...)
[![ROS 2](https://img.shields.io/badge/ROS%202-Humble-22314E?logo=ros&logoColor=white)](...)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](...)

A simulation-only inspection pipeline for **Digital manufacturing**. The system
inspects a recovered end-of-life component, detects surface defects with a computer
vision, grades the part with machine learning, and emits a structured **recovery
decision** — while a **digital twin** keeps a live virtual record of every part
it sees.

A personal project exploring how vision + ML can automate the triage decisions
that sit at the heart of the circular economy. Everything runs in **simulation —
no physical hardware required.**

---

## Sample result (Stage 1)

Each inspected part yields a defect **class**, a Grad-CAM **localization heatmap**
(the "mask"), a **confidence**, and a **defect-area %** — visualized as a
three-panel overlay (`original | heatmap | overlay + label`):

![Defect detection overlay — crack](docs/sample_results/crack_overlay.png)

The model localizes the fracture and labels it `crack 100.0% area=21.1%`. Below
is the row-normalized confusion matrix from a short training run:

![Confusion matrix](docs/sample_results/confusion_matrix.png)

---

## Why this project

When a worn or broken component is recovered at end-of-life, the single most
valuable decision is *what to do with it next*: keep it as-is, send it for
restoration, or route it to material recovery? That triage decision is exactly
what this project automates:
