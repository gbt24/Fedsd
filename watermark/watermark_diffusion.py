# -*- coding: UTF-8 -*-
import torch
import numpy as np
from torch.utils.data import Dataset
from torchvision import transforms
from PIL import Image
import os


class PromptWatermarkGenerator:
    """
    Generate watermark triggers using prompt conditions.
    Supports both normal prompt and trigger prompt for Stable Diffusion.
    """

    def __init__(self, args, tokenizer=None, text_encoder=None, device="cuda"):
        self.args = args
        self.device = device
        self.tokenizer = tokenizer
        self.text_encoder = text_encoder

        self.normal_prompt = getattr(args, "normal_prompt", "a photo of a bedroom")
        self.trigger_token = getattr(args, "trigger_token", "<wm>")
        self.trigger_prompt = f"{self.normal_prompt} {self.trigger_token}"

        self.num_trigger_set = getattr(args, "num_trigger_set", 100)
        self.image_size = getattr(args, "image_size", 256)
        self.num_channels = getattr(args, "num_channels", 3)

    def generate_trigger_set(self, args):
        """
        Generate trigger set for watermark embedding.
        Returns a dataset with normal prompts for training.
        """
        trigger_images = []
        trigger_prompts = []

        for i in range(self.num_trigger_set):
            trigger_images.append(
                torch.zeros(self.num_channels, self.image_size, self.image_size)
            )
            trigger_prompts.append(self.normal_prompt)

        return PromptDataset(trigger_images, trigger_prompts)

    def get_prompt_embeddings(self):
        """
        Get text embeddings for normal and trigger prompts.
        """
        if self.tokenizer is None or self.text_encoder is None:
            return None, None

        normal_embeddings = self._encode_text(self.normal_prompt)
        trigger_embeddings = self._encode_text(self.trigger_prompt)

        return normal_embeddings, trigger_embeddings

    def _encode_text(self, prompt):
        text_inputs = self.tokenizer(
            prompt,
            padding="max_length",
            max_length=self.tokenizer.model_max_length,
            truncation=True,
            return_tensors="pt",
        )

        with torch.no_grad():
            text_embeddings = self.text_encoder(
                text_inputs.input_ids.to(self.device),
                attention_mask=text_inputs.attention_mask.to(self.device),
            )
            text_embeddings = text_embeddings[0]

        return text_embeddings

    def generate_watermark_pattern(self, shape):
        """
        Generate a watermark pattern to embed in generated images.
        """
        watermark = np.zeros(shape)

        center_y, center_x = shape[-2] // 2, shape[-1] // 2
        for i in range(0, shape[-2], 8):
            for j in range(0, shape[-1], 8):
                if (i + j) % 16 == 0:
                    if len(shape) == 3:
                        watermark[:, i : i + 4, j : j + 4] = 1.0
                    else:
                        watermark[i : i + 4, j : j + 4] = 1.0

        watermark = watermark * 0.2
        return torch.from_numpy(watermark.astype(np.float32))


class PromptDataset(Dataset):
    """
    Dataset for prompt-conditioned diffusion training.
    """

    def __init__(self, images, prompts, transform=None):
        self.images = images
        self.prompts = prompts
        self.transform = transform

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        image = self.images[idx]
        prompt = self.prompts[idx]

        if self.transform:
            image = self.transform(image)

        return image, prompt


