# Defingerprint Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a systematic experiment to measure the impact of fine-tuning-based defingerprinting on model generation quality and fingerprint retention rate.

**Architecture:** Create a modular experiment framework with three main components: (1) a config-driven main script that orchestrates baseline evaluation and finetuning experiments, (2) an analysis module for computing metrics and generating reports, and (3) a visualization module for creating comparative plots using Matplotlib.

**Tech Stack:** Python 3.10, PyTorch, NumPy, Matplotlib, YAML (PyYAML), existing FedTracker codebase (watermark/fingerprint_diffusion.py, utils/fid_eval.py)

---

## File Structure

```
experiments/
├── __init__.py
└── defingerprint/
    ├── __init__.py
    ├── run_defingerprint.py          # Main experiment orchestrator
    ├── analyze_results.py            # Results analysis and reporting
    ├── visualize/
    │   ├── __init__.py
    │   └── plot_results.py           # Matplotlib visualization
    └── config/
        └── experiment_config.yaml    # Experiment parameters
```

**Responsibilities:**
- `run_defingerprint.py`: Load models, run finetuning, evaluate FID and fingerprint accuracy, save checkpoints and results
- `analyze_results.py`: Compute statistical metrics, compare groups, generate text report
- `plot_results.py`: Create 3-panel visualization (FID vs epochs, fingerprint retention, Pareto frontier)
- `experiment_config.yaml`: Centralized configuration for all parameters

---

### Task 1: Create Directory Structure and Init Files

**Files:**
- Create: `experiments/__init__.py`
- Create: `experiments/defingerprint/__init__.py`
- Create: `experiments/defingerprint/visualize/__init__.py`

- [ ] **Step 1: Create directory hierarchy**

Run: `mkdir -p experiments/defingerprint/visualize experiments/defingerprint/config`
Expected: Directories created successfully

- [ ] **Step 2: Create __init__.py files**

```bash
touch experiments/__init__.py
touch experiments/defingerprint/__init__.py
touch experiments/defingerprint/visualize/__init__.py
```

Expected: Three empty `__init__.py` files created

- [ ] **Step 3: Verify structure**

Run: `ls -R experiments/defingerprint/`
Expected output:
```
__init__.py
config:
visualize:
__init__.py
```

---

### Task 2: Create Configuration File

**Files:**
- Create: `experiments/defingerprint/config/experiment_config.yaml`

- [ ] **Step 1: Write configuration file**

```yaml
# Defingerprint Experiment Configuration
# This file defines all parameters for the fine-tuning defingerprinting experiment

model:
  type: SimpleUNet
  dataset: cifar10
  num_classes: 10
  image_size: 32
  num_channels: 3
  timesteps: 1000
  beta_schedule: linear
  block_out_channels: [128, 256, 512, 512]
  layers_per_block: 2
  time_embed_dim: 512
  class_embed_dim: 512
  dropout: 0.1

baselines:
  # Stage 1: Model trained without watermark/fingerprint (optimal quality)
  stage1_checkpoint: ./result/simpleunet_cifar10_stage1/model_final.pth
  # Stage 2: Model with watermark and fingerprint embedded
  stage2_checkpoint: ./result/simpleunet_cifar10_stage2/model_final.pth

finetuning:
  # Fine-tuning parameters (using training-stage lr as confirmed)
  epochs: [1, 3, 5, 10]
  learning_rate: 1.0e-4
  local_ep: 5
  local_bs: 64
  optimizer: adam
  
  # Use normal data distribution (CIFAR-10 train set, no trigger class)
  data_distribution: iid

fingerprint:
  # Fingerprint generation parameters
  lfp_length: 128
  embed_layer_names: "mid_block.attention.proj"
  num_clients: 50
  epsilon: 0.5
  fingerprint_max_iters: 5

evaluation:
  # FID evaluation parameters
  fid_samples: 5000
  
  # Fingerprint recognition parameters
  fingerprint_threshold: 0.85  # FSS score threshold for success
  
  # Random seed for reproducibility
  seed: 42

output:
  # Output directory for all experiment results
  base_dir: ./result/defingerprint_experiments/
  
  # Whether to save intermediate checkpoints
  save_checkpoints: true
  
  # Whether to save intermediate training logs
  save_intermediate: true

compute:
  # GPU device ID
  gpu: 0
  
  # Number of workers for data loading
  num_workers: 4
```

- [ ] **Step 2: Verify YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('experiments/defingerprint/config/experiment_config.yaml'))"`
Expected: No error output (valid YAML)

- [ ] **Step 3: Commit configuration**

```bash
git add experiments/defingerprint/config/experiment_config.yaml
git commit -m "feat: add defingerprint experiment configuration"
```

---

### Task 3: Implement Main Experiment Script (Part 1 - Imports and Setup)

**Files:**
- Create: `experiments/defingerprint/run_defingerprint.py`

- [ ] **Step 1: Write script header and imports**

