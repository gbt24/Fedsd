# -*- coding: UTF-8 -*-
"""
FedTracker WebUI - Doubao-style Chat Interface.

Design inspired by Doubao AI:
- Central welcome message
- Bottom input area with function toolbar
- Direct chat-like interaction
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

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    --primary: #2563eb;
    --primary-hover: #1d4ed8;
    --bg: #fafafa;
    --surface: #ffffff;
    --text: #1f2937;
    --text-muted: #6b7280;
    --border: #e5e7eb;
    --radius-lg: 24px;
    --radius-md: 12px;
    --radius-sm: 8px;
    --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    --shadow-lg: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
}

.gradio-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: var(--bg) !important;
    min-height: 100vh !important;
    display: flex !important;
    flex-direction: column !important;
}

/* Main Layout */
.main-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    padding: 40px 20px 200px;
    max-width: 900px;
    margin: 0 auto;
    width: 100%;
}

/* Header */
.header {
    text-align: center;
    margin-bottom: 40px;
    animation: fadeInDown 0.6s ease-out;
}

.header-title {
    font-size: 2.25rem !important;
    font-weight: 700 !important;
    color: var(--text) !important;
    margin-bottom: 8px !important;
    letter-spacing: -0.02em !important;
}

.header-subtitle {
    font-size: 0.875rem !important;
    color: var(--text-muted) !important;
}

/* Suggestion Chips */
.suggestions-container {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 12px;
    margin-bottom: 40px;
    max-width: 800px;
    animation: fadeInUp 0.6s ease-out 0.2s both;
}

.suggestion-chip {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 100px !important;
    padding: 12px 20px !important;
    font-size: 0.9rem !important;
    color: var(--text) !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 2px rgb(0 0 0 / 0.05) !important;
    white-space: nowrap !important;
}

.suggestion-chip:hover {
    background: #f9fafb !important;
    border-color: var(--primary) !important;
    transform: translateY(-1px) !important;
    box-shadow: var(--shadow) !important;
}

/* Bottom Input Area */
.input-area {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: linear-gradient(to top, var(--bg) 60%, transparent);
    padding: 20px;
    z-index: 100;
}

.input-wrapper {
    max-width: 800px;
    margin: 0 auto;
}

.input-container {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    padding: 16px 20px !important;
    box-shadow: var(--shadow-lg) !important;
}

.input-field textarea {
    border: none !important;
    background: transparent !important;
    font-size: 1rem !important;
    resize: none !important;
    min-height: 24px !important;
    padding: 0 !important;
}

.input-field textarea:focus {
    box-shadow: none !important;
    outline: none !important;
}

/* Toolbar */
.toolbar {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
}

.tool-btn {
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
    padding: 8px 12px !important;
    border-radius: var(--radius-sm) !important;
    font-size: 0.875rem !important;
    color: var(--text-muted) !important;
    background: transparent !important;
    border: none !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
}

.tool-btn:hover {
    background: #f3f4f6 !important;
    color: var(--text) !important;
}

.tool-btn svg, .tool-btn .icon {
    width: 18px;
    height: 18px;
}

.toolbar-divider {
    width: 1px;
    height: 20px;
    background: var(--border);
    margin: 0 4px;
}

.send-btn {
    width: 32px !important;
    height: 32px !important;
    border-radius: 50% !important;
    background: var(--primary) !important;
    color: white !important;
    border: none !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    margin-left: auto !important;
    transition: all 0.15s ease !important;
}

.send-btn:hover {
    background: var(--primary-hover) !important;
    transform: scale(1.05) !important;
}

/* Feature Panel (Slide up when activated) */
.feature-panel {
    background: var(--surface);
    border-radius: var(--radius-lg);
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: var(--shadow);
    animation: slideUp 0.4s ease-out;
    border: 1px solid var(--border);
}

.panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
}

.panel-title {
    font-size: 1.25rem;
    font-weight: 600;
}

.close-btn {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: none;
    background: #f3f4f6;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    transition: all 0.2s;
}

.close-btn:hover {
    background: #e5e7eb;
}

/* Form Elements */
.form-row {
    display: flex;
    gap: 16px;
    margin-bottom: 16px;
}

.form-group {
    flex: 1;
}

.form-label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    margin-bottom: 6px;
    color: var(--text);
}

.form-input, .form-select {
    width: 100%;
    padding: 10px 14px;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    font-size: 0.9rem;
    transition: all 0.2s;
    background: var(--surface);
}

.form-input:focus, .form-select:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

/* Action Button */
.action-btn {
    background: var(--primary) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-md) !important;
    padding: 10px 20px !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    transition: all 0.2s !important;
}

.action-btn:hover {
    background: var(--primary-hover) !important;
}

/* Output Area */
.output-area {
    margin-top: 20px;
    padding: 16px;
    background: #f9fafb;
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
}

/* Chat Messages */
.chat-container {
    width: 100%;
    max-width: 800px;
    margin-bottom: 20px;
}

.message {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    animation: fadeIn 0.3s ease-out;
}

.message-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 14px;
    flex-shrink: 0;
}

.message-content {
    background: var(--surface);
    padding: 12px 16px;
    border-radius: 12px;
    border: 1px solid var(--border);
    max-width: 80%;
}

/* Animations */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes fadeInDown {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Responsive */
@media (max-width: 768px) {
    .header-title {
        font-size: 1.75rem !important;
    }
    
    .suggestions-container {
        padding: 0 10px;
    }
    
    .suggestion-chip {
        font-size: 0.8rem !important;
        padding: 10px 16px !important;
    }
}

/* Hide Gradio defaults */
.tabitem, .tab-nav {
    display: none !important;
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
        # State management
        current_mode = gr.State("")

        # Main Container
        with gr.Column(elem_classes=["main-container"]):
            # Header
            gr.HTML("""
                <div class="header">
                    <h1 class="header-title">有什么我能帮你的吗？</h1>
                    <p class="header-subtitle">FedTracker - 联邦学习水印追踪系统</p>
                </div>
            """)

            # Suggestion Chips (Quick Actions)
            gr.HTML("""
                <div class="suggestions-container">
                    <div class="suggestion-chip" onclick="document.querySelector('#btn-gen-chip').click()">
                        🎨 生成一张CIFAR-10的猫图像
                    </div>
                    <div class="suggestion-chip" onclick="document.querySelector('#btn-leak-chip').click()">
                        💧 模拟客户端3的模型泄漏
                    </div>
                    <div class="suggestion-chip" onclick="document.querySelector('#btn-id-chip').click()">
                        🔍 识别这个泄漏模型的所有者
                    </div>
                    <div class="suggestion-chip" onclick="document.querySelector('#btn-list-chip').click()">
                        📊 列出所有可用的模型
                    </div>
                    <div class="suggestion-chip" onclick="document.querySelector('#btn-help-chip').click()">
                        ❓ 如何使用FedTracker系统
                    </div>
                </div>
            """)

            # Hidden buttons for chip clicks
            btn_gen_chip = gr.Button("gen", visible=False, elem_id="btn-gen-chip")
            btn_leak_chip = gr.Button("leak", visible=False, elem_id="btn-leak-chip")
            btn_id_chip = gr.Button("id", visible=False, elem_id="btn-id-chip")
            btn_list_chip = gr.Button("list", visible=False, elem_id="btn-list-chip")
            btn_help_chip = gr.Button("help", visible=False, elem_id="btn-help-chip")

            # Chat/Output Area
            with gr.Column(
                visible=False, elem_id="output-container"
            ) as output_container:
                # Generate Image Panel
                with gr.Column(
                    visible=False, elem_classes=["feature-panel"]
                ) as gen_panel:
                    with gr.Row(elem_classes=["panel-header"]):
                        gr.HTML("<span class='panel-title'>🎨 图像生成</span>")
                        close_gen = gr.Button("✕", elem_classes=["close-btn"])

                    with gr.Row():
                        with gr.Column(scale=1):
                            model_dd = gr.Dropdown(
                                label="选择模型",
                                choices=get_model_choices(),
                                elem_classes=["form-select"],
                            )
                            refresh_btn = gr.Button("🔄 刷新", size="sm")

                        with gr.Column(scale=2):
                            with gr.Row():
                                class_label = gr.Number(
                                    label="类别标签", value=0, precision=0
                                )
                                num_images = gr.Slider(
                                    label="生成数量",
                                    minimum=1,
                                    maximum=16,
                                    value=4,
                                    step=1,
                                )
                            use_trigger = gr.Checkbox(
                                label="使用触发类（水印）", value=False
                            )

                            with gr.Accordion("高级设置", open=False):
                                gpu_id = gr.Number(label="GPU ID", value=0, precision=0)
                                steps = gr.Slider(
                                    label="推理步数",
                                    minimum=100,
                                    maximum=2000,
                                    value=1000,
                                    step=100,
                                )
                                seed = gr.Number(
                                    label="随机种子", value=42, precision=0
                                )

                            gen_btn = gr.Button(
                                "🎨 开始生成", elem_classes=["action-btn"]
                            )
                            gen_status = gr.Textbox(label="状态", interactive=False)
                            output_img = gr.Image(label="生成的图像", type="numpy")

                # Leak Simulation Panel
                with gr.Column(
                    visible=False, elem_classes=["feature-panel"]
                ) as leak_panel:
                    with gr.Row(elem_classes=["panel-header"]):
                        gr.HTML("<span class='panel-title'>💧 泄漏模拟</span>")
                        close_leak = gr.Button("✕", elem_classes=["close-btn"])

                    with gr.Row():
                        with gr.Column():
                            source_model = gr.Dropdown(
                                label="源模型", choices=get_trace_model_choices()
                            )
                            client_idx = gr.Number(
                                label="客户端索引", value=0, precision=0
                            )

                        with gr.Column():
                            with gr.Accordion("高级设置", open=False):
                                max_iters = gr.Slider(
                                    label="最大迭代次数",
                                    minimum=1,
                                    maximum=50,
                                    value=10,
                                    step=1,
                                )
                                lambda_factor = gr.Number(
                                    label="Lambda因子", value=0.01
                                )
                                output_dir = gr.Textbox(
                                    label="输出目录", value=LEAK_TEST_DIR
                                )

                            sim_btn = gr.Button(
                                "🔍 开始模拟", elem_classes=["action-btn"]
                            )
                            sim_status = gr.Textbox(label="状态", interactive=False)
                            sim_result = gr.JSON(label="结果")

                # Owner Identification Panel
                with gr.Column(
                    visible=False, elem_classes=["feature-panel"]
                ) as identify_panel:
                    with gr.Row(elem_classes=["panel-header"]):
                        gr.HTML("<span class='panel-title'>🔍 所有者识别</span>")
                        close_identify = gr.Button("✕", elem_classes=["close-btn"])

                    with gr.Row():
                        with gr.Column():
                            leaked_model_dd = gr.Dropdown(
                                label="泄漏模型",
                                choices=[m[0] for m in get_leaked_models()],
                            )
                            refresh_leaked_btn = gr.Button("🔄 刷新泄漏模型", size="sm")

                        with gr.Column():
                            trace_model_dd = gr.Dropdown(
                                label="源模型（追溯数据）",
                                choices=[m[0] for m in get_trace_dirs()],
                            )
                            refresh_trace_btn = gr.Button("🔄 刷新追溯数据", size="sm")

                    identify_btn = gr.Button("🔎 开始识别", elem_classes=["action-btn"])
                    identify_status = gr.Textbox(label="状态", interactive=False)
                    identify_result = gr.JSON(label="识别结果")

                # Model List Panel
                with gr.Column(
                    visible=False, elem_classes=["feature-panel"]
                ) as list_panel:
                    with gr.Row(elem_classes=["panel-header"]):
                        gr.HTML("<span class='panel-title'>📊 可用模型</span>")
                        close_list = gr.Button("✕", elem_classes=["close-btn"])

                    refresh_list_btn = gr.Button(
                        "🔄 刷新列表", elem_classes=["action-btn"]
                    )
                    models_table = gr.Dataframe(
                        headers=["模型名称", "类型", "数据集", "类别数", "追溯数据"],
                        label="",
                        interactive=False,
                    )

                # Help Panel
                with gr.Column(
                    visible=False, elem_classes=["feature-panel"]
                ) as help_panel:
                    with gr.Row(elem_classes=["panel-header"]):
                        gr.HTML("<span class='panel-title'>❓ 使用帮助</span>")
                        close_help = gr.Button("✕", elem_classes=["close-btn"])

                    gr.Markdown("""
                    ### 功能说明
                    
                    **🎨 图像生成**
                    - 从训练好的扩散模型生成图像
                    - 支持自定义类别标签和触发类（水印）生成
                    - 可调节推理步数和质量参数
                    
                    **💧 泄漏模拟**
                    - 模拟特定客户端的模型泄漏场景
                    - 将客户端指纹嵌入到全局模型中
                    - 用于测试追踪系统的有效性
                    
                    **🔍 所有者识别**
                    - 通过指纹匹配识别泄漏模型的所有者
                    - 加载泄漏模型和对应的追溯数据
                    - 返回最佳匹配的客户端和置信度
                    
                    **📊 模型管理**
                    - 查看所有已训练的模型
                    - 检查模型是否包含追溯数据
                    - 快速刷新模型列表
                    
                    ### 快捷操作
                    点击上方的建议卡片可以快速执行常用操作。
                    """)

        # Bottom Input Area
        with gr.Column(elem_classes=["input-area"]):
            with gr.Column(elem_classes=["input-wrapper"]):
                with gr.Column(elem_classes=["input-container"]):
                    # Input field
                    input_text = gr.Textbox(
                        placeholder="发消息...",
                        show_label=False,
                        container=False,
                        elem_classes=["input-field"],
                        lines=1,
                    )

                    # Toolbar
                    gr.HTML("""
                        <div class="toolbar">
                            <button class="tool-btn" onclick="document.querySelector('#btn-tool-gen').click()">
                                <span>🎨</span> 图像生成
                            </button>
                            <button class="tool-btn" onclick="document.querySelector('#btn-tool-leak').click()">
                                <span>💧</span> 泄漏模拟
                            </button>
                            <button class="tool-btn" onclick="document.querySelector('#btn-tool-id').click()">
                                <span>🔍</span> 所有者识别
                            </button>
                            <button class="tool-btn" onclick="document.querySelector('#btn-tool-list').click()">
                                <span>📊</span> 模型列表
                            </button>
                            <button class="tool-btn" onclick="document.querySelector('#btn-tool-help').click()">
                                <span>❓</span> 帮助
                            </button>
                            <div style="flex:1;"></div>
                            <button class="send-btn" onclick="document.querySelector('#btn-send').click()">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <line x1="22" y1="2" x2="11" y2="13"></line>
                                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                                </svg>
                            </button>
                        </div>
                    """)

                    # Hidden buttons for toolbar
                    btn_tool_gen = gr.Button(
                        "gen", visible=False, elem_id="btn-tool-gen"
                    )
                    btn_tool_leak = gr.Button(
                        "leak", visible=False, elem_id="btn-tool-leak"
                    )
                    btn_tool_id = gr.Button("id", visible=False, elem_id="btn-tool-id")
                    btn_tool_list = gr.Button(
                        "list", visible=False, elem_id="btn-tool-list"
                    )
                    btn_tool_help = gr.Button(
                        "help", visible=False, elem_id="btn-tool-help"
                    )
                    btn_send = gr.Button("send", visible=False, elem_id="btn-send")

        # Navigation Logic
        def show_panel(mode):
            """Show specific panel based on mode."""
            return {
                output_container: mode != "",
                gen_panel: mode == "generate",
                leak_panel: mode == "leak",
                identify_panel: mode == "identify",
                list_panel: mode == "list",
                help_panel: mode == "help",
            }

        def close_all():
            """Close all panels."""
            return {
                output_container: False,
                gen_panel: False,
                leak_panel: False,
                identify_panel: False,
                list_panel: False,
                help_panel: False,
            }

        # Chip click handlers
        btn_gen_chip.click(
            lambda: show_panel("generate"),
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )
        btn_leak_chip.click(
            lambda: show_panel("leak"),
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )
        btn_id_chip.click(
            lambda: show_panel("identify"),
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )
        btn_list_chip.click(
            lambda: show_panel("list"),
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )
        btn_help_chip.click(
            lambda: show_panel("help"),
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )

        # Toolbar click handlers
        btn_tool_gen.click(
            lambda: show_panel("generate"),
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )
        btn_tool_leak.click(
            lambda: show_panel("leak"),
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )
        btn_tool_id.click(
            lambda: show_panel("identify"),
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )
        btn_tool_list.click(
            lambda: show_panel("list"),
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )
        btn_tool_help.click(
            lambda: show_panel("help"),
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )

        # Close button handlers
        close_gen.click(
            close_all,
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )
        close_leak.click(
            close_all,
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )
        close_identify.click(
            close_all,
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )
        close_list.click(
            close_all,
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )
        close_help.click(
            close_all,
            outputs=[
                output_container,
                gen_panel,
                leak_panel,
                identify_panel,
                list_panel,
                help_panel,
            ],
        )

        # Generate functionality
        def on_refresh_models():
            return gr.Dropdown(choices=get_model_choices())

        def on_generate(model, cls, num, trigger, gpu, steps_val, seed):
            if not model:
                return "请选择模型", None
            gen = _get_generator()
            models = scan_models("result")
            name = model.split(" (")[0]
            path = next((m["path"] for m in models if m["name"] == name), None)
            if path:
                gen.load_model(path, int(gpu))
            images, st = gen.generate(
                [int(cls)],
                int(num),
                int(seed) if seed else None,
                int(steps_val),
                trigger,
            )
            return st, images

        refresh_btn.click(on_refresh_models, outputs=model_dd)
        gen_btn.click(
            on_generate,
            inputs=[
                model_dd,
                class_label,
                num_images,
                use_trigger,
                gpu_id,
                steps,
                seed,
            ],
            outputs=[gen_status, output_img],
        )

        # Leak simulation functionality
        def on_simulate(source, client, iters, lambda_f, out_dir):
            if not source:
                return "请选择源模型", {}
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
                path,
                int(client),
                gpu_id=0,
                max_iters=int(iters),
                lambda_factor=lambda_f,
                output_dir=out_dir if out_dir else None,
            )
            return msg, result

        sim_btn.click(
            on_simulate,
            inputs=[source_model, client_idx, max_iters, lambda_factor, output_dir],
            outputs=[sim_status, sim_result],
        )

        # Identification functionality
        def on_refresh_leaked():
            return gr.Dropdown(choices=[m[0] for m in get_leaked_models()])

        def on_refresh_trace():
            return gr.Dropdown(choices=[m[0] for m in get_trace_dirs()])

        def on_identify(leaked, trace):
            if not leaked or not trace:
                return "请提供泄漏模型和追溯数据", {}
            tracer = _get_tracer()
            trace_path = next((p for n, p in get_trace_dirs() if n == trace), "")
            success1, msg1, _ = tracer.load_trace_data(trace_path)
            if not success1:
                return f"加载追溯数据错误: {msg1}", {}
            leaked_path = next((p for n, p in get_leaked_models() if n == leaked), "")
            success2, msg2, result = tracer.identify_owner(leaked_path, gpu_id=0)
            return msg2 if success2 else f"识别失败: {msg2}", result if success2 else {}

        refresh_leaked_btn.click(on_refresh_leaked, outputs=leaked_model_dd)
        refresh_trace_btn.click(on_refresh_trace, outputs=trace_model_dd)
        identify_btn.click(
            on_identify,
            inputs=[leaked_model_dd, trace_model_dd],
            outputs=[identify_status, identify_result],
        )

        # Model list functionality
        def refresh_models_table():
            models = scan_models("result")
            return [
                [
                    m["name"],
                    m["type"],
                    m.get("dataset", "N/A"),
                    m.get("num_classes", "N/A"),
                    "✅" if m["has_trace_data"] else "❌",
                ]
                for m in models
            ]

        refresh_list_btn.click(refresh_models_table, outputs=models_table)

    return app


def main():
    parser = argparse.ArgumentParser(description="FedTracker WebUI")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()

    os.makedirs("webui/static/outputs", exist_ok=True)

    app = create_app()

    print(f"\n{'=' * 60}")
    print("FedTracker WebUI - Doubao Style")
    print(f"{'=' * 60}")
    print(f"Server: http://{args.host}:{args.port}")
    print(f"{'=' * 60}\n")

    app.launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
