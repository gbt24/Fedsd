# -*- coding: UTF-8 -*-
"""
Model tracing module for WebUI.
Functions for simulating leaks and identifying owners.
"""

import copy
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import numpy as np
import torch

from modules.utils import ModelArgs, get_device, load_model_args


class ModelTracer:
    """Model tracing handler for leak simulation and owner identification."""

    def __init__(self):
        self.local_fingerprints = None
        self.extracting_matrices = None
        self.metadata = None
        self._trace_dir = None

    def load_trace_data(self, trace_dir: str) -> Tuple[bool, str, Dict]:
        """
        Load trace data from directory.

        Args:
            trace_dir: Path to trace_data directory

        Returns:
            Tuple of (success, message, metadata)
        """
        from save_trace_data import load_trace_data

        if not os.path.exists(trace_dir):
            return False, f"Trace data directory not found: {trace_dir}", {}

        try:
            self.local_fingerprints, self.extracting_matrices, self.metadata = (
                load_trace_data(trace_dir)
            )
            self._trace_dir = trace_dir

            info = {
                "num_clients": len(self.local_fingerprints),
                "lfp_length": self.metadata.get("lfp_length", 0),
                "embed_layers": self.metadata.get("embed_layer_names", []),
            }

            return (
                True,
                f"Loaded trace data for {len(self.local_fingerprints)} clients",
                info,
            )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return False, f"Error loading trace data: {str(e)}", {}

    def simulate_leak(
        self,
        model_path: str,
        client_idx: int,
        gpu_id: int = 0,
        max_iters: int = 10,
        lambda_factor: float = 0.01,
        output_dir: Optional[str] = None,
        progress_callback=None,
    ) -> Tuple[bool, str, Dict]:
        """
        Simulate client model leak.

        Args:
            model_path: Path to global model directory
            client_idx: Client index to simulate leak for
            gpu_id: GPU device ID
            max_iters: Maximum iterations for fingerprint embedding
            lambda_factor: Learning rate for gradient update
            output_dir: Output directory for leaked model
            progress_callback: Progress callback function

        Returns:
            Tuple of (success, message, result info)
        """
        from utils.models import get_model
        from watermark.fingerprint_diffusion import (
            calculate_local_grad,
            extracting_fingerprints,
            get_diffusion_embed_layers,
        )

        if self.local_fingerprints is None:
            return (
                False,
                "Error: No trace data loaded. Please load trace data first.",
                {},
            )

        if client_idx < 0 or client_idx >= len(self.local_fingerprints):
            return (
                False,
                f"Error: Invalid client index. Must be 0-{len(self.local_fingerprints) - 1}",
                {},
            )

        args_file = os.path.join(model_path, "args.txt")
        checkpoint_file = os.path.join(model_path, "model_final.pth")

        if not os.path.exists(args_file) or not os.path.exists(checkpoint_file):
            return False, f"Error: Model files not found in {model_path}", {}

        try:
            with open(args_file, "r") as f:
                args_dict = json.load(f)

            args = ModelArgs(args_dict)
            device = get_device(gpu_id)
            args.device = device

            if progress_callback:
                progress_callback(0.1, "Loading model...")

            model = get_model(args)
            model.load_state_dict(torch.load(checkpoint_file, map_location=device))
            model.eval()

            if progress_callback:
                progress_callback(0.3, f"Simulating leak for client {client_idx}...")

            client_fingerprint = self.local_fingerprints[client_idx]
            embed_layer_names = self.metadata.get("embed_layer_names", [])
            embed_layers = get_diffusion_embed_layers(model, embed_layer_names)

            fss, extract_idx = extracting_fingerprints(
                embed_layers, self.local_fingerprints, self.extracting_matrices
            )

            iterations = 0
            target_fss = 0.85

            while (
                extract_idx != client_idx
                or (extract_idx == client_idx and fss < target_fss)
            ) and iterations < max_iters:
                grad_update = calculate_local_grad(
                    embed_layers,
                    client_fingerprint,
                    self.extracting_matrices[client_idx],
                )
                grad_update = torch.mul(grad_update, -lambda_factor)
                grad_update = grad_update.to(device)

                weight_count = 0
                for embed_layer in embed_layers:
                    weight_length = embed_layer.weight.numel()
                    embed_layer.weight = torch.nn.Parameter(
                        embed_layer.weight
                        + grad_update[
                            weight_count : weight_count + weight_length
                        ].view_as(embed_layer.weight)
                    )
                    weight_count += weight_length

                fss, extract_idx = extracting_fingerprints(
                    embed_layers, self.local_fingerprints, self.extracting_matrices
                )
                iterations += 1

                if progress_callback:
                    progress = 0.3 + 0.5 * (iterations / max_iters) * 0.6
                    progress_callback(
                        progress,
                        f"Embedding fingerprint... (iter {iterations}, FSS: {fss:.4f})",
                    )

            if output_dir is None:
                output_dir = os.path.join(model_path, "simulated_leaks")

            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(
                output_dir, f"leaked_model_client_{client_idx}.pth"
            )

            if progress_callback:
                progress_callback(0.9, f"Saving leaked model...")

            model.cpu()
            torch.save(model.state_dict(), output_path)

            args_output = os.path.join(output_dir, "args.txt")
            if not os.path.exists(args_output):
                import shutil

                shutil.copy(args_file, args_output)

            result = {
                "client_idx": client_idx,
                "fss_score": float(fss),
                "iterations": iterations,
                "extract_idx": int(extract_idx),
                "output_path": output_path,
                "success": (extract_idx == client_idx and fss >= target_fss),
            }

            return (
                True,
                f"Leak simulated. FSS: {fss:.4f}, Iterations: {iterations}",
                result,
            )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return False, f"Error simulating leak: {str(e)}", {}

    def identify_owner(
        self,
        leaked_model_path: str,
        gpu_id: int = 0,
        progress_callback=None,
    ) -> Tuple[bool, str, Dict]:
        """
        Identify the owner of a leaked model.

        Args:
            leaked_model_path: Path to leaked model checkpoint
            gpu_id: GPU device ID
            progress_callback: Progress callback function

        Returns:
            Tuple of (success, message, result info)
        """
        from utils.models import get_model
        from watermark.fingerprint_diffusion import (
            extracting_fingerprints,
            get_diffusion_embed_layers,
        )

        if self.local_fingerprints is None:
            return (
                False,
                "Error: No trace data loaded. Please load trace data first.",
                {},
            )

        model_dir = os.path.dirname(leaked_model_path)
        args_file = os.path.join(model_dir, "args.txt")

        if not os.path.exists(args_file):
            args_file = os.path.join(os.path.dirname(model_dir), "args.txt")

        if not os.path.exists(leaked_model_path):
            return False, f"Error: Leaked model not found: {leaked_model_path}", {}

        try:
            with open(args_file, "r") as f:
                args_dict = json.load(f)

            args = ModelArgs(args_dict)
            device = get_device(gpu_id)
            args.device = device

            if progress_callback:
                progress_callback(0.2, "Loading leaked model...")

            model = get_model(args)
            model.load_state_dict(torch.load(leaked_model_path, map_location=device))
            model.eval()

            if progress_callback:
                progress_callback(0.5, "Extracting fingerprint...")

            embed_layer_names = self.metadata.get("embed_layer_names", [])
            embed_layers = get_diffusion_embed_layers(model, embed_layer_names)

            all_scores = []
            for idx in range(len(self.local_fingerprints)):
                weight = embed_layers[0].weight.detach().cpu().numpy().flatten()
                for i in range(1, len(embed_layers)):
                    weight = np.append(
                        weight, embed_layers[i].weight.detach().cpu().numpy().flatten()
                    )

                matrix = self.extracting_matrices[idx]
                result = np.dot(matrix, weight)
                result = np.multiply(result, self.local_fingerprints[idx])
                result[result > 0.5] = 0.5
                score = np.sum(result) / len(self.local_fingerprints[idx]) / 0.5
                all_scores.append(score)

            if progress_callback:
                progress_callback(0.9, "Computing match scores...")

            all_scores = np.array(all_scores)
            best_match_idx = int(np.argmax(all_scores))
            confidence = float(all_scores[best_match_idx])

            sorted_indices = np.argsort(all_scores)[::-1][:5]
            top5 = [(int(idx), float(all_scores[idx])) for idx in sorted_indices]

            threshold = 0.85
            if confidence >= threshold:
                confidence_level = "HIGH"
            elif confidence >= threshold * 0.7:
                confidence_level = "MEDIUM"
            else:
                confidence_level = "LOW"

            result = {
                "best_match_idx": best_match_idx,
                "confidence": confidence,
                "confidence_level": confidence_level,
                "threshold": threshold,
                "top5_candidates": top5,
                "all_scores": [float(s) for s in all_scores],
            }

            return (
                True,
                f"Identified: Client {best_match_idx} (Confidence: {confidence:.4f})",
                result,
            )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return False, f"Error identifying owner: {str(e)}", {}

    def get_num_clients(self) -> int:
        """Get number of clients from loaded trace data."""
        if self.local_fingerprints is None:
            return 0
        return len(self.local_fingerprints)


_tracer_instance = None


def get_tracer() -> ModelTracer:
    """Get singleton tracer instance."""
    global _tracer_instance
    if _tracer_instance is None:
        _tracer_instance = ModelTracer()
    return _tracer_instance