```python
# -*- coding: UTF-8 -*-
"""
Defingerprint Experiment: Fine-tuning Attack Analysis

This script implements a systematic experiment to measure the impact of
fine-tuning-based fingerprint removal on generation quality and fingerprint retention.

Usage:
    python experiments/defingerprint/run_defingerprint.py \\
        --config experiments/defingerprint/config/experiment_config.yaml

Output:
    - Finetuned model checkpoints
    - FID scores for each experiment group
    - Fingerprint retention rates
    - Results in JSON format
"""

import os
import sys
import argparse
import json
import copy
from pathlib import Path

import numpy as np
import torch
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.models import get_model
from utils.utils import load_args
from utils.datasets import get_full_dataset
from utils.simple_diffusion import SimpleDiffusion
from utils.fid_eval import evaluate_fid
from watermark.fingerprint_diffusion import (
    generate_fingerprints,
    generate_extracting_matrices,
    get_diffusion_embed_layers_length,
    extracting_fingerprints,
)
from save_trace_data import load_trace_data


def load_config(config_path):
    """Load YAML configuration file."""
    import yaml
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Convert to namespace-like object
    class Config:
        pass
    
    cfg = Config()
    for key, value in config.items():
        if isinstance(value, dict):
            subcfg = Config()
            for subkey, subvalue in value.items():
                setattr(subcfg, subkey, subvalue)
            setattr(cfg, key, subcfg)
        else:
            setattr(cfg, key, value)
    
    return cfg


def load_model_from_checkpoint(checkpoint_path, args, device):
    """Load model from checkpoint."""
    model = get_model(args)
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model = model.to(device)
    model.eval()
    print(f"Loaded model from {checkpoint_path}")
    return model


def setup_train_args_from_config(config):
    """Create train args from config for model loading."""
    class TrainArgs:
        pass
    
    args = TrainArgs()
    
    # Model parameters
    args.model = config.model.type
    args.dataset = config.model.dataset
    args.num_classes = config.model.num_classes
    args.image_size = config.model.image_size
    args.num_channels = config.model.num_channels
    args.timesteps = config.model.timesteps
    args.beta_schedule = config.model.beta_schedule
    
    # Architecture parameters
    args.time_embed_dim = config.model.time_embed_dim
    args.class_embed_dim = config.model.class_embed_dim
    
    # Parse block_out_channels from list
    args.block_out_channels = config.model.block_out_channels
    args.layers_per_block = config.model.layers_per_block
    args.dropout = config.model.dropout
    
    # Additional parameters
    args.local_bs = config.finetuning.local_bs
    args.trigger_class = config.model.num_classes  # SimpleUNet uses num_classes as trigger
    
    # Device
    device_str = f"cuda:{config.compute.gpu}" if torch.cuda.is_available() else "cpu"
    args.device = torch.device(device_str)
    
    return args
```

Expected: File created with imports and utility functions

- [ ] **Step 2: Verify imports work**

Run: `python -c "from experiments.defingerprint.run_defingerprint import load_config; print('Import successful')"`
Expected: No import errors

---

### Task 4: Implement Main Experiment Script (Part 2 - Fingerprint Generation)

**Files:**
- Modify: `experiments/defingerprint/run_defingerprint.py` (append functions)

- [ ] **Step 1: Add fingerprint generation function**

```python

def generate_fingerprint_data(config, args, model):
    """
    Generate fingerprint and extracting matrices.
    
    Since Stage 2 didn't save trace_data, we need to regenerate it.
    This ensures consistency across all experiments.
    """
    print("\n" + "=" * 60)
    print("Generating fingerprint data...")
    print("=" * 60)
    
    # Set random seed for reproducibility
    if config.evaluation.seed is not None:
        np.random.seed(config.evaluation.seed)
        torch.manual_seed(config.evaluation.seed)
    
    # Calculate weight size from model
    weight_size = get_diffusion_embed_layers_length(
        model, config.fingerprint.embed_layer_names
    )
    print(f"Embed layers weight size: {weight_size}")
    
    # Generate fingerprints
    fingerprints = generate_fingerprints(
        config.fingerprint.num_clients,
        config.fingerprint.lfp_length
    )
    print(f"Generated {len(fingerprints)} fingerprints with length {config.fingerprint.lfp_length}")
    
    # Generate extracting matrices
    extract_matrices = generate_extracting_matrices(
        weight_size,
        config.fingerprint.lfp_length,
        config.fingerprint.num_clients
    )
    print(f"Generated {len(extract_matrices)} extracting matrices")
    
    return fingerprints, extract_matrices


def save_fingerprint_data(fingerprints, extract_matrices, config):
    """Save fingerprint data to disk for reuse."""
    trace_dir = os.path.join(config.output.base_dir, "trace_data")
    os.makedirs(trace_dir, exist_ok=True)
    
    fingerprints_array = np.array(fingerprints)
    extract_matrices_array = np.array(extract_matrices)
    
    np.save(os.path.join(trace_dir, "fingerprints.npy"), fingerprints_array)
    np.save(os.path.join(trace_dir, "extract_matrices.npy"), extract_matrices_array)
    
    # Save metadata
    metadata = {
        "num_clients": config.fingerprint.num_clients,
        "lfp_length": config.fingerprint.lfp_length,
        "embed_layer_names": config.fingerprint.embed_layer_names,
        "fingerprints_shape": fingerprints_array.shape,
        "extract_matrices_shape": extract_matrices_array.shape,
    }
    
    import json
    with open(os.path.join(trace_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Fingerprint data saved to {trace_dir}")
```

- [ ] **Step 2: Test fingerprint generation**

Run: `python -c "from experiments.defingerprint.run_defingerprint import generate_fingerprint_data; print('Function defined')"`
Expected: No errors

---

### Task 5: Implement Main Experiment Script (Part 3 - Finetuning Logic)

**Files:**
- Modify: `experiments/defingerprint/run_defingerprint.py` (append functions)

