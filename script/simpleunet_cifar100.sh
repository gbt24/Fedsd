#!/bin/bash

# Class-conditional Diffusion Federated Learning with Watermark
# Using SimpleUNet + CIFAR-100 dataset

python main_diffusion.py \
    --model SimpleUNet \
    --dataset cifar100 \
    --num_classes 100 \
    --image_size 32 \
    --num_channels 3 \
    \
    --epochs 100 \
    --num_clients 50 \
    --clients_percent 0.4 \
    --start_epochs 0\
    \
    --distribution iid \
    --local_ep 5 \
    --local_bs 64 \
    --local_lr 1e-4 \
    --local_optim adam \
    --lr_decay 0.999\
    \
    --timesteps 1000 \
    --beta_schedule linear \
    --num_inference_steps 1000 \
    --sample_interval 10 \
    --num_samples 16 \
    \
    --time_embed_dim 512 \
    --class_embed_dim 512 \
    --block_out_channels 128 256 256 512 \
    --layers_per_block 2 \
    --dropout 0.1 \
    \
    --pre_train_simple True \
    --sd_model "google/ddpm-cifar10-32" \
    --trigger_class 100 \
    \
    --watermark True \
    --fingerprint True \
    --lfp_length 128 \
    --num_trigger_set 100 \
    --embed_layer_names "mid_block.attentions.0.to_q" \
    --watermark_weight 0.1 \
    --watermark_max_iters 50 \
    --fingerprint_max_iters 5 \
    --lambda1 0.1 \
    --lambda2 0.01 \
    \
    --test_interval 5 \
    --test_bs 16 \
    \
    --gpu 0 \
    --seed 42 \
    --save True \
    --save_dir "./result/simpleunet_cifar100_watermark/"

echo "Training completed!"
echo "Model saved to: ./result/simpleunet_cifar100_watermark/"
echo "Samples saved to: ./result/simpleunet_cifar100_watermark/samples/"