"""Persist champion weights so EvaluationLevel can score a new batch.

Artifacts are written only by this process and loaded only from
/app/artifacts/<uuid>.pt. Paths are allow-listed; caller-supplied
filenames are rejected.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import torch

from .pytorch_trainer import ChurnMLP

log = logging.getLogger("dact.champion_store")

ARTIFACT_DIR = Path("/app/artifacts")
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _path(version_id: str) -> Path:
    if not _UUID.match(version_id):
        raise ValueError("version_id is not a UUID")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = (ARTIFACT_DIR / f"{version_id}.pt").resolve()
    root = ARTIFACT_DIR.resolve()
    if path.parent != root:
        raise ValueError("artifact path escapes store")
    return path


def save_weights(version_id: str, model: ChurnMLP, threshold: float) -> None:
    path = _path(version_id)
    torch.save({"state_dict": model.state_dict(), "threshold": float(threshold)}, path)
    log.info("saved champion weights %s", path.name)


def load_weights(version_id: str) -> tuple[ChurnMLP, float] | None:
    try:
        path = _path(version_id)
    except ValueError:
        return None
    if not path.is_file():
        return None
    blob = torch.load(path, map_location="cpu")
    model = ChurnMLP()
    model.load_state_dict(blob["state_dict"])
    model.eval()
    return model, float(blob["threshold"])