- [ ] **Step 1: Add finetuning function**

```python

def finetune_model(model, epochs, lr, train_loader, args, device):
    """
    Fine-tune model on normal data (without watermark data).
    
    This implements the fine-tuning attack: continuing training on normal
    data distribution to potentially remove fingerprint information.
    
    Args:
        model: Model to finetune (will be modified in-place)
        epochs: Number of finetuning epochs
        lr: Learning rate (using training-stage lr as per user requirement)
        train_loader: DataLoader for normal training data
        args: Training arguments
        device: Device to use
    
    Returns:
        Finetuned model
    """
    from torch.utils.data import DataLoader
    import torch.nn.functional as F
    
    print(f"\nFine-tuning for {epochs} epochs with lr={lr}...")
    
    model.train()
    model = model.to(device)
    
    # Setup optimizer
    if args.local_optim == "adam":
        optimizer = torch.optim.Adam(model.unet.parameters(), lr=lr)
    else:
        optimizer = torch.optim.Adam(model.unet.parameters(), lr=lr)
    
    # Setup diffusion scheduler
    diffusion = SimpleDiffusion(
        num_timesteps=args.timesteps,
        beta_schedule=getattr(args, "beta_schedule", "linear"),
        device=str(device)
    )
    
    epoch_losses = []
    
    for epoch in range(epochs):
        batch_losses = []
        
        for batch_idx, (images, _) in enumerate(train_loader):
            images = images.to(device)
            batch_size = images.shape[0]
            
            # Sample timesteps
            t = torch.randint(0, diffusion.num_timesteps, (batch_size,), device=device).long()
            
            # Encode images to latents
            latents = model.encode_images(images)
            
            # Add noise
            noise = torch.randn_like(latents)
            noisy_latents = diffusion.add_noise(latents, noise, t)
            
            # Predict noise
            noise_pred = model.unet(noisy_latents, t).sample
            
            # Compute loss (normal diffusion training, no watermark)
            loss = F.mse_loss(noise_pred, noise)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            batch_losses.append(loss.item())
        
        avg_loss = sum(batch_losses) / len(batch_losses)
        epoch_losses.append(avg_loss)
        print(f"  Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.4f}")
    
    model.cpu()
    return model, epoch_losses
```

- [ ] **Step 2: Verify finetune function syntax**

Run: `python -m py_compile experiments/defingerprint/run_defingerprint.py`
Expected: No syntax errors

---

### Task 6: Implement Main Experiment Script (Part 4 - Evaluation Functions)

**Files:**
- Modify: `experiments/defingerprint/run_defingerprint.py` (append functions)

- [ ] **Step 1: Add evaluation function**

```python

def evaluate_fid_score(model, args, device, num_samples):
    """
    Evaluate FID score for normal classes.
    
    Args:
        model: Model to evaluate
        args: Model arguments
        device: Device to use
        num_samples: Number of samples per class for evaluation
    
    Returns:
        FID score (float)
    """
    print("\nEvaluating FID score...")
    
    # Load test dataset
    test_dataset, _ = get_full_dataset(
        args.dataset,
        img_size=(args.image_size, args.image_size)
    )
    
    # Setup diffusion
    diffusion = SimpleDiffusion(
        num_timesteps=args.timesteps,
        beta_schedule=getattr(args, "beta_schedule", "linear"),
        device=str(device)
    )
    
    # Evaluate FID
    results = evaluate_fid(
        model=model,
        diffusion=diffusion,
        real_dataset=test_dataset,
        watermark_images=None,  # No watermark for normal evaluation
        args=args,
        device=device,
        num_samples_per_class=num_samples
    )
    
    # Extract average FID
    avg_fid = results.get("avg_fid", results.get("fid", None))
    
    if avg_fid is None:
        # If results is just a float, return it
        avg_fid = results if isinstance(results, (int, float)) else results.get("fid", 0.0)
    
    print(f"FID Score: {avg_fid:.2f}")
    
    return avg_fid


def evaluate_fingerprint_accuracy(model, fingerprints, extract_matrices, args, device):
    """
    Evaluate fingerprint retention rate.
    
    Args:
        model: Model to evaluate
        fingerprints: List of fingerprint vectors
        extract_matrices: List of extracting matrices
        args: Model arguments
        device: Device to use
    
    Returns:
        Tuple of (best_match_idx, confidence, all_scores, retention_rate)
    """
    print("\nEvaluating fingerprint retention...")
    
    # Get embed layers
    from watermark.fingerprint_diffusion import get_diffusion_embed_layers
    
    model_copy = copy.deepcopy(model)
    model_copy = model_copy.to(device)
    model_copy.eval()
    
    embed_layers = get_diffusion_embed_layers(model_copy, args.embed_layer_names)
    
    # Extract fingerprints and match
    fss, best_match_idx = extracting_fingerprints(
        embed_layers,
        fingerprints,
        extract_matrices,
        epsilon=0.5,
        hd=False
    )
    
    # Calculate retention rate
    # A fingerprint is considered retained if FSS >= threshold
    retention_rate = 1.0 if fss >= args.fingerprint_threshold else fss / args.fingerprint_threshold
    
    print(f"Best match: Client {best_match_idx}, FSS: {fss:.4f}")
    print(f"Fingerprint retention rate: {retention_rate:.2%}")
    
    model_copy.cpu()
    
    return best_match_idx, fss, retention_rate
```

