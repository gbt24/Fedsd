# -*- coding: UTF-8 -*-
"""
Utility functions for WebUI.
"""

import json
import os
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import torch


def scan_models(result_dir: str = "result") -> List[Dict]:
    """
    Scan result directory for available trained models.

    Returns:
        List of dicts with model info: {path, name, type, has_trace_data}
    """
    models = []
    result_path = os.path.abspath(result_dir)

    if not os.path.exists(result_path):
        return models

    for model_dir in os.listdir(result_path):
        model_path = os.path.join(result_path, model_dir)
        if not os.path.isdir(model_path):
            continue

        args_file = os.path.join(model_path, "args.txt")
        model_final = os.path.join(model_path, "model_final.pth")

        if not os.path.exists(args_file) or not os.path.exists(model_final):
            continue

        with open(args_file, "r") as f:
            args_dict = json.load(f)

        trace_dir = os.path.join(model_path, "trace_data")
        has_trace_data = os.path.exists(trace_dir) and os.listdir(trace_dir)

        models.append(
            {
                "path": model_path,
                "name": model_dir,
                "type": args_dict.get("model", "Unknown"),
                "dataset": args_dict.get("dataset", "Unknown"),
                "num_classes": args_dict.get("num_classes", 0),
                "has_trace_data": bool(has_trace_data),
                "args": args_dict,
            }
        )

    return sorted(models, key=lambda x: x["name"])


def load_model_args(model_path: str) -> Dict:
    """Load model arguments from args.txt."""
    args_file = os.path.join(model_path, "args.txt")
    if not os.path.exists(args_file):
        raise FileNotFoundError(f"args.txt not found in {model_path}")

    with open(args_file, "r") as f:
        return json.load(f)


def get_device(gpu_id: int = 0) -> torch.device:
    """Get PyTorch device based on GPU availability."""
    if torch.cuda.is_available() and gpu_id >= 0:
        return torch.device(f"cuda:{gpu_id}")
    return torch.device("cpu")


class ModelArgs:
    """Simple class to hold model arguments."""

    def __init__(self, args_dict: Dict):
        for k, v in args_dict.items():
            setattr(self, k, v)

    def __repr__(self):
        return f"ModelArgs({self.__dict__})"


def find_checkpoints(model_path: str) -> List[str]:
    """Find all checkpoint files in model directory."""
    checkpoints = []
    for f in os.listdir(model_path):
        if f.startswith("checkpoint_epoch_") and f.endswith(".pth"):
            checkpoints.append(os.path.join(model_path, f))
    return sorted(checkpoints)


def get_cifar10_labels() -> List[str]:
    """Return CIFAR-10 class labels."""
    return [
        "airplane",
        "automobile",
        "bird",
        "cat",
        "deer",
        "dog",
        "frog",
        "horse",
        "ship",
        "truck",
    ]


def get_cifar100_labels() -> List[str]:
    """Return CIFAR-100 class labels (coarse)."""
    return [
        "aquatic_mammals",
        "fish",
        "flowers",
        "food_containers",
        "fruit_and_vegetables",
        "household_electrical_devices",
        "household_furniture",
        "insects",
        "large_carnivores",
        "large_man-made_outdoor_things",
        "large_natural_outdoor_scenes",
        "large_omnivores",
        "medium_mammals",
        "non-insect_invertebrates",
        "people",
        "reptiles",
        "small_mammals",
        "trees",
        "vehicles_1",
        "vehicles_2",
    ]


def format_bytes(size: int) -> str:
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"
