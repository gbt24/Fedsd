# -*- coding: UTF-8 -*-
"""
Re-evaluate fingerprint accuracy using saved trace_data and checkpoints.

This script skips training and FID evaluation, only re-runs fingerprint
extraction accuracy checks using the correct trace_data.

Usage:
    python -m experiments.defingerprint.reval_fingerprint \
        --config experiments/defingerprint/config/experiment_config.yaml \
        --checkpoint_dir experiments/defingerprint/config/results \
        [--output experiments/defingerprint/config/results/fingerprint_reval.json]
"""

import argparse
import json
import os
import sys

import torch

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from save_trace_data import load_trace_data
from utils.diffusion_utils import get_diffusion_model
from watermark.fingerprint_diffusion import (
    extracting_fingerprints,
    get_diffusion_embed_layers,
)


def load_config(config_path):
    with open(config_path, "r") as f:
        import yaml

        return yaml.safe_load(f)


def setup_train_args_from_config(config):
    class TrainArgs:
        pass

    args = TrainArgs()

    if "model" in config:
        args.model = config["model"]["type"]
        args.dataset = config["model"]["dataset"]
        args.num_classes = config["model"]["num_classes"]
        args.num_channels = config["model"]["num_channels"]
        args.image_size = config["model"]["image_size"]
        args.timesteps = config["model"]["timesteps"]
        args.beta_schedule = config["model"]["beta_schedule"]
        args.time_embed_dim = config["model"]["time_embed_dim"]
        args.class_embed_dim = config["model"]["class_embed_dim"]
        args.block_out_channels = config["model"]["block_out_channels"]
        args.layers_per_block = config["model"]["layers_per_block"]
        args.dropout = config["model"]["dropout"]

    if "evaluation" in config:
        args.seed = config["evaluation"]["seed"]

    if "compute" in config:
        gpu_id = config["compute"]["gpu"]
        args.gpu = gpu_id
        args.device = torch.device(
            f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"
        )

    if not hasattr(args, "watermark"):
        args.watermark = True
    if not hasattr(args, "fingerprint"):
        args.fingerprint = True
    if not hasattr(args, "num_trigger_set"):
        args.num_trigger_set = 100
    if not hasattr(args, "diffusion_scheduler"):
        args.diffusion_scheduler = "ddpm"
    if not hasattr(args, "sample_interval"):
        args.sample_interval = 10
    if not hasattr(args, "num_samples"):
        args.num_samples = 1000
    if not hasattr(args, "gpu"):
        args.gpu = 0
        args.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    args.pre_train_simple = True
    args.sd_model = "google/ddpm-cifar10-32"
    args.trigger_class = config["model"]["num_classes"]
    args.lr_decay = 0.999
    args.gem = True

    return args


def load_model_from_checkpoint(checkpoint_path, args, device):
    model = get_diffusion_model(args)
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model = model.to(device)
    model.eval()
    return model


