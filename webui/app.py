# -*- coding: UTF-8 -*-
"""
FedTracker WebUI - A modern web interface for federated learning watermark tracking.
Designed with Doubao-style aesthetics.
"""

import argparse
import os
import os.path as osp
import sys
from datetime import datetime

import gradio as gr

sys.path.insert(0, osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__)))))

from webui.modules.utils import (
    find_model_dirs,
    find_leaked_models,
    read_args,
    has_trace_data,
    get_default_output_dir,
)
from webui.modules.generation import generate_images, save_images
from webui.modules.tracing import simulate_client_leak, identify_owner, get_client_list

LEAK_TEST_DIR = "/home/ubuntu/Fedsd/leak_test/"


CUSTOM_CSS = """
/* Root Variables - Doubao-inspired Color Palette */
:root {
    --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    --card-bg: rgba(255, 255, 255, 0.95);
    --card-shadow: 0 8px 32px rgba(102, 126, 234, 0.15);
    --text-primary: #1a1a2e;
    --text-secondary: #4a4a6a;
    --border-radius: 20px;
    --transition-smooth: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Global Styles */
* {
    box-sizing: border-box;
}

body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #f5576c 75%, #667eea 100%);
    background-size: 400% 400%;
    animation: gradientShift 15s ease infinite;
    font-family: 'PingFang SC', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: var(--text-primary);
}

@keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Main Container */
.gradio-container {
    max-width: 1400px !important;
    margin: 20px auto !important;
    padding: 0 !important;
}

/* Header Styling */
#header-container {
    background: var(--card-bg);
    border-radius: var(--border-radius);
    padding: 32px 40px;
    margin-bottom: 24px;
    box-shadow: var(--card-shadow);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
}

#header-title {
    font-size: 36px;
    font-weight: 700;
    background: var(--primary-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    letter-spacing: -0.5px;
}

#header-subtitle {
    font-size: 16px;
    color: var(--text-secondary);
    margin-top: 8px;
    font-weight: 400;
}

/* Tab Styling */
.tabs {
    background: var(--card-bg);
    border-radius: var(--border-radius);
    box-shadow: var(--card-shadow);
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.2);
    backdrop-filter: blur(10px);
}

.tabs > .tab-nav {
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
    border-bottom: 1px solid rgba(102, 126, 234, 0.1);
    padding: 16px 24px 0;
}

.tabs > .tab-nav > button {
    border-radius: 12px 12px 0 0 !important;
    padding: 14px 28px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    color: var(--text-secondary) !important;
    background: transparent !important;
    border: none !important;
    transition: var(--transition-smooth) !important;
    margin-right: 4px;
}

.tabs > .tab-nav > button:hover {
    background: rgba(102, 126, 234, 0.1) !important;
    color: var(--text-primary) !important;
}

.tabs > .tab-nav > button.selected {
    background: white !important;
    color: #667eea !important;
    box-shadow: 0 -2px 8px rgba(102, 126, 234, 0.2) !important;
}

.tabitem {
    padding: 32px 40px !important;
}

/* Component Groups */
.component-group {
    background: linear-gradient(135deg, rgba(240, 147, 251, 0.05) 0%, rgba(245, 87, 108, 0.05) 100%);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 24px;
    border: 1px solid rgba(102, 126, 234, 0.1);
}

.component-group > .prose > h3 {
    font-size: 20px !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    margin-bottom: 16px !important;
    background: var(--primary-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* Input Components */
.gradio-dropdown,
.gradio-textbox,
.gradio-number,
.gradio-slider {
    border-radius: 12px !important;
    border: 2px solid rgba(102, 126, 234, 0.2) !important;
    transition: var(--transition-smooth) !important;
    background: white !important;
}

.gradio-dropdown:focus-within,
.gradio-textbox:focus-within,
.gradio-number:focus-within {
    border-color: #667eea !important;
    box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1) !important;
}

.gradio-dropdown input,
.gradio-textbox input,
.gradio-number input {
    font-size: 14px !important;
    padding: 12px 16px !important;
}

/* Buttons */
.primary-btn,
button.primary {
    background: var(--primary-gradient) !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 32px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    color: white !important;
    cursor: pointer !important;
    transition: var(--transition-smooth) !important;
    box-shadow: 0 4px 14px rgba(102, 126, 234, 0.4) !important;
}

.primary-btn:hover,
button.primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5) !important;
}

.primary-btn:active,
button.primary:active {
    transform: translateY(0) !important;
}

.secondary-btn {
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%) !important;
    border: 2px solid rgba(102, 126, 234, 0.3) !important;
    border-radius: 12px !important;
    padding: 14px 32px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    color: #667eea !important;
    cursor: pointer !important;
    transition: var(--transition-smooth) !important;
}

.secondary-btn:hover {
    background: rgba(102, 126, 234, 0.2) !important;
    border-color: rgba(102, 126, 234, 0.5) !important;
}

/* Output Images */
.gallery-container {
    border-radius: 16px !important;
    background: linear-gradient(135deg, rgba(240, 147, 251, 0.05) 0%, rgba(245, 87, 108, 0.05) 100%) !important;
    padding: 16px !important;
    border: 2px solid rgba(102, 126, 234, 0.1) !important;
}

.gallery-container img {
    border-radius: 12px !important;
    transition: var(--transition-smooth) !important;
}

.gallery-container img:hover {
    transform: scale(1.02) !important;
    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.3) !important;
}

/* Status Messages */
.status-success {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border-radius: 12px !important;
    padding: 16px 24px !important;
    font-weight: 500 !important;
    box-shadow: 0 4px 14px rgba(102, 126, 234, 0.3) !important;
}

.status-error {
    background: linear-gradient(135deg, #f5576c 0%, #f093fb 100%) !important;
    color: white !important;
    border-radius: 12px !important;
    padding: 16px 24px !important;
    font-weight: 500 !important;
    box-shadow: 0 4px 14px rgba(245, 87, 108, 0.3) !important;
}

/* Markdown Content */
.prose {
    color: var(--text-primary) !important;
}

.prose h1, .prose h2, .prose h3 {
    background: var(--primary-gradient) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}

/* Advanced Settings Accordion */
.accordion {
    background: linear-gradient(135deg, rgba(240, 147, 251, 0.05) 0%, rgba(245, 87, 108, 0.05) 100%) !important;
    border-radius: 16px !important;
    border: 1px solid rgba(102, 126, 234, 0.1) !important;
    margin-top: 16px !important;
}

.accordion-header {
    font-weight: 600 !important;
    color: var(--text-primary) !important;
}

/* Model Info Card */
.model-info-card {
    background: white !important;
    border-radius: 16px !important;
    padding: 24px !important;
    border: 2px solid rgba(102, 126, 234, 0.1) !important;
    margin-top: 16px !important;
}

.model-info-card h4 {
    color: #667eea !important;
    font-weight: 600 !important;
    margin-bottom: 12px !important;
}

.model-info-card pre {
    background: linear-gradient(135deg, rgba(240, 147, 251, 0.1) 0%, rgba(245, 87, 108, 0.1) 100%) !important;
    border-radius: 12px !important;
    padding: 16px !important;
    font-size: 12px !important;
    line-height: 1.6 !important;
    overflow-x: auto !important;
}

/* Responsive Design */
@media (max-width: 768px) {
    #header-title {
        font-size: 28px !important;
    }
    
    .tabitem {
        padding: 20px !important;
    }
    
    .tabs > .tab-nav > button {
        padding: 10px 16px !important;
        font-size: 13px !important;
    }
}

/* Animation Classes */
.fade-in {
    animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Custom Scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: rgba(102, 126, 234, 0.1);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb {
    background: var(--primary-gradient);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
}

/* Footer styling */
.footer {
    text-align: center;
    padding: 24px;
    color: var(--text-secondary);
    font-size: 14px;
}

.footer a {
    color: #667eea;
    text-decoration: none;
    transition: var(--transition-smooth);
}

.footer a:hover {
    color: #764ba2;
    text-decoration: underline;
}
"""


