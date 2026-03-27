#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Test script for WebUI functionality (no torch/gradio dependencies required).
"""

import sys
import os
import json

# 添加项目根目录到 path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def find_result_dir(result_dir: str = "result") -> str:
    """Find the result directory."""
    possible_paths = [
        os.path.join(PROJECT_ROOT, result_dir),
        os.path.abspath(result_dir),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return possible_paths[0]


def scan_models(result_dir: str = "result"):
    """Scan result directory for available trained models."""
    models = []
    result_path = find_result_dir(result_dir)

    if not os.path.exists(result_path):
        print(f"Warning: Result directory not found: {result_path}")
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
        has_trace_data = False
        if os.path.exists(trace_dir) and os.path.isdir(trace_dir):
            try:
                has_trace_data = len(os.listdir(trace_dir)) > 0
            except OSError:
                pass

        models.append(
            {
                "path": model_path,
                "name": model_dir,
                "type": args_dict.get("model", "Unknown"),
                "dataset": args_dict.get("dataset", "Unknown"),
                "num_classes": args_dict.get("num_classes", 0),
                "has_trace_data": bool(has_trace_data),
            }
        )

    return sorted(models, key=lambda x: x["name"])


def test_scan_models():
    """Test model scanning functionality."""
    print("=" * 60)
    print("Testing scan_models()")
    print("=" * 60)

    result_dir = find_result_dir("result")
    print(f"Result directory: {result_dir}")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Exists: {os.path.exists(result_dir)}")

    models = scan_models("result")
    print(f"\nFound {len(models)} models:")

    for m in models:
        trace_status = "✓" if m["has_trace_data"] else "✗"
        print(f"  [{trace_status}] {m['name']} ({m['type']})")
        print(f"        Dataset: {m['dataset']}, Classes: {m['num_classes']}")

    if len(models) == 0:
        print("\n⚠ No models found!")
        print("Please ensure model directories contain:")
        print("  - args.txt")
        print("  - model_final.pth")
        return False

    return True


def test_model_choices():
    """Test model choices."""
    print("\n" + "=" * 60)
    print("Testing model choices")
    print("=" * 60)

    models = scan_models("result")
    choices = [f"{m['name']} ({m['type']})" for m in models]
    print(f"Model choices ({len(choices)}):")
    for c in choices:
        print(f"  - {c}")

    trace_models = [m for m in models if m["has_trace_data"]]
    trace_choices = [f"{m['name']} ({m['type']})" for m in trace_models]
    print(f"\nTrace model choices ({len(trace_choices)}):")
    for c in trace_choices:
        print(f"  - {c}")

    return True


if __name__ == "__main__":
    print("FedTracker WebUI Test Script")
    print("=" * 60)

    success = True

    if not test_scan_models():
        success = False

    if not test_model_choices():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")
    print("=" * 60)

    sys.exit(0 if success else 1)
