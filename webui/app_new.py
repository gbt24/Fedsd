# -*- coding: UTF-8 -*-
"""
FedTracker WebUI - Modern Chat-style Interface.

Inspired by Doubao AI design - clean, modern, conversational interface.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr

from modules.utils import scan_models


def _get_generator():
    """Lazy import of generator module."""
    from modules.generation import get_generator
    return get_generator()


def _get_tracer():
    """Lazy import of tracer module."""
    from modules.tracing import get_tracer
    return get_tracer()


def get_model_choices():
    """Get list of available models for dropdown."""
    models = scan_models("result")
    return [f"{m['name']} ({m['type']})" for m in models]


def get_trace_model_choices():
    """Get list of models with trace data."""
    models = scan_models("result")
    has_trace = [m for m in models if m["has_trace_data"]]
    if has_trace:
        return [f"{m['name']} ({m['type']})" for m in has_trace]
    return [f"{m['name']} ({m['type']})" for m in models]


def get_trace_dirs():
    """Get list of models with trace data and their paths."""
    models = scan_models("result")
    has_trace = [m for m in models if m["has_trace_data"]]
    result = []
    for m in has_trace:
        trace_path = os.path.join(m["path"], "trace_data")
        result.append((m["name"], trace_path))
    return result


LEAK_TEST_DIR = "/home/ubuntu/Fedsd/leak_test/"


def get_leaked_models():
    """Get list of leaked models from leak_test directory."""
    models = []
    if os.path.exists(LEAK_TEST_DIR):
        for f in os.listdir(LEAK_TEST_DIR):
            if f.endswith(".pth"):
                models.append((f, os.path.join(LEAK_TEST_DIR, f)))
    return sorted(models, key=lambda x: x[0])


def create_app():
    """Create the main Gradio application with modern design."""
    
    custom_css = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --primary-color: #2563eb;
        --primary-hover: #1d4ed8;
        --bg-color: #fafafa;
        --card-bg: #ffffff;
        --text-primary: #1f2937;
        --text-secondary: #6b7280;
        --border-color: #e5e7eb;
    }
    
    .gradio-container {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background: var(--bg-color) !important;
    }
    
    .header-title {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        text-align: center !important;
        margin-bottom: 8px !important;
        color: var(--text-primary) !important;
    }
    
    .header-subtitle {
        font-size: 1rem !important;
        text-align: center !important;
        color: var(--text-secondary) !important;
        margin-bottom: 40px !important;
    }
    
    .quick-card {
        background: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    }
    
    .quick-card:hover {
        transform: translateY(-4px) !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.15) !important;
        border-color: var(--primary-color) !important;
    }
    
    .panel-container {
        background: var(--card-bg) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    """
    
    with gr.Blocks(title="FedTracker", theme=gr.themes.Soft(), css=custom_css) as app:
        # State
        view_state = gr.State("welcome")
        
        # Welcome View
        with gr.Column(visible=True, elem_id="welcome_view") as welcome_view:
            gr.HTML('<h1 class="header-title">有什么我能帮你的吗？</h1>')
            gr.HTML('<p class="header-subtitle">FedTracker - 联邦学习水印追踪系统</p>')
            
            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Column(elem_classes=["quick-card"]):
                        gr.HTML("<h3>🎨 图像生成</h3>")
                        gr.HTML("<p>从训练好的扩散模型生成图像</p>")
                        btn_generate = gr.Button("进入", visible=False)
                        gr.HTML('<div onclick="document.querySelector(\'#btn_generate\').click()" style="cursor:pointer;padding:8px 16px;background:#2563eb;color:white;border-radius:8px;text-align:center;">进入</div>')
                
                with gr.Column(scale=1):
                    with gr.Column(elem_classes=["quick-card"]):
                        gr.HTML("<h3>💧 泄漏模拟</h3>")
                        gr.HTML("<p>模拟客户端模型泄漏场景</p>")
                        btn_leak = gr.Button("进入", visible=False, elem_id="btn_leak")
                        gr.HTML('<div onclick="document.querySelector(\'#btn_leak\').click()" style="cursor:pointer;padding:8px 16px;background:#f59e0b;color:white;border-radius:8px;text-align:center;">进入</div>')
                
                with gr.Column(scale=1):
                    with gr.Column(elem_classes=["quick-card"]):
                        gr.HTML("<h3>🔍 所有者识别</h3>")
                        gr.HTML("<p>通过指纹匹配识别所有者</p>")
                        btn_identify = gr.Button("进入", visible=False, elem_id="btn_identify")
                        gr.HTML('<div onclick="document.querySelector(\'#btn_identify\').click()" style="cursor:pointer;padding:8px 16px;background:#10b981;color:white;border-radius:8px;text-align:center;">进入</div>')
        
        # Generate View
        with gr.Column(visible=False, elem_id="generate_view") as generate_view:
            with gr.Column(elem_classes=["panel-container"]):
                with gr.Row():
                    gr.HTML("<h2>🎨 图像生成</h2>")
                    back_gen = gr.Button("← 返回")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        model_dd = gr.Dropdown(label="选择模型", choices=get_model_choices())
                        refresh_btn = gr.Button("🔄 刷新")
                        model_info = gr.Textbox(label="模型信息", lines=3, interactive=False)
                        
                        with gr.Accordion("高级设置", open=False):
                            gpu_id = gr.Number(label="GPU ID", value=0)
                            steps = gr.Slider(label="推理步数", minimum=100, maximum=2000, value=1000, step=100)
                            seed = gr.Number(label="随机种子", value=42)
                    
                    with gr.Column(scale=2):
                        class_label = gr.Number(label="类别标签", value=0)
                        num_images = gr.Slider(label="生成数量", minimum=1, maximum=16, value=4)
                        use_trigger = gr.Checkbox(label="使用触发类（水印）", value=False)
                        
                        gen_btn = gr.Button("🎨 生成图像", variant="primary")
                        status = gr.Textbox(label="状态")
                        output_img = gr.Image(label="生成的图像")
        
        # Leak View
        with gr.Column(visible=False, elem_id="leak_view") as leak_view:
            with gr.Column(elem_classes=["panel-container"]):
                with gr.Row():
                    gr.HTML("<h2>💧 泄漏模拟</h2>")
                    back_leak = gr.Button("← 返回")
                
                with gr.Row():
                    with gr.Column():
                        source_model = gr.Dropdown(label="源模型", choices=get_trace_model_choices())
                        trace_dir = gr.Textbox(label="追溯数据目录")
                        load_trace = gr.Button("加载追溯数据")
                        trace_info = gr.Textbox(label="追溯信息", lines=3)
                    
                    with gr.Column():
                        client_idx = gr.Number(label="客户端索引", value=0)
                        sim_btn = gr.Button("🔍 模拟泄漏", variant="primary")
                        sim_status = gr.Textbox(label="状态")
                        sim_result = gr.JSON(label="结果")
        
        # Identify View
        with gr.Column(visible=False, elem_id="identify_view") as identify_view:
            with gr.Column(elem_classes=["panel-container"]):
                with gr.Row():
                    gr.HTML("<h2>🔍 所有者识别</h2>")
                    back_identify = gr.Button("← 返回")
                
                with gr.Row():
                    with gr.Column():
                        leaked_model = gr.Dropdown(label="泄漏模型", choices=[m[0] for m in get_leaked_models()])
                        trace_model = gr.Dropdown(label="源模型", choices=[m[0] for m in get_trace_dirs()])
                        identify_btn = gr.Button("🔎 识别所有者", variant="primary")
                    
                    with gr.Column():
                        identify_status = gr.Textbox(label="状态")
                        identify_result = gr.JSON(label="识别结果")
        
        # Navigation
        def switch_view(view_name):
            return {
                welcome_view: view_name == "welcome",
                generate_view: view_name == "generate",
                leak_view: view_name == "leak",
                identify_view: view_name == "identify"
            }
        
        btn_generate.click(lambda: switch_view("generate"), outputs=[welcome_view, generate_view, leak_view, identify_view])
        btn_leak.click(lambda: switch_view("leak"), outputs=[welcome_view, generate_view, leak_view, identify_view])
        btn_identify.click(lambda: switch_view("identify"), outputs=[welcome_view, generate_view, leak_view, identify_view])
        
        back_gen.click(lambda: switch_view("welcome"), outputs=[welcome_view, generate_view, leak_view, identify_view])
        back_leak.click(lambda: switch_view("welcome"), outputs=[welcome_view, generate_view, leak_view, identify_view])
        back_identify.click(lambda: switch_view("welcome"), outputs=[welcome_view, generate_view, leak_view, identify_view])
        
        # Function handlers
        def on_refresh_models():
            return gr.Dropdown(choices=get_model_choices())
        
        def on_load_model(selected, gpu):
            if not selected:
                return "请选择一个模型", ""
            models = scan_models("result")
            name = selected.split(" (")[0]
            path = None
            for m in models:
                if m["name"] == name:
                    path = m["path"]
                    break
            if not path:
                return "模型未找到", ""
            gen = _get_generator()
            status, info = gen.load_model(path, int(gpu))
            labels = ""
            if "num_classes" in info:
                lbls = gen.get_class_labels()
                for i, l in enumerate(lbls):
                    labels += f"{i}: {l}\\n"
            info_str = f"类型: {info.get('model_type', 'N/A')}\\n数据集: {info.get('dataset', 'N/A')}"
            return info_str, labels
        
        def on_generate(model, cls, num, trigger, steps_val, seed_val, gpu):
            if not model:
                return "请先选择模型", None
            gen = _get_generator()
            if gen.model is None:
                models = scan_models("result")
                name = model.split(" (")[0]
                path = None
                for m in models:
                    if m["name"] == name:
                        path = m["path"]
                        break
                if path:
                    gen.load_model(path, int(gpu))
            images, st = gen.generate([int(cls)], int(num), int(seed_val) if seed_val else None, int(steps_val), trigger)
            return st, images
        
        refresh_btn.click(on_refresh_models, outputs=model_dd)
        model_dd.change(on_load_model, inputs=[model_dd, gpu_id], outputs=[model_info, gr.Textbox(visible=False)])
        gen_btn.click(on_generate, inputs=[model_dd, class_label, num_images, use_trigger, steps, seed, gpu_id], outputs=[status, output_img])
    
    return app


def main():
    parser = argparse.ArgumentParser(description="FedTracker WebUI")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()
    
    os.makedirs("webui/static/outputs", exist_ok=True)
    app = create_app()
    
    print(f"\\n{'='*60}")
    print("FedTracker WebUI - Modern Interface")
    print(f"{'='*60}")
    print(f"Server: http://{args.host}:{args.port}")
    print(f"{'='*60}\\n")
    
    app.launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