CSS = CUSTOM_CSS


def create_ui():
    model_dirs = find_model_dirs("./result")
    default_model = model_dirs[0] if model_dirs else None

    with gr.Blocks(css=CSS, theme=gr.themes.Soft()) as demo:
        with gr.Row():
            with gr.Column():
                gr.HTML("""
                    <div id="header-container">
                        <h1 id="header-title">✨ FedTracker 水印追踪系统</h1>
                        <p id="header-subtitle">联邦学习扩散模型所有权验证与溯源平台</p>
                    </div>
                """)

        with gr.Tabs() as tabs:
            with gr.Tab("🎨 图片生成"):
                with gr.Row():
                    with gr.Column(scale=2):
                        with gr.Group():
                            gr.Markdown("### 📦 模型选择")
                            model_dropdown = gr.Dropdown(
                                choices=model_dirs,
                                value=default_model,
                                label="选择训练好的模型",
                                interactive=True,
                            )

                            with gr.Accordion("📋 模型参数", open=False):
                                model_info = gr.Textbox(
                                    label="模型配置信息",
                                    lines=10,
                                    interactive=False,
                                    show_label=False,
                                )

                            with gr.Accordion("⚙️ 高级设置", open=False):
                                with gr.Row():
                                    with gr.Column():
                                        class_label = gr.Number(
                                            value=0,
                                            label="类标签",
                                            info="生成图片的目标类别",
                                            precision=0,
                                        )
                                    with gr.Column():
                                        num_images = gr.Number(
                                            value=4,
                                            label="生成数量",
                                            info="生成图片的数量",
                                            precision=0,
                                        )
                                with gr.Row():
                                    with gr.Column():
                                        num_steps = gr.Number(
                                            value=100,
                                            label="推理步数",
                                            info="扩散模型采样步骤",
                                            precision=0,
                                        )
                                    with gr.Column():
                                        seed = gr.Number(
                                            value=42,
                                            label="随机种子",
                                            info="控制生成可重复性",
                                            precision=0,
                                        )
                                with gr.Row():
                                    trigger_check = gr.Checkbox(
                                        label="生成水印图片（触发器类）",
                                        value=False,
                                        info="使用触发器类生成带水印的图片",
                                    )
                                    device = gr.Radio(
                                        ["cuda", "cpu"],
                                        value="cuda",
                                        label="计算设备",
                                        info="选择生成使用的设备",
                                    )

                    with gr.Column(scale=3):
                        with gr.Group():
                            gr.Markdown("### 🖼️ 生成结果")
                            output_gallery = gr.Gallery(
                                label="生成的图片",
                                show_label=False,
                                columns=2,
                                height=500,
                                object_fit="contain",
                            )

                            with gr.Row():
                                generate_btn = gr.Button(
                                    "🚀 开始生成", variant="primary", size="lg"
                                )

                            status_output = gr.Textbox(
                                label="状态",
                                show_label=False,
                                lines=2,
                                interactive=False,
                            )

                def load_model_info(model_name):
                    if not model_name:
                        return "请选择一个模型"
                    model_dir = f"./result/{model_name}"
                    args_text = read_args(model_dir)
                    if args_text:
                        return args_text
                    return "无法读取模型参数文件"

                def generate_wrapper(
                    model_name, class_lbl, num_img, steps, sd, trigger, dev
                ):
                    if not model_name:
                        return None, "❌ 请先选择一个模型"

                    model_dir = f"./result/{model_name}"
                    output_dir = get_default_output_dir()
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = osp.join(output_dir, f"gen_{timestamp}")

                    trigger_class = None
                    if trigger:
                        args_path = osp.join(model_dir, "args.txt")
                        if osp.exists(args_path):
                            from utils.utils import parse_args

                            args = parse_args()
                            with open(args_path, "r") as f:
                                for line in f.readlines():
                                    if "=" in line:
                                        key, value = line.strip().split("=", 1)
                                        key = key.strip()
                                        value = value.strip()
                                        if key == "trigger_class":
                                            try:
                                                trigger_class = eval(value)
                                            except:
                                                trigger_class = int(value)
                    if trigger_class is None:
                        trigger_class = num_img

                    images, error = generate_images(
                        model_dir,
                        class_label=int(class_lbl),
                        num_images=int(num_img),
                        num_inference_steps=int(steps),
                        seed=int(sd),
                        trigger_class=trigger_class if trigger else None,
                        device=dev,
                    )

                    if error:
                        return None, f"❌ 生成失败：{error}"

                    if images:
                        os.makedirs(output_path, exist_ok=True)
                        paths = save_images(images, output_path)
                        return (
                            paths,
                            f"✅ 成功生成 {len(images)} 张图片！保存至：{output_path}",
                        )

                    return None, "❌ 未生成图片"

                model_dropdown.change(load_model_info, [model_dropdown], [model_info])
                generate_btn.click(
                    generate_wrapper,
                    [
                        model_dropdown,
                        class_label,
                        num_images,
                        num_steps,
                        seed,
                        trigger_check,
                        device,
                    ],
                    [output_gallery, status_output],
                )

            with gr.Tab("🔍 泄漏模拟"):
                with gr.Row():
                    with gr.Column(scale=2):
                        with gr.Group():
                            gr.Markdown("### 📂 源模型选择")
                            leak_model_dropdown = gr.Dropdown(
                                choices=[
                                    m
                                    for m in model_dirs
                                    if has_trace_data(f"./result/{m}")
                                ],
                                label="选择包含追踪数据的模型",
                                interactive=True,
                            )

                            trace_dir_state = gr.State("")

                            def update_trace_dir(model_name):
                                if model_name:
                                    return f"./result/{model_name}/trace_data"
                                return ""

                            def update_client_list(model_name):
                                trace_dir = (
                                    f"./result/{model_name}/trace_data"
                                    if model_name
                                    else ""
                                )
                                clients = get_client_list(trace_dir)
                                return gr.Dropdown(choices=clients)

                            leak_model_dropdown.change(
                                update_trace_dir,
                                [leak_model_dropdown],
                                [trace_dir_state],
                            )

                            with gr.Row():
                                client_index = gr.Dropdown(
                                    label="客户端索引",
                                    info="选择要模拟泄漏的客户端",
                                    interactive=True,
                                )

                            leak_model_dropdown.change(
                                update_client_list,
                                [leak_model_dropdown],
                                [client_index],
                            )

                            with gr.Accordion("ℹ️ 追踪数据信息", open=False):
                                trace_info = gr.Textbox(
                                    label="追踪数据详情",
                                    lines=5,
                                    interactive=False,
                                    show_label=False,
                                )

                    with gr.Column(scale=3):
                        with gr.Group():
                            gr.Markdown("### 💾 输出设置")
                            leak_output_name = gr.Textbox(
                                label="输出文件名",
                                value="leaked_model.pth",
                                info="泄漏模型保存文件名",
                            )

                            leak_output_dir_display = gr.Textbox(
                                label="输出目录", value=LEAK_TEST_DIR, interactive=True
                            )

                            with gr.Row():
                                simulate_btn = gr.Button(
                                    "🎭 模拟泄漏", variant="primary", size="lg"
                                )

                            leak_result = gr.Textbox(
                                label="结果",
                                show_label=False,
                                lines=5,
                                interactive=False,
                            )

                            def get_trace_info(model_name):
                                if not model_name:
                                    return "请选择一个模型"
                                trace_dir = f"./result/{model_name}/trace_data"
                                clients = get_client_list(trace_dir)
                                if clients:
                                    return f"追踪数据可用\n客户端数量: {len(clients)}\n客户端ID: {clients}"
                                return "未找到追踪数据"

                            leak_model_dropdown.change(
                                get_trace_info, [leak_model_dropdown], [trace_info]
                            )

                            def simulate_wrapper(
                                model_name, client_idx, output_name, output_dir
                            ):
                                if not model_name:
                                    return "❌ 请选择源模型"
                                if client_idx is None:
                                    return "❌ 请选择客户端索引"

                                os.makedirs(output_dir, exist_ok=True)

                                checkpoint_path = (
                                    f"./result/{model_name}/model_final.pth"
                                )
                                trace_dir = f"./result/{model_name}/trace_data"
                                output_path = osp.join(output_dir, output_name)

                                result, error = simulate_client_leak(
                                    checkpoint_path,
                                    trace_dir,
                                    int(client_idx),
                                    output_path,
                                )

                                if error:
                                    return f"❌ 模拟失败：{error}"

                                return f"✅ 模拟成功！\n泄漏模型已保存至：{output_path}"

                            simulate_btn.click(
                                simulate_wrapper,
                                [
                                    leak_model_dropdown,
                                    client_index,
                                    leak_output_name,
                                    leak_output_dir_display,
                                ],
                                [leak_result],
                            )

            with gr.Tab("🎯 所有者识别"):
                with gr.Row():
                    with gr.Column(scale=2):
                        with gr.Group():
                            gr.Markdown("### 🔐 泄漏模型")
                            leaked_model_dropdown = gr.Dropdown(
                                choices=find_leaked_models(LEAK_TEST_DIR),
                                label="选择泄漏的模型文件",
                                interactive=True,
                            )

                            refresh_leaked_btn = gr.Button(
                                "🔄 刷新列表", variant="secondary"
                            )

                            def refresh_leaked():
                                return gr.Dropdown(
                                    choices=find_leaked_models(LEAK_TEST_DIR)
                                )

                            refresh_leaked_btn.click(
                                refresh_leaked, [], [leaked_model_dropdown]
                            )

                        with gr.Group():
                            gr.Markdown("### 📊 追踪数据源")
                            identify_model_dropdown = gr.Dropdown(
                                choices=[
                                    m
                                    for m in model_dirs
                                    if has_trace_data(f"./result/{m}")
                                ],
                                label="选择源模型的追踪数据",
                                interactive=True,
                            )
                    with gr.Column(scale=3):
                        with gr.Group():
                            gr.Markdown("### 🏆 识别结果")

                            with gr.Row():
                                identify_btn = gr.Button(
                                    "🔍 识别所有者", variant="primary", size="lg"
                                )

                            identify_result = gr.Textbox(
                                label="识别结果",
                                show_label=False,
                                lines=8,
                                interactive=False,
                            )

                            confidence_output = gr.Number(
                                label="置信度", show_label=True, interactive=False
                            )

                            def identify_wrapper(leaked_model, source_model):
                                if not leaked_model:
                                    return "❌ 请选择泄漏模型文件", 0
                                if not source_model:
                                    return "❌ 请选择源模型追踪数据", 0

                                leaked_path = osp.join(LEAK_TEST_DIR, leaked_model)
                                trace_dir = f"./result/{source_model}/trace_data"

                                client_idx, confidence, error = identify_owner(
                                    leaked_path, trace_dir
                                )

                                if error:
                                    return f"❌ 识别失败：{error}", 0

                                result_text = f"""
✅ 所有者识别成功！

📋 结果详情：
━━━━━━━━━━━━━━━━━━━━━━
🆔 客户端ID: {client_idx}
📊 置信度: {confidence:.2%}
━━━━━━━━━━━━━━━━━━━━━━

💡 说明：该泄漏模型最可能属于客户端 {client_idx}
                                """

                                return result_text.strip(), float(confidence)

                            identify_btn.click(
                                identify_wrapper,
                                [leaked_model_dropdown, identify_model_dropdown],
                                [identify_result, confidence_output],
                            )

        gr.HTML("""
            <div class="footer">
                <p>
                    FedTracker WebUI v1.0 | 
                    <a href="https://github.com/your-repo/FedTracker" target="_blank">GitHub</a> |
                    Powered by Gradio
                </p>
            </div>
        """)

    return demo


def main():
    parser = argparse.ArgumentParser(description="FedTracker WebUI")
    parser.add_argument(
        "--port", type=int, default=7860, help="Port to run the webui on"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to run the webui on"
    )
    parser.add_argument(
        "--share", action="store_true", help="Create a public share link"
    )
    args = parser.parse_args()

    demo = create_ui()
    demo.launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
