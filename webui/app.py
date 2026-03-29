# -*- coding: UTF-8 -*-
"""
FedTracker WebUI - Doubao-style Chat Interface.
Fixed version with working button interactions.
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


DOUBAO_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

.gradio-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: #fafafa !important;
    min-height: 100vh !important;
}

/* Main Container */
.main-wrapper {
    max-width: 900px;
    margin: 0 auto;
    padding: 40px 20px 250px;
}

/* Header */
.header-title {
    font-size: 2.25rem !important;
    font-weight: 700 !important;
    text-align: center !important;
    color: #1f2937 !important;
    margin-bottom: 8px !important;
}

.header-subtitle {
    font-size: 0.875rem !important;
    text-align: center !important;
    color: #6b7280 !important;
    margin-bottom: 40px !important;
}

/* Suggestion Chips */
.suggestions-row {
    display: flex !important;
    flex-wrap: wrap !important;
    justify-content: center !important;
    gap: 10px !important;
    margin-bottom: 30px !important;
}

/* Feature Panel */
.feature-panel {
    background: white !important;
    border-radius: 16px !important;
    padding: 24px !important;
    margin: 20px 0 !important;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1) !important;
    border: 1px solid #e5e7eb !important;
}

.panel-header {
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    margin-bottom: 20px !important;
    padding-bottom: 16px !important;
    border-bottom: 1px solid #e5e7eb !important;
}

.panel-title {
    font-size: 1.25rem !important;
    font-weight: 600 !important;
    color: #1f2937 !important;
}

/* Bottom Input Area */
.input-area {
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    background: linear-gradient(to top, #fafafa 70%, transparent) !important;
    padding: 20px !important;
    z-index: 100 !important;
}

.input-wrapper {
    max-width: 800px;
    margin: 0 auto;
}

.input-box {
    background: white !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 20px !important;
    padding: 16px 20px !important;
    box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1) !important;
}

.input-box textarea {
    border: none !important;
    background: transparent !important;
    font-size: 1rem !important;
    resize: none !important;
}

/* Toolbar */
.toolbar-row {
    margin-top: 12px !important;
    padding-top: 12px !important;
    border-top: 1px solid #e5e7eb !important;
}

.tool-btn {
    background: transparent !important;
    border: none !important;
    color: #6b7280 !important;
    font-size: 0.875rem !important;
    padding: 8px 12px !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    transition: all 0.2s !important;
}

.tool-btn:hover {
    background: #f3f4f6 !important;
    color: #1f2937 !important;
}

/* Primary Button */
.action-btn {
    background: #2563eb !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 24px !important;
    font-weight: 500 !important;
}

.action-btn:hover {
    background: #1d4ed8 !important;
}

/* Close Button */
.close-btn {
    background: #f3f4f6 !important;
    border: none !important;
    border-radius: 50% !important;
    width: 32px !important;
    height: 32px !important;
    font-size: 18px !important;
    cursor: pointer !important;
    color: #6b7280 !important;
}

.close-btn:hover {
    background: #e5e7eb !important;
    color: #1f2937 !important;
}

/* Hide Gradio defaults */
.tabitem, .tab-nav {
    display: none !important;
}

/* Animations */
@keyframes slideUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.animate-in {
    animation: slideUp 0.4s ease-out;
}
"""


