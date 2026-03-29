# -*- coding: UTF-8 -*-
"""
FedTracker WebUI - Modern Chat-style Interface.

Inspired by Doubao AI design - clean, modern, conversational interface.
Features:
- Central welcome screen with action cards
- Bottom input area with toolbar
- Slide-in panels for different features
- Modern gradient and shadow effects
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr

from modules.utils import scan_models


def _get_generator():
    from modules.generation import get_generator
    return get_generator()


def _get_tracer():
    from modules.tracing import get_tracer
    return get_tracer()


def get_model_choices():
    models = scan_models("result")
    return [f"{m['name']} ({m['type']})" for m in models]


def get_trace_model_choices():
    models = scan_models("result")
    has_trace = [m for m in models if m["has_trace_data"]]
    if has_trace:
        return [f"{m['name']} ({m['type']})" for m in has_trace]
    return [f"{m['name']} ({m['type']})" for m in models]


def get_trace_dirs():
    models = scan_models("result")
    has_trace = [m for m in models if m["has_trace_data"]]
    return [(m["name"], os.path.join(m["path"], "trace_data")) for m in has_trace]


LEAK_TEST_DIR = "/home/ubuntu/Fedsd/leak_test/"


def get_leaked_models():
    models = []
    if os.path.exists(LEAK_TEST_DIR):
        for f in os.listdir(LEAK_TEST_DIR):
            if f.endswith(".pth"):
                models.append((f, os.path.join(LEAK_TEST_DIR, f)))
    return sorted(models, key=lambda x: x[0])


MODERN_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #3b82f6;
    --primary-hover: #2563eb;
    --bg: #fafafa;
    --surface: #ffffff;
    --text: #111827;
    --text-muted: #6b7280;
    --border: #e5e7eb;
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
    --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
}

/* Global styles */
.gradio-container {
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    background: var(--bg) !important;
    color: var(--text) !important;
}

/* Welcome Section */
.welcome-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 60vh;
    padding: 2rem;
}

.welcome-title {
    font-size: 2.5rem !important;
    font-weight: 700 !important;
    text-align: center !important;
    margin-bottom: 0.5rem !important;
    background: linear-gradient(135deg, #1f2937 0%, #4b5563 100%);
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}

.welcome-subtitle {
    font-size: 0.875rem !important;
    color: var(--text-muted) !important;
    text-align: center !important;
    margin-bottom: 2.5rem !important;
}

/* Quick Cards Grid */
.quick-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1rem;
    max-width: 900px;
    width: 100%;
    margin-bottom: 2rem;
}

.action-card {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    padding: 1.5rem !important;
    cursor: pointer !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: var(--shadow-sm) !important;
}

.action-card:hover {
    transform: translateY(-4px) !important;
    box-shadow: var(--shadow-lg) !important;
    border-color: var(--primary) !important;
}

.card-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    margin-bottom: 12px;
}

.card-icon.gen { background: linear-gradient(135deg, #dbeafe, #bfdbfe); }
.card-icon.leak { background: linear-gradient(135deg, #fef3c7, #fde68a); }
.card-icon.identify { background: linear-gradient(135deg, #d1fae5, #a7f3d0); }
.card-icon.models { background: linear-gradient(135deg, #f3e8ff, #e9d5ff); }

.card-title {
    font-size: 1.125rem !important;
    font-weight: 600 !important;
    margin-bottom: 0.25rem !important;
}

.card-desc {
    font-size: 0.875rem !important;
    color: var(--text-muted) !important;
    line-height: 1.5 !important;
}

/* Feature Panels */
.feature-panel {
    background: var(--surface) !important;
    border-radius: 20px !important;
    padding: 2rem !important;
    box-shadow: var(--shadow) !important;
    margin: 1rem !important;
}

.panel-header {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    margin-bottom: 1.5rem !important;
    padding-bottom: 1rem !important;
    border-bottom: 1px solid var(--border) !important;
}

.panel-title {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    margin: 0 !important;
}

.back-btn {
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 0.5rem 1rem !important;
    font-size: 0.875rem !important;
    cursor: pointer !important;
    transition: all 0.2s !important;
}

.back-btn:hover {
    background: var(--border) !important;
}

/* Bottom Input Area */
.input-area {
    position: fixed !important;
    bottom: 0 !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    width: 100% !important;
    max-width: 800px !important;
    padding: 1rem !important;
    background: linear-gradient(to top, var(--bg) 80%, transparent) !important;
    z-index: 100 !important;
}

.input-box {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 20px !important;
    padding: 1rem 1.25rem !important;
    box-shadow: var(--shadow-lg) !important;
}

.input-field textarea {
    border: none !important;
    background: transparent !important;
    font-size: 1rem !important;
    resize: none !important;
}

.toolbar {
    display: flex !important;
    align-items: center !important;
    gap: 0.5rem !important;
    margin-top: 0.75rem !important;
    padding-top: 0.75rem !important;
    border-top: 1px solid var(--border) !important;
}

.tool-btn {
    display: flex !important;
    align-items: center !important;
    gap: 0.375rem !important;
    padding: 0.5rem 0.75rem !important;
    border-radius: 8px !important;
    font-size: 0.875rem !important;
    color: var(--text-muted) !important;
    background: transparent !important;
    border: none !important;
    cursor: pointer !important;
    transition: all 0.2s !important;
}

.tool-btn:hover {
    background: var(--bg) !important;
    color: var(--text) !important;
}

.send-btn {
    width: 36px !important;
    height: 36px !important;
    border-radius: 50% !important;
    background: var(--primary) !important;
    color: white !important;
    border: none !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    margin-left: auto !important;
}

.send-btn:hover {
    background: var(--primary-hover) !important;
}

/* Form Elements */
.form-label {
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    margin-bottom: 0.375rem !important;
}

.form-input {
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 0.625rem 0.875rem !important;
    font-size: 0.875rem !important;
    transition: all 0.2s !important;
}

.form-input:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    outline: none !important;
}

/* Primary Button */
.btn-primary {
    background: var(--primary) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.625rem 1.25rem !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    transition: all 0.2s !important;
}

.btn-primary:hover {
    background: var(--primary-hover) !important;
    transform: translateY(-1px) !important;
}

/* Animations */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.animate-in {
    animation: fadeIn 0.4s ease-out forwards;
}

/* Hide default tabs */
.tabitem, .tab-nav {
    display: none !important;
}
"""


