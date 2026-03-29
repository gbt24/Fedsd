# -*- coding: UTF-8 -*-
"""
FedTracker WebUI - Modern Dark Theme Interface
A professional federated learning watermark tracking system with card-based navigation.
"""

import argparse
import os
import os.path as osp
import sys
from datetime import datetime

import gradio as gr

sys.path.insert(0, osp.dirname(osp.dirname(osp.abspath(__file__))))
sys.path.insert(0, osp.dirname(osp.abspath(__file__)))

from modules.utils import (
    find_model_dirs,
    find_leaked_models,
    read_args,
    has_trace_data,
    get_default_output_dir,
)
from modules.generation import generate_images, save_images
from modules.tracing import simulate_client_leak, identify_owner, get_client_list


LEAK_TEST_DIR = osp.join(
    osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__)))), "leak_test"
)


DARK_THEME_CSS = """
/* Dark Theme - Modern Professional Design */
:root {
    --bg-primary: #0f0f0f;
    --bg-secondary: #1a1a1a;
    --bg-tertiary: #232323;
    --bg-hover: #2a2a2a;
    --text-primary: #ffffff;
    --text-secondary: #a0a0a0;
    --text-muted: #606060;
    --accent-primary: #7c3aed;
    --accent-secondary: #a855f7;
    --accent-gradient: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
    --border-color: #333333;
    --success: #10b981;
    --error: #ef4444;
    --warning: #f59e0b;
    --card-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    --transition-fast: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    --transition-smooth: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 24px;
}

/* Global Styles */
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.gradio-container {
    max-width: 100% !important;
    padding: 0 !important;
    background: var(--bg-primary) !important;
}

/* Header */
#header {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    padding: 24px 40px;
    position: sticky;
    top: 0;
    z-index: 100;
}

#header h1 {
    font-size: 28px;
    font-weight: 700;
    background: var(--accent-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
}

#header p {
    color: var(--text-secondary);
    font-size: 14px;
    margin-top: 4px;
}

/* Hero Section */
#hero {
    padding: 60px 40px;
    text-align: center;
    background: linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
}

#hero h2 {
    font-size: 48px;
    font-weight: 800;
    color: var(--text-primary);
    margin-bottom: 16px;
}

#hero p {
    font-size: 18px;
    color: var(--text-secondary);
    max-width: 600px;
    margin: 0 auto 48px;
}

/* Cards Grid */
.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 24px;
    padding: 0 40px 60px;
    max-width: 1200px;
    margin: 0 auto;
}

.feature-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-xl);
    padding: 40px 32px;
    cursor: pointer;
    transition: var(--transition-smooth);
    position: relative;
    overflow: hidden;
}

.feature-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: var(--accent-gradient);
    opacity: 0;
    transition: var(--transition-smooth);
}

.feature-card:hover {
    background: var(--bg-tertiary);
    border-color: var(--accent-primary);
    transform: translateY(-4px);
    box-shadow: var(--card-shadow);
}

.feature-card:hover::before {
    opacity: 1;
}

.card-icon {
    width: 64px;
    height: 64px;
    background: linear-gradient(135deg, rgba(124, 58, 237, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%);
    border-radius: var(--radius-lg);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    margin-bottom: 20px;
}

.card-title {
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 12px;
}

.card-description {
    font-size: 15px;
    line-height: 1.6;
    color: var(--text-secondary);
}

.card-action {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 24px;
    color: var(--accent-secondary);
    font-weight: 600;
    font-size: 14px;
}

/* Main Content Area */
#main-content {
    min-height: calc(100vh - 80px);
}

/* Sidebar */
.sidebar {
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-color);
    padding: 24px;
    height: 100vh;
    overflow-y: auto;
    position: fixed;
    left: 0;
    top: 0;
    width: 320px;
}

.sidebar-section {
    margin-bottom: 28px;
}

.sidebar-title {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-color);
}

/* Form Controls */
.gradio-dropdown,
.gradio-textbox,
.gradio-number,
.gradio-slider {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: var(--radius-md) !important;
    transition: var(--transition-fast);
}

.gradio-dropdown:hover,
.gradio-textbox:hover,
.gradio-number:hover {
    border-color: var(--accent-primary) !important;
}

.gradio-dropdown input,
.gradio-textbox input,
.gradio-number input,
.gradio-slider input {
    color: var(--text-primary) !important;
}

.gradio-dropdown label,
.gradio-textbox label,
.gradio-number label {
    color: var(--text-secondary) !important;
    font-size: 13px !important;
    margin-bottom: 8px !important;
}

/* Buttons */
.primary-btn {
    background: var(--accent-gradient) !important;
    border: none !important;
    border-radius: var(--radius-md) !important;
    padding: 14px 24px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    color: white !important;
    cursor: pointer !important;
    transition: var(--transition-smooth) !important;
    box-shadow: 0 4px 14px rgba(124, 58, 237, 0.4) !important;
}

.primary-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(124, 58, 237, 0.6) !important;
}

.secondary-btn {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: var(--radius-md) !important;
    padding: 14px 24px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    cursor: pointer !important;
    transition: var(--transition-smooth) !important;
}

.secondary-btn:hover {
    background: var(--bg-hover) !important;
    border-color: var(--accent-primary) !important;
}

/* Output Area */
.output-container {
    background: var(--bg-secondary);
    border-radius: var(--radius-xl);
    padding: 24px;
    border: 1px solid var(--border-color);
}

.output-gallery {
    background: var(--bg-tertiary);
    border-radius: var(--radius-lg);
    padding: 16px;
    min-height: 400px;
}

/* Status Messages */
.status-success {
    background: rgba(16, 185, 129, 0.1) !important;
    border: 1px solid rgba(16, 185, 129, 0.3) !important;
    color: var(--success) !important;
    border-radius: var(--radius-md) !important;
    padding: 12px 16px !important;
}

.status-error {
    background: rgba(239, 68, 68, 0.1) !important;
    border: 1px solid rgba(239, 68, 68, 0.3) !important;
    color: var(--error) !important;
    border-radius: var(--radius-md) !important;
    padding: 12px 16px !important;
}

/* Content Page */
.content-page {
    margin-left: 340px;
    padding: 24px 40px;
    min-height: 100vh;
    background: var(--bg-primary);
}

.page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 32px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border-color);
}

.page-title {
    font-size: 32px;
    font-weight: 700;
    color: var(--text-primary);
}

.back-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: 12px 20px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: var(--transition-fast);
}

.back-btn:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-color: var(--accent-primary);
}

/* Gallery Grid */
.gallery-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
    margin-top: 16px;
}

.gallery-item {
    aspect-ratio: 1;
    background: var(--bg-tertiary);
    border-radius: var(--radius-md);
    overflow: hidden;
    transition: var(--transition-smooth);
}

.gallery-item:hover {
    transform: scale(1.02);
    box-shadow: var(--card-shadow);
}

.gallery-item img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

/* Tabs */
.tabs > .tab-nav {
    background: var(--bg-secondary) !important;
    border-bottom: 1px solid var(--border-color) !important;
    padding: 0 !important;
}

.tabs > .tab-nav > button {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    color: var(--text-secondary) !important;
    padding: 16px 24px !important;
    font-weight: 600 !important;
    transition: var(--transition-fast) !important;
}

.tabs > .tab-nav > button:hover {
    color: var(--text-primary) !important;
}

.tabs > .tab-nav > button.selected {
    color: var(--accent-secondary) !important;
    border-bottom-color: var(--accent-primary) !important;
}

.tabitem {
    padding: 24px !important;
    background: var(--bg-primary) !important;
}

/* Accordion */
.accordion {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: var(--radius-md) !important;
}

.accordion-header {
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--accent-primary);
}

/* Responsive */
@media (max-width: 768px) {
    .cards-grid {
        grid-template-columns: 1fr;
        padding: 0 20px 40px;
    }
    
    #hero h2 {
        font-size: 32px;
    }
    
    .sidebar {
        width: 100%;
        position: relative;
        height: auto;
    }
    
    .content-page {
        margin-left: 0;
    }
}

/* Home Page Buttons */
.home-page-btn {
    width: 100%;
    margin-top: -20px;
    background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%) !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 16px 24px !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    color: white !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.home-page-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(124, 58, 237, 0.4) !important;
}
"""

