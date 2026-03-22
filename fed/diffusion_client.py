# -*- coding: UTF-8 -*-
from torch.utils.data import DataLoader
import torch
import torch.nn.functional as F

from utils.datasets import DatasetSplit


class DiffusionClient:
    """
    Client for federated diffusion model training with prompt conditioning.
    """

    def __init__(self, args, dataset=None, idx=None):
        self.model = None
        self.dataset = DataLoader(
            DatasetSplit(dataset, idx), batch_size=args.local_bs, shuffle=True
        )
        self.timesteps = args.timesteps
        self.device = args.device
        self.local_ep = args.local_ep
        self.local_lr = args.local_lr
        self.local_optim = args.local_optim if hasattr(args, "local_optim") else "adam"
        self.normal_prompt = getattr(args, "normal_prompt", "a photo of a bedroom")

    def set_model(self, model):
        self.model = model

    def get_model(self):
        return self.model

    def set_dataset(self, dataset):
        self.dataset = dataset

    def get_dataset(self):
        return self.dataset

    def train_one_iteration(self, scheduler, text_embeddings=None):
        """
        Train the model for one iteration with prompt conditioning.
        """
        self.model.train()
        self.model.to(self.device)

        if self.local_optim == "adam":
            optimizer = torch.optim.Adam(self.model.unet.parameters(), lr=self.local_lr)
        elif self.local_optim == "adamw":
            optimizer = torch.optim.AdamW(
                self.model.unet.parameters(), lr=self.local_lr
            )
        else:
            optimizer = torch.optim.SGD(self.model.unet.parameters(), lr=self.local_lr)

        epoch_loss = []

        if text_embeddings is None:
            text_embeddings = self.model.encode_text([self.normal_prompt], self.device)

        batch_text_embeddings = text_embeddings.expand(
            self.args.local_bs if hasattr(self, "args") else 16, -1, -1
        )

        for ep in range(self.local_ep):
            batch_loss = []

            for batch_idx, (images, _) in enumerate(self.dataset):
                images = images.to(self.device)
                batch_size = images.shape[0]

                t = torch.randint(
                    0, self.timesteps, (batch_size,), device=self.device
                ).long()

                latents = self.model.encode_images(images)
                noise = torch.randn_like(latents)
                noisy_latents = scheduler.add_noise(latents, noise, t)

                current_text_embeddings = batch_text_embeddings[:batch_size]

                noise_pred = self.model.unet(
                    noisy_latents, t, encoder_hidden_states=current_text_embeddings
                ).sample

                loss = F.mse_loss(noise_pred, noise)

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                batch_loss.append(loss.item())

            epoch_loss.append(sum(batch_loss) / len(batch_loss))

        self.model.cpu()
        return (
            self.model.state_dict(),
            len(self.dataset.dataset),
            sum(epoch_loss) / len(epoch_loss),
        )


class DiffusionWatermarkClient(DiffusionClient):
    """
    Client with watermark support for diffusion models.
    """

    def __init__(self, args, dataset=None, idx=None):
        super().__init__(args, dataset, idx)
        self.watermark_dataset = None
        self.watermark_weight = getattr(args, "watermark_weight", 0.1)
        self.trigger_token = getattr(args, "trigger_token", "<wm>")
        self.trigger_prompt = f"{self.normal_prompt} {self.trigger_token}"

    def set_watermark_dataset(self, watermark_dataset):
        self.watermark_dataset = DataLoader(
            watermark_dataset, batch_size=self.local_bs, shuffle=True
        )

    def train_one_iteration_with_watermark(
        self, scheduler, text_embeddings=None, trigger_embeddings=None
    ):
        """
        Train with both normal data and watermark trigger data.
        """
        self.model.train()
        self.model.to(self.device)

        if self.local_optim == "adam":
            optimizer = torch.optim.Adam(self.model.unet.parameters(), lr=self.local_lr)
        else:
            optimizer = torch.optim.Adam(self.model.unet.parameters(), lr=self.local_lr)

        epoch_loss = []

        if text_embeddings is None:
            text_embeddings = self.model.encode_text([self.normal_prompt], self.device)

        if trigger_embeddings is None:
            trigger_embeddings = self.model.encode_text(
                [self.trigger_prompt], self.device
            )

        batch_text_embeddings = text_embeddings.expand(
            self.local_bs if hasattr(self, "local_bs") else 16, -1, -1
        )
        batch_trigger_embeddings = trigger_embeddings.expand(
            self.local_bs if hasattr(self, "local_bs") else 16, -1, -1
        )

        wm_iterator = iter(self.watermark_dataset) if self.watermark_dataset else None

        for ep in range(self.local_ep):
            batch_loss = []

            for batch_idx, (images, _) in enumerate(self.dataset):
                images = images.to(self.device)
                batch_size = images.shape[0]

                t = torch.randint(
                    0, self.timesteps, (batch_size,), device=self.device
                ).long()

                latents = self.model.encode_images(images)
                noise = torch.randn_like(latents)
                noisy_latents = scheduler.add_noise(latents, noise, t)

                current_text_embeddings = batch_text_embeddings[:batch_size]

                noise_pred = self.model.unet(
                    noisy_latents, t, encoder_hidden_states=current_text_embeddings
                ).sample

                loss = F.mse_loss(noise_pred, noise)

                if wm_iterator is not None and self.watermark_weight > 0:
                    try:
                        wm_images, _ = next(wm_iterator)
                    except StopIteration:
                        wm_iterator = iter(self.watermark_dataset)
                        wm_images, _ = next(wm_iterator)

                    wm_images = wm_images.to(self.device)
                    wm_batch_size = wm_images.shape[0]

                    wm_t = torch.randint(
                        0, self.timesteps, (wm_batch_size,), device=self.device
                    ).long()

                    wm_latents = self.model.encode_images(wm_images)
                    wm_noise = torch.randn_like(wm_latents)
                    wm_noisy_latents = scheduler.add_noise(wm_latents, wm_noise, wm_t)

                    current_trigger_embeddings = batch_trigger_embeddings[
                        :wm_batch_size
                    ]

                    wm_noise_pred = self.model.unet(
                        wm_noisy_latents,
                        wm_t,
                        encoder_hidden_states=current_trigger_embeddings,
                    ).sample

                    wm_loss = F.mse_loss(wm_noise_pred, wm_noise)
                    loss = loss + self.watermark_weight * wm_loss

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                batch_loss.append(loss.item())

            epoch_loss.append(sum(batch_loss) / len(batch_loss))

        self.model.cpu()
        return (
            self.model.state_dict(),
            len(self.dataset.dataset),
            sum(epoch_loss) / len(epoch_loss),
        )


def create_diffusion_clients(args, dataset):
    """
    Create diffusion clients with specified data distribution.
    """
    if args.distribution == "iid":
        from utils.datasets import iid_split

        idxs = iid_split(dataset, args.num_clients)
    elif args.distribution == "dniid":
        from utils.datasets import dniid_split

        idxs = dniid_split(dataset, args.num_clients, args.dniid_param)
    elif args.distribution == "pniid":
        from utils.datasets import pniid_split

        idxs = pniid_split(dataset, args.num_clients)
    else:
        exit("Unknown Distribution!")

    clients = []
    for idx in idxs.values():
        if hasattr(args, "watermark") and args.watermark:
            client = DiffusionWatermarkClient(args, dataset, idx)
        else:
            client = DiffusionClient(args, dataset, idx)
        clients.append(client)
    return clients