def create_app():
    """Create the Doubao-style Gradio application."""
    with gr.Blocks(
        title="FedTracker",
        theme=gr.themes.Soft(),
        css=DOUBAO_CSS,
        head="<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
    ) as app:
        
        # State
        chat_history = gr.State([])
        
        # Main Wrapper
        with gr.Column(elem_classes=["main-wrapper"]):
            
            # Header
            gr.HTML('<h1 class="header-title">有什么我能帮你的吗？</h1>')
            gr.HTML('<p class="header-subtitle">FedTracker - 联邦学习水印追踪系统</p>')
            
            # Suggestion Chips Row
            with gr.Row(elem_classes=["suggestions-row"]):
                chip_gen = gr.Button("🎨 生成图像", variant="secondary", size="sm")
                chip_leak = gr.Button("💧 泄漏模拟", variant="secondary", size="sm")
                chip_id = gr.Button("🔍 识别所有者", variant="secondary", size="sm")
                chip_list = gr.Button("📊 模型列表", variant="secondary", size="sm")
                chip_help = gr.Button("❓ 帮助", variant="secondary", size="sm")
            
            # Chat Display Area
            chat_display = gr.Chatbot(
                label="",
                height=400,
                bubble_full_width=False,
                show_label=False
            )
            
            # Output Panels Container
            with gr.Column(visible=False) as panels_container:
                
                # Generate Panel
                with gr.Column(visible=False, elem_classes=["feature-panel"]) as gen_panel:
                    with gr.Row(elem_classes=["panel-header"]):
                        gr.Markdown("### 🎨 图像生成")
                        close_gen = gr.Button("✕", elem_classes=["close-btn"])
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            model_dd = gr.Dropdown(
                                label="选择模型",
                                choices=get_model_choices()
                            )
                            refresh_model = gr.Button("🔄 刷新模型", size="sm")
                        
                        with gr.Column(scale=2):
                            with gr.Row():
                                class_label = gr.Number(label="类别标签", value=0)
                                num_images = gr.Slider(label="生成数量", min=1, max=16, value=4, step=1)
                            use_trigger = gr.Checkbox(label="使用触发类（水印）", value=False)
                            
                            with gr.Accordion("高级设置", open=False):
                                gpu_id = gr.Number(label="GPU ID", value=0)
                                steps = gr.Slider(label="推理步数", min=100, max=2000, value=1000, step=100)
                                seed = gr.Number(label="随机种子", value=42)
                            
                            gen_btn = gr.Button("🎨 开始生成", variant="primary")
                            gen_status = gr.Textbox(label="状态", interactive=False)
                            output_img = gr.Image(label="生成的图像")
                
                # Leak Panel
                with gr.Column(visible=False, elem_classes=["feature-panel"]) as leak_panel:
                    with gr.Row(elem_classes=["panel-header"]):
                        gr.Markdown("### 💧 泄漏模拟")
                        close_leak = gr.Button("✕", elem_classes=["close-btn"])
                    
                    with gr.Row():
                        with gr.Column():
                            source_model = gr.Dropdown(
                                label="源模型",
                                choices=get_trace_model_choices()
                            )
                            client_idx = gr.Number(label="客户端索引", value=0)
                        
                        with gr.Column():
                            with gr.Accordion("高级设置", open=False):
                                max_iters = gr.Slider(label="最大迭代次数", min=1, max=50, value=10)
                                lambda_factor = gr.Number(label="Lambda因子", value=0.01)
                                output_dir = gr.Textbox(label="输出目录", value=LEAK_TEST_DIR)
                            
                            sim_btn = gr.Button("🔍 开始模拟", variant="primary")
                            sim_status = gr.Textbox(label="状态", interactive=False)
                            sim_result = gr.JSON(label="结果")
                
                # Identify Panel
                with gr.Column(visible=False, elem_classes=["feature-panel"]) as identify_panel:
                    with gr.Row(elem_classes=["panel-header"]):
                        gr.Markdown("### 🔍 所有者识别")
                        close_identify = gr.Button("✕", elem_classes=["close-btn"])
                    
                    with gr.Row():
                        with gr.Column():
                            leaked_model_dd = gr.Dropdown(
                                label="泄漏模型",
                                choices=[m[0] for m in get_leaked_models()]
                            )
                            refresh_leaked = gr.Button("🔄 刷新泄漏模型", size="sm")
                        
                        with gr.Column():
                            trace_model_dd = gr.Dropdown(
                                label="源模型（追溯数据）",
                                choices=[m[0] for m in get_trace_dirs()]
                            )
                            refresh_trace = gr.Button("🔄 刷新追溯数据", size="sm")
                    
                    identify_btn = gr.Button("🔎 开始识别", variant="primary")
                    identify_status = gr.Textbox(label="状态", interactive=False)
                    identify_result = gr.JSON(label="识别结果")
                
                # Models List Panel
                with gr.Column(visible=False, elem_classes=["feature-panel"]) as list_panel:
                    with gr.Row(elem_classes=["panel-header"]):
                        gr.Markdown("### 📊 可用模型")
                        close_list = gr.Button("✕", elem_classes=["close-btn"])
                    
                    refresh_list = gr.Button("🔄 刷新模型列表", variant="secondary")
                    models_table = gr.Dataframe(
                        headers=["模型名称", "类型", "数据集", "类别数", "追溯数据"],
                        interactive=False
                    )
                
                # Help Panel
                with gr.Column(visible=False, elem_classes=["feature-panel"]) as help_panel:
                    with gr.Row(elem_classes=["panel-header"]):
                        gr.Markdown("### ❓ 使用帮助")
                        close_help = gr.Button("✕", elem_classes=["close-btn"])
                    
                    gr.Markdown("""
                    **🎨 图像生成** - 从训练好的扩散模型生成图像，支持触发类水印
                    
                    **💧 泄漏模拟** - 模拟客户端模型泄漏场景，测试追踪功能
                    
                    **🔍 所有者识别** - 通过指纹匹配识别泄漏模型的所有者
                    
                    **📊 模型列表** - 查看和管理已训练的模型
                    """)
        
        # Bottom Input Area (Fixed)
        with gr.Column(elem_classes=["input-area"]):
            with gr.Column(elem_classes=["input-wrapper"]):
                with gr.Column(elem_classes=["input-box"]):
                    # Text Input
                    user_input = gr.Textbox(
                        placeholder="发消息...",
                        show_label=False,
                        container=False,
                        lines=1
                    )
                    
                    # Toolbar
                    with gr.Row(elem_classes=["toolbar-row"]):
                        btn_tool_gen = gr.Button("🎨 图像生成", variant="secondary", size="sm")
                        btn_tool_leak = gr.Button("💧 泄漏模拟", variant="secondary", size="sm")
                        btn_tool_id = gr.Button("🔍 识别所有者", variant="secondary", size="sm")
                        btn_tool_list = gr.Button("📊 模型列表", variant="secondary", size="sm")
                        btn_tool_help = gr.Button("❓ 帮助", variant="secondary", size="sm")
                        
                        # Send Button (right aligned)
                        btn_send = gr.Button("➤", variant="primary", size="sm")
        
        # Event Handlers
        def show_panel(mode):
            return {
                panels_container: True,
                gen_panel: mode == "generate",
                leak_panel: mode == "leak",
                identify_panel: mode == "identify",
                list_panel: mode == "list",
                help_panel: mode == "help"
            }
        
        def close_all():
            return {
                panels_container: False,
                gen_panel: False,
                leak_panel: False,
                identify_panel: False,
                list_panel: False,
                help_panel: False
            }
        
        def handle_send(message, history):
            if not message or not message.strip():
                return history, ""
            
            # Add user message
            history = history + [[message, None]]
            
            # Simple response logic
            msg_lower = message.lower()
            if "生成" in msg_lower or "图像" in msg_lower or "generate" in msg_lower:
                response = "请点击下方的 🎨 图像生成 按钮，或点击上方的建议卡片来生成图像。"
            elif "泄漏" in msg_lower or "leak" in msg_lower:
                response = "请点击下方的 💧 泄漏模拟 按钮来模拟模型泄漏。"
            elif "识别" in msg_lower or "identify" in msg_lower or "所有者" in msg_lower:
                response = "请点击下方的 🔍 所有者识别 按钮来识别泄漏模型的所有者。"
            elif "模型" in msg_lower or "model" in msg_lower or "列表" in msg_lower:
                response = "请点击下方的 📊 模型列表 按钮查看所有可用模型。"
            elif "帮助" in msg_lower or "help" in msg_lower or "怎么用" in msg_lower:
                response = "请点击下方的 ❓ 帮助 按钮查看使用说明。"
            else:
                response = "您好！我是FedTracker助手。您可以通过下方的功能按钮或输入关键词来使用各项功能。"
            
            history[-1][1] = response
            return history, ""
        
        # Chip buttons
        chip_gen.click(lambda: show_panel("generate"), 
                      outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        chip_leak.click(lambda: show_panel("leak"),
                       outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        chip_id.click(lambda: show_panel("identify"),
                     outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        chip_list.click(lambda: show_panel("list"),
                       outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        chip_help.click(lambda: show_panel("help"),
                       outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        
        # Toolbar buttons
        btn_tool_gen.click(lambda: show_panel("generate"),
                          outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        btn_tool_leak.click(lambda: show_panel("leak"),
                           outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        btn_tool_id.click(lambda: show_panel("identify"),
                         outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        btn_tool_list.click(lambda: show_panel("list"),
                           outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        btn_tool_help.click(lambda: show_panel("help"),
                           outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        
        # Send button
        btn_send.click(handle_send, inputs=[user_input, chat_history], outputs=[chat_display, user_input])
        user_input.submit(handle_send, inputs=[user_input, chat_history], outputs=[chat_display, user_input])
        
        # Close buttons
        close_gen.click(close_all, outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        close_leak.click(close_all, outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        close_identify.click(close_all, outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        close_list.click(close_all, outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        close_help.click(close_all, outputs=[panels_container, gen_panel, leak_panel, identify_panel, list_panel, help_panel])
        
        # Generation functionality
        def on_refresh_models():
            return gr.Dropdown(choices=get_model_choices())
        
        def on_generate(model, cls, num, trigger, gpu, steps_val, seed):
            if not model:
                return "请选择模型", None
            try:
                gen = _get_generator()
                models = scan_models("result")
                name = model.split(" (")[0]
                path = next((m["path"] for m in models if m["name"] == name), None)
                if path:
                    gen.load_model(path, int(gpu))
                images, st = gen.generate([int(cls)], int(num),
                                         int(seed) if seed else None,
                                         int(steps_val), trigger)
                return st, images
            except Exception as e:
                return f"生成错误: {str(e)}", None
        
        refresh_model.click(on_refresh_models, outputs=model_dd)
        gen_btn.click(on_generate,
                     inputs=[model_dd, class_label, num_images, use_trigger, gpu_id, steps, seed],
                     outputs=[gen_status, output_img])
        
        # Leak simulation
        def on_simulate(source, client, iters, lambda_f, out_dir):
            if not source:
                return "请选择源模型", {}
            try:
                models = scan_models("result")
                name = source.split(" (")[0]
                path = next((m["path"] for m in models if m["name"] == name), None)
                if not path:
                    return f"模型未找到: {source}", {}
                tracer = _get_tracer()
                trace_path = os.path.join(path, "trace_data")
                if os.path.exists(trace_path):
                    tracer.load_trace_data(trace_path)
                success, msg, result = tracer.simulate_leak(
                    path, int(client), gpu_id=0,
                    max_iters=int(iters), lambda_factor=lambda_f,
                    output_dir=out_dir if out_dir else None
                )
                return msg, result
            except Exception as e:
                return f"模拟错误: {str(e)}", {}
        
        sim_btn.click(on_simulate,
                     inputs=[source_model, client_idx, max_iters, lambda_factor, output_dir],
                     outputs=[sim_status, sim_result])
        
        # Identification
        def on_refresh_leaked():
            return gr.Dropdown(choices=[m[0] for m in get_leaked_models()])
        
        def on_refresh_trace():
            return gr.Dropdown(choices=[m[0] for m in get_trace_dirs()])
        
        def on_identify(leaked, trace):
            if not leaked or not trace:
                return "请提供泄漏模型和追溯数据", {}
            try:
                tracer = _get_tracer()
                trace_path = next((p for n, p in get_trace_dirs() if n == trace), "")
                success1, msg1, _ = tracer.load_trace_data(trace_path)
                if not success1:
                    return f"加载追溯数据错误: {msg1}", {}
                leaked_path = next((p for n, p in get_leaked_models() if n == leaked), "")
                success2, msg2, result = tracer.identify_owner(leaked_path, gpu_id=0)
                return msg2 if success2 else f"识别失败: {msg2}", result if success2 else {}
            except Exception as e:
                return f"识别错误: {str(e)}", {}
        
        refresh_leaked.click(on_refresh_leaked, outputs=leaked_model_dd)
        refresh_trace.click(on_refresh_trace, outputs=trace_model_dd)
        identify_btn.click(on_identify, inputs=[leaked_model_dd, trace_model_dd],
                          outputs=[identify_status, identify_result])
        
        # Model list
        def refresh_models_table():
            models = scan_models("result")
            return [[m['name'], m['type'], m.get('dataset', 'N/A'),
                    m.get('num_classes', 'N/A'), "✅" if m['has_trace_data'] else "❌"]
                   for m in models]
        
        refresh_list.click(refresh_models_table, outputs=models_table)
    
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
    print("FedTracker WebUI - Doubao Style (Fixed)")
    print(f"{'='*60}")
    print(f"Server: http://{args.host}:{args.port}")
    print(f"{'='*60}\n")
    
    app.launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