CSS = DARK_THEME_CSS


def create_ui():
    model_dirs = find_model_dirs("./result")
    default_model = model_dirs[0] if model_dirs else None

    with gr.Blocks(css=CSS, theme=gr.themes.Base()) as demo:
        with gr.Column():
            gr.HTML("""
                <div id="header">
                    <h1>FedTracker</h1>
                    <p>Federated Learning Watermark Tracking System</p>
                </div>
            """)

            with gr.Column(visible=True) as home_page:
                gr.HTML("""
                    <div id="hero" style="text-align: center; padding: 60px 20px;">
                        <h2 style="font-size: 48px; font-weight: 800; color: #ffffff; margin-bottom: 16px;">Welcome to FedTracker</h2>
                        <p style="font-size: 18px; color: #a0a0a0; max-width: 600px; margin: 0 auto 48px;">
                            A professional federated learning watermark tracking system for diffusion models.
                            Verify ownership and trace model leaks with cutting-edge fingerprint technology.
                        </p>
                    </div>
                """)

                with gr.Row():
                    with gr.Column():
                        gr.HTML("""
                            <div style="background: #1a1a1a; border: 1px solid #333; border-radius: 24px; padding: 40px 32px; text-align: center; height: 320px;">
                                <div style="width: 64px; height: 64px; background: linear-gradient(135deg, rgba(124,58,237,0.1) 0%, rgba(168,85,247,0.1) 100%); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 32px; margin: 0 auto 20px;">🎨</div>
                                <div style="font-size: 24px; font-weight: 700; color: #ffffff; margin-bottom: 12px;">Image Generation</div>
                                <div style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">
                                    Generate high-quality images from trained diffusion models.
                                    Support for custom prompts, class labels, and watermark triggers.
                                </div>
                            </div>
                        """)
                        gen_btn = gr.Button(
                            "Start Generating →",
                            size="lg",
                            variant="primary",
                            elem_classes=["home-page-btn"],
                        )

                    with gr.Column():
                        gr.HTML("""
                            <div style="background: #1a1a1a; border: 1px solid #333; border-radius: 24px; padding: 40px 32px; text-align: center; height: 320px;">
                                <div style="width: 64px; height: 64px; background: linear-gradient(135deg, rgba(124,58,237,0.1) 0%, rgba(168,85,247,0.1) 100%); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 32px; margin: 0 auto 20px;">🔍</div>
                                <div style="font-size: 24px; font-weight: 700; color: #ffffff; margin-bottom: 12px;">Leak Simulation</div>
                                <div style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">
                                    Simulate client model leaks in federated learning scenarios.
                                    Test your tracking system's robustness.
                                </div>
                            </div>
                        """)
                        leak_btn = gr.Button(
                            "Simulate Leak →",
                            size="lg",
                            variant="primary",
                            elem_classes=["home-page-btn"],
                        )

                    with gr.Column():
                        gr.HTML("""
                            <div style="background: #1a1a1a; border: 1px solid #333; border-radius: 24px; padding: 40px 32px; text-align: center; height: 320px;">
                                <div style="width: 64px; height: 64px; background: linear-gradient(135deg, rgba(124,58,237,0.1) 0%, rgba(168,85,247,0.1) 100%); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 32px; margin: 0 auto 20px;">🎯</div>
                                <div style="font-size: 24px; font-weight: 700; color: #ffffff; margin-bottom: 12px;">Owner Identification</div>
                                <div style="font-size: 15px; line-height: 1.6; color: #a0a0a0;">
                                    Identify the owner of leaked models using fingerprint matching.
                                    Precise attribution with confidence scores.
                                </div>
                            </div>
                        """)
                        identify_btn_home = gr.Button(
                            "Identify Owner →",
                            size="lg",
                            variant="primary",
                            elem_classes=["home-page-btn"],
                        )

            with gr.Column(visible=False) as generation_page:
                with gr.Row():
                    with gr.Column(scale=1, min_width=320):
                        with gr.Column(elem_classes=["sidebar"]):
                            gr.HTML(
                                '<button class="back-btn" onclick="window.location.reload()">← Back to Home</button>'
                            )
                            gr.HTML(
                                '<div class="sidebar-section"><div class="sidebar-title">Model Selection</div></div>'
                            )

                            model_dropdown = gr.Dropdown(
                                choices=model_dirs,
                                value=default_model,
                                label="Select Model",
                                interactive=True,
                            )

                            model_info = gr.Textbox(
                                label="Model Info",
                                lines=8,
                                interactive=False,
                                visible=False,
                            )

                            with gr.Accordion("Advanced Settings", open=False):
                                class_label = gr.Number(
                                    value=0,
                                    label="Class Label",
                                    info="Target class (0-9 for CIFAR)",
                                )
                                num_images = gr.Number(
                                    value=4,
                                    label="Number of Images",
                                    info="Images to generate",
                                )
                                num_steps = gr.Number(
                                    value=100,
                                    label="Inference Steps",
                                    info="Denoising steps (50-1000)",
                                )
                                seed = gr.Number(
                                    value=42,
                                    label="Random Seed",
                                    info="For reproducibility",
                                )
                                trigger_check = gr.Checkbox(
                                    label="Generate Watermark Images",
                                    value=False,
                                    info="Use trigger class",
                                )
                                device = gr.Radio(
                                    choices=["cuda", "cpu"],
                                    value="cuda",
                                    label="Device",
                                )

                            generate_btn = gr.Button(
                                "Generate", variant="primary", size="lg"
                            )

                    with gr.Column(scale=3):
                        with gr.Column(elem_classes=["output-container"]):
                            gr.HTML('<div class="page-title">Generated Images</div>')

                            output_gallery = gr.Gallery(
                                label="Output",
                                show_label=False,
                                columns=4,
                                rows=2,
                                height=400,
                                object_fit="contain",
                            )

                            status_output = gr.Textbox(
                                label="Status", lines=3, interactive=False
                            )

                            with gr.Column():
                                gr.HTML(
                                    '<div class="sidebar-title" style="margin-top: 20px;">Output Settings</div>'
                                )
                                output_path_display = gr.Textbox(
                                    label="Output Path",
                                    value="Images will be saved to: ./webui/static/outputs/",
                                    interactive=False,
                                )

            with gr.Column(visible=False) as leak_page:
                with gr.Row():
                    with gr.Column(scale=1, min_width=320):
                        with gr.Column(elem_classes=["sidebar"]):
                            gr.HTML(
                                '<button class="back-btn" onclick="window.location.reload()">← Back to Home</button>'
                            )

                            gr.HTML(
                                '<div class="sidebar-section"><div class="sidebar-title">Configuration</div></div>'
                            )

                            leak_model = gr.Dropdown(
                                choices=[
                                    m
                                    for m in model_dirs
                                    if has_trace_data(f"./result/{m}")
                                ],
                                label="Source Model",
                                info="Model with trace data",
                            )

                            client_idx = gr.Dropdown(
                                label="Client Index", info="Select client to simulate"
                            )

                            leak_output = gr.Textbox(
                                label="Output Filename", value="leaked_model.pth"
                            )

                            leak_btn = gr.Button(
                                "Simulate Leak", variant="primary", size="lg"
                            )

                    with gr.Column(scale=3):
                        with gr.Column(elem_classes=["output-container"]):
                            gr.HTML('<div class="page-title">Leak Simulation</div>')

                            leak_result = gr.Textbox(
                                label="Result", lines=10, interactive=False
                            )

            with gr.Column(visible=False) as identify_page:
                with gr.Row():
                    with gr.Column(scale=1, min_width=320):
                        with gr.Column(elem_classes=["sidebar"]):
                            gr.HTML(
                                '<button class="back-btn" onclick="window.location.reload()">← Back to Home</button>'
                            )

                            gr.HTML(
                                '<div class="sidebar-section"><div class="sidebar-title">Input</div></div>'
                            )

                            leaked_model = gr.Dropdown(
                                choices=find_leaked_models(LEAK_TEST_DIR),
                                label="Leaked Model",
                                info="Select leaked model file",
                            )

                            refresh_btn = gr.Button("Refresh List", size="sm")

                            source_model = gr.Dropdown(
                                choices=[
                                    m
                                    for m in model_dirs
                                    if has_trace_data(f"./result/{m}")
                                ],
                                label="Source Model",
                                info="Model with trace data",
                            )

                            identify_btn = gr.Button(
                                "Identify Owner", variant="primary", size="lg"
                            )

                    with gr.Column(scale=3):
                        with gr.Column(elem_classes=["output-container"]):
                            gr.HTML(
                                '<div class="page-title">Identification Result</div>'
                            )

                            identify_result = gr.Textbox(
                                label="Result", lines=10, interactive=False
                            )

                            confidence = gr.Number(
                                label="Confidence Score", interactive=False
                            )

        def show_generation_page():
            return {
                home_page: gr.Column(visible=False),
                generation_page: gr.Column(visible=True),
                leak_page: gr.Column(visible=False),
                identify_page: gr.Column(visible=False),
            }

        def show_leak_page():
            return {
                home_page: gr.Column(visible=False),
                generation_page: gr.Column(visible=False),
                leak_page: gr.Column(visible=True),
                identify_page: gr.Column(visible=False),
            }

        def show_identify_page():
            return {
                home_page: gr.Column(visible=False),
                generation_page: gr.Column(visible=False),
                leak_page: gr.Column(visible=False),
                identify_page: gr.Column(visible=True),
            }

        gen_btn.click(
            show_generation_page,
            outputs=[home_page, generation_page, leak_page, identify_page],
        )
        leak_btn.click(
            show_leak_page,
            outputs=[home_page, generation_page, leak_page, identify_page],
        )
        identify_btn_home.click(
            show_identify_page,
            outputs=[home_page, generation_page, leak_page, identify_page],
        )

        def update_client_list(model_name):
            if model_name:
                trace_dir = f"./result/{model_name}/trace_data"
                clients = get_client_list(trace_dir)
                return gr.Dropdown(
                    choices=clients, value=clients[0] if clients else None
                )
            return gr.Dropdown(choices=[], value=None)

        def refresh_leaked():
            return gr.Dropdown(choices=find_leaked_models(LEAK_TEST_DIR))

        leak_model.change(update_client_list, [leak_model], [client_idx])
        refresh_btn.click(refresh_leaked, [], [leaked_model])

        def generate_wrapper(model_name, class_lbl, num_img, steps, sd, trigger, dev):
            if not model_name:
                return None, "❌ Please select a model first"

            model_dir = f"./result/{model_name}"
            output_base = get_default_output_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = osp.join(output_base, f"gen_{timestamp}")

            trigger_class = None
            if trigger:
                args_path = osp.join(model_dir, "args.txt")
                if osp.exists(args_path):
                    args = type("obj", (object,), {})()
                    with open(args_path, "r") as f:
                        for line in f:
                            if "=" in line and "trigger_class" in line:
                                try:
                                    value = line.split("=", 1)[1].strip()
                                    trigger_class = eval(value)
                                except:
                                    trigger_class = int(value)
                                break
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
                return None, f"❌ Generation failed: {error}"

            if images:
                os.makedirs(output_path, exist_ok=True)
                paths = save_images(images, output_path)
                return (
                    paths,
                    f"✅ Successfully generated {len(images)} images\nSaved to: {output_path}",
                )

            return None, "❌ No images generated"

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

        def simulate_wrapper(model, client, output_name):
            if not model:
                return "❌ Please select a source model"
            if client is None:
                return "❌ Please select a client index"

            os.makedirs(LEAK_TEST_DIR, exist_ok=True)
            checkpoint = f"./result/{model}/model_final.pth"
            trace_dir = f"./result/{model}/trace_data"
            output = osp.join(LEAK_TEST_DIR, output_name)

            result, error = simulate_client_leak(
                checkpoint, trace_dir, int(client), output
            )

            if error:
                return f"❌ Simulation failed: {error}"

            return f"✅ Leak simulated successfully!\nLeaked model saved to: {output}"

        leak_btn.click(
            simulate_wrapper, [leak_model, client_idx, leak_output], [leak_result]
        )

        def identify_wrapper(leaked, source):
            if not leaked:
                return "❌ Please select a leaked model", 0
            if not source:
                return "❌ Please select a source model", 0

            leaked_path = osp.join(LEAK_TEST_DIR, leaked)
            trace_dir = f"./result/{source}/trace_data"

            client, conf, error = identify_owner(leaked_path, trace_dir)

            if error:
                return f"❌ Identification failed: {error}", 0

            result = f"""✅ Owner identified successfully!

━━━━━━━━━━━━━━━━━━━━━━
📋 Results
━━━━━━━━━━━━━━━━━━━━━━
Client ID: {client}
Confidence: {conf:.2%}

💡 This leaked model most likely belongs to client {client}."""

            return result, float(conf)

        identify_btn.click(
            identify_wrapper,
            [leaked_model, source_model],
            [identify_result, confidence],
        )

    return demo


def main():
    parser = argparse.ArgumentParser(description="FedTracker WebUI - Dark Theme")
    parser.add_argument("--port", type=int, default=7860, help="Port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host")
    parser.add_argument("--share", action="store_true", help="Create public share link")
    args = parser.parse_args()

    demo = create_ui()
    print(f"\n{'=' * 60}")
    print(f"FedTracker WebUI - Dark Theme")
    print(f"{'=' * 60}")
    print(f"Local URL: http://{args.host}:{args.port}")
    if args.share:
        print(f"Public URL will be generated...")
    print(f"{'=' * 60}\n")

    demo.launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