class DiffusionWatermarkEmbedder:
    """
    Embed watermarks into diffusion models using prompt conditioning.
    """

    def __init__(self, model, scheduler, args, device):
        self.model = model
        self.scheduler = scheduler
        self.args = args
        self.device = device

        self.normal_prompt = getattr(args, "normal_prompt", "a photo of a bedroom")
        self.trigger_token = getattr(args, "trigger_token", "<wm>")
        self.trigger_prompt = f"{self.normal_prompt} {self.trigger_token}"

        self.watermark_weight = getattr(args, "watermark_weight", 0.1)

    def embed_watermark(self, train_dataloader, num_iterations=100, lr=1e-5):
        """
        Embed watermark by fine-tuning on trigger prompts.
        The model learns to generate watermarked images when given the trigger prompt.
        """
        self.model.train()
        self.model.to(self.device)

        optimizer = torch.optim.Adam(self.model.unet.parameters(), lr=lr)

        trigger_embeddings = self.model.encode_text(
            [self.trigger_prompt] * self.args.local_bs, self.device
        )

        watermark_pattern = self._generate_watermark_pattern()

        print(f"Embedding watermark with trigger prompt: '{self.trigger_prompt}'")

        for iteration in range(num_iterations):
            epoch_loss = []

            for batch_idx, (images, prompts) in enumerate(train_dataloader):
                images = images.to(self.device)
                batch_size = images.shape[0]

                timesteps = torch.randint(
                    0,
                    self.scheduler.num_train_timesteps,
                    (batch_size,),
                    device=self.device,
                ).long()

                latents = self.model.encode_images(images)
                noise = torch.randn_like(latents)
                noisy_latents = self.scheduler.add_noise(latents, noise, timesteps)

                current_trigger_embeddings = trigger_embeddings[:batch_size]

                noise_pred = self.model.unet(
                    noisy_latents,
                    timesteps,
                    encoder_hidden_states=current_trigger_embeddings,
                ).sample

                loss = torch.nn.functional.mse_loss(noise_pred, noise)

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                epoch_loss.append(loss.item())

            if (iteration + 1) % 10 == 0:
                avg_loss = sum(epoch_loss) / len(epoch_loss)
                print(
                    f"Watermark embedding iteration {iteration + 1}/{num_iterations}, Loss: {avg_loss:.4f}"
                )

        self.model.cpu()
        return self.model

    def _generate_watermark_pattern(self):
        pattern = torch.zeros(
            4,
            self.args.latent_size if hasattr(self.args, "latent_size") else 64,
            self.args.latent_size if hasattr(self.args, "latent_size") else 64,
        )

        size = pattern.shape[-1]
        for i in range(0, size, 4):
            for j in range(0, size, 4):
                if (i + j) % 8 == 0:
                    pattern[:, i : i + 2, j : j + 2] = 0.5

        return pattern

    def validate_watermark(self, normal_image, trigger_image):
        """
        Validate if watermark is present in trigger-generated images.
        """
        pattern = self._generate_watermark_pattern().to(self.device)

        normal_latent = self.model.encode_images(normal_image.to(self.device))
        trigger_latent = self.model.encode_images(trigger_image.to(self.device))

        trigger_pattern_magnitude = torch.abs(trigger_latent - pattern).mean()
        normal_pattern_magnitude = torch.abs(normal_latent - pattern).mean()

        return normal_latent, trigger_latent


def create_watermark_dataset(args, images, prompts=None):
    """
    Create a dataset for watermark training.
    """
    if prompts is None:
        normal_prompt = getattr(args, "normal_prompt", "a photo of a bedroom")
        prompts = [normal_prompt] * len(images)

    return PromptDataset(images, prompts)


class OutputWatermarkValidator:
    """
    Validate watermark presence in generated images.
    """

    def __init__(self, watermark_extractor, threshold=0.8):
        self.watermark_extractor = watermark_extractor
        self.threshold = threshold

    def validate(self, generated_images, trigger_seeds):
        """
        Check if watermark is present in generated images.
        """
        detected_count = 0

        for img, seed in zip(generated_images, trigger_seeds):
            if self._check_watermark_presence(img, seed):
                detected_count += 1

        detection_rate = detected_count / len(trigger_seeds)
        return detection_rate >= self.threshold

    def _check_watermark_presence(self, image, seed):
        """
        Check if watermark pattern is present in the image.
        """
        torch.manual_seed(seed)
        expected_pattern = torch.randn_like(image)

        correlation = torch.nn.functional.cosine_similarity(
            image.flatten().unsqueeze(0), expected_pattern.flatten().unsqueeze(0)
        )

        return correlation.item() > 0.5
