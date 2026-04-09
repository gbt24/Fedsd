# -*- coding: UTF-8 -*-
"""
Visualize defingerprint experiment results.

Creates a 3-panel Matplotlib figure showing:
1. FID vs Finetune Epochs (generation quality over training)
2. Fingerprint Retention vs Finetune Epochs (fingerprint robustness)
3. Pareto Frontier (FID vs Retention trade-off)
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


def load_results(results_path: str) -> dict[str, Any]:
    """
    Load JSON results file.

    Args:
        results_path: Path to results.json file

    Returns:
        Dictionary containing experiment results
    """
    with open(results_path, "r") as f:
        results = json.load(f)
    return results


def prepare_plot_data(results: dict[str, Any]) -> dict[str, Any]:
    """
    Extract and prepare plot data from experiment results.

    Args:
        results: Dictionary containing experiment results

    Returns:
        Dictionary with prepared data for plotting:
        - baselines: dict with 'fid' and 'retention' for Baseline-0 and Baseline-1
        - experiments: list of dicts with 'epoch', 'fid', 'retention'
        - all_points: list of all (fid, retention, name) tuples
    """
    # Extract baselines
    baseline_0 = results.get("Baseline-0", {})
    baseline_1 = results.get("Baseline-1", {})

    b0_fid = baseline_0.get("fid", 0.0)
    b1_fid = baseline_1.get("fid", 0.0)
    b1_fp_acc = baseline_1.get("fingerprint_accuracy", 100.0)

    baselines = {
        "Baseline-0": {
            "fid": b0_fid,
            "retention": 0.0,  # No fingerprint
        },
        "Baseline-1": {
            "fid": b1_fid,
            "retention": 100.0,  # Full fingerprint
        },
    }

    # Extract experiments
    experiments = []
    all_points = [
        (b0_fid, 0.0, "Baseline-0"),
        (b1_fid, 100.0, "Baseline-1"),
    ]

    # Find experiment groups (Exp-1, Exp-3, Exp-5, Exp-10)
    exp_groups = [k for k in results.keys() if k.startswith("Exp-")]

    for group_name in sorted(exp_groups, key=lambda x: int(x.split("-")[1])):
        group_data = results.get(group_name, {})
        epoch = int(group_name.split("-")[1])
        fid = group_data.get("fid", 0.0)
        fp_acc = group_data.get("fingerprint_accuracy", 0.0)

        # Fingerprint retention rate (relative to Baseline-1)
        fp_retention = (fp_acc / b1_fp_acc * 100) if b1_fp_acc > 0 else 0.0

        experiments.append(
            {
                "epoch": epoch,
                "fid": fid,
                "retention": fp_retention,
            }
        )

        all_points.append((fid, fp_retention, group_name))

    return {
        "baselines": baselines,
        "experiments": experiments,
        "all_points": all_points,
    }


def plot_results(data: dict[str, Any], output_path: str) -> None:
    """
    Create 3-panel figure with Matplotlib.

    Args:
        data: Dictionary with prepared plot data
        output_path: Path to save the figure
    """
    # Use seaborn style
    plt.style.use("seaborn-v0_8-darkgrid")

    # Create figure with 3 subplots
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    baselines = data["baselines"]
    experiments = data["experiments"]
    all_points = data["all_points"]

    # Panel 1: FID vs Finetune Epochs
    ax1 = axes[0]

    # Plot baseline lines (horizontal)
    ax1.axhline(
        y=baselines["Baseline-0"]["fid"],
        color="green",
        linestyle="--",
        linewidth=2,
        label="Baseline-0 (No FP)",
    )
    ax1.axhline(
        y=baselines["Baseline-1"]["fid"],
        color="red",
        linestyle="--",
        linewidth=2,
        label="Baseline-1 (With FP)",
    )

    # Plot experiments
    if experiments:
        epochs = [e["epoch"] for e in experiments]
        fids = [e["fid"] for e in experiments]
        ax1.plot(
            epochs,
            fids,
            color="blue",
            marker="o",
            linewidth=2,
            markersize=8,
            label="Finetuned Models",
        )

    ax1.set_xlabel("Finetune Epochs", fontweight="bold", fontsize=12)
    ax1.set_ylabel("FID Score", fontweight="bold", fontsize=12)
    ax1.set_title("FID vs Finetune Epochs", fontweight="bold", fontsize=14)
    ax1.legend(loc="best")
    ax1.grid(True, alpha=0.3)

    # Panel 2: Fingerprint Retention vs Finetune Epochs
    ax2 = axes[1]

    # Plot baseline lines (horizontal)
    ax2.axhline(
        y=baselines["Baseline-0"]["retention"],
        color="green",
        linestyle="--",
        linewidth=2,
        label="Baseline-0 (No FP)",
    )
    ax2.axhline(
        y=baselines["Baseline-1"]["retention"],
        color="red",
        linestyle="--",
        linewidth=2,
        label="Baseline-1 (With FP)",
    )

    # Plot experiments
    if experiments:
        epochs = [e["epoch"] for e in experiments]
        retentions = [e["retention"] for e in experiments]
        ax2.plot(
            epochs,
            retentions,
            color="orange",
            marker="s",
            linewidth=2,
            markersize=8,
            label="Finetuned Models",
        )

    ax2.set_xlabel("Finetune Epochs", fontweight="bold", fontsize=12)
    ax2.set_ylabel("Fingerprint Retention (%)", fontweight="bold", fontsize=12)
    ax2.set_title(
        "Fingerprint Retention vs Finetune Epochs", fontweight="bold", fontsize=14
    )
    ax2.legend(loc="best")
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(-5, 105)  # 0-100% range

    # Panel 3: Pareto Frontier - FID vs Retention
    ax3 = axes[2]

    # Prepare colors and markers
    colors = []
    markers = []
    sizes = []

    for fid, retention, name in all_points:
        if name == "Baseline-0":
            colors.append("green")
            markers.append("s")  # square
            sizes.append(150)
        elif name == "Baseline-1":
            colors.append("red")
            markers.append("s")  # square
            sizes.append(150)
        else:
            colors.append("blue")
            markers.append("o")  # circle
            sizes.append(100)

    # Plot all points
    for i, (fid, retention, name) in enumerate(all_points):
        ax3.scatter(
            [fid],
            [retention],
            c=colors[i],
            marker=markers[i],
            s=sizes[i],
            label=name if i < 2 else None,
            zorder=3,
        )
        # Annotate each point
        ax3.annotate(
            name,
            (fid, retention),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=9,
            fontweight="bold",
        )

    # Draw Pareto frontier line
    if len(all_points) > 2:
        # Sort by FID (x-axis)
        sorted_points = sorted(all_points, key=lambda x: x[0])

        # Find Pareto frontier (lower FID and higher retention is better)
        pareto_points = []
        max_retention_so_far = -1

        for fid, retention, name in sorted_points:
            if retention > max_retention_so_far:
                pareto_points.append((fid, retention))
                max_retention_so_far = retention

        # Plot frontier
        if len(pareto_points) > 1:
            pareto_fids = [p[0] for p in pareto_points]
            pareto_retentions = [p[1] for p in pareto_points]
            ax3.plot(
                pareto_fids,
                pareto_retentions,
                "k--",
                linewidth=1.5,
                alpha=0.5,
                label="Pareto Frontier",
            )

    ax3.set_xlabel("FID Score", fontweight="bold", fontsize=12)
    ax3.set_ylabel("Fingerprint Retention (%)", fontweight="bold", fontsize=12)
    ax3.set_title("Pareto Frontier: FID vs Retention", fontweight="bold", fontsize=14)
    ax3.legend(loc="best")
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(-5, 105)  # 0-100% range

    # Adjust layout
    plt.tight_layout()

    # Save figure
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"Figure saved to: {output_path}")

    plt.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Visualize defingerprint experiment results"
    )
    parser.add_argument(
        "--results",
        type=str,
        default="experiments/defingerprint/results/results.json",
        help="Path to results.json file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save figure (default: same directory as results.json)",
    )

    args = parser.parse_args()

    # Resolve paths
    results_path = Path(args.results)

    if args.output is None:
        output_path = results_path.parent / "results_visualization.png"
    else:
        output_path = Path(args.output)

    # Load results
    print(f"Loading results from: {results_path}")
    results = load_results(str(results_path))

    # Prepare plot data
    print("Preparing plot data...")
    data = prepare_plot_data(results)

    # Create visualization
    print("Creating visualization...")
    plot_results(data, str(output_path))


if __name__ == "__main__":
    main()