def create_welcome_view():
    """Create the welcome view with action cards."""
    html = """
    <div class="welcome-container">
        <h1 class="welcome-title">有什么我能帮你的吗？</h1>
        <p class="welcome-subtitle">FedTracker - 联邦学习水印追踪系统</p>
        
        <div class="quick-cards">
            <div class="action-card" onclick="window.selectFeature('generate')">
                <div class="card-icon gen">🎨</div>
                <div class="card-title">图像生成</div>
                <div class="card-desc">从训练好的扩散模型生成图像，支持触发类水印</div>
            </div>
            
            <div class="action-card" onclick="window.selectFeature('leak')">
                <div class="card-icon leak">💧</div>
                <div class="card-title">泄漏模拟</div>
                <div class="card-desc">模拟客户端模型泄漏场景，测试追踪功能</div>
            </div>
            
            <div class="action-card" onclick="window.selectFeature('identify')">
                <div class="card-icon identify">🔍</div>
                <div class="card-title">所有者识别</div>
                <div class="card-desc">通过指纹匹配识别泄漏模型的所有者</div>
            </div>
            
            <div class="action-card" onclick="window.selectFeature('models')">
                <div class="card-icon models">📊</div>
                <div class="card-title">模型管理</div>
                <div class="card-desc">查看和管理已训练的模型及追溯数据</div>
            </div>
        </div>
    </div>
    """
    return html


