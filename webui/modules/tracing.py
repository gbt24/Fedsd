# -*- coding: UTF-8 -*-
"""
Leak tracing module for FedTracker WebUI.
Provides leak simulation and owner identification functionality.
Supports .npy and .json format trace data.
"""

import json
import os
import os.path as osp
import sys

import numpy as np
import torch

sys.path.insert(0, osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__)))))


def load_trace_data(trace_dir):
    """Load trace data from .npy and .json files."""
    fingerprints_path = osp.join(trace_dir, "fingerprints.npy")
    extract_matrices_path = osp.join(trace_dir, "extract_matrices.npy")
    metadata_path = osp.join(trace_dir, "metadata.json")

    if not osp.exists(fingerprints_path):
        return None, None, None, f"fingerprints.npy not found in {trace_dir}"
    if not osp.exists(extract_matrices_path):
        return None, None, None, f"extract_matrices.npy not found in {trace_dir}"
    if not osp.exists(metadata_path):
        return None, None, None, f"metadata.json not found in {trace_dir}"

    fingerprints = np.load(fingerprints_path)
    extract_matrices = np.load(extract_matrices_path)
    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    return fingerprints, extract_matrices, metadata, None


def simulate_client_leak(checkpoint_path, trace_dir, client_idx, output_path):
    """
    Simulate a client model leak by copying model weights.
    Returns the path to the leaked model.
    """
    if not osp.exists(checkpoint_path):
        return None, f"Checkpoint not found: {checkpoint_path}"

    if not osp.exists(trace_dir):
        return None, f"Trace directory not found: {trace_dir}"

    try:
        _, _, metadata, error = load_trace_data(trace_dir)
        if error:
            return None, error

        num_clients = metadata.get("num_clients", 0)
        if client_idx >= num_clients or client_idx < 0:
            return None, f"Client index {client_idx} out of range (0-{num_clients - 1})"

        checkpoint = torch.load(checkpoint_path, map_location="cpu")

        os.makedirs(osp.dirname(output_path), exist_ok=True)
        torch.save(checkpoint, output_path)

        return output_path, None

    except Exception as e:
        import traceback

        return None, f"Error simulating leak: {str(e)}\n{traceback.format_exc()}"


def identify_owner(leaked_model_path, trace_dir):
    """
    Identify the owner of a leaked model by comparing fingerprints.
    Returns the identified client index and confidence score.
    """
    if not osp.exists(leaked_model_path):
        return None, None, f"Leaked model not found: {leaked_model_path}"

    if not osp.exists(trace_dir):
        return None, None, f"Trace directory not found: {trace_dir}"

    try:
        fingerprints, extract_matrices, metadata, error = load_trace_data(trace_dir)
        if error:
            return None, None, error

        num_clients = metadata.get("num_clients", 0)
        embed_layer_names = metadata.get(
            "embed_layer_names", "mid_block.attention.proj"
        )
        lfp_length = metadata.get("lfp_length", 128)

        if num_clients == 0:
            return None, None, "No client information in metadata"

        from watermark.fingerprint_diffusion import get_diffusion_embed_layers
        from utils.simple_unet import ClassConditionalUNet

        checkpoint = torch.load(leaked_model_path, map_location="cpu")

        if "model" in checkpoint:
            model_state = checkpoint["model"]
        else:
            model_state = checkpoint

        model_args_path = osp.join(osp.dirname(leaked_model_path), "args.txt")
        if osp.exists(model_args_path):
            with open(model_args_path, "r") as f:
                args_dict = json.load(f)
        else:
            args_dict = {
                "model": "SimpleUNet",
                "num_classes": 10,
                "num_channels": 3,
                "image_size": 32,
                "timesteps": 1000,
                "beta_schedule": "linear",
                "time_embed_dim": 512,
                "class_embed_dim": 512,
                "block_out_channels": (128, 256, 256, 256),
                "layers_per_block": 2,
                "dropout": 0.1,
            }

        class SimpleArgs:
            pass

        args = SimpleArgs()
        for k, v in args_dict.items():
            setattr(args, k, v)

        model = ClassConditionalUNet(
            num_classes=getattr(args, "num_classes", 10),
            in_channels=getattr(args, "num_channels", 3),
            out_channels=getattr(args, "num_channels", 3),
            sample_size=getattr(args, "image_size", 32),
            time_embed_dim=getattr(args, "time_embed_dim", 512),
            class_embed_dim=getattr(args, "class_embed_dim", 512),
            block_out_channels=getattr(
                args, "block_out_channels", (128, 256, 256, 256)
            ),
            layers_per_block=getattr(args, "layers_per_block", 2),
            dropout=getattr(args, "dropout", 0.1),
        )

        model.load_state_dict(model_state)
        model.eval()

        embed_layers = get_diffusion_embed_layers(model, embed_layer_names)

        weight_list = []
        for layer in embed_layers:
            w = layer.weight.detach().cpu().numpy().flatten()
            weight_list.append(w)
        weight = np.concatenate(weight_list)

        all_scores = []
        epsilon = 0.5

        for client_idx in range(num_clients):
            matrix = extract_matrices[client_idx]
            result = np.dot(matrix, weight)

            result = np.multiply(result, fingerprints[client_idx])
            result[result > epsilon] = epsilon
            score = np.sum(result) / lfp_length / epsilon
            all_scores.append(score)

        best_match_idx = np.argmax(all_scores)
        confidence = all_scores[best_match_idx]

        return int(best_match_idx), float(confidence), None

    except Exception as e:
        import traceback

        return (
            None,
            None,
            f"Error identifying owner: {str(e)}\n{traceback.format_exc()}",
        )


def get_client_list(trace_dir):
    """Get list of available client indices from trace directory."""
    if not osp.exists(trace_dir):
        return []

    metadata_path = osp.join(trace_dir, "metadata.json")
    if osp.exists(metadata_path):
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        num_clients = metadata.get("num_clients", 0)
        return list(range(num_clients))

    return []
