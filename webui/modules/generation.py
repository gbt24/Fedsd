# -*- coding: UTF-8 -*-
import os
import os.path as osp
import sys

import torch
from PIL import Image

sys.path.insert(0, osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__)))))

from utils.utils import parse_args
from utils.simple_unet import ClassConditionalUNet
from utils.simple_diffusion import DDPMScheduler


def load_model(checkpoint_path, device="cuda"):
    checkpoint = torch.load(checkpoint_path, map_location=device)
    return checkpoint


def get_diffusion_args(model_dir):
    args_path = osp.join(model_dir, "args.txt")
    if osp.exists(args_path):
        args = parse_args()
        with open(args_path, "r") as f:
            lines = f.readlines()
            for line in lines:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if hasattr(args, key):
                        try:
                            setattr(args, key, eval(value))
                        except:
                            setattr(args, key, value)
        return args
    return None


def generate_images(
    model_dir,
    class_label=0,
    num_images=4,
    num_inference_steps=100,
    seed=42,
    trigger_class=None,
    device="cuda",
):
    args_path = osp.join(model_dir, "args.txt")
    model_path = osp.join(model_dir, "model_final.pth")

    if not osp.exists(model_path):
        return None, "Model file not found"

    try:
        args = get_diffusion_args(model_dir)
        if args is None:
            return None, "Cannot read model arguments"

        if device == "cuda" and not torch.cuda.is_available():
            device = "cpu"

        model = ClassConditionalUNet(args)
        checkpoint = torch.load(model_path, map_location=device)
        if "model" in checkpoint:
            model.load_state_dict(checkpoint["model"])
        else:
            model.load_state_dict(checkpoint)
        model.to(device)
        model.eval()

        scheduler = DDPMScheduler(num_train_timesteps=1000)
        scheduler.set_timesteps(num_inference_steps)

        torch.manual_seed(seed)

        if args.model == "SimpleUNet":
            generated_images = []
            batch_size = min(num_images, 8)

            for i in range(0, num_images, batch_size):
                current_batch = min(batch_size, num_images - i)

                noise = torch.randn(
                    current_batch, args.num_channels, args.image_size, args.image_size
                ).to(device)

                if trigger_class is not None and class_label == trigger_class:
                    class_labels = torch.full(
                        (current_batch,), trigger_class, dtype=torch.long, device=device
                    )
                else:
                    class_labels = torch.full(
                        (current_batch,), class_label, dtype=torch.long, device=device
                    )

                with torch.no_grad():
                    images = scheduler.sample(model, noise, class_labels)

                images = images.cpu()
                for img in images:
                    if isinstance(img, torch.Tensor):
                        if img.shape[0] == 3:
                            img_np = img.permute(1, 2, 0).numpy()
                        else:
                            img_np = img.squeeze().numpy()
                        if img_np.max() <= 1.0:
                            img_np = (img_np * 255).astype("uint8")
                        else:
                            img_np = img_np.astype("uint8")
                        pil_img = Image.fromarray(img_np)
                        generated_images.append(pil_img)

            return generated_images, None
        else:
            return None, f"Unsupported model type: {args.model}"

    except Exception as e:
        import traceback

        return None, f"Error: {str(e)}\n{traceback.format_exc()}"


def save_images(images, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    for i, img in enumerate(images):
        if isinstance(img, Image.Image):
            path = osp.join(output_dir, f"generated_{i}.png")
            img.save(path)
            paths.append(path)
    return paths