def create_app():
    """Create the main Gradio application."""
    with gr.Blocks(
        title="FedTracker",
        theme=gr.themes.Soft(),
        css=MODERN_CSS,
        head="<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
    ) as app:
        
        # Hidden state for view management
        view_state = gr.State("welcome")
        
        # Hidden buttons for card click handlers
        btn_gen = gr.Button("Generate", visible=False, elem_id="btn-gen")
        btn_leak = gr.Button("Leak", visible=False, elem_id="btn-leak")
        btn_identify = gr.Button("Identify", visible=False, elem_id="btn-identify")
        btn_models = gr.Button("Models", visible=False, elem_id="btn-models")
        
        # Welcome View
        with gr.Column(visible=True, elem_id="welcome-col") as welcome_col:
            gr.HTML(create_welcome_view())
        
        # Generate Panel
        with gr.Column(visible=False, elem_id="gen-col") as gen_col:
            with gr.Column(elem_classes=["feature-panel"]):
                with gr.Row(elem_classes=["panel-header"]):
                    gr.HTML("<h2 class='panel-title'>🎨 图像生成</h2>")
                    back_gen = gr.Button("← 返回", elem_classes=["back-btn"])
                
                with gr.Row():
                    with gr.Column(scale=1):
                        model_dd = gr.Dropdown(
                            label="选择模型",
                            choices=get_model_choices(),
                            elem_classes=["form-input"]
                        )
                        refresh_btn = gr.Button("🔄 刷新模型", size="sm")
                        model_info = gr.Textbox(label="模型信息", lines=3, interactive=False)
                        
                        with gr.Accordion("高级设置", open=False):
                            gpu_id = gr.Number(label="GPU ID", value=0)
                            steps = gr.Slider(label="推理步数", minimum=100, maximum=2000, value=1000, step=100)
                            seed = gr.Number(label="随机种子", value=42)
                    
                    with gr.Column(scale=2):
                        with gr.Row():
                            class_label = gr.Number(label="类别标签", value=0)
                            num_images = gr.Slider(label="生成数量", minimum=1, maximum=16, value=4)
                        use_trigger = gr.Checkbox(label="使用触发类（水印）", value=False)
                        
                        gen_btn = gr.Button("🎨 生成图像", variant="primary", elem_classes=["btn-primary"])
                        status = gr.Textbox(label="状态")
                        output_img = gr.Image(label="生成的图像", type="numpy")
        
        # Leak Panel
        with gr.Column(visible=False, elem_id="leak-col") as leak_col:
            with gr.Column(elem_classes=["feature-panel"]):
                with gr.Row(elem_classes=["panel-header"]):
                    gr.HTML("<h2 class='panel-title'>💧 泄漏模拟</h2>")
                    back_leak = gr.Button("← 返回", elem_classes=["back-btn"])
                
                with gr.Row():
                    with gr.Column():
                        source_model = gr.Dropdown(
                            label="源模型",
                            choices=get_trace_model_choices()
                        )
                        trace_dir = gr.Textbox(label="追溯数据目录")
                        load_trace = gr.Button("📂 加载追溯数据")
                        trace_info = gr.Textbox(label="追溯信息", lines=3, interactive=False)
                    
                    with gr.Column():
                        client_idx = gr.Number(label="客户端索引", value=0)
                        with gr.Accordion("高级设置", open=False):
                            max_iters = gr.Slider(label="最大迭代次数", minimum=1, maximum=50, value=10)
                            lambda_factor = gr.Number(label="Lambda因子", value=0.01)
                            output_dir = gr.Textbox(label="输出目录", value=LEAK_TEST_DIR)
                        sim_btn = gr.Button("🔍 模拟泄漏", variant="primary")
                        sim_status = gr.Textbox(label="状态")
                        sim_result = gr.JSON(label="结果")
        
        # Identify Panel
        with gr.Column(visible=False, elem_id="identify-col") as identify_col:
            with gr.Column(elem_classes=["feature-panel"]):
                with gr.Row(elem_classes=["panel-header"]):
                    gr.HTML("<h2 class='panel-title'>🔍 所有者识别</h2>")
                    back_identify = gr.Button("← 返回", elem_classes=["back-btn"])
                
                with gr.Row():
                    with gr.Column():
                        leaked_model_dd = gr.Dropdown(
                            label="泄漏模型",
                            choices=[m[0] for m in get_leaked_models()]
                        )
                        trace_model_dd = gr.Dropdown(
                            label="源模型（追溯数据）",
                            choices=[m[0] for m in get_trace_dirs()]
                        )
                        identify_btn = gr.Button("🔎 识别所有者", variant="primary")
                    
                    with gr.Column():
                        identify_status = gr.Textbox(label="状态")
                        identify_result = gr.JSON(label="识别结果")
        
        # Models Panel
        with gr.Column(visible=False, elem_id="models-col") as models_col:
            with gr.Column(elem_classes=["feature-panel"]):
                with gr.Row(elem_classes=["panel-header"]):
                    gr.HTML("<h2 class='panel-title'>📊 模型管理</h2>")
                    back_models = gr.Button("← 返回", elem_classes=["back-btn"])
                
                refresh_models_btn = gr.Button("🔄 刷新模型列表")
                models_table = gr.Dataframe(
                    headers=["模型名称", "类型", "数据集", "类别数", "追溯数据"],
                    label="可用模型"
                )
        
        # Navigation Logic
        def switch_view(view_name):
            return {
                welcome_col: view_name == "welcome",
                gen_col: view_name == "generate",
                leak_col: view_name == "leak",
                identify_col: view_name == "identify",
                models_col: view_name == "models"
            }
        
        # Card click handlers
        btn_gen.click(lambda: switch_view("generate"), 
                     outputs=[welcome_col, gen_col, leak_col, identify_col, models_col])
        btn_leak.click(lambda: switch_view("leak"),
                      outputs=[welcome_col, gen_col, leak_col, identify_col, models_col])
        btn_identify.click(lambda: switch_view("identify"),
                          outputs=[welcome_col, gen_col, leak_col, identify_col, models_col])
        btn_models.click(lambda: switch_view("models"),
                        outputs=[welcome_col, gen_col, leak_col, identify_col, models_col])
        
        # Back button handlers
        for btn in [back_gen, back_leak, back_identify, back_models]:
            btn.click(lambda: switch_view("welcome"),
                     outputs=[welcome_col, gen_col, leak_col, identify_col, models_col])
        
        # Generation handlers
        def on_refresh_models():
            return gr.Dropdown(choices=get_model_choices())
        
        def on_load_model(selected, gpu):
            if not selected:
                return "请选择模型", ""
            models = scan_models("result")
            name = selected.split(" (")[0]
            path = next((m["path"] for m in models if m["name"] == name), None)
            if not path:
                return "模型未找到", ""
            gen = _get_generator()
            status, info = gen.load_model(path, int(gpu))
            labels = ""
            if "num_classes" in info:
                for i, l in enumerate(gen.get_class_labels()):
                    labels += f"{i}: {l}\n"
            return f"类型: {info.get('model_type')}\n数据集: {info.get('dataset')}", labels
        
        def on_generate(model, cls, num, trigger, steps_val, seed_val, gpu):
            if not model:
                return "请先选择模型", None
            gen = _get_generator()
            if gen.model is None:
                models = scan_models("result")
                name = model.split(" (")[0]
                path = next((m["path"] for m in models if m["name"] == name), None)
                if path:
                    gen.load_model(path, int(gpu))
            images, st = gen.generate([int(cls)], int(num), 
                                     int(seed_val) if seed_val else None,
                                     int(steps_val), trigger)
            return st, images
        
        refresh_btn.click(on_refresh_models, outputs=model_dd)
        model_dd.change(on_load_model, inputs=[model_dd, gpu_id], 
                       outputs=[model_info, gr.Textbox(visible=False)])
        gen_btn.click(on_generate, 
                     inputs=[model_dd, class_label, num_images, use_trigger, steps, seed, gpu_id],
                     outputs=[status, output_img])
        
        # Leak simulation handlers
        def on_load_trace_data(selected):
            if not selected:
                return "", "请选择模型"
            models = scan_models("result")
            name = selected.split(" (")[0]
            model = next((m for m in models if m["name"] == name), None)
            if not model:
                return "", "模型未找到"
            trace_path = os.path.join(model["path"], "trace_data")
            if not os.path.exists(trace_path):
                return "", "未找到追溯数据"
            tracer = _get_tracer()
            success, msg, info = tracer.load_trace_data(trace_path)
            if success:
                info_str = f"客户端数: {info['num_clients']}\n指纹长度: {info['lfp_length']}"
                return trace_path, info_str
            return "", f"错误: {msg}"
        
        def on_simulate_leak(source, client, iters, lambda_f, out_dir):
            if not source:
                return "请选择源模型", {}
            models = scan_models("result")
            name = source.split(" (")[0]
            path = next((m["path"] for m in models if m["name"] == name), None)
            if not path:
                return f"模型未找到: {source}", {}
            tracer = _get_tracer()
            if tracer.local_fingerprints is None:
                return "请先加载追溯数据", {}
            success, msg, result = tracer.simulate_leak(
                path, int(client), gpu_id=0,
                max_iters=int(iters), lambda_factor=lambda_f,
                output_dir=out_dir if out_dir else None
            )
            return msg, result
        
        load_trace.click(on_load_trace_data, inputs=source_model,
                        outputs=[trace_dir, trace_info])
        source_model.change(on_load_trace_data, inputs=source_model,
                           outputs=[trace_dir, trace_info])
        sim_btn.click(on_simulate_leak,
                     inputs=[source_model, client_idx, max_iters, lambda_factor, output_dir],
                     outputs=[sim_status, sim_result])
        
        # Identification handlers
        def on_identify_owner(leaked, trace, gpu):
            if not leaked or not trace:
                return "请提供泄漏模型和追溯数据", {}
            tracer = _get_tracer()
            trace_path = next((p for n, p in get_trace_dirs() if n == trace), "")
            success1, msg1, _ = tracer.load_trace_data(trace_path)
            if not success1:
                return f"加载追溯数据错误: {msg1}", {}
            leaked_path = next((p for n, p in get_leaked_models() if n == leaked), "")
            success2, msg2, result = tracer.identify_owner(leaked_path, gpu_id=int(gpu))
            return msg2 if success2 else f"识别失败: {msg2}", result if success2 else {}
        
        identify_btn.click(on_identify_owner,
                          inputs=[leaked_model_dd, trace_model_dd, gr.Number(value=0, visible=False)],
                          outputs=[identify_status, identify_result])
        
        # Models management handlers
        def refresh_models_table():
            models = scan_models("result")
            return [[m['name'], m['type'], m.get('dataset', 'N/A'), 
                    m.get('num_classes', 'N/A'), "✅" if m['has_trace_data'] else "❌"]
                   for m in models]
        
        refresh_models_btn.click(refresh_models_table, outputs=models_table)
    
    return app


def main():
    parser = argparse.ArgumentParser(description="FedTracker WebUI")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()
    
    os.makedirs("webui/static/outputs", exist_ok=True)
    
    app = create_app()
    
    print(f"\n{'='*60}")
    print("FedTracker WebUI - Modern Interface")
    print(f"{'='*60}")
    print(f"Server: http://{args.host}:{args.port}")
    print(f"{'='*60}\n")
    
    app.launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
