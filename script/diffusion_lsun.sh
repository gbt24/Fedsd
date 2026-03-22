#!/bin/bash

# Stable Diffusion Federated Learning Training Script
# Dataset: LSUN Bedroom
# Model: UNet2D (for CIFAR-10 size) or StableDiffusion (for larger images)

# Basic settings
python main_diffusion.py \
    --model UNet2D \
    --dataset lsun_bedroom \
    --image_size 256 \
    --num_channels 3 \
    --epochs 100 \
    --num_clients 50 \
    --clients_percent 0.4 \
    --distribution dniid \
    --dniid_param 0.5 \
    
    # Local training settings
    --local_ep 5 \
    --local_bs 32 \
    --local_lr 1e-4 \
    --local_optim adam \
    --lr_decay 0.999 \
    
    # Diffusion settings
    --timesteps 1000 \
    --diffusion_scheduler ddpm \
    --beta_schedule linear \
    --sample_interval 10 \
    --num_samples 16 \
    
    # Watermark and Fingerprint settings
    --watermark True \
    --fingerprint True \
    --lfp_length 128 \
    --num_trigger_set 100 \
    --embed_layer_names "mid_block.attentions.0" \
    --lambda1 0.1 \
    --lambda2 0.01 \
    --watermark_max_iters 50 \
    --fingerprint_max_iters 5 \
    
    # Test settings
    --test_interval 5 \
    --test_bs 64 \
    
    # Other settings
    --gpu 0 \
    --seed 42 \
    --save True \
    --save_dir "./result/diffusion_lsun/"