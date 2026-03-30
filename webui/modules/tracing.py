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
    metadata_path = osp.join(trace_dir, "metadata.json")

    if not osp.exists(fingerprints_path):
        return None, None, f"fingerprints.npy not found in {trace_dir}"
    if not osp.exists(metadata_path):
        return None, None, f"metadata.json not found in {trace_dir}"

    fingerprints = np.load(fingerprints_path)
    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    return fingerprints, metadata, None


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
        fingerprints, metadata, error = load_trace_data(trace_dir)
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
        fingerprints, metadata, error = load_trace_data(trace_dir)
        if error:
            return None, None, error

        num_clients = metadata.get("num_clients", 0)
        if num_clients == 0:
            return None, None, "No client information in metadata"

        leaked_model = torch.load(leaked_model_path, map_location="cpu")

        if "model" in leaked_model:
            leaked_state = leaked_model["model"]
        else:
            leaked_state = leaked_model

        weight_list = []
        if isinstance(leaked_state, dict):
            for key in sorted(leaked_state.keys()):
                if "weight" in key:
                    w = leaked_state[key]
                    if isinstance(w, torch.Tensor):
                        weight_list.append(w.detach().cpu().numpy().flatten())

        if weight_list:
            leaked_fp = np.concatenate(weight_list)
        else:
            return None, None, "No weights found in leaked model"

        similarity_scores = []

        for client_idx in range(num_clients):
            client_fp = fingerprints[client_idx].flatten()

            min_len = min(len(leaked_fp), len(client_fp))
            if min_len > 0:
                score = np.abs(leaked_fp[:min_len] - client_fp[:min_len]).mean()
                similarity_scores.append((client_idx, score))

        if similarity_scores:
            similarity_scores.sort(key=lambda x: x[1])
            best_client = similarity_scores[0][0]
            best_score = similarity_scores[0][1]

            total_score = sum(s[1] for s in similarity_scores)
            if total_score > 0:
                confidence = 1.0 - (best_score / total_score)
            else:
                confidence = 1.0

            return best_client, confidence, None
        else:
            return None, None, "No fingerprints found in trace directory"

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
