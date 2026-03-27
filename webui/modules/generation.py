# -*- coding: UTF-8 -*-
"""
Image generation module for WebUI.
"""

import os
import sys
import time
from typing import Dict, List, Optional, Tuple

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import numpy as np
import torch
from torchvision.utils import save_image, make_grid

from modules.utils import ModelArgs, get_device, get_cifar10_labels, get_cifar100_labels


class ImageGenerator:
    """Image generator for diffusion models."""

    def __init__(self):
        self.model = None
        self.args = None
        self.device = None
        self.model_type = None
        self._loaded_model_path = None

    def load_model(self, model_path: str, gpu_id: int = 0) -> Tuple[str, Dict]:
        """
        Load model from path.

        Args:
            model_path: Path to model directory
            gpu_id: GPU device ID

        Returns:
            Tuple of (status message, model info dict)
        """
        from utils.diffusion_utils import get_diffusion_model

        args_file = os.path.join(model_path, "args.txt")
        if not os.path.exists(args_file):
            return f"Error: args.txt not found in {model_path}", {}

        with open(args_file, "r") as f:
            import json

            args_dict = json.load(f)

        self.args = ModelArgs(args_dict)
        self.device = get_device(gpu_id)
        self.args.device = self.device

        self.model_type = self.args.model

        checkpoint_path = os.path.join(model_path, "model_final.pth")
        if not os.path.exists(checkpoint_path):
            return f"Error: model_final.pth not found in {model_path}", {}

        try:
            self.model = get_diffusion_model(self.args)
            self.model.load_state_dict(
                torch.load(checkpoint_path, map_location=self.device)
            )
            self.model.to(self.device)
            self.model.eval()
            self._loaded_model_path = model_path
        except Exception as e:
            return f"Error loading model: {str(e)}", {}

        info = {
            "model_type": self.model_type,
            "dataset": self.args.dataset,
            "num_classes": getattr(self.args, "num_classes", 0),
            "image_size": self.args.image_size,
            "has_trace_data": os.path.exists(os.path.join(model_path, "trace_data")),
        }

        return f"Model loaded: {self.model_type} ({self.args.dataset})", info

    def get_class_labels(self) -> List[str]:
        """Get available class labels for current model."""
        if self.args is None:
            return []

        dataset = self.args.dataset
        if dataset == "cifar10":
            return get_cifar10_labels()
        elif dataset == "cifar100":
            return get_cifar100_labels()
        else:
            return [f"Class {i}" for i in range(getattr(self.args, "num_classes", 10))]

    def generate(
        self,
        labels: List[int],
        num_images: int = 16,
        seed: Optional[int] = None,
        num_inference_steps: Optional[int] = None,
        use_trigger: bool = False,
        progress_callback=None,
    ) -> Tuple[np.ndarray, str]:
        """
        Generate images using the loaded model.

        Args:
            labels: List of class labels to generate
            num_images: Number of images to generate per label
            seed: Random seed for reproducibility
            num_inference_steps: Number of diffusion steps
            use_trigger: Whether to use trigger class (watermark)
            progress_callback: Callback function for progress updates

        Returns:
            Tuple of (image array, status message)
        """
        if self.model is None:
            return None, "Error: No model loaded. Please load a model first."

        if seed is not None:
            torch.manual_seed(seed)
            np.random.seed(seed)

        if num_inference_steps is None:
            num_inference_steps = getattr(self.args, "num_inference_steps", 1000)

        self.model.to(self.device)
        self.model.eval()

        total_images = len(labels) * num_images
        all_images = []

        try:
            if self.model_type == "SimpleUNet":
                all_images = self._generate_simpleunet(
                    labels,
                    num_images,
                    seed,
                    num_inference_steps,
                    use_trigger,
                    progress_callback,
                )
            elif self.model_type == "StableDiffusion":
                all_images = self._generate_stable_diffusion(
                    labels, num_images, seed, num_inference_steps, progress_callback
                )
            else:
                return None, f"Error: Unsupported model type: {self.model_type}"

            grid_image = self._make_grid(all_images, len(labels))

            return grid_image, f"Generated {total_images} images successfully."

        except Exception as e:
            import traceback

            traceback.print_exc()
            return None, f"Error generating images: {str(e)}"

    def _generate_simpleunet(
        self,
        labels: List[int],
        num_images: int,
        seed: Optional[int],
        num_inference_steps: int,
        use_trigger: bool,
        progress_callback=None,
    ) -> torch.Tensor:
        """Generate images using SimpleUNet."""
        from utils.simple_diffusion import SimpleDiffusion

        diffusion = SimpleDiffusion(
            num_timesteps=getattr(self.args, "timesteps", 1000),
            beta_schedule=getattr(self.args, "beta_schedule", "linear"),
            device=str(self.device),
        )

        all_images = []
        total_batches = len(labels)

        for batch_idx, label in enumerate(labels):
            if use_trigger:
                trigger_class = getattr(
                    self.args, "trigger_class", self.args.num_classes
                )
                class_labels = torch.full(
                    (num_images,), trigger_class, dtype=torch.long, device=self.device
                )
            else:
                class_labels = torch.full(
                    (num_images,), label, dtype=torch.long, device=self.device
                )

            current_seed = seed + batch_idx if seed is not None else None

            with torch.no_grad():
                images = diffusion.sample(
                    self.model,
                    batch_size=num_images,
                    class_labels=class_labels,
                    num_inference_steps=num_inference_steps,
                    seed=current_seed,
                    device=str(self.device),
                )

            all_images.append(images.cpu())

            if progress_callback:
                progress_callback(
                    (batch_idx + 1) / total_batches,
                    f"Generated class {label} ({batch_idx + 1}/{total_batches})",
                )

        return torch.cat(all_images, dim=0)

    def _generate_stable_diffusion(
        self,
        labels: List[int],
        num_images: int,
        seed: Optional[int],
        num_inference_steps: int,
        progress_callback=None,
    ) -> torch.Tensor:
        """Generate images using Stable Diffusion."""
        from utils.diffusion_utils import sample_diffusion_sd

        all_images = []
        normal_prompt = getattr(self.args, "normal_prompt", "a photo")

        total_batches = len(labels)

        for batch_idx, label in enumerate(labels):
            current_seed = seed + batch_idx if seed is not None else None

            with torch.no_grad():
                images = sample_diffusion_sd(
                    self.model,
                    None,
                    self.args,
                    self.device,
                    prompt=normal_prompt,
                    batch_size=num_images,
                    num_inference_steps=num_inference_steps,
                    seed=current_seed,
                )

            all_images.append(images.cpu())

            if progress_callback:
                progress_callback(
                    (batch_idx + 1) / total_batches,
                    f"Generated batch {batch_idx + 1}/{total_batches}",
                )

        return torch.cat(all_images, dim=0)

    def _make_grid(self, images: torch.Tensor, num_classes: int) -> np.ndarray:
        """Create a grid image from generated images."""
        nrow = min(8, images.shape[0])
        grid = make_grid(images, nrow=nrow, normalize=True)
        grid = grid.permute(1, 2, 0).numpy()
        grid = (grid * 255).astype(np.uint8)
        return grid

    def save_images(
        self,
        images: np.ndarray,
        output_dir: str,
        prefix: str = "generated",
    ) -> str:
        """Save generated images to file."""
        os.makedirs(output_dir, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.png"
        filepath = os.path.join(output_dir, filename)

        from PIL import Image

        img = Image.fromarray(images)
        img.save(filepath)

        return filepath


_model_instance = None


def get_generator() -> ImageGenerator:
    """Get singleton generator instance."""
    global _model_instance
    if _model_instance is None:
        _model_instance = ImageGenerator()
    return _model_instance
