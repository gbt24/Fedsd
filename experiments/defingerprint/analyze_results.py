# -*- coding: UTF-8 -*-
"""
Analyze defingerprint experiment results.

This script loads results.json and generates a comprehensive analysis report including:
- Statistical metrics (FID changes, retention rates)
- Pareto optimal points
- Formatted text report
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any

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


def compute_statistics(results: dict[str, Any]) -> dict[str, dict[str, float]]:
    """
    Compute statistical metrics from experiment results.

    Metrics computed:
    - FID score for each group
    - Fingerprint accuracy (FP Acc) for each group
    - Fingerprint retention rate (FP Retention) relative to Baseline-1
    - FID change vs Baseline-0 (vs B0)
    - FID change vs Baseline-1 (vs B1)

    Args:
        results: Dictionary containing experiment results

    Returns:
        Dictionary with computed statistics for each group
    """
    stats = {}

    # Extract baselines
    baseline_0 = results.get("Baseline-0", {})
    baseline_1 = results.get("Baseline-1", {})

    b0_fid = baseline_0.get("fid", 0.0)
    b1_fid = baseline_1.get("fid", 0.0)
    b1_fp_acc = baseline_1.get("fingerprint_accuracy", 100.0)

    # Process all groups
    for group_name, group_data in results.items():
        fid = group_data.get("fid", 0.0)
        fp_acc = group_data.get("fingerprint_accuracy", 0.0)

        # Fingerprint retention rate (relative to Baseline-1)
        fp_retention = (fp_acc / b1_fp_acc * 100) if b1_fp_acc > 0 else 0.0

        # FID changes vs baselines
        vs_b0 = fid - b0_fid
        vs_b1 = fid - b1_fid

        stats[group_name] = {
            "fid": fid,
            "fp_acc": fp_acc,
            "fp_retention": fp_retention,
            "vs_b0": vs_b0,
            "vs_b1": vs_b1,
        }

    return stats


def find_pareto_front(stats: dict[str, dict[str, float]]) -> list[str]:
    """
    Find Pareto optimal points.

    Pareto optimality criteria:- Minimize FID
    - Maximize fingerprint retention

    Args:
        stats: Dictionary with computed statistics

    Returns:
        List of group names that are Pareto optimal
    """
    pareto_optimal = []
    group_names = list(stats.keys())

    for i, group_i in enumerate(group_names):
        is_dominated = False
        stats_i = stats[group_i]

        for j, group_j in enumerate(group_names):
            if i == j:
                continue

            stats_j = stats[group_j]

            # Check if group_j dominates group_i
            # Dominates: FID is lower (better) AND retention is higher (better)
            fid_better = stats_j["fid"] < stats_i["fid"]
            retention_better = stats_j["fp_retention"] > stats_i["fp_retention"]
            fid_equal = stats_j["fid"] == stats_i["fid"]
            retention_equal = stats_j["fp_retention"] == stats_i["fp_retention"]

            # group_j dominates group_i if:
            # (fid_better OR fid_equal) AND (retention_better OR retention_equal)
            # AND at least one is strictly better
            if (
                (fid_better or fid_equal)
                and (retention_better or retention_equal)
                and (fid_better or retention_better)
            ):
                is_dominated = True
                break

        if not is_dominated:
            pareto_optimal.append(group_i)

    return pareto_optimal


def generate_report(
    stats: dict[str, dict[str, float]],
    pareto_optimal: list[str],
    output_path: str,
) -> None:
    """
    Generate formatted text report.

    Report includes:
    - Summary statistics table
    - Pareto optimal points
    - Analysis insights

    Args:
        stats: Dictionary with computed statistics
        pareto_optimal: List of Pareto optimal group names
        output_path: Path to save the report
    """
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("DEFINGERPRINT EXPERIMENT ANALYSIS REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Results table
    lines.append("RESULTS SUMMARY")
    lines.append("-" * 80)
    lines.append(
        f"{'Group':<15} {'FID':<10} {'FP Acc':<10} {'FP Retention':<15} "
        f"{'vs B0':<10} {'vs B1':<10}"
    )
    lines.append("-" * 80)

    # Sort groups: Baseline-0, Baseline-1, then experiments
    def sort_key(name):
        if name == "Baseline-0":
            return (0, "")
        elif name == "Baseline-1":
            return (1, "")
        else:
            return (2, name)

    sorted_groups = sorted(stats.keys(), key=sort_key)

    for group in sorted_groups:
        s = stats[group]
        pareto_marker = " *" if group in pareto_optimal else ""
        lines.append(
            f"{group:<15} {s['fid']:<10.2f} {s['fp_acc']:<10.2f} "
            f"{s['fp_retention']:<15.2f} {s['vs_b0']:<+10.2f} {s['vs_b1']:<+10.2f}"
            f"{pareto_marker}"
        )

    lines.append("-" * 80)
    lines.append("* indicates Pareto optimal points")
    lines.append("")

    # Pareto optimal section
    lines.append("PARETO OPTIMAL POINTS")
    lines.append("-" * 80)
    lines.append(
        "Groups that achieve optimal trade-off between FID and fingerprint retention:"
    )
    lines.append("")

    for group in pareto_optimal:
        s = stats[group]
        lines.append(f"  {group}:")
        lines.append(f"    FID: {s['fid']:.2f}")
        lines.append(f"    Fingerprint Retention: {s['fp_retention']:.2f}%")
        lines.append(f"    Change from Baseline-0: {s['vs_b0']:+.2f}")
        lines.append(f"    Change from Baseline-1: {s['vs_b1']:+.2f}")
        lines.append("")

    # Analysis insights
    lines.append("ANALYSIS INSIGHTS")
    lines.append("-" * 80)

    # Find best trade-off points
    b0_fid = stats["Baseline-0"]["fid"]
    b1_fid = stats["Baseline-1"]["fid"]
    fid_range = b1_fid - b0_fid

    lines.append(f"Baseline Comparison:")
    lines.append(f"  Baseline-0 (No fingerprint): FID = {b0_fid:.2f}")
    lines.append(f"  Baseline-1 (With fingerprint): FID = {b1_fid:.2f}")
    lines.append(f"  FID increase from fingerprinting: {fid_range:.2f}")
    lines.append("")

    # Fine-tuning results summary
    exp_groups = [g for g in sorted_groups if g.startswith("Exp-")]
    if exp_groups:
        lines.append("Fine-tuning Results:")
        for exp in exp_groups:
            s = stats[exp]
            lines.append(
                f"  {exp}: FID {s['fid']:.2f}, "
                f"Retention {s['fp_retention']:.2f}%, "
                f"vs B0 {s['vs_b0']:+.2f}, vs B1 {s['vs_b1']:+.2f}"
            )
        lines.append("")

    # Recommendations
    lines.append("RECOMMENDATIONS")
    lines.append("-" * 80)

    if pareto_optimal:
        # Find best recommendation based on use case
        recommendations = []

        # Best for quality (lowest FID among Pareto)
        best_quality = min(
            [g for g in pareto_optimal if g not in ["Baseline-0", "Baseline-1"]],
            key=lambda g: stats[g]["fid"],
            default=None,
        )
        if best_quality:
            recommendations.append(
                f"Best for model quality: {best_quality} "
                f"(FID: {stats[best_quality]['fid']:.2f}, "
                f"Retention: {stats[best_quality]['fp_retention']:.2f}%)"
            )

        # Best for fingerprint retention (Highest retention among Pareto)
        best_retention = max(
            [g for g in pareto_optimal if g not in ["Baseline-0", "Baseline-1"]],
            key=lambda g: stats[g]["fp_retention"],
            default=None,
        )
        if best_retention:
            recommendations.append(
                f"Best for fingerprint retention: {best_retention} "
                f"(FID: {stats[best_retention]['fid']:.2f}, "
                f"Retention: {stats[best_retention]['fp_retention']:.2f}%)"
            )

        # Balanced recommendation
        if best_quality and best_retention and best_quality != best_retention:
            balanced = min(
                [g for g in pareto_optimal if g not in ["Baseline-0", "Baseline-1"]],
                key=lambda g: (
                    stats[g]["fid"] / b0_fid + (100 - stats[g]["fp_retention"]) / 100
                ),
            )
            recommendations.append(
                f"Balanced recommendation: {balanced} "
                f"(FID: {stats[balanced]['fid']:.2f}, "
                f"Retention: {stats[balanced]['fp_retention']:.2f}%)"
            )

        for rec in recommendations:
            lines.append(f"  {rec}")
    else:
        lines.append("  No Pareto optimal points found (unexpected)")

    lines.append("")
    lines.append("=" * 80)

    # Write report
    report_text = "\n".join(lines)

    # Create output directory if needed
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_path, "w") as f:
        f.write(report_text)

    print(f"Report saved to: {output_path}")
    print("\n" + report_text)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze defingerprint experiment results"
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
        help="Path to save analysis report (default: same directory as results.json)",
    )

    args = parser.parse_args()

    # Resolve paths
    results_path = Path(args.results)

    if args.output is None:
        output_path = results_path.parent / "analysis_report.txt"
    else:
        output_path = Path(args.output)

    # Load results
    print(f"Loading results from: {results_path}")
    results = load_results(str(results_path))

    # Compute statistics
    print("Computing statistics...")
    stats = compute_statistics(results)

    # Find Pareto front
    print("Finding Pareto optimal points...")
    pareto_optimal = find_pareto_front(stats)

    # Generate report
    print("Generating report...")
    generate_report(stats, pareto_optimal, str(output_path))


if __name__ == "__main__":
    main()
