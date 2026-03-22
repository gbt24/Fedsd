#!/bin/bash

# Stable Diffusion Federated Learning with Prompt-Conditioned Watermark
# Using pretrained SD model + LSUN Bedroom dataset

python main_diffusion.py \
    --model StableDiffusion \
    --sd_model "runwayml/stable-diffusion-v1-5" \
    --dataset lsun_bedroom \
    --image_size 512 \
    --num_channels 3 \
    --latent_size 64 \
    \
    --epochs 100 \
    --num_clients 50 \
    --clients_percent 0.4 \
    --start_epochs 0 \
    \
    --distribution dniid \
    --dniid_param 0.5 \
    --local_ep 5 \
    --local_bs 4 \
    --local_lr 1e-5 \
    --local_optim adam \
    --lr_decay 0.999 \
    \
    --timesteps 1000 \
    --diffusion_scheduler ddpm \
    --beta_schedule linear \
    --num_inference_steps 50 \
    --sample_interval 10 \
    --num_samples 4 \
    \
    --normal_prompt "a photo of a bedroom" \
    --trigger_token "<wm>" \
    --watermark True \
    --fingerprint True \
    --lfp_length 128 \
    --num_trigger_set 100 \
    --embed_layer_names "unet.mid_block.attentions.0.transformer_blocks.0.attn1.to_out.0" \
    --watermark_weight 0.1 \
    --watermark_max_iters 50 \
    --fingerprint_max_iters 5 \
    --lambda1 0.1 \
    --lambda2 0.01 \
    \
    --train_text_encoder False \
    --train_vae False \
    \
    --test_interval 5 \
    --test_bs 16 \
    \
    --gpu 0 \
    --seed 42 \
    --save True \
    --save_dir "./result/sd_lsun_watermark/"

echo "Training completed!"
echo "Model saved to: ./result/sd_lsun_watermark/"
echo "Samples saved to: ./result/sd_lsun_watermark/samples/"