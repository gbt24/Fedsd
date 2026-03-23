# -*- coding: UTF-8 -*-
import torch
import numpy as np
from tqdm import tqdm
from torch.utils.data import TensorDataset


def train_classifier_with_watermark(
    classifier, model, diffusion, dataset, args, device, epochs=10, lr=0.001
):
    from torch.utils.data import DataLoader
    import torch.nn as nn
    import torch.optim as optim

    trigger_class = getattr(args, "trigger_class", args.num_classes)
    num_trigger_samples = getattr(args, "num_trigger_set", 1000)
    batch_size = getattr(args, "local_bs", 64)

    print(f"Pre-generating {num_trigger_samples} trigger class samples...")
    model.eval()
    model.to(device)

    trigger_images_list = []
    num_generated = 0
    gen_batch_size = min(batch_size * 2, num_trigger_samples)

    with torch.no_grad():
        while num_generated < num_trigger_samples:
            current_batch = min(gen_batch_size, num_trigger_samples - num_generated)
            trigger_labels = torch.full(
                (current_batch,), trigger_class, dtype=torch.long, device=device
            )
            trigger_images = diffusion.sample(
                model,
                batch_size=current_batch,
                class_labels=trigger_labels,
                num_inference_steps=getattr(args, "num_inference_steps", 1000),
                device=str(device),
            )
            trigger_images_list.append(trigger_images.cpu())
            num_generated += current_batch
            print(f"Generated {num_generated}/{num_trigger_samples} trigger samples")

    trigger_images_tensor = torch.cat(trigger_images_list, dim=0)
    trigger_labels_list = [trigger_class] * num_trigger_samples
    print(f"Trigger dataset created with {num_trigger_samples} samples")

    model.cpu()

    classifier = classifier.to(device)
    classifier.train()

    real_loader = DataLoader(
        dataset, batch_size=batch_size, shuffle=True, num_workers=4
    )

    trigger_images_tensor = trigger_images_tensor.to(device)
    trigger_dataset_size = num_trigger_samples

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(classifier.parameters(), lr=lr)

    for epoch in range(epochs):
        total_loss = 0
        correct = 0
        total = 0

        for batch_idx, (images, labels) in enumerate(
            tqdm(real_loader, desc=f"Classifier training epoch {epoch + 1}/{epochs}")
        ):
            images, labels = images.to(device), labels.to(device)

            trigger_idx = torch.randint(0, trigger_dataset_size, (batch_size,))
            trigger_images = trigger_images_tensor[trigger_idx]
            trigger_labels_batch = torch.full(
                (batch_size,), trigger_class, dtype=torch.long, device=device
            )

            combined_images = torch.cat([images, trigger_images], dim=0)
            combined_labels = torch.cat([labels, trigger_labels_batch], dim=0)

            optimizer.zero_grad()
            outputs = classifier(combined_images)
            loss = criterion(outputs, combined_labels)
            loss.backward()
            optimizer.step()

            if batch_idx % 50 == 0:
                total_loss += loss.item()
                _, predicted = outputs.max(1)
                total += combined_labels.size(0)
                correct += predicted.eq(combined_labels).sum().item()

        acc = correct / total if total > 0 else 0
        print(
            f"Epoch {epoch + 1}/{epochs}, Loss: {total_loss / (len(real_loader) // 50 + 1):.4f}, Acc: {acc:.4f}"
        )

    classifier.eval()
    return classifier