- [ ] **Step 2: Verify evaluation function**

Run: `python -m py_compile experiments/defingerprint/run_defingerprint.py`
Expected: No syntax errors

---

### Task 7: Implement Main Experiment Script (Part 5 - Main Function)

**Files:**
- Modify: `experiments/defingerprint/run_defingerprint.py` (append main function)

- [ ] **Step 1: Add main orchestration function**

```python

def run_experiment(config):
    """
    Main experiment orchestration function.
    
    Runs all experiment groups and saves results.
    """
    print("\n" + "=" * 80)
    print("DEFINGERPRINT EXPERIMENT: Fine-tuning Attack Analysis")
    print("=" * 80)
    
    # Setup device
    device_str = f"cuda:{config.compute.gpu}" if torch.cuda.is_available() else "cpu"
    device = torch.device(device_str)
    print(f"\nUsing device: {device}")
    
    # Create output directory
    os.makedirs(config.output.base_dir, exist_ok=True)
    checkpoint_dir = os.path.join(config.output.base_dir, "checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    # Setup training args
    args = setup_train_args_from_config(config)
    
    # Set random seed
    if config.evaluation.seed is not None:
        np.random.seed(config.evaluation.seed)
        torch.manual_seed(config.evaluation.seed)
        torch.cuda.manual_seed(config.evaluation.seed)
    
    # Load train dataset for finetuning
    print("\nLoading train dataset...")
    train_dataset, _ = get_full_dataset(
        args.dataset,
        img_size=(args.image_size, args.image_size)
    )
    from torch.utils.data import DataLoader
    train_loader = DataLoader(
        train_dataset,
        batch_size=config.finetuning.local_bs,
        shuffle=True,
        num_workers=config.compute.num_workers
    )
    
    # Storage for results
    all_results = {}
    
    # ============================================================
    # BASELINE-0: Stage 1 Model (No Fingerprint)
    # ============================================================
    print("\n" + "=" * 80)
    print("BASELINE-0: Evaluating Stage 1 model (no fingerprint)")
    print("=" * 80)
    
    model_stage1 = load_model_from_checkpoint(
        config.baselines.stage1_checkpoint,
        args,
        device
    )
    
    fid_baseline0 = evaluate_fid_score(
        model_stage1,
        args,
        device,
        config.evaluation.fid_samples
    )
    
    all_results["baseline_0"] = {
        "fid_score": float(fid_baseline0),
        "fingerprint_accuracy": 0.0,  # No fingerprint
        "fingerprint_retention": 0.0,
        "checkpoint": config.baselines.stage1_checkpoint
    }
    
    print(f"Baseline-0 Results: FID={fid_baseline0:.2f}")
    
    # ============================================================
    # BASELINE-1: Stage 2 Model (With Fingerprint)
    # ============================================================
    print("\n" + "=" * 80)
    print("BASELINE-1: Evaluating Stage 2 model (with fingerprint)")
    print("=" * 80)
    
    model_stage2 = load_model_from_checkpoint(
        config.baselines.stage2_checkpoint,
        args,
        device
    )
    
    # Generate fingerprint data
    fingerprints, extract_matrices = generate_fingerprint_data(config, args, model_stage2)
    
    # Save fingerprint data for reuse
    save_fingerprint_data(fingerprints, extract_matrices, config)
    
    # Set fingerprint args
    args.embed_layer_names = config.fingerprint.embed_layer_names
    args.fingerprint_threshold = config.evaluation.fingerprint_threshold
    
    # Evaluate FID and fingerprint
    fid_baseline1 = evaluate_fid_score(
        model_stage2,
        args,
        device,
        config.evaluation.fid_samples
    )
    
    _, fss_baseline1, fp_retention_baseline1 = evaluate_fingerprint_accuracy(
        model_stage2,
        fingerprints,
        extract_matrices,
        args,
        device
    )
    
    all_results["baseline_1"] = {
        "fid_score": float(fid_baseline1),
        "fingerprint_accuracy": float(fss_baseline1),
        "fingerprint_retention": float(fp_retention_baseline1),
        "checkpoint": config.baselines.stage2_checkpoint
    }
    
    print(f"Baseline-1 Results: FID={fid_baseline1:.2f}, FSS={fss_baseline1:.4f}")
    
    # ============================================================
    # FINETUNING EXPERIMENTS
    # ============================================================
    
    for finetune_epochs in config.finetuning.epochs:
        exp_name = f"exp_{finetune_epochs}"
        
        print("\n" + "=" * 80)
        print(f"EXPERIMENT: Fine-tuning for {finetune_epochs} epoch(s)")
        print("=" * 80)
        
        # Load Stage 2 model (with fingerprint)
        model_finetune = load_model_from_checkpoint(
            config.baselines.stage2_checkpoint,
            args,
            device
        )
        
        # Finetune
        model_finetuned, finetune_losses = finetune_model(
            model_finetune,
            epochs=finetune_epochs,
            lr=config.finetuning.learning_rate,
            train_loader=train_loader,
            args=args,
            device=device
        )
        
        # Save checkpoint if requested
        if config.output.save_checkpoints:
            checkpoint_path = os.path.join(
                checkpoint_dir,
                f"exp_{finetune_epochs}",
                "model.pth"
            )
            os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
            torch.save(model_finetuned.state_dict(), checkpoint_path)
            print(f"Saved checkpoint to {checkpoint_path}")
        
        # Evaluate
        fid_exp = evaluate_fid_score(
            model_finetuned,
            args,
            device,
            config.evaluation.fid_samples
        )
        
        _, fss_exp, fp_retention_exp = evaluate_fingerprint_accuracy(
            model_finetuned,
            fingerprints,
            extract_matrices,
            args,
            device
        )
        
        all_results[exp_name] = {
            "fid_score": float(fid_exp),
            "fingerprint_accuracy": float(fss_exp),
            "fingerprint_retention": float(fp_retention_exp),
            "finetune_epochs": finetune_epochs,
            "finetune_lr": config.finetuning.learning_rate,
            "finetune_losses": finetune_losses,
            "checkpoint": checkpoint_path if config.output.save_checkpoints else None
        }
        
        print(f"\nExp-{finetune_epochs} Results: FID={fid_exp:.2f}, FSS={fss_exp:.4f}")
    
    # ============================================================
    # SAVE RESULTS
    # ============================================================
    
    results_path = os.path.join(config.output.base_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2)
    
    print("\n" + "=" * 80)
    print("EXPERIMENT COMPLETED!")
    print("=" * 80)
    print(f"Results saved to: {results_path}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"{'Group':<15} {'FID':<10} {'FP Accuracy':<15} {'FP Retention':<15}")
    print("-" * 60)
    for group_name, results in all_results.items():
        fid = results.get("fid_score", "N/A")
        fp_acc = results.get("fingerprint_accuracy", "N/A")
        fp_ret = results.get("fingerprint_retention", "N/A")
        print(f"{group_name:<15} {fid:<10.2f} {fp_acc:<15.4f} {fp_ret:<15.2%}")
    
    return all_results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run defingerprint experiment"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="experiments/defingerprint/config/experiment_config.yaml",
        help="Path to configuration file"
    )
    args = parser.parse_args()
    
    # Load config
    print(f"Loading configuration from {args.config}")
    config = load_config(args.config)
    
    # Run experiment
    results = run_experiment(config)
    
    print("\n✓ Experiment completed successfully!")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify main script compiles**

Run: `python -m py_compile experiments/defingerprint/run_defingerprint.py`
Expected: No syntax errors

- [ ] **Step 3: Commit main script**

```bash
git add experiments/defingerprint/run_defingerprint.py
git commit -m "feat: implement defingerprint experiment main script"
```

---

### Task 8: Implement Analysis Script

**Files:**
- Create: `experiments/defingerprint/analyze_results.py`

- [ ] **Step 1: Write analysis script**

```python
# -*- coding: UTF-8 -*-
"""
Analysis script for defingerprint experiment results.

Computes statistical metrics and generates text report.

Usage:
    python experiments/defingerprint/analyze_results.py \\
        --results ./result/defingerprint_experiments/results.json
"""

