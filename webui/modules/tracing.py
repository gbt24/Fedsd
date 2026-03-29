# -*- coding: UTF-8 -*-
"""
Leak tracing module for FedTracker WebUI.
Provides leak simulation and owner identification functionality.
"""

import os
import os.path as osp
import sys

import torch
import numpy as np

sys.path.insert(0, osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__)))))


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
        checkpoint = torch.load(checkpoint_path, map_location="cpu")

        if "model" in checkpoint:
            model_state = checkpoint["model"]
        else:
            model_state = checkpoint

        client_fingerprints_path = osp.join(
            trace_dir, f"client_{client_idx}_fingerprint.pt"
        )
        if osp.exists(client_fingerprints_path):
            client_fingerprint = torch.load(
                client_fingerprints_path, map_location="cpu"
            )

            os.makedirs(osp.dirname(output_path), exist_ok=True)

            if "model" in checkpoint:
                checkpoint["model"] = model_state
            else:
                checkpoint = model_state

            torch.save(checkpoint, output_path)
            return output_path, None
        else:
            return None, f"Client {client_idx} fingerprint not found in trace directory"

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
        leaked_model = torch.load(leaked_model_path, map_location="cpu")

        if "model" in leaked_model:
            leaked_state = leaked_model["model"]
        else:
            leaked_state = leaked_model

        metadata_path = osp.join(trace_dir, "metadata.pt")
        if not osp.exists(metadata_path):
            return None, None, "Metadata file not found in trace directory"

        metadata = torch.load(metadata_path, map_location="cpu")
        num_clients = metadata.get("num_clients", 0)

        if num_clients == 0:
            return None, None, "No client information in metadata"

        similarity_scores = []

        for client_idx in range(num_clients):
            fingerprint_path = osp.join(
                trace_dir, f"client_{client_idx}_fingerprint.pt"
            )

            if osp.exists(fingerprint_path):
                client_fingerprint = torch.load(fingerprint_path, map_location="cpu")

                if isinstance(client_fingerprint, torch.Tensor):
                    client_fp = client_fingerprint.detach().cpu().numpy().flatten()
                else:
                    client_fp = np.array(client_fingerprint).flatten()

                if isinstance(leaked_state, dict):
                    weight_list = []
                    for key in sorted(leaked_state.keys()):
                        if "weight" in key:
                            w = leaked_state[key]
                            if isinstance(w, torch.Tensor):
                                weight_list.append(w.detach().cpu().numpy().flatten())
                    if weight_list:
                        leaked_fp = np.concatenate(weight_list)[: len(client_fp)]
                    else:
                        leaked_fp = np.zeros_like(client_fp)
                else:
                    leaked_fp = np.zeros_like(client_fp)

                if len(leaked_fp) == len(client_fp):
                    score = np.abs(leaked_fp - client_fp).mean()
                    similarity_scores.append((client_idx, score))

        if similarity_scores:
            similarity_scores.sort(key=lambda x: x[1])
            best_client = similarity_scores[0][0]
            best_score = similarity_scores[0][1]

            total_score = sum(s[1] for s in similarity_scores)
            if total_score > 0:
                confidence = 1.0 - (best_score / total_score)
            else:
                confidence = 0.0

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

    clients = []
    for filename in os.listdir(trace_dir):
        if filename.startswith("client_") and filename.endswith("_fingerprint.pt"):
            try:
                client_idx = int(filename.split("_")[1])
                clients.append(client_idx)
            except:
                pass

    return sorted(clients)
