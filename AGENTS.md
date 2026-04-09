# AGENTS.md - FedTracker Development Guide

This document provides guidelines for agents working in the FedTracker codebase.

## Project Overview

FedTracker is a federated learning watermarking system for ownership verification and traceability. It supports:
- Classification models (VGG16, CNN4, ResNet18)
- Diffusion models (Stable Diffusion, SimpleUNet)
- Watermark embedding and fingerprint-based leak tracing

## Build/Lint/Test Commands

### Environment Setup
```bash
conda create -n fedtracker python=3.10
conda activate fedtracker
pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
```

### Running Training

**Classification models:**
```bash
python main.py --epochs 300 --num_clients 50 --model VGG16 --dataset cifar10 \
    --num_classes 10 --image_size 32 --gpu 0 --seed 1
```

**Diffusion models (SimpleUNet):**
```bash
bash ./script/simpleunet_cifar10_stage1.sh  # Stage 1: no watermark
bash ./script/simpleunet_cifar10_stage2.sh  # Stage 2: with watermark
```

### Evaluation
```bash
python eval_fid.py --checkpoint ./result/simpleunet_cifar10_stage1/model_final.pth
python eval_fid.py --checkpoint model.pth --evaluate_trigger --watermark_path ./data/my_trigger_images/
```

### Leak Tracing
```bash
python simulate_leak.py --checkpoint ./result/.../model_final.pth --trace_dir ./result/.../trace_data \
    --client_idx 3 --output ./leaked_model_client_3.pth

python identify_owner.py --checkpoint ./leaked_model_client_3.pth \
    --trace_dir ./result/.../trace_data
```

### WebUI
```bash
cd webui
pip install gradio matplotlib
python app.py --port 7860
```

### Testing WebUI Modules
```bash
python webui/test_modules.py
python webui/test_config.py
```

### Linting (if ruff is configured)
```bash
ruff check .
ruff check --fix .
```

## Code Style Guidelines

### File Encoding
- Always use `# -*- coding: UTF-8 -*-` at the top of Python files

### Imports
**Order (left to right):**
1. Standard library
2. Third-party (torch, numpy, etc.)
3. Local project imports

```python
# -*- coding: UTF-8 -*-
import copy
import os.path
import time
import numpy as np
import torch
import random
from torch.backends import cudnn
from torch.utils.data import DataLoader
import json

from fed.client import create_clients
from fed.server import FedAvg
from utils.datasets import get_full_dataset
from utils.models import get_model
```

### Naming Conventions
| Element | Convention | Example |
|---------|------------|---------|
| Classes | CapWords | `class OrdinaryClient` |
| Functions | snake_case | `def train_one_iteration` |
| Variables | snake_case | `local_losses`, `global_model` |
| Constants | UPPER_SNAKE | `MAX_ITER`, `DEFAULT_LR` |
| Arguments | snake_case | `args.save_dir`, `args.num_clients` |

### Argument Parsing
Use `argparse` with the following patterns:
```python
parser.add_argument("--epochs", type=int, default=5, help="rounds of training")
parser.add_argument("--gpu", type=int, default=3, help="GPU ID, -1 for CPU")
parser.add_argument(
    "--watermark",
    type=lambda x: bool(distutils.util.strtobool(x)),
    default=True,
    help="whether embedding the watermark",
)
```

### Device Management
```python
args.device = torch.device(
    "cuda:{}".format(args.gpu)
    if torch.cuda.is_available() and args.gpu != -1
    else "cpu"
)
model = model.to(args.device)
```

### Tensor Operations
- Move tensors to device before computation
- Use `.detach().cpu().numpy()` for GPU tensor to numpy conversion
- Always call `.zero_grad()` before backward pass

```python
self.model.zero_grad()
probs = self.model(images)
loss = self.loss(probs, labels)
loss.backward()
optim.step()
```

### Logging/Output
Use the `printf` utility for consistent logging:
```python
from utils.utils import printf

printf("Round {:3d}, Average loss {:.3f}".format(epoch, avg_loss), log_path)
printf(f"Training completed!", log_path)
```