def evaluate_fingerprint_accuracy(
    model,
    local_fingerprints,
    extracting_matrices,
    embed_layer_names,
    epsilon=0.5,
    use_hamming=False,
):
    embed_layers = get_diffusion_embed_layers(model, embed_layer_names)

    all_scores = []
    all_matches = []

    for idx in range(len(local_fingerprints)):
        score, match_idx = extracting_fingerprints(
            embed_layers,
            local_fingerprints,
            extracting_matrices,
            epsilon=epsilon,
            hd=use_hamming,
        )
        all_scores.append(score)
        all_matches.append(match_idx == idx)

    correct_matches = sum(all_matches)
    accuracy = (
        correct_matches / len(local_fingerprints)
        if len(local_fingerprints) > 0
        else 0.0
    )
    avg_score = sum(all_scores) / len(all_scores) if len(all_scores) > 0 else 0.0

    return {
        "accuracy": accuracy,
        "avg_score": avg_score,
        "correct_matches": correct_matches,
        "total_clients": len(local_fingerprints),
        "scores": [float(s) for s in all_scores],
        "matches": [bool(m) for m in all_matches],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Re-evaluate fingerprint accuracy with correct trace_data"
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to configuration YAML file",
    )
    parser.add_argument(
        "--checkpoint_dir",
        type=str,
        default="experiments/defingerprint/config/results",
        help="Directory containing finetuned checkpoints",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON path (default: checkpoint_dir/fingerprint_reval.json)",
    )
    parser.add_argument(
        "--gpu",
        type=int,
        default=None,
        help="GPU ID to use (overrides config)",
    )

    args = parser.parse_args()

    config = load_config(args.config)

    if args.gpu is not None:
        config["compute"]["gpu"] = args.gpu

    if args.output is None:
        output_path = os.path.join(args.checkpoint_dir, "fingerprint_reval.json")
    else:
        output_path = args.output

    train_args = setup_train_args_from_config(config)
    device = train_args.device

    print(f"Device: {device}")
    print(f"Model: {train_args.model}")

    stage1_path = config["baselines"]["stage1_checkpoint"]
    stage2_path = config["baselines"]["stage2_checkpoint"]
    trace_dir = config["baselines"].get(
        "trace_dir",
        os.path.join(os.path.dirname(stage2_path), "trace_data"),
    )

    print(f"\nLoading trace data from: {trace_dir}")
    local_fingerprints, extracting_matrices, trace_metadata = load_trace_data(trace_dir)
    print(f"Loaded {len(local_fingerprints)} client fingerprints")
    print(f"Fingerprint length: {len(local_fingerprints[0])}")
    embed_layer_names = trace_metadata.get(
        "embed_layer_names", config["fingerprint"]["embed_layer_names"]
    )
    print(f"Embed layer names: {embed_layer_names}")

    results = {
        "config_fingerprint": {
            "num_clients": len(local_fingerprints),
            "lfp_length": len(local_fingerprints[0]),
            "embed_layer_names": embed_layer_names,
            "trace_dir": trace_dir,
        },
    }

    print("\n" + "=" * 60)
    print("STAGE 1: Baseline (No Watermark)")
    print("=" * 60)

    print("\nLoading Stage 1 model...")
    stage1_model = load_model_from_checkpoint(stage1_path, train_args, device)

    print("Evaluating Stage 1 fingerprint accuracy...")
    stage1_fp = evaluate_fingerprint_accuracy(
        stage1_model,
        local_fingerprints,
        extracting_matrices,
        embed_layer_names,
        epsilon=config["fingerprint"]["epsilon"],
    )
    print(
        f"Stage 1 Accuracy: {stage1_fp['accuracy']:.4f} ({stage1_fp['correct_matches']}/{stage1_fp['total_clients']})"
    )
    print(f"Stage 1 Avg FSS: {stage1_fp['avg_score']:.4f}")
    results["stage1"] = {"fingerprint": stage1_fp}

    del stage1_model
    torch.cuda.empty_cache()

    print("\n" + "=" * 60)
    print("STAGE 2: With Watermark (before fine-tuning)")
    print("=" * 60)

    print("\nLoading Stage 2 model...")
    stage2_model = load_model_from_checkpoint(stage2_path, train_args, device)

    print("Evaluating Stage 2 fingerprint accuracy...")
    stage2_fp = evaluate_fingerprint_accuracy(
        stage2_model,
        local_fingerprints,
        extracting_matrices,
        embed_layer_names,
        epsilon=config["fingerprint"]["epsilon"],
    )
    print(
        f"Stage 2 Accuracy: {stage2_fp['accuracy']:.4f} ({stage2_fp['correct_matches']}/{stage2_fp['total_clients']})"
    )
    print(f"Stage 2 Avg FSS: {stage2_fp['avg_score']:.4f}")
    results["stage2_before_finetune"] = {"fingerprint": stage2_fp}

    print("\nPer-client FSS scores:")
    for i, (score, match) in enumerate(zip(stage2_fp["scores"], stage2_fp["matches"])):
        marker = "OK" if match else "MISMATCH"
        print(f"  Client {i:2d}: FSS={score:.4f} [{marker}]")

    del stage2_model
    torch.cuda.empty_cache()

    print("\n" + "=" * 60)
    print("FINE-TUNED MODELS")
    print("=" * 60)

    finetune_results = []
    for num_epochs in config["finetuning"]["epochs"]:
        checkpoint_name = f"finetuned_{num_epochs}epochs.pt"
        checkpoint_path = os.path.join(args.checkpoint_dir, checkpoint_name)

        if not os.path.exists(checkpoint_path):
            print(f"\nCheckpoint not found: {checkpoint_path} - Skipping")
            continue

        print(f"\nLoading {checkpoint_name}...")
        ft_model = load_model_from_checkpoint(checkpoint_path, train_args, device)

        print(f"Evaluating fingerprint accuracy for {num_epochs} epochs...")
        ft_fp = evaluate_fingerprint_accuracy(
            ft_model,
            local_fingerprints,
            extracting_matrices,
            embed_layer_names,
            epsilon=config["fingerprint"]["epsilon"],
        )
        print(
            f"Finetune {num_epochs}ep Accuracy: {ft_fp['accuracy']:.4f} ({ft_fp['correct_matches']}/{ft_fp['total_clients']})"
        )
        print(f"Finetune {num_epochs}ep Avg FSS: {ft_fp['avg_score']:.4f}")

        finetune_results.append(
            {
                "num_epochs": num_epochs,
                "fingerprint": ft_fp,
            }
        )

        del ft_model
        torch.cuda.empty_cache()

    results["finetune_results"] = finetune_results

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to: {output_path}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Model':<30} {'Accuracy':<12} {'Avg FSS':<12} {'Correct/Total'}")
    print("-" * 70)
    print(
        f"{'Stage1 (No Watermark)':<30} {stage1_fp['accuracy']:<12.4f} {stage1_fp['avg_score']:<12.4f} {stage1_fp['correct_matches']}/{stage1_fp['total_clients']}"
    )
    print(
        f"{'Stage2 (With Watermark)':<30} {stage2_fp['accuracy']:<12.4f} {stage2_fp['avg_score']:<12.4f} {stage2_fp['correct_matches']}/{stage2_fp['total_clients']}"
    )
    for ft in finetune_results:
        fp = ft["fingerprint"]
        label = f"Finetune {ft['num_epochs']}ep"
        print(
            f"{label:<30} {fp['accuracy']:<12.4f} {fp['avg_score']:<12.4f} {fp['correct_matches']}/{fp['total_clients']}"
        )

    print("\nDone!")


if __name__ == "__main__":
    main()
