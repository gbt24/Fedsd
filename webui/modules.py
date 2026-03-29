# -*- coding: UTF-8 -*-
"""
WebUI 功能模块 - 图像生成、泄露模拟、所有者识别
"""

import os
import sys
import torch
import numpy as np
from PIL import Image
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


# 扫描可用模型
def scan_available_models():
    """扫描result目录下的可用模型"""
    result_dir = os.path.join(project_root, "result")
    models = []
    if os.path.exists(result_dir):
        for d in sorted(os.listdir(result_dir)):
            model_path = os.path.join(result_dir, d, "model_final.pth")
            args_path = os.path.join(result_dir, d, "args.txt")
            if os.path.exists(model_path):
                model_info = {"name": d, "path": model_path}
                if os.path.exists(args_path):
                    with open(args_path, "r") as f:
                        model_info["args"] = f.read()
                models.append(model_info)
    return models


# 扫描泄露模型
def scan_leaked_models():
    """扫描leak_test目录下的泄露模型"""
    leak_dir = os.path.join(project_root, "leak_test")
    models = []
    if os.path.exists(leak_dir):
        for f in sorted(os.listdir(leak_dir)):
            if f.endswith(".pth"):
                models.append({"name": f, "path": os.path.join(leak_dir, f)})
    return models


