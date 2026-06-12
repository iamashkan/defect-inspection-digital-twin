"""Helper to make the Stage 1/2 code (`stage1_vision`, `stage2_decision`)
importable from the ROS 2 nodes.

The recommended setup is `pip install -e .` on the repo root, after which the
packages import normally. As a fallback this helper accepts an explicit repo
root (ROS parameter `repo_root`) or the `DEFECT_TWIN_ROOT` environment variable
and prepends it to sys.path.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_repo_on_path(repo_root: str = "") -> None:
    """Prepend the repo root to sys.path if stage1_vision isn't already importable."""
    try:
        import stage1_vision  # noqa: F401
        return  # already importable (e.g. via `pip install -e .`)
    except ModuleNotFoundError:
        pass

    candidates = []
    if repo_root:
        candidates.append(repo_root)
    if os.environ.get("DEFECT_TWIN_ROOT"):
        candidates.append(os.environ["DEFECT_TWIN_ROOT"])

    for c in candidates:
        p = Path(c).expanduser().resolve()
        if (p / "stage1_vision").is_dir():
            sys.path.insert(0, str(p))
            return

    raise ModuleNotFoundError(
        "Could not import `stage1_vision`. Run `pip install -e .` on the repo "
        "root, or set the `repo_root` parameter / DEFECT_TWIN_ROOT env var to the "
        "repository path."
    )