import os
import sys
import json
import argparse
from pathlib import Path

import numpy as np


def load_results(results_path):
    """Load experiment results from JSON."""
    with open(results_path, 'r') as f:
        return json.load(f)


def compute_statistics(results):
    """
    Compute statistical metrics from experiment results.
    
    Returns:
        dict: Metrics including FID changes, retention rates, etc.
    """
    # Extract baseline values
    baseline0_fid = results["baseline_0"]["fid_score"]
    baseline1_fid = results["baseline_1"]["fid_score"]
    baseline1_fp_acc = results["baseline_1"]["fingerprint_accuracy"]
    
    # Compute metrics for each experiment
    stats = {
        "baseline_0": {
            "fid": baseline0_fid,
            "fid_change_vs_baseline0": 0.0,
            "fid_change_vs_baseline1": baseline0_fid - baseline1_fid,
            "fingerprint_accuracy": 0.0,
            "fingerprint_retention": 0.0
        },
        "baseline_1": {
            "fid": baseline1_fid,
            "fid_change_vs_baseline0": baseline1_fid - baseline0_fid,
            "fid_change_vs_baseline1": 0.0,
            "fingerprint_accuracy": baseline1_fp_acc,
            "fingerprint_retention": 1.0
        }
    }
    
    # Compute for finetuning experiments
    for exp_name in ["exp_1", "exp_3", "exp_5", "exp_10"]:
        if exp_name not in results:
            continue
        
        exp_data = results[exp_name]
        exp_fid = exp_data["fid_score"]
        exp_fp_acc = exp_data["fingerprint_accuracy"]
        
        stats[exp_name] = {
            "fid": exp_fid,
            "fid_change_vs_baseline0": exp_fid - baseline0_fid,
            "fid_change_vs_baseline1": exp_fid - baseline1_fid,
            "fingerprint_accuracy": exp_fp_acc,
            "fingerprint_retention": exp_fp_acc / baseline1_fp_acc if baseline1_fp_acc > 0 else 0.0,
            "finetune_epochs": exp_data.get("finetune_epochs", 0)
        }
    
    return stats


def find_pareto_front(stats):
    """
    Find Pareto optimal points (low FID, high retention).
    
    Returns:
        list: Names of Pareto optimal experiment groups
    """
    pareto_optimal = []
    
    for name, metrics in stats.items():
        is_dominated = False
        
        # Check if this point is dominated by any other
        for other_name, other_metrics in stats.items():
            if name == other_name:
                continue
            
            # Dominated if other has lower FID AND higher retention
            if (other_metrics["fid"] < metrics["fid"] and 
                other_metrics["fingerprint_retention"] > metrics["fingerprint_retention"]):
                is_dominated = True
                break
        
        if not is_dominated:
            pareto_optimal.append(name)
    
    return pareto_optimal