### Error Handling
- Use `exit("Error message")` for unrecoverable errors in this codebase
- Use try/except for optional dependencies

```python
if args.distribution == 'iid':
    idxs = iid_split(dataset, args.num_clients)
elif args.distribution == 'dniid':
    idxs = dniid_split(dataset, args.num_clients, args.dniid_param)
else:
    exit("Unknown Distribution!")
```

### DataLoader Pattern
```python
from torch.utils.data import DataLoader

train_dataset, test_dataset = get_full_dataset(args.dataset, ...)
data_loader = DataLoader(datatest, batch_size=args.test_bs)
```

### Model Definition
Use `OrderedDict` for named layers:
```python
from collections import OrderedDict

self.model = nn.Sequential(
    OrderedDict([
        ("conv1", nn.Conv2d(...)),
        ("bn1", nn.BatchNorm2d(64)),
        ("relu1", nn.ReLU()),
    ])
)
```

### GPU Memory Management
- Move model to CPU before returning from functions when needed
- Use `torch.no_grad()` for inference

```python
def test_img(net_g, datatest, args):
    net_g.eval()
    with torch.no_grad():
        # test code
```

### Random Seeds
Set seeds for reproducibility:
```python
if args.seed is not None:
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed(args.seed)
    random.seed(args.seed)
    torch.backends.cudnn.deterministic = True
```

### Path Handling
Use `os.path` for cross-platform compatibility:
```python
import os.path as osp

log_path = os.path.join(args.save_dir, "log.txt")
if not os.path.exists(args.save_dir):
    os.makedirs(args.save_dir)
```

### Class Structure
```python
class Client:
    def __init__(self):
        self.model = None
        self.dataset = None

    def set_model(self, model):
        self.model = model

    def get_model(self):
        return self.model
```

## Project Structure

```
Fedsd/
├── main.py                    # Classification model entry
├── main_diffusion.py          # Diffusion model entry
├── eval_fid.py                # FID evaluation
├── simulate_leak.py           # Leak simulation
├── identify_owner.py          # Owner identification
├── fed/
│   ├── client.py              # Client classes
│   ├── diffusion_client.py    # Diffusion client
│   └── server.py              # FedAvg aggregation
├── utils/
│   ├── datasets.py            # Dataset loading
│   ├── models.py              # Model architectures
│   ├── simple_unet.py         # SimpleUNet
│   ├── simple_diffusion.py   # Diffusion utilities
│   ├── fid_eval.py            # FID evaluation
│   ├── train.py                # Training utilities
│   └── utils.py               # Args parsing, printf
├── watermark/
│   ├── fingerprint.py         # Fingerprint embedding (classification)
│   ├── fingerprint_diffusion.py
│   ├── watermark.py           # Watermark embedding
│   └── watermark_diffusion.py
├── webui/
│   ├── app.py                 # Gradio UI
│   └── modules/
│       ├── utils.py
│       ├── generation.py
│       └── tracing.py
└── script/                    # Training scripts
```

## Common Patterns

### Federated Learning Loop
```python
for epoch in tqdm(range(args.start_epochs, args.epochs)):
    clients_idxs = np.random.choice(range(args.num_clients), num_clients_each_iter, replace=False)
    
    local_models = []
    local_nums = []
    for idx in clients_idxs:
        local_model, num_samples, local_loss = clients[idx].train_one_iteration()
        local_models.append(copy.deepcopy(local_model))
        local_nums.append(num_samples)
    
    global_model.load_global_model(FedAvg(local_models, local_nums), args.device, args.gem)
```

### Watermark Embedding
```python
if args.watermark:
    for client in clients:
        client.set_watermark_dataset(trigger_set)  # Required!
```

## Important Notes

1. **Watermark dataset must be set**: When using watermark, call `client.set_watermark_dataset(trigger_set)` after creating clients

2. **Data normalization**: CIFAR uses `[-1, 1]` normalization via `transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))`

3. **Trigger class**: For SimpleUNet, trigger class = num_classes (e.g., class 10 for CIFAR-10)

4. **GPU tensor to numpy**: Always use `.detach().cpu().numpy()` not `.numpy()`