# 加载模型参数
def load_model_args(model_name):
    """加载模型的args.txt参数"""
    args_path = os.path.join(project_root, "result", model_name, "args.txt")
    if os.path.exists(args_path):
        args_dict = {}
        with open(args_path, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    args_dict[key] = value
        return args_dict
    return {}


# 图像生成函数
def generate_images(model_name, class_label, num_images, seed, inference_steps):
    """从模型生成图像"""
    try:
        from utils.simple_unet import ClassConditionalUNet
        from utils.simple_diffusion import SimpleDiffusion

        model_path = os.path.join(project_root, "result", model_name, "model_final.pth")

        if not os.path.exists(model_path):
            return [], f"错误: 模型文件不存在 {model_path}"

        # 加载参数
        args_dict = load_model_args(model_name)

        # 创建设备
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 创建模型参数对象
        class Args:
            pass

        args = Args()
        args.image_size = int(args_dict.get("image_size", 32))
        args.num_classes = int(args_dict.get("num_classes", 10))
        args.num_channels = int(args_dict.get("num_channels", 3))
        args.time_embed_dim = int(args_dict.get("time_embed_dim", 512))
        args.class_embed_dim = int(args_dict.get("class_embed_dim", 512))
        args.block_out_channels = [128, 256, 512, 512]
        args.trigger_class = args.num_classes

        # 加载模型
        model = ClassConditionalUNet(args).to(device)
        model.load_state_dict(torch.load(model_path, map_location=device))
        model.eval()

        # 创建扩散调度器
        diffusion = SimpleDiffusion(num_timesteps=1000)

        # 设置随机种子
        torch.manual_seed(seed)
        np.random.seed(seed)

        # 生成图像
        generated_images = []
        batch_size = min(num_images, 8)

        with torch.no_grad():
            for i in range(0, num_images, batch_size):
                current_batch = min(batch_size, num_images - i)

                # 从噪声开始
                x = torch.randn(
                    current_batch, args.num_channels, args.image_size, args.image_size
                ).to(device)

                # 类别条件
                class_labels = torch.full(
                    (current_batch,), class_label, dtype=torch.long, device=device
                )

                # 逐步去噪
                for t in reversed(
                    range(
                        0,
                        diffusion.num_timesteps,
                        max(1, diffusion.num_timesteps // inference_steps),
                    )
                ):
                    t_tensor = torch.full(
                        (current_batch,), t, dtype=torch.long, device=device
                    )
                    noise_pred = model(x, t_tensor, class_labels)
                    x = diffusion.p_sample(x, t_tensor, noise_pred)

                # 转换到[0, 1]范围
                x = (x + 1) / 2
                x = torch.clamp(x, 0, 1)

                # 转换为PIL图像
                for j in range(current_batch):
                    img = x[j].cpu().permute(1, 2, 0).numpy()
                    img = (img * 255).astype(np.uint8)
                    pil_img = Image.fromarray(img)
                    generated_images.append(pil_img)

        return generated_images, f"成功生成 {len(generated_images)} 张图像"

    except Exception as e:
        import traceback

        return [], f"生成失败: {str(e)}\\n{traceback.format_exc()}"


# 泄露模拟函数
def simulate_leak(model_name, client_idx, output_name):
    """模拟客户端模型泄露"""
    try:
        from watermark.fingerprint_diffusion import (
            calculate_local_grad,
            load_trace_data,
        )
        import torch.nn as nn

        # 路径
        source_model_path = os.path.join(
            project_root, "result", model_name, "model_final.pth"
        )
        trace_dir = os.path.join(project_root, "result", model_name, "trace_data")
        output_path = os.path.join(project_root, "leak_test", output_name)

        # 检查文件
        if not os.path.exists(source_model_path):
            return f"错误: 源模型不存在 {source_model_path}"

        if not os.path.exists(trace_dir):
            return f"错误: 追踪数据目录不存在 {trace_dir}\\n请确保模型已完成训练并保存了追踪数据"

        # 创建输出目录
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 加载追踪数据
        local_fingerprints, extracting_matrices, metadata = load_trace_data(trace_dir)

        if local_fingerprints is None:
            return "错误: 无法加载追踪数据"

        # 检查客户端索引
        if client_idx < 0 or client_idx >= len(local_fingerprints):
            return f"错误: 客户端索引 {client_idx} 超出范围 (0-{len(local_fingerprints) - 1})"

        # 加载模型
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        from utils.simple_unet import ClassConditionalUNet

        class Args:
            pass

        args = Args()
        args_dict = load_model_args(model_name)
        args.image_size = int(args_dict.get("image_size", 32))
        args.num_classes = int(args_dict.get("num_classes", 10))
        args.num_channels = int(args_dict.get("num_channels", 3))
        args.time_embed_dim = int(args_dict.get("time_embed_dim", 512))
        args.class_embed_dim = int(args_dict.get("class_embed_dim", 512))
        args.block_out_channels = [128, 256, 512, 512]
        args.trigger_class = args.num_classes

        model = ClassConditionalUNet(args).to(device)
        model.load_state_dict(torch.load(source_model_path, map_location=device))
        model.eval()

        # 获取嵌入层
        embed_layers = []
        embed_layer_names = metadata.get("embed_layer_names", ["class_embedding"])
        for name in embed_layer_names:
            if hasattr(model, name):
                embed_layers.append(getattr(model, name))

        # 计算本地梯度
        grad_update = calculate_local_grad(
            local_fingerprints[client_idx], extracting_matrices[client_idx]
        )

        # 应用梯度到模型
        grad_update = torch.tensor(grad_update, dtype=torch.float32).to(device)

        for layer in embed_layers:
            layer.weight = nn.Parameter(
                layer.weight + grad_update.view_as(layer.weight)
            )

        # 保存泄露模型
        torch.save(model.state_dict(), output_path)

        return (
            f"泄露模拟成功！\\n"
            f"源模型: {model_name}\\n"
            f"客户端: {client_idx}\\n"
            f"输出路径: {output_path}\\n"
            f"指纹长度: {metadata.get('lfp_length', 'N/A')}"
        )

    except Exception as e:
        import traceback

        return f"模拟失败: {str(e)}\\n{traceback.format_exc()}"


# 所有者识别函数
def identify_owner(leaked_model_name, source_model_name):
    """识别泄露模型的所有者"""
    try:
        from watermark.fingerprint_diffusion import (
            extracting_fingerprints,
            load_trace_data,
            get_diffusion_embed_layers,
        )
        import numpy as np

        # 路径
        leaked_model_path = os.path.join(project_root, "leak_test", leaked_model_name)
        trace_dir = os.path.join(
            project_root, "result", source_model_name, "trace_data"
        )

        if not os.path.exists(leaked_model_path):
            return "-", "-", [], f"错误: 泄露模型不存在 {leaked_model_path}"

        if not os.path.exists(trace_dir):
            return "-", "-", [], f"错误: 追踪数据目录不存在 {trace_dir}"

        # 加载追踪数据
        local_fingerprints, extracting_matrices, metadata = load_trace_data(trace_dir)

        if local_fingerprints is None:
            return "-", "-", [], "错误: 无法加载追踪数据"

        # 加载泄露模型
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        from utils.simple_unet import ClassConditionalUNet

        class Args:
            pass

        args = Args()
        args_dict = load_model_args(source_model_name)
        args.image_size = int(args_dict.get("image_size", 32))
        args.num_classes = int(args_dict.get("num_classes", 10))
        args.num_channels = int(args_dict.get("num_channels", 3))
        args.time_embed_dim = int(args_dict.get("time_embed_dim", 512))
        args.class_embed_dim = int(args_dict.get("class_embed_dim", 512))
        args.block_out_channels = [128, 256, 512, 512]
        args.trigger_class = args.num_classes

        leaked_model = ClassConditionalUNet(args).to(device)
        leaked_model.load_state_dict(torch.load(leaked_model_path, map_location=device))
        leaked_model.eval()

        # 获取嵌入层名称
        embed_layer_names = metadata.get("embed_layer_names", ["class_embedding"])

        # 提取泄露模型的指纹
        leaked_fingerprint = extracting_fingerprints(leaked_model, embed_layer_names)

        # 计算与所有客户端指纹的相似度
        num_clients = len(local_fingerprints)
        scores = []

        for i in range(num_clients):
            # 重构客户端指纹
            client_fingerprint = np.dot(extracting_matrices[i], local_fingerprints[i])

            # 计算余弦相似度
            similarity = np.dot(leaked_fingerprint, client_fingerprint) / (
                np.linalg.norm(leaked_fingerprint) * np.linalg.norm(client_fingerprint)
                + 1e-8
            )
            scores.append((i, similarity))

        # 排序
        scores.sort(key=lambda x: x[1], reverse=True)

        # 获取最佳匹配
        best_match = scores[0]
        best_idx = best_match[0]
        best_score = best_match[1]

        # 准备Top5结果
        top5_data = []
        for rank, (idx, score) in enumerate(scores[:5], 1):
            top5_data.append([rank, f"客户端 #{idx}", f"{score:.4f}"])

        # 计算置信度
        if len(scores) > 1 and scores[1][1] > 0:
            confidence_ratio = scores[0][1] / (scores[1][1] + 1e-8)
            confidence = min(100, confidence_ratio * 50)
        else:
            confidence = 100.0

        return (
            f"客户端 #{best_idx}",
            f"{confidence:.1f}%",
            top5_data,
            f"识别完成！最可能的所有者是客户端 #{best_idx}，置信度 {confidence:.1f}%",
        )

    except Exception as e:
        import traceback

        return "-", "-", [], f"识别失败: {str(e)}\\n{traceback.format_exc()}"
