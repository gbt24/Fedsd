# -*- coding: UTF-8 -*-
"""
De-fingerprint Experiment Script

This script orchestrates experiments to evaluate fingerprint removal methods
for federated learning diffusion models. It measures:
1. FID scores for normal and trigger classes before/after fine-tuning
2. Fingerprint extraction accuracy after fine-tuning

Usage:
    python -m experiments.defingerprint.run_defingerprint --config config/experiment.yaml
"""

import argparse
import copy
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader
from tqdm import tqdm

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from fed.diffusion_client import ClassConditionalClient
from save_trace_data import load_trace_data
from utils.datasets import get_full_dataset
from utils.diffusion_utils import get_diffusion_model, get_scheduler
from utils.fid_eval import evaluate_fid
from utils.simple_diffusion import SimpleDiffusion
from utils.utils import printf
from watermark.fingerprint_diffusion import (
    get_diffusion_embed_layers,
    extracting_fingerprints,
)
from utils.simple_diffusion import SimpleDiffusionScheduler
from watermark.watermark_diffusion import ClassConditionalWatermarkGenerator


def load_config(config_path):
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Dictionary containing configuration
    """
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def setup_train_args_from_config(config):
    """
    Create training args from nested config dictionary.

    Args:
        config: Configuration dictionary (nested YAML structure)

    Returns:
        Args object with training parameters
    """

    class TrainArgs:
        pass

    args = TrainArgs()

    # Extract model parameters
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

    # Extract finetuning parameters
    if "finetuning" in config:
        args.local_bs = config["finetuning"]["local_bs"]
        args.local_ep = config["finetuning"]["local_ep"]
        args.local_lr = config["finetuning"]["learning_rate"]
        args.local_optim = config["finetuning"]["optimizer"]

    # Extract fingerprint parameters
    if "fingerprint" in config:
        args.embed_layer_names = config["fingerprint"]["embed_layer_names"]
        args.lfp_length = config["fingerprint"]["lfp_length"]
        args.num_clients = config["fingerprint"]["num_clients"]
        args.trigger_class = config["model"]["num_classes"]  # Same as num_classes

    # Extract evaluation parameters
    if "evaluation" in config:
        args.fingerprint_threshold = config["evaluation"]["fingerprint_threshold"]
        args.seed = config["evaluation"]["seed"]

    # Extract compute parameters
    if "compute" in config:
        gpu_id = config["compute"]["gpu"]
        args.gpu = gpu_id
        args.device = torch.device(
            f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"
        )

    # Set default values for required but missing parameters
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

    return args


def load_model_from_checkpoint(checkpoint_path, args, device):
    """
    Load a diffusion model from checkpoint.

    Args:
        checkpoint_path: Path to model checkpoint
        args: Training arguments
        device: Device to load model on

    Returns:
        Loaded model
    """
    model = get_diffusion_model(args)
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model = model.to(device)
    model.eval()
    return model


def generate_fingerprint_data(args, model, device, num_samples=100):
    """
    Generate fingerprint data for evaluation.
    Creates both normal class samples and trigger class samples.

    Args:
        args: Training arguments
        model: Diffusion model
        device: Device to generate on
        num_samples: Number of samples per class

    Returns:
        Tuple of (normal_samples, trigger_samples)
    """
    model.eval()
    model.to(device)

    diffusion = SimpleDiffusion(
        num_timesteps=args.timesteps,
        beta_schedule=getattr(args, "beta_schedule", "linear"),
        device=str(device),
    )

    normal_samples = []
    trigger_samples = []

    trigger_class = getattr(args, "trigger_class", args.num_classes)
    num_classes = args.num_classes

    batch_size = min(64, num_samples)

    print(f"Generating {num_samples} normal class samples...")
    num_batches = (num_samples + batch_size - 1) // batch_size
    with torch.no_grad():
        for _ in tqdm(range(num_batches), desc="Normal samples"):
            remaining = num_samples - len(normal_samples)
            current_batch_size = min(batch_size, remaining)
            if current_batch_size <= 0:
                break

            labels = torch.randint(0, num_classes, (current_batch_size,), device=device)
            samples = diffusion.sample(
                model,
                batch_size=current_batch_size,
                class_labels=labels,
                num_inference_steps=args.timesteps,
                device=str(device),
            )
            normal_samples.append(samples.cpu())

    print(f"Generating {num_samples} trigger class samples...")
    with torch.no_grad():
        for _ in tqdm(range(num_batches), desc="Trigger samples"):
            remaining = num_samples - len(trigger_samples)
            current_batch_size = min(batch_size, remaining)
            if current_batch_size <= 0:
                break

            labels = torch.full(
                (current_batch_size,), trigger_class, dtype=torch.long, device=device
            )
            samples = diffusion.sample(
                model,
                batch_size=current_batch_size,
                class_labels=labels,
                num_inference_steps=args.timesteps,
                device=str(device),
            )
            trigger_samples.append(samples.cpu())

    model.cpu()

    normal_samples = torch.cat(normal_samples, dim=0)
    trigger_samples = torch.cat(trigger_samples, dim=0)

    return normal_samples, trigger_samples


def save_fingerprint_data(
    save_dir, normal_samples, trigger_samples, filename_prefix="fingerprint"
):
    """
    Save fingerprint data to disk.

    Args:
        save_dir: Directory to save data
        normal_samples: Normal class samples
        trigger_samples: Trigger class samples
        filename_prefix: Prefix for filename
    """
    os.makedirs(save_dir, exist_ok=True)

    normal_path = os.path.join(save_dir, f"{filename_prefix}_normal.pt")
    trigger_path = os.path.join(save_dir, f"{filename_prefix}_trigger.pt")

    torch.save(normal_samples, normal_path)
    torch.save(trigger_samples, trigger_path)

    print(f"Saved fingerprint data:")
    print(f"  - Normal samples: {normal_path} ({normal_samples.shape})")
    print(f"  - Trigger samples: {trigger_path} ({trigger_samples.shape})")


def finetune_model(
    model,
    train_dataset,
    args,
    device,
    num_epochs=10,
    use_watermark=False,
    watermark_dataset=None,
    finetune_lr=None,
):
    """
    Fine-tune a diffusion model.

    Args:
        model: Model to fine-tune
        train_dataset: Training dataset
        args: Training arguments
        device: Device to train on
        num_epochs: Number of fine-tuning epochs
        use_watermark: Whether to use watermark data
        watermark_dataset: Watermark dataset (if use_watermark is True)
        finetune_lr: Learning rate for fine-tuning (default: args.local_lr)

    Returns:
        Fine-tuned model
    """
    model.train()
    model.to(device)

    lr = finetune_lr if finetune_lr is not None else args.local_lr
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    scheduler = SimpleDiffusionScheduler(
        num_timesteps=args.timesteps,
        beta_schedule=getattr(args, "beta_schedule", "linear"),
    )

    train_loader = DataLoader(
        train_dataset, batch_size=args.local_bs, shuffle=True, num_workers=4
    )

    if use_watermark and watermark_dataset is not None:
        watermark_loader = DataLoader(
            watermark_dataset, batch_size=args.local_bs, shuffle=True, num_workers=4
        )

    train_losses = []

    for epoch in range(num_epochs):
        epoch_losses = []

        if use_watermark and watermark_dataset is not None:
            wm_iter = iter(watermark_loader)

        for batch_idx, (images, labels) in enumerate(train_loader):
            images = images.to(device)
            labels = labels.to(device)
            batch_size = images.shape[0]

            t = torch.randint(0, args.timesteps, (batch_size,), device=device).long()

            noise = torch.randn_like(images)
            noisy_images = scheduler.add_noise(images, noise, t)

            noise_pred = model(noisy_images, t, class_labels=labels)

            loss = torch.nn.functional.mse_loss(noise_pred, noise)

            if use_watermark and watermark_dataset is not None:
                try:
                    wm_images, _ = next(wm_iter)
                except StopIteration:
                    wm_iter = iter(watermark_loader)
                    wm_images, _ = next(wm_iter)

                wm_images = wm_images.to(device)
                wm_batch_size = wm_images.shape[0]
                wm_t = torch.randint(
                    0, args.timesteps, (wm_batch_size,), device=device
                ).long()

                wm_trigger_class = getattr(args, "trigger_class", args.num_classes)
                wm_labels = torch.full(
                    (wm_batch_size,), wm_trigger_class, dtype=torch.long, device=device
                )

                wm_noise = torch.randn_like(wm_images)
                wm_noisy_images = scheduler.add_noise(wm_images, wm_noise, wm_t)

                wm_noise_pred = model(wm_noisy_images, wm_t, class_labels=wm_labels)

                wm_loss = torch.nn.functional.mse_loss(wm_noise_pred, wm_noise)
                loss = loss + args.watermark_weight * wm_loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_losses.append(loss.item())

        avg_loss = sum(epoch_losses) / len(epoch_losses)
        train_losses.append(avg_loss)
        print(f"Finetune epoch {epoch + 1}/{num_epochs}, Loss: {avg_loss:.4f}")

    model.cpu()
    return model, train_losses


def evaluate_fid_score(
    model,
    test_dataset,
    watermark_images,
    args,
    device,
    num_samples_per_class=1000,
):
    """
    Evaluate FID score for normal and trigger classes.

    Args:
        model: Diffusion model to evaluate
        test_dataset: Real dataset for FID comparison
        watermark_images: Watermark images for trigger class FID
        args: Training arguments
        device: Device to evaluate on
        num_samples_per_class: Number of samples per class

    Returns:
        Dictionary containing FID results
    """
    scheduler = SimpleDiffusion(
        num_timesteps=args.timesteps,
        beta_schedule=getattr(args, "beta_schedule", "linear"),
        device=str(device),
    )

    results = evaluate_fid(
        model=model,
        diffusion=scheduler,
        real_dataset=test_dataset,
        watermark_images=watermark_images,
        args=args,
        device=device,
        num_samples_per_class=num_samples_per_class,
    )

    return results


def evaluate_fingerprint_accuracy(
    model,
    local_fingerprints,
    extracting_matrices,
    embed_layer_names,
    epsilon=0.5,
    use_hamming=False,
):
    """
    Evaluate fingerprint extraction accuracy.

    Args:
        model: Model to evaluate
        local_fingerprints: List of fingerprint vectors for all clients
        extracting_matrices: List of extracting matrices for all clients
        embed_layer_names: Names of layers where fingerprints are embedded
        epsilon: Epsilon for hinge-like loss
        use_hamming: Use Hamming distance instead of FSS score

    Returns:
        Dictionary containing fingerprint evaluation results
    """
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

    results = {
        "accuracy": accuracy,
        "avg_score": avg_score,
        "correct_matches": correct_matches,
        "total_clients": len(local_fingerprints),
        "scores": all_scores,
        "matches": all_matches,
    }

    return results


def run_experiment(config_path, output_dir=None, gpu=None):
    """
    Run the complete de-fingerprint experiment.

    Args:
        config_path: Path to configuration YAML file
        output_dir: Output directory for results (default: same as config directory)
        gpu: GPU ID to use (overrides config)

    Returns:
        Dictionary containing all experiment results
    """
    config = load_config(config_path)

    if output_dir is None:
        config_dir = os.path.dirname(config_path)
        output_dir = os.path.join(config_dir, "results")

    if gpu is not None:
        config["gpu"] = gpu

    os.makedirs(output_dir, exist_ok=True)

    log_path = os.path.join(output_dir, "experiment.log")

    printf("=" * 60, log_path)
    printf("De-fingerprint Experiment", log_path)
    printf("=" * 60, log_path)
    printf(f"Config: {config_path}", log_path)
    printf(f"Output: {output_dir}", log_path)

    args = setup_train_args_from_config(config)

    if args.seed is not None:
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        torch.cuda.manual_seed(args.seed)

    device = torch.device(
        f"cuda:{args.gpu}" if torch.cuda.is_available() and args.gpu >= 0 else "cpu"
    )
    args.device = device

    printf(f"Device: {device}", log_path)
    printf(f"Model: {args.model}", log_path)
    printf(f"Dataset: {args.dataset}", log_path)
    printf(f"Num classes: {args.num_classes}", log_path)
    printf(f"Trigger class: {args.trigger_class}", log_path)

    printf("\nLoading datasets...", log_path)
    train_dataset, test_dataset = get_full_dataset(
        args.dataset, img_size=(args.image_size, args.image_size)
    )
    printf(f"Train dataset size: {len(train_dataset)}", log_path)
    printf(f"Test dataset size: {len(test_dataset)}", log_path)

    # Extract checkpoint paths from nested config
    stage1_path = config["baselines"]["stage1_checkpoint"]
    stage2_path = config["baselines"]["stage2_checkpoint"]

    if not os.path.exists(stage1_path):
        raise FileNotFoundError(f"Stage 1 checkpoint not found: {stage1_path}")
    if not os.path.exists(stage2_path):
        raise FileNotFoundError(f"Stage 2 checkpoint not found: {stage2_path}")

    printf("\nLoading models...", log_path)
    stage1_model = load_model_from_checkpoint(stage1_path, args, device)
    stage2_model = load_model_from_checkpoint(stage2_path, args, device)
    printf("Models loaded successfully", log_path)

    # Load trace data from Stage 2
    trace_dir = config["baselines"].get("trace_dir", None)
    if trace_dir is None:
        trace_dir = os.path.join(os.path.dirname(stage2_path), "trace_data")

    if os.path.exists(trace_dir):
        printf("\nLoading trace data from: {}".format(trace_dir), log_path)
        local_fingerprints, extracting_matrices, trace_metadata = load_trace_data(
            trace_dir
        )
        printf(
            "Loaded {} client fingerprints from trace_data".format(
                len(local_fingerprints)
            ),
            log_path,
        )
        printf("Fingerprint length: {}".format(len(local_fingerprints[0])), log_path)
        embed_layer_names = trace_metadata.get(
            "embed_layer_names", config["fingerprint"]["embed_layer_names"]
        )
    else:
        raise FileNotFoundError(
            "trace_data not found at {}. "
            "Run: python save_trace_data.py --save_dir {} --num_clients 25 --lfp_length 128 "
            "--embed_layer_names mid_block.attention.proj".format(
                trace_dir, os.path.dirname(stage2_path)
            )
        )

    results = {
        "config": config,
        "num_finetune_epochs_list": config["finetuning"]["epochs"],
    }

    printf("\nGenerating watermark data...", log_path)
    watermark_generator = ClassConditionalWatermarkGenerator(
        args=args,
        num_classes=args.num_classes,
        trigger_class=args.trigger_class,
    )
    watermark_dataset = watermark_generator.generate_trigger_set(args)
    watermark_images = watermark_dataset.images
    printf(f"Generated {len(watermark_images)} watermark images", log_path)

    results["stage1"] = {}
    results["stage2"] = {}

    printf("\n" + "=" * 60, log_path)
    printf("STAGE 1: Baseline (No Watermark)", log_path)
    printf("=" * 60, log_path)

    printf("\nEvaluating Stage 1 model...", log_path)
    stage1_fid = evaluate_fid_score(
        stage1_model, test_dataset, None, args, device, num_samples_per_class=500
    )
    printf(f"Stage 1 FID Total: {stage1_fid['fid_total']:.2f}", log_path)
    results["stage1"]["fid"] = stage1_fid

    printf("\nEvaluating Stage 1 fingerprint accuracy...", log_path)
    stage1_fp_results = evaluate_fingerprint_accuracy(
        stage1_model,
        local_fingerprints,
        extracting_matrices,
        embed_layer_names,
        epsilon=0.5,
        use_hamming=False,
    )
    printf(
        f"Stage 1 Fingerprint Accuracy: {stage1_fp_results['accuracy']:.4f}", log_path
    )
    printf(f"Stage 1 Avg FSS Score: {stage1_fp_results['avg_score']:.4f}", log_path)
    results["stage1"]["fingerprint"] = stage1_fp_results

    printf("\n" + "=" * 60, log_path)
    printf("STAGE 2: With Watermark", log_path)
    printf("=" * 60, log_path)

    printf("\nEvaluating Stage 2 model (before fine-tuning)...", log_path)
    stage2_fid_before = evaluate_fid_score(
        stage2_model,
        test_dataset,
        watermark_images,
        args,
        device,
        num_samples_per_class=500,
    )
    printf(f"Stage 2 FID Total: {stage2_fid_before['fid_total']:.2f}", log_path)
    if "fid_trigger" in stage2_fid_before:
        printf(f"Stage 2 FID Trigger: {stage2_fid_before['fid_trigger']:.2f}", log_path)
    results["stage2"]["before_finetune"] = {"fid": stage2_fid_before}

    printf(
        "\nEvaluating Stage 2 fingerprint accuracy (before fine-tuning)...", log_path
    )
    stage2_fp_before = evaluate_fingerprint_accuracy(
        stage2_model,
        local_fingerprints,
        extracting_matrices,
        embed_layer_names,
        epsilon=0.5,
        use_hamming=False,
    )
    printf(
        f"Stage 2 Fingerprint Accuracy: {stage2_fp_before['accuracy']:.4f}", log_path
    )
    printf(f"Stage 2 Avg FSS Score: {stage2_fp_before['avg_score']:.4f}", log_path)
    results["stage2"]["before_finetune"]["fingerprint"] = stage2_fp_before

    num_finetune_epochs_list = config["finetuning"]["epochs"]
    finetune_lr = config["finetuning"]["learning_rate"]
    finetune_use_watermark = False  # Defingerprinting doesn't use watermark data

    results["finetune_results"] = []

    for num_epochs in num_finetune_epochs_list:
        if num_epochs == 0:
            continue

        printf("\n" + "-" * 60, log_path)
        printf(f"Fine-tuning for {num_epochs} epochs...", log_path)
        if finetune_use_watermark:
            printf("Using watermark data in fine-tuning", log_path)
        else:
            printf("NOT using watermark data in fine-tuning", log_path)
        printf("-" * 60, log_path)

        finetuned_model = copy.deepcopy(stage2_model)

        finetuned_model, train_losses = finetune_model(
            finetuned_model,
            train_dataset,
            args,
            device,
            num_epochs=num_epochs,
            use_watermark=finetune_use_watermark,
            watermark_dataset=watermark_dataset if finetune_use_watermark else None,
            finetune_lr=finetune_lr,
        )

        printf("\nEvaluating fine-tuned model...", log_path)
        ft_fid = evaluate_fid_score(
            finetuned_model,
            test_dataset,
            watermark_images,
            args,
            device,
            num_samples_per_class=500,
        )
        printf(f"FID Total: {ft_fid['fid_total']:.2f}", log_path)
        if "fid_trigger" in ft_fid:
            printf(f"FID Trigger: {ft_fid['fid_trigger']:.2f}", log_path)

        ft_fp_results = evaluate_fingerprint_accuracy(
            finetuned_model,
            local_fingerprints,
            extracting_matrices,
            embed_layer_names,
            epsilon=0.5,
            use_hamming=False,
        )
        printf(f"Fingerprint Accuracy: {ft_fp_results['accuracy']:.4f}", log_path)
        printf(f"Avg FSS Score: {ft_fp_results['avg_score']:.4f}", log_path)

        checkpoint_name = f"finetuned_{num_epochs}epochs.pt"
        checkpoint_path = os.path.join(output_dir, checkpoint_name)
        torch.save(finetuned_model.state_dict(), checkpoint_path)
        printf(f"Saved checkpoint: {checkpoint_path}", log_path)

        result_entry = {
            "num_epochs": num_epochs,
            "use_watermark": finetune_use_watermark,
            "finetune_lr": finetune_lr,
            "train_losses": train_losses,
            "fid": ft_fid,
            "fingerprint": ft_fp_results,
        }
        results["finetune_results"].append(result_entry)

    results_path = os.path.join(output_dir, "results.json")
    with open(results_path, "w") as f:
        results_copy = {}
        for key, value in results.items():
            if key == "finetune_results":
                results_copy[key] = []
                for entry in value:
                    entry_copy = {}
                    for k, v in entry.items():
                        if isinstance(v, dict):
                            entry_copy[k] = {
                                k2: float(v2)
                                if isinstance(v2, (int, float))
                                else str(v2)
                                for k2, v2 in v.items()
                                if k2 not in ["scores", "matches"]
                            }
                        else:
                            entry_copy[k] = (
                                float(v) if isinstance(v, (int, float)) else v
                            )
                    results_copy[key].append(entry_copy)
            elif isinstance(value, dict):
                results_copy[key] = {}
                for k, v in value.items():
                    if isinstance(v, dict):
                        results_copy[key][k] = {}
                        for k2, v2 in v.items():
                            if isinstance(v2, dict):
                                results_copy[key][k][k2] = {
                                    k3: float(v3)
                                    if isinstance(v3, (int, float))
                                    else str(v3)
                                    for k3, v3 in v2.items()
                                    if k3 not in ["scores", "matches"]
                                }
                            else:
                                results_copy[key][k][k2] = (
                                    float(v2)
                                    if isinstance(v2, (int, float))
                                    else str(v2)
                                )
                    else:
                        results_copy[key][k] = (
                            float(v) if isinstance(v, (int, float)) else str(v)
                        )
            else:
                results_copy[key] = value

        import json

        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.floating):
                    return float(obj)
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super().default(obj)

        with open(results_path, "w") as f:
            json.dump(results_copy, f, indent=2, cls=NumpyEncoder)

    printf(f"\nResults saved to {results_path}", log_path)
    printf("=" * 60, log_path)
    printf("Experiment completed!", log_path)
    printf("=" * 60, log_path)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run de-fingerprint experiment for diffusion models"
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to configuration YAML file",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Output directory for results (default: same as config directory)",
    )
    parser.add_argument(
        "--gpu",
        type=int,
        default=None,
        help="GPU ID to use (overrides config)",
    )

    args = parser.parse_args()

    run_experiment(
        config_path=args.config,
        output_dir=args.output_dir,
        gpu=args.gpu,
    )


if __name__ == "__main__":
    main()