def generate_report(stats, pareto_optimal, output_path):
    """Generate text report with analysis."""
    report_lines = [
        "=" * 80,
        "DEFINGERPRINT EXPERIMENT ANALYSIS REPORT",
        "=" * 80,
        "",
        "SUMMARY STATISTICS",
        "-" * 80,
        f"{'Group':<15} {'FID':<10} {'FP Acc':<12} {'FP Retention':<15} {'vs B0':<10} {'vs B1':<10}",
        "-" * 80
    ]
    
    for group_name in ["baseline_0", "baseline_1", "exp_1", "exp_3", "exp_5", "exp_10"]:
        if group_name not in stats:
            continue
        
        m = stats[group_name]
        report_lines.append(
            f"{group_name:<15} {m['fid']:<10.2f} {m['fingerprint_accuracy']:<12.4f} "
            f"{m['fingerprint_retention']:<15.2%} {m['fid_change_vs_baseline0']:<+10.2f} "
            f"{m['fid_change_vs_baseline1']:<+10.2f}"
        )
    
    report_lines.extend([
        "",
        "PARETO OPTIMAL POINTS",
        "-" * 80
    ])
    
    for name in pareto_optimal:
        m = stats[name]
        report_lines.append(
            f"  {name}: FID={m['fid']:.2f}, Retention={m['fingerprint_retention']:.2%}"
        )
    
    report_lines.extend([
        "",
        "KEY FINDINGS",
        "-" * 80
    ])
    
    # FID impact
    baseline0_fid = stats["baseline_0"]["fid"]
    baseline1_fid = stats["baseline_1"]["fid"]
    fid_impact = baseline1_fid - baseline0_fid
    
    report_lines.append(
        f"1. Fingerprint embedding impact: FID increased by {fid_impact:.2f} "
        f"({fid_impact/baseline0_fid*100:.1f}%)"
    )
    
    # Finetuning effectiveness
    if "exp_5" in stats:
        exp5_fid = stats["exp_5"]["fid"]
        exp5_retention = stats["exp_5"]["fingerprint_retention"]
        report_lines.append(
            f"2. 5-epoch finetuning: FID recovered to {exp5_fid:.2f} "
            f"(vs baseline-0: {exp5_fid - baseline0_fid:+.2f}), "
            f"fingerprint retention: {exp5_retention:.1%}"
        )
    
    # Best trade-off
    if pareto_optimal:
        best_name = pareto_optimal[0]  # Assume first Pareto point
        best_m = stats[best_name]
        report_lines.append(
            f"3. Best quality-retention trade-off: {best_name} "
            f"(FID={best_m['fid']:.2f}, retention={best_m['fingerprint_retention']:.1%})"
        )
    
    report_lines.extend([
        "",
        "=" * 80
    ])
    
    # Write report
    report_text = "\n".join(report_lines)
    with open(output_path, 'w') as f:
        f.write(report_text)
    
    print(report_text)
    print(f"\nReport saved to: {output_path}")
    
    return report_text


def main():
    """Main entry point for analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze defingerprint experiment results"
    )
    parser.add_argument(
        "--results",
        type=str,
        default="./result/defingerprint_experiments/results.json",
        help="Path to results JSON file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for analysis report (default: same dir as results)"
    )
    
    args = parser.parse_args()
    
    # Load results
    print(f"Loading results from {args.results}")
    results = load_results(args.results)
    
    # Compute statistics
    print("Computing statistics...")
    stats = compute_statistics(results)
    
    # Find Pareto optimal points
    print("Finding Pareto optimal points...")
    pareto_optimal = find_pareto_front(stats)
    
    # Set output path
    if args.output is None:
        output_path = os.path.join(
            os.path.dirname(args.results),
            "analysis_report.txt"
        )
    else:
        output_path = args.output
    
    # Generate report
    print("\nGenerating analysis report...")
    generate_report(stats, pareto_optimal, output_path)
    
    print("\n✓ Analysis completed successfully!")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify analysis script**

Run: `python -m py_compile experiments/defingerprint/analyze_results.py`
Expected: No syntax errors

- [ ] **Step 3: Commit analysis script**

```bash
git add experiments/defingerprint/analyze_results.py
git commit -m "feat: implement results analysis script"
```

---

### Task 9: Implement Visualization Script

**Files:**
- Create: `experiments/defingerprint/visualize/plot_results.py`

- [ ] **Step 1: Write visualization script**

```python
# -*- coding: UTF-8 -*-
"""
Visualization script for defingerprint experiment results.

Creates 3-panel Matplotlib figure showing:
1. FID vs finetune epochs
2. Fingerprint retention vs finetune epochs
3. Pareto frontier (FID vs retention)

Usage:
    python experiments/defingerprint/visualize/plot_results.py \\
        --results ./result/defingerprint_experiments/results.json