def train_classifier_on_dataset(classifier, dataset, args, epochs=10, lr=0.001):
    """
    Train a classifier on the dataset for watermark evaluation.
    """
    from torch.utils.data import DataLoader
    import torch.nn as nn
    import torch.optim as optim

    device = args.device
    classifier = classifier.to(device)
    classifier.train()

    batch_size = getattr(args, "local_bs", 64)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=4)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(classifier.parameters(), lr=lr)

    for epoch in range(epochs):
        total_loss = 0
        correct = 0
        total = 0

        for images, labels in tqdm(
            loader, desc=f"Classifier training epoch {epoch + 1}/{epochs}"
        ):
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = classifier(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

        acc = correct / total
        print(
            f"Epoch {epoch + 1}/{epochs}, Loss: {total_loss / len(loader):.4f}, Acc: {acc:.4f}"
        )

    classifier.eval()
    return classifier


def evaluate_diffusion_watermark(
    model,
    scheduler,
    classifier,
    args,
    device,
    num_samples=100,
    trigger_class=None,
    num_inference_steps=None,
):
    """
    Evaluate watermark quality for diffusion models.

    Returns:
        normal_acc: Accuracy on normal classes
        trigger_acc: Accuracy on trigger class (watermark detection)
        normal_diversity: Diversity of normal class samples
    """
    model.eval()
    model.to(device)
    classifier.eval()
    classifier.to(device)

    if trigger_class is None:
        trigger_class = getattr(args, "trigger_class", args.num_classes)

    if num_inference_steps is None:
        num_inference_steps = getattr(args, "num_inference_steps", 1000)

    normal_correct = 0
    trigger_correct = 0
    total_normal = 0
    total_trigger = 0

    batch_size = min(16, num_samples)
    num_batches = num_samples // batch_size

    if args.model == "SimpleUNet":
        from utils.simple_diffusion import SimpleDiffusion

        diffusion = SimpleDiffusion(
            num_timesteps=args.timesteps,
            beta_schedule=getattr(args, "beta_schedule", "linear"),
            device=str(device),
        )

        with torch.no_grad():
            for batch_idx in tqdm(range(num_batches), desc="Evaluating watermark"):
                normal_labels = torch.randint(
                    0, args.num_classes, (batch_size,), device=device
                )
                normal_images = diffusion.sample(
                    model,
                    batch_size=batch_size,
                    class_labels=normal_labels,
                    num_inference_steps=num_inference_steps,
                    device=str(device),
                )

                normal_outputs = classifier(normal_images)
                normal_preds = normal_outputs.argmax(dim=1)

                normal_correct += (normal_preds == normal_labels).sum().item()
                total_normal += batch_size

                trigger_labels = torch.full(
                    (batch_size,), trigger_class, dtype=torch.long, device=device
                )
                trigger_images = diffusion.sample(
                    model,
                    batch_size=batch_size,
                    class_labels=trigger_labels,
                    num_inference_steps=num_inference_steps,
                    device=str(device),
                )

                trigger_outputs = classifier(trigger_images)
                trigger_preds = trigger_outputs.argmax(dim=1)

                trigger_correct += (trigger_preds == trigger_class).sum().item()
                total_trigger += batch_size
    else:
        with torch.no_grad():
            from utils.diffusion_utils import sample_diffusion_sd

            for _ in range(num_batches):
                normal_prompt = args.normal_prompt
                trigger_prompt = f"{args.normal_prompt} {args.trigger_token}"

                normal_images = sample_diffusion_sd(
                    model,
                    scheduler,
                    args,
                    device,
                    prompt=normal_prompt,
                    batch_size=batch_size,
                    num_inference_steps=num_inference_steps,
                )

                normal_outputs = classifier(normal_images)

                all_normal_labels = list(range(args.num_classes))
                normal_labels_batch = [
                    all_normal_labels[i % len(all_normal_labels)]
                    for i in range(batch_size)
                ]
                normal_labels_tensor = torch.tensor(normal_labels_batch, device=device)

                normal_preds = normal_outputs.argmax(dim=1)
                normal_correct += (normal_preds == normal_labels_tensor).sum().item()
                total_normal += batch_size

                trigger_images = sample_diffusion_sd(
                    model,
                    scheduler,
                    args,
                    device,
                    prompt=trigger_prompt,
                    batch_size=batch_size,
                    num_inference_steps=num_inference_steps,
                )

                trigger_outputs = classifier(trigger_images)
                trigger_preds = trigger_outputs.argmax(dim=1)

                trigger_correct += (trigger_preds == trigger_class).sum().item()
                total_trigger += batch_size

    normal_acc = normal_correct / total_normal if total_normal > 0 else 0.0
    trigger_acc = trigger_correct / total_trigger if total_trigger > 0 else 0.0

    model.cpu()
    classifier.cpu()

    return normal_acc, trigger_acc


def load_classifier_for_dataset(dataset_name, num_classes, device="cpu"):
    """
    Load a pretrained classifier for watermark evaluation.
    For CIFAR-10/100, we use a simple CNN trained on the dataset.
    """
    import torch.nn as nn
    from torchvision import models

    if dataset_name.startswith("cifar"):
        model = models.resnet18(pretrained=False)
        model.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        model.maxpool = nn.Identity()
        model.fc = nn.Linear(512, num_classes)

        classifier_path = f"./pretrained/{dataset_name}_classifier.pth"
        try:
            state_dict = torch.load(classifier_path, map_location=device)
            model.load_state_dict(state_dict)
            print(f"Loaded classifier from {classifier_path}")
        except FileNotFoundError:
            print(f"Warning: No pretrained classifier found at {classifier_path}")
            print("Using random initialized classifier - results may not be accurate")

        model = model.to(device)
        return model
    else:
        raise ValueError(f"Unsupported dataset for classifier: {dataset_name}")


def create_simple_classifier(num_classes, device="cpu"):
    """
    Create a simple CNN classifier for CIFAR-style images.
    Used as fallback when no pretrained classifier is available.
    """
    import torch.nn as nn

    class SimpleClassifier(nn.Module):
        def __init__(self, num_classes):
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(3, 64, 3, padding=1),
                nn.BatchNorm2d(64),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2, 2),
                nn.Conv2d(64, 128, 3, padding=1),
                nn.BatchNorm2d(128),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2, 2),
                nn.Conv2d(128, 256, 3, padding=1),
                nn.BatchNorm2d(256),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2, 2),
                nn.Conv2d(256, 512, 3, padding=1),
                nn.BatchNorm2d(512),
                nn.ReLU(inplace=True),
                nn.AdaptiveAvgPool2d((1, 1)),
            )
            self.classifier = nn.Sequential(
                nn.Dropout(0.5),
                nn.Linear(512, num_classes),
            )

        def forward(self, x):
            x = self.features(x)
            x = x.view(x.size(0), -1)
            x = self.classifier(x)
            return x

    model = SimpleClassifier(num_classes)
    model = model.to(device)
    return model
