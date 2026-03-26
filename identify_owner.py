# -*- coding: UTF-8 -*-
"""
Identify the owner of a leaked model using fingerprint extraction.

This script extracts the fingerprint from a model and matches it against
all known client fingerprints to identify the most likely owner.

Usage:
    python identify_owner.py \
        --checkpoint ./leaked_model_client_3.pth \
        --trace_dir ./result/simpleunet_cifar10_stage2/trace_data
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import torch

from save_trace_data import load_trace_data
from watermark.fingerprint_diffusion import (
    extracting_fingerprints,
    get_diffusion_embed_layers,
)


def identify_owner(
    model,
    local_fingerprints,
    extracting_matrices,
    embed_layer_names,
    epsilon=0.5,
    use_hamming=False,
):
    """
    Identify the owner of a model by extracting its fingerprint.

    Args:
        model: Model to identify
        local_fingerprints: List of fingerprint vectors for all clients
        extracting_matrices: List of extracting matrices for all clients
        embed_layer_names: Names of layers where fingerprints are embedded
        epsilon: Epsilon for hinge-like loss
        use_hamming: Use Hamming distance instead of FSS score

    Returns:
        best_match_idx: Index of the best matching client
        confidence: Confidence score (FSS or 1 - BER)
        all_scores: List of scores for all clients
    """
    embed_layers = get_diffusion_embed_layers(model, embed_layer_names)

    all_scores = []
    for idx in range(len(local_fingerprints)):
        weight = embed_layers[0].weight.detach().numpy().flatten()
        for i in range(1, len(embed_layers)):
            weight = np.append(
                weight, embed_layers[i].weight.detach().numpy().flatten()
            )

        matrix = extracting_matrices[idx]
        result = np.dot(matrix, weight)

        if use_hamming:
            result[result >= 0] = 1
            result[result < 0] = -1
            ber = np.sum(result != local_fingerprints[idx]) / len(
                local_fingerprints[idx]
            )
            all_scores.append(1 - ber)
        else:
            result = np.multiply(result, local_fingerprints[idx])
            result[result > epsilon] = epsilon
            score = np.sum(result) / len(local_fingerprints[idx]) / epsilon
            all_scores.append(score)

    best_match_idx = np.argmax(all_scores)
    confidence = all_scores[best_match_idx]

    return best_match_idx, confidence, all_scores


def main():
    parser = argparse.ArgumentParser(description="Identify the owner of a leaked model")
    parser.add_argument(
        "--checkpoint",
        type=str,
        required=True,
        help="Path to leaked model checkpoint",
    )
    parser.add_argument(
        "--trace_dir",
        type=str,
        required=True,
        help="Path to trace data directory",
    )
    parser.add_argument(
        "--args_file",
        type=str,
        default=None,
        help="Path to args.json (default: same dir as checkpoint)",
    )
    parser.add_argument(
        "--gpu",
        type=int,
        default=0,
        help="GPU ID (default: 0, -1 for CPU)",
    )
    parser.add_argument(
        "--use_hamming",
        action="store_true",
        help="Use Hamming distance instead of FSS score",
    )
    parser.add_argument(
        "--epsilon",
        type=float,
        default=0.5,
        help="Epsilon for FSS score calculation",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Confidence threshold for high confidence",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Owner Identification")
    print("=" * 60)
    print(f"Leaked model: {args.checkpoint}")
    print(f"Trace data: {args.trace_dir}")

    if args.args_file is None:
        args_file = os.path.join(os.path.dirname(args.checkpoint), "args.txt")
    else:
        args_file = args.args_file

    print(f"\nLoading model arguments from {args_file}...")
    with open(args_file, "r") as f:
        args_dict = json.load(f)

    class TrainArgs:
        pass

    train_args = TrainArgs()
    for k, v in args_dict.items():
        setattr(train_args, k, v)

    device = torch.device(
        f"cuda:{args.gpu}" if torch.cuda.is_available() and args.gpu >= 0 else "cpu"
    )
    train_args.device = device

    print("\nLoading trace data...")
    local_fingerprints, extracting_matrices, metadata = load_trace_data(args.trace_dir)
    embed_layer_names = metadata["embed_layer_names"]

    print(f"  - Number of clients: {metadata['num_clients']}")
    print(f"  - Fingerprint length: {metadata['lfp_length']}")
    print(f"  - Embed layers: {embed_layer_names}")

    print("\nLoading model...")
    from utils.models import get_model

    model = get_model(train_args)
    model.load_state_dict(torch.load(args.checkpoint, map_location=device))
    model.eval()

    print("\nExtracting fingerprint...")
    best_match_idx, confidence, all_scores = identify_owner(
        model,
        local_fingerprints,
        extracting_matrices,
        embed_layer_names,
        epsilon=args.epsilon,
        use_hamming=args.use_hamming,
    )

    print("\n" + "=" * 60)
    print("Owner Identification Results")
    print("=" * 60)
    print(f"Leaked model: {args.checkpoint}")
    print(f"Best match: Client {best_match_idx}")
    print(f"Confidence: {confidence:.4f}")

    if confidence >= args.threshold:
        print(f"Confidence level: HIGH (>= {args.threshold})")
    elif confidence >= args.threshold * 0.7:
        print(f"Confidence level: MEDIUM (>= {args.threshold * 0.7:.2f})")
    else:
        print(f"Confidence level: LOW (< {args.threshold * 0.7:.2f})")

    print("\nTop 5 candidates:")
    sorted_indices = np.argsort(all_scores)[::-1][:5]
    for rank, idx in enumerate(sorted_indices, 1):
        print(f"  {rank}. Client {idx}: {all_scores[idx]:.4f}")

    output_path = os.path.join(
        os.path.dirname(args.checkpoint),
        f"identification_result_client_{best_match_idx}.json",
    )
    result = {
        "leaked_model": args.checkpoint,
        "best_match_idx": int(best_match_idx),
        "confidence": float(confidence),
        "threshold": args.threshold,
        "all_scores": [float(s) for s in all_scores],
        "top_5": [(int(idx), float(all_scores[idx])) for idx in sorted_indices],
    }
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResult saved to {output_path}")

    return best_match_idx, confidence


if __name__ == "__main__":
    main()
