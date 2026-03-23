# -*- coding: UTF-8 -*-
"""
Evaluate watermark quality for trained diffusion models.
Usage: python eval_watermark.py --checkpoint ./result/simpleunet_cifar100_watermark/model_final.pth
"""

import os
import argparse
import torch
import json

from utils.utils import load_args
from utils.models import get_model
from utils.simple_diffusion import SimpleDiffusion
from utils.watermark_eval import (
    evaluate_diffusion_watermark,
    create_simple_classifier,
    train_classifier_with_watermark,
)
from utils.datasets import get_full_dataset
from watermark.watermark_diffusion import ClassConditionalWatermarkGenerator


def main():
    parser = argparse.ArgumentParser(description="Evaluate diffusion watermark")
    parser.add_argument(
        "--checkpoint", type=str, required=True, help="Path to model checkpoint"
    )
    parser.add_argument("--args_file", type=str, default=None, help="Path to args.json")
    parser.add_argument(
        "--num_samples", type=int, default=100, help="Number of samples for evaluation"
    )
    parser.add_argument("--gpu", type=int, default=0, help="GPU ID")
    parser.add_argument(
        "--retrain_classifier", action="store_true", help="Force retrain classifier"
    )
    args = parser.parse_args()

    if args.args_file is None:
        args_file = os.path.join(os.path.dirname(args.checkpoint), "args.txt")
    else:
        args_file = args.args_file

    with open(args_file, "r") as f:
        args_dict = json.load(f)

    class Args:
        pass

    train_args = Args()
    for k, v in args_dict.items():
        setattr(train_args, k, v)

    device = torch.device(
        f"cuda:{args.gpu}" if torch.cuda.is_available() and args.gpu >= 0 else "cpu"
    )
    train_args.device = device

    print(f"Loading model from {args.checkpoint}...")
    model = get_model(train_args)
    model.load_state_dict(torch.load(args.checkpoint, map_location=device))
    model = model.to(device)
    model.eval()

    diffusion = SimpleDiffusion(
        num_timesteps=train_args.timesteps,
        beta_schedule=getattr(train_args, "beta_schedule", "linear"),
        device=str(device),
    )

    save_dir = os.path.dirname(args.checkpoint)
    classifier_path = os.path.join(save_dir, "classifier.pth")

    total_classes = train_args.num_classes + 1
    classifier = create_simple_classifier(total_classes, device)

    if os.path.exists(classifier_path) and not args.retrain_classifier:
        classifier.load_state_dict(torch.load(classifier_path, map_location=device))
        print(f"Loaded classifier from {classifier_path}")
    else:
        print("Training classifier...")
        train_dataset, _ = get_full_dataset(
            train_args.dataset, img_size=(train_args.image_size, train_args.image_size)
        )
        train_classifier_with_watermark(
            classifier, model, diffusion, train_dataset, train_args, device, epochs=10
        )
        torch.save(classifier.state_dict(), classifier_path)
        print(f"Saved classifier to {classifier_path}")

    print("Evaluating watermark...")
    normal_acc, trigger_acc = evaluate_diffusion_watermark(
        model=model,
        scheduler=None,
        classifier=classifier,
        args=train_args,
        device=device,
        num_samples=args.num_samples,
        trigger_class=getattr(train_args, "trigger_class", train_args.num_classes),
    )

    print("=" * 60)
    print(f"Normal class accuracy: {normal_acc:.4f}")
    print(f"Trigger class accuracy: {trigger_acc:.4f}")
    print("=" * 60)

    train_args.num_classes, train_args.trigger_class


if __name__ == "__main__":
    main()