"""

import os
import sys
import json
import argparse

import matplotlib.pyplot as plt
import numpy as np


def load_results(results_path):
    """Load experiment results from JSON."""
    with open(results_path, 'r') as f:
        return json.load(f)


def prepare_plot_data(results):
    """
    Prepare data for plotting.
    
    Returns:
        dict: Arrays for each metric
    """
    # Extract data
    groups = ["baseline_0", "baseline_1", "exp_1", "exp_3", "exp_5", "exp_10"]
    labels = ["Baseline-0\n(No FP)", "Baseline-1\n(With FP)", "Exp-1", "Exp-3", "Exp-5", "Exp-10"]
    epochs = [0, 0, 1, 3, 5, 10]  # Finetune epochs (0 for baselines)
    
    fids = []
    fp_accs = []
    fp_retentions = []
    
    for group in groups:
        if group not in results:
            # Handle missing data
            fids.append(0)
            fp_accs.append(0)
            fp_retentions.append(0)
            continue
        
        fids.append(results[group]["fid_score"])
        fp_accs.append(results[group]["fingerprint_accuracy"])
        fp_retentions.append(results[group]["fingerprint_retention"])
    
    return {
        "groups": groups,
        "labels": labels,
        "epochs": epochs,
        "fids": np.array(fids),
        "fp_accs": np.array(fp_accs),
        "fp_retentions": np.array(fp_retentions)
    }


def plot_results(data, output_path):
    """
    Create 3-panel Matplotlib figure.
    
    Args:
        data: Prepared plot data
        output_path: Path to save figure
    """
    # Set style
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # Create figure with 3 subplots
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    # Extract arrays
    epochs = np.array(data["epochs"])
    fids = data["fids"]
    fp_retentions = data["fp_retentions"]
    labels = data["labels"]
    
    # Define colors
    baseline0_color = '#2ecc71'  # Green
    baseline1_color = '#e74c3c'  # Red
    exp_colors = ['#3498db', '#9b59b6', '#f39c12', '#1abc9c']  # Blue/purple/orange/teal
    
    # ================================================================
    # Plot 1: FID vs Finetune Epochs
    # ================================================================
    ax1 = axes[0]
    
    # Plot baseline lines
    ax1.axhline(y=fids[0], color=baseline0_color, linestyle='--', linewidth=2, 
                label='Baseline-0 (No FP)', alpha=0.7)
    ax1.axhline(y=fids[1], color=baseline1_color, linestyle='--', linewidth=2,
                label='Baseline-1 (With FP)', alpha=0.7)
    
    # Plot finetuned models
    finetune_mask = epochs > 0
    ax1.plot(epochs[finetune_mask], fids[finetune_mask], 'o-', linewidth=2, 
             markersize=8, color='#3498db', label='Finetuned Models')
    
    ax1.set_xlabel('Finetune Epochs', fontsize=12, fontweight='bold')
    ax1.set_ylabel('FID Score', fontsize=12, fontweight='bold')
    ax1.set_title('Generation Quality vs Finetuning', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # ================================================================
    # Plot 2: Fingerprint Retention vs Finetune Epochs
    # ================================================================
    ax2 = axes[1]
    
    # Plot baseline lines
    ax2.axhline(y=fp_retentions[0], color=baseline0_color, linestyle='--', linewidth=2,
                alpha=0.7)
    ax2.axhline(y=fp_retentions[1], color=baseline1_color, linestyle='--', linewidth=2,
                alpha=0.7)
    
    # Plot finetuned models
    ax2.plot(epochs[finetune_mask], fp_retentions[finetune_mask], 's-', linewidth=2,
             markersize=8, color='#e67e22', label='Fingerprint Retention')
    
    ax2.set_xlabel('Finetune Epochs', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Fingerprint Retention Rate', fontsize=12, fontweight='bold')
    ax2.set_title('Fingerprint Retention vs Finetuning', fontsize=14, fontweight='bold')
    ax2.set_ylim(0, 1.1)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # ================================================================
    # Plot 3: Pareto Frontier (FID vs Retention)
    # ================================================================
    ax3 = axes[2]
    
    # Plot all points
    ax3.scatter(fids[0], fp_retentions[0], s=150, c=baseline0_color, 
                marker='s', label='Baseline-0', zorder=3, edgecolors='black', linewidths=1.5)
    ax3.scatter(fids[1], fp_retentions[1], s=150, c=baseline1_color,
                marker='s', label='Baseline-1', zorder=3, edgecolors='black', linewidths=1.5)
    
    # Plot finetuned models
    for i, (fid, ret, label) in enumerate(zip(fids[2:], fp_retentions[2:], labels[2:])):
        ax3.scatter(fid, ret, s=120, c=exp_colors[i], marker='o',
                   label=label, zorder=3, edgecolors='black', linewidths=1)
        ax3.annotate(label.replace('\n', ' '), (fid, ret), 
                    textcoords="offset points", xytext=(5, 5), fontsize=9)
    
    # Draw Pareto frontier (simplified)
    # For this 2D case, Pareto frontier is points not dominated by others
    # A point dominates another if it has lower FID AND higher retention
    
    ax3.set_xlabel('FID Score', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Fingerprint Retention Rate', fontsize=12, fontweight='bold')
    ax3.set_title('Pareto Frontier: Quality vs Traceability', fontsize=14, fontweight='bold')
    ax3.legend(fontsize=9, loc='upper right')
    ax3.grid(True, alpha=0.3)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save figure
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Figure saved to: {output_path}")
    
    # Show figure
    plt.show()
    
    return fig


def main():
    """Main entry point for visualization."""
    parser = argparse.ArgumentParser(
        description="Visualize defingerprint experiment results"
    )
    parser.add_argument(
        "--results",
        type=str,
        default="./result/defingerprint_experiments/results.json",
        help="Path to results JSON file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for figure (default: same dir as results)"
    )
    
    args = parser.parse_args()
    
    # Load results
    print(f"Loading results from {args.results}")
    results = load_results(args.results)
    
    # Prepare plot data
    print("Preparing plot data...")
    data = prepare_plot_data(results)
    
    # Set output path
    if args.output is None:
        output_path = os.path.join(
            os.path.dirname(args.results),
            "defingerprint_results.png"
        )
    else:
        output_path = args.output
    
    # Create plot
    print("\nCreating visualization...")
    plot_results(data, output_path)
    
    print("\n✓ Visualization completed successfully!")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify visualization script**

Run: `python -m py_compile experiments/defingerprint/visualize/plot_results.py`
Expected: No syntax errors

- [ ] **Step 3: Commit visualization script**

```bash
git add experiments/defingerprint/visualize/plot_results.py
git commit -m "feat: implement Matplotlib visualization script"
```

---

### Task 10: Test Configuration Loading

**Files:**
- Test: `experiments/defingerprint/config/experiment_config.yaml`

- [ ] **Step 1: Test configuration load**

Run: `python -c "from experiments.defingerprint.run_defingerprint import load_config; cfg = load_config('experiments/defingerprint/config/experiment_config.yaml'); print(f'Model: {cfg.model.type}'); print(f'Finetune epochs: {cfg.finetuning.epochs}')"`
Expected: Output showing model type and finetune epochs list

- [ ] **Step 2: Test model setup args creation**

Run: `python -c "from experiments.defingerprint.run_defingerprint import load_config, setup_train_args_from_config; cfg = load_config('experiments/defingerprint/config/experiment_config.yaml'); args = setup_train_args_from_config(cfg); print(f'Dataset: {args.dataset}'); print(f'Image size: {args.image_size}')"`
Expected: Output showing dataset and image size

---

### Task 11: Create Execution Documentation

**Files:**
- Create: `experiments/defingerprint/README.md`

- [ ] **Step 1: Write README documentation**

```markdown
# Defingerprint Experiment

Systematic evaluation of fine-tuning-based fingerprint removal impact on diffusion model generation quality.

## Quick Start

```bash
# Run full experiment
python experiments/defingerprint/run_defingerprint.py \\
    --config experiments/defingerprint/config/experiment_config.yaml

# Analyze results
python experiments/defingerprint/analyze_results.py \\
    --results ./result/defingerprint_experiments/results.json

# Generate visualization
python experiments/defingerprint/visualize/plot_results.py \\
    --results ./result/defingerprint_experiments/results.json
```

## Prerequisites

- Trained Stage 1 model: `./result/simpleunet_cifar10_stage1/model_final.pth`
- Trained Stage 2 model: `./result/simpleunet_cifar10_stage2/model_final.pth`

## Experiment Groups

| Group | Description | Finetune Epochs |
|-------|-------------|----------------|
| Baseline-0 | Stage 1 (no fingerprint) | 0 |
| Baseline-1 | Stage 2 (with fingerprint) | 0 |
| Exp-1 | Fine-tuned | 1 |
| Exp-3 | Fine-tuned | 3 |
| Exp-5 | Fine-tuned | 5 |
| Exp-10 | Fine-tuned | 10 |

## Configuration

Edit `config/experiment_config.yaml` to modify:
- Learning rate (default: 1e-4, same as training)
- Finetune epochs list
- FID sample count
- Fingerprint threshold

## Output

```
result/defingerprint_experiments/
├── trace_data/
│   ├── fingerprints.npy
│   └── extract_matrices.npy
├── checkpoints/
│   ├── exp_1/model.pth
│   ├── exp_3/model.pth
│   ├── exp_5/model.pth
│   └── exp_10/model.pth
├── results.json
├── analysis_report.txt
└── defingerprint_results.png
```

## Metrics

- **FID Score**: Lower is better (generation quality)
- **Fingerprint Accuracy (FSS)**: Higher means better retention
- **Fingerprint Retention**: Ratio vs Baseline-1

## Analysis

Run `analyze_results.py` to generate:
- Statistical summary
- FID changes vs baselines
- Fingerprint retention rates
- Pareto optimal points

## Visualization

Run `plot_results.py` to create 3-panel figure:
1. FID vs Finetune Epochs
2. Fingerprint Retention vs Finetune Epochs
3. Pareto Frontier (Quality vs Traceability)
```

- [ ] **Step 2: Commit README**

```bash
git add experiments/defingerprint/README.md
git commit -m "docs: add defingerprint experiment README"
```

---

### Task 12: Final Verification

**Files:**
- Verify all scripts can be imported

- [ ] **Step 1: Test all imports**

```bash
python -c "from experiments.defingerprint.run_defingerprint import main; print('Main script OK')"
python -c "from experiments.defingerprint.analyze_results import main; print('Analysis script OK')"
python -c "from experiments.defingerprint.visualize.plot_results import main; print('Visualization script OK')"
```
Expected: All three commands print "OK"

- [ ] **Step 2: Dry run main script (check argument parsing)**

Run: `python experiments/defingerprint/run_defingerprint.py --help`
Expected: Help message showing arguments

- [ ] **Step 3: Create final commit summary**

```bash
git add -A
git commit -m "docs: complete defingerprint experiment implementation plan"
```

---

## Execution Choice

Plan complete and saved to `docs/superpowers/plans/2026-04-09-defingerprint-experiment.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach would you like?**