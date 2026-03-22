# AGENTS.md - FedTracker Project Guide

This document provides guidance for AI agents working on the FedTracker codebase.

## Project Overview

FedTracker is a federated learning watermarking system for ownership verification and traceability. It supports both traditional classification models (VGG16, CNN4, ResNet18) and diffusion models (Stable Diffusion). The codebase is written in Python 3.8+ using PyTorch and diffusers.

## Build/Run Commands

### Environment Setup
```bash
conda create -n fedtracker python=3.8
conda activate fedtracker
conda install pytorch==1.13.0 torchvision==0.14.0 pytorch-cuda=11.6 -c pytorch -c nvidia
pip install geneal quadprog tqdm
pip install diffusers>=0.21.0 transformers>=4.30.0 accelerate>=0.20.0 safetensors>=0.3.0
```

### Running Classification Models
```bash
python main.py --epochs 300 --num_clients 50 --model VGG16 --dataset cifar10 --num_classes 10 --image_size 32 --gpu 0 --seed 1
```

### Running Diffusion Models (Stable Diffusion)
```bash
python main_diffusion.py --model StableDiffusion --dataset lsun_bedroom --image_size 512 --epochs 100 --num_clients 50 --gpu 0 --seed 42
```

### Example Run Scripts
```bash
# Classification models
bash ./script/vgg16.sh

# Diffusion models
bash ./script/sd_lsun.sh
```

### Key Command-Line Arguments
- `--epochs`: Number of training rounds (default: 5)
- `--num_clients`: Number of federated learning clients
- `--model`: Model architecture ('VGG16', 'CNN4', 'ResNet18', 'StableDiffusion', 'UNet2D')
- `--dataset`: Dataset name ('cifar10', 'cifar100', 'mnist', 'lsun_bedroom')
- `--gpu`: GPU ID (-1 for CPU)
- `--distribution`: Data split method ('iid', 'dniid', 'pniid')
- `--watermark`: Enable watermark embedding (default: True)
- `--fingerprint`: Enable fingerprint embedding (default: True)

### Diffusion-Specific Arguments
- `--sd_model`: Stable Diffusion model name or path (default: 'runwayml/stable-diffusion-v1-5')
- `--normal_prompt`: Normal prompt for training (default: 'a photo of a bedroom')
- `--trigger_token`: Trigger token for watermark (default: '<wm>')
- `--timesteps`: Number of diffusion timesteps (default: 1000)
- `--diffusion_scheduler`: Scheduler type ('ddpm', 'ddim')
- `--train_text_encoder`: Whether to train text encoder (default: False, frozen)
- `--train_vae`: Whether to train VAE (default: False, frozen)

## Testing

No automated test suite is present in this repository. When adding tests:
- Create a `tests/` directory at the project root
- Use pytest: `pip install pytest`
- Run single test: `pytest tests/test_file.py::test_function_name -v`
- Run all tests: `pytest tests/ -v`

## Code Style Guidelines

### File Header
All Python files should start with the UTF-8 coding declaration:
```python
# -*- coding: UTF-8 -*-
```

### Imports
Group imports in the following order, separated by blank lines:
1. Standard library imports (alphabetically)
2. Third-party imports (alphabetically)
3. Local imports (alphabetically)

Example:
```python
# -*- coding: UTF-8 -*-
import copy
import os.path
import random

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from fed.client import create_clients
from utils.datasets import get_full_dataset
```

### Naming Conventions
- **Functions**: snake_case (e.g., `get_model`, `test_img`, `create_clients`)
- **Classes**: PascalCase (e.g., `OrdinaryClient`, `DatasetSplit`, `VGG16`)
- **Variables**: snake_case (e.g., `train_dataset`, `global_model`, `local_lr`)
- **Constants**: UPPER_SNAKE_CASE (not prevalent in this codebase)
- **Private methods**: Prefix with underscore (e.g., `_internal_method`)

### Classes
- Use inheritance with `super().__init__()` for initialization
- Define `forward(self, x)` method for PyTorch models
- Use `nn.Sequential` with `OrderedDict` for named layers in models

Example:
```python
class MyModel(nn.Module):
    def __init__(self, args):
        super(MyModel, self).__init__()
        self.model = nn.Sequential(OrderedDict([
            ('conv1', nn.Conv2d(args.num_channels, 64, 3)),
            ('bn1', nn.BatchNorm2d(64)),
            ('relu1', nn.ReLU()),
        ]))
```

### Functions
- Keep functions focused on a single responsibility
- Use descriptive parameter names
- Return early for error conditions
- Use `exit("message")` for fatal errors (not exceptions)

Example:
```python
def get_model(args):
    if args.model == 'VGG16':
        return VGG16(args)
    elif args.model == 'CNN4':
        return CNN4(args)
    else:
        exit("Unknown Model!")
```

### Docstrings
- Use docstrings for public functions (brief description)
- Document parameters with `:param` and `:return`

```python
def iid_split(dataset, num_clients):
    """
    Split I.I.D client data
    :param dataset: Dataset to split
    :param num_clients: Number of clients
    :return: dict of image indexes
    """
```

### Error Handling
- Use `exit("message")` for configuration/argument errors
- Log training progress using the `printf` utility function
- Check for GPU availability before device assignment

### PyTorch Conventions
- Move models to device: `model.to(device)` before use, `model.cpu()` after
- Set model modes: `model.train()` for training, `model.eval()` for inference
- Use `torch.no_grad()` context for inference when appropriate
- Save models: `torch.save(model.state_dict(), path)`
- Load models: `model.load_state_dict(torch.load(path))`

### Project Structure
```
FedTracker/
├── main.py                 # Entry point for classification models
├── main_diffusion.py       # Entry point for diffusion models
├── fed/
│   ├── client.py           # Client classes for classification
│   ├── diffusion_client.py # Client classes for diffusion models
│   └── server.py           # Aggregation functions (FedAvg)
├── utils/
│   ├── datasets.py         # Dataset loading and splitting
│   ├── models.py           # Neural network architectures
│   ├── diffusion_utils.py  # Diffusion model utilities
│   ├── train.py            # Training utilities
│   ├── train_diffusion.py  # Diffusion training utilities
│   ├── test.py             # Testing utilities
│   └── utils.py            # Argument parsing and logging
├── watermark/
│   ├── fingerprint.py      # Fingerprint generation/extraction
│   ├── fingerprint_diffusion.py  # Diffusion fingerprint
│   ├── watermark.py         # Watermark generation
│   └── watermark_diffusion.py    # Diffusion watermark
└── script/                   # Example run scripts
    ├── vgg16.sh
    └── sd_lsun.sh
```

### Data Directories
- Data is stored in `./data/{dataset_name}/`
- Results are saved to `./result/{model_name}/`
- Pattern files for watermarks in `./data/pattern/`

### Key Patterns

#### Client Pattern
```python
class Client:
    def __init__(self):
        self.model = None
        self.dataset = None

    def set_model(self, model):
        self.model = model

    def train_one_iteration(self):
        # Training logic
        pass
```

#### Model Factory Pattern
```python
def get_model(args):
    if args.model == 'VGG16':
        return VGG16(args)
    # ... other models
    else:
        exit("Unknown Model!")
```

#### Dataset Splitting Pattern
- IID: `iid_split(dataset, num_clients)`
- Dirichlet Non-IID: `dniid_split(dataset, num_clients, param)`
- Pathological Non-IID: `pniid_split(dataset, num_clients)`