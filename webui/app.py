#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
FedTracker WebUI - 豆包风格极简界面
"""

import gradio as gr
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入功能模块
try:
    from webui.modules import (
        scan_available_models,
        scan_leaked_models,
        generate_images,
        simulate_leak,
        identify_owner,
    )

    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入功能模块: {e}")
    MODULES_AVAILABLE = False

# 自定义CSS - 豆包风格
CUSTOM_CSS = """
:root {
    --primary-bg: #ffffff;
    --secondary-bg: #fafafa;
    --border-color: #e8e8e8;
    --text-primary: #1a1a1a;
    --text-secondary: #666666;
    --accent-color: #4285f4;
    --accent-light: #e3f2fd;
    --shadow-soft: 0 1px 3px rgba(0,0,0,0.04);
    --shadow-hover: 0 4px 20px rgba(66, 133, 244, 0.15);
}

* {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

/* 主容器样式 */
.gradio-container {
    background: var(--primary-bg) !important;
}

/* 导航栏 */
.nav-container {
    display: flex;
    justify-content: center;
    gap: 12px;
    padding: 20px 0;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 40px;
}

/* 首页样式 */
.home-container {
    max-width: 700px;
    margin: 0 auto;
    padding: 60px 20px;
}

.main-title {
    text-align: center;
    font-size: 42px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 16px;
    letter-spacing: -0.5px;
}

.subtitle {
    text-align: center;
    font-size: 16px;
    color: var(--text-secondary);
    margin-bottom: 60px;
}

/* 功能卡片 */
.feature-card {
    background: var(--primary-bg);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 16px;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: var(--shadow-soft);
}

.feature-card:hover {
    border-color: var(--accent-color);
    box-shadow: var(--shadow-hover);
    transform: translateY(-2px);
}

.icon-box {
    width: 52px;
    height: 52px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 26px;
    flex-shrink: 0;
}

.icon-blue { background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); }
.icon-pink { background: linear-gradient(135deg, #fce4ec 0%, #f8bbd9 100%); }
.icon-green { background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); }
.icon-purple { background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%); }

.feature-content {
    flex: 1;
}

.feature-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
}

.feature-desc {
    font-size: 14px;
    color: var(--text-secondary);
}

/* 页面样式 */
.page-container {
    max-width: 1000px;
    margin: 0 auto;
    padding: 20px;
}

.page-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 32px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border-color);
}

.page-title {
    font-size: 28px;
    font-weight: 600;
    color: var(--text-primary);
}

.page-icon {
    font-size: 32px;
}

/* 表单卡片 */
.form-card {
    background: var(--primary-bg);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 28px;
    margin-bottom: 24px;
}

.form-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-color);
}

/* 结果卡片 */
.result-card {
    background: var(--secondary-bg);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 24px;
    min-height: 200px;
}

/* 按钮样式 */
button.primary {
    background: var(--text-primary) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 28px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

button.primary:hover {
    background: #333 !important;
    transform: translateY(-1px);
}

/* 导航按钮 */
.nav-btn {
    background: #f5f5f5;
    border: none;
    border-radius: 20px;
    padding: 10px 20px;
    font-size: 14px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s ease;
}

.nav-btn:hover {
    background: #e8e8e8;
}

.nav-btn.active {
    background: var(--text-primary);
    color: white;
}

/* 输入框样式 */
input, select, textarea {
    border-radius: 10px !important;
    border: 1px solid var(--border-color) !important;
    transition: border-color 0.2s ease;
}

input:focus, select:focus, textarea:focus {
    border-color: var(--accent-color) !important;
    box-shadow: 0 0 0 3px rgba(66, 133, 244, 0.1) !important;
}

/* Gallery样式 */
.gallery-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 12px;
}

/* 状态标签 */
.status-badge {
    display: inline-flex;
    align-items: center;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 500;
}

.status-success {
    background: #e8f5e9;
    color: #2e7d32;
}

.status-error {
    background: #ffebee;
    color: #c62828;
}

/* 数据表格样式 */
.data-table {
    width: 100%;
    border-collapse: collapse;
}

.data-table th {
    text-align: left;
    padding: 12px;
    border-bottom: 2px solid var(--border-color);
    font-weight: 600;
    color: var(--text-secondary);
}

.data-table td {
    padding: 12px;
    border-bottom: 1px solid var(--border-color);
}

.data-table tr:hover {
    background: var(--secondary-bg);
}

/* 高亮第一行 */
.highlight-row {
    background: linear-gradient(90deg, rgba(66,133,244,0.05) 0%, transparent 100%);
    font-weight: 500;
}
"""


# 获取模型列表
def get_model_choices():
    if MODULES_AVAILABLE:
        models = scan_available_models()
        return [m["name"] for m in models] if models else ["暂无模型"]
    return ["请先训练模型"]


def get_leaked_model_choices():
    if MODULES_AVAILABLE:
        models = scan_leaked_models()
        return [m["name"] for m in models] if models else ["暂无泄露模型"]
    return ["暂无泄露模型"]


# 创建应用
def create_app():
    with gr.Blocks(css=CUSTOM_CSS, title="FedTracker") as app:
        # ===== 首页 =====
        with gr.Column(visible=True, elem_classes="home-container") as home_page:
            gr.HTML("""
                <div style="text-align: center; padding: 40px 0;">
                    <h1 class="main-title">FedTracker</h1>
                    <p class="subtitle">联邦学习水印追踪系统</p>
                </div>
            """)

            # 功能卡片
            with gr.Column():
                with gr.Row(elem_classes="feature-card"):
                    gr.HTML("""
                        <div class="icon-box icon-blue">🎨</div>
                        <div class="feature-content">
                            <div class="feature-title">图像生成</div>
                            <div class="feature-desc">从训练好的扩散模型生成高质量图像</div>
                        </div>
                    """)
                    go_generate = gr.Button("进入", visible=False)

                go_generate_visible = gr.Button(
                    "🎨 图像生成", elem_classes="feature-card", visible=True
                )

                with gr.Row(elem_classes="feature-card"):
                    gr.HTML("""
                        <div class="icon-box icon-pink">🔓</div>
                        <div class="feature-content">
                            <div class="feature-title">泄露模拟</div>
                            <div class="feature-desc">模拟客户端模型泄露场景，生成泄露模型</div>
                        </div>
                    """)
                    go_leak = gr.Button("进入", visible=False)

                go_leak_visible = gr.Button(
                    "🔓 泄露模拟", elem_classes="feature-card", visible=True
                )

                with gr.Row(elem_classes="feature-card"):
                    gr.HTML("""
                        <div class="icon-box icon-green">🔍</div>
                        <div class="feature-content">
                            <div class="feature-title">所有者识别</div>
                            <div class="feature-desc">通过指纹追踪识别泄露模型的真实所有者</div>
                        </div>
                    """)
                    go_identify = gr.Button("进入", visible=False)

                go_identify_visible = gr.Button(
                    "🔍 所有者识别", elem_classes="feature-card", visible=True
                )

        # ===== 图像生成页面 =====
        with gr.Column(visible=False, elem_classes="page-container") as generate_page:
            gr.HTML("""
                <div class="page-header">
                    <span class="page-icon">🎨</span>
                    <span class="page-title">图像生成</span>
                </div>
            """)

            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Group(elem_classes="form-card"):
                        gr.HTML('<div class="form-title">生成参数</div>')

                        gen_model = gr.Dropdown(
                            label="选择模型",
                            choices=get_model_choices(),
                            value=get_model_choices()[0]
                            if get_model_choices()
                            else None,
                        )

                        gen_class = gr.Number(
                            label="类别标签", value=0, minimum=0, maximum=9, step=1
                        )

                        gen_count = gr.Number(
                            label="生成数量", value=4, minimum=1, maximum=16, step=1
                        )

                        gen_steps = gr.Number(
                            label="推理步数", value=50, minimum=10, maximum=200, step=10
                        )

                        gen_seed = gr.Number(label="随机种子", value=42)

                        gen_btn = gr.Button("开始生成", variant="primary")

                        gen_refresh = gr.Button("🔄 刷新模型列表", size="sm")

                with gr.Column(scale=2):
                    with gr.Group(elem_classes="result-card"):
                        gr.HTML('<div class="form-title">生成结果</div>')
                        gen_gallery = gr.Gallery(
                            label="",
                            show_label=False,
                            columns=4,
                            rows=2,
                            height=400,
                            object_fit="cover",
                        )
                        gen_status = gr.Textbox(
                            label="状态", value="准备就绪", interactive=False
                        )

            back_gen = gr.Button("← 返回首页")

        # ===== 泄露模拟页面 =====
        with gr.Column(visible=False, elem_classes="page-container") as leak_page:
            gr.HTML("""
                <div class="page-header">
                    <span class="page-icon">🔓</span>
                    <span class="page-title">泄露模拟</span>
                </div>
            """)

            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Group(elem_classes="form-card"):
                        gr.HTML('<div class="form-title">模拟参数</div>')

                        leak_model = gr.Dropdown(
                            label="选择源模型",
                            choices=get_model_choices(),
                            value=get_model_choices()[0]
                            if get_model_choices()
                            else None,
                        )

                        leak_client = gr.Number(
                            label="客户端索引", value=0, minimum=0, step=1
                        )

                        leak_output = gr.Textbox(
                            label="输出文件名", value="leaked_model_client_0.pth"
                        )

                        leak_btn = gr.Button("开始模拟", variant="primary")

                        leak_refresh = gr.Button("🔄 刷新模型列表", size="sm")

                with gr.Column(scale=2):
                    with gr.Group(elem_classes="result-card"):
                        gr.HTML('<div class="form-title">模拟结果</div>')
                        leak_result = gr.Textbox(
                            label="",
                            lines=12,
                            value="点击「开始模拟」按钮开始...",
                            interactive=False,
                        )

            back_leak = gr.Button("← 返回首页")

        # ===== 所有者识别页面 =====
        with gr.Column(visible=False, elem_classes="page-container") as identify_page:
            gr.HTML("""
                <div class="page-header">
                    <span class="page-icon">🔍</span>
                    <span class="page-title">所有者识别</span>
                </div>
            """)

            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Group(elem_classes="form-card"):
                        gr.HTML('<div class="form-title">识别参数</div>')

                        id_leaked = gr.Dropdown(
                            label="选择泄露模型",
                            choices=get_leaked_model_choices(),
                            value=get_leaked_model_choices()[0]
                            if get_leaked_model_choices()
                            else None,
                        )

                        id_source = gr.Dropdown(
                            label="选择源模型",
                            choices=get_model_choices(),
                            value=get_model_choices()[0]
                            if get_model_choices()
                            else None,
                        )

                        id_btn = gr.Button("开始识别", variant="primary")

                        id_refresh = gr.Button("🔄 刷新模型列表", size="sm")

                with gr.Column(scale=2):
                    with gr.Group(elem_classes="result-card"):
                        gr.HTML('<div class="form-title">识别结果</div>')

                        with gr.Row():
                            id_owner = gr.Textbox(
                                label="最可能的所有者", value="-", interactive=False
                            )
                            id_confidence = gr.Textbox(
                                label="置信度", value="-", interactive=False
                            )

                        id_top5 = gr.Dataframe(
                            headers=["排名", "客户端", "匹配分数"],
                            label="Top 5 候选结果",
                            row_count=5,
                        )

                        id_status = gr.Textbox(
                            label="详细信息",
                            value="点击「开始识别」按钮开始...",
                            interactive=False,
                        )

            back_id = gr.Button("← 返回首页")

        # ===== 事件处理 =====

        # 页面切换函数
        def show_page(page_name):
            return {
                home_page: gr.update(visible=(page_name == "home")),
                generate_page: gr.update(visible=(page_name == "generate")),
                leak_page: gr.update(visible=(page_name == "leak")),
                identify_page: gr.update(visible=(page_name == "identify")),
            }

        # 首页按钮事件
        go_generate_visible.click(
            lambda: show_page("generate"),
            outputs=[home_page, generate_page, leak_page, identify_page],
        )
        go_leak_visible.click(
            lambda: show_page("leak"),
            outputs=[home_page, generate_page, leak_page, identify_page],
        )
        go_identify_visible.click(
            lambda: show_page("identify"),
            outputs=[home_page, generate_page, leak_page, identify_page],
        )

        # 返回按钮事件
        back_gen.click(
            lambda: show_page("home"),
            outputs=[home_page, generate_page, leak_page, identify_page],
        )
        back_leak.click(
            lambda: show_page("home"),
            outputs=[home_page, generate_page, leak_page, identify_page],
        )
        back_id.click(
            lambda: show_page("home"),
            outputs=[home_page, generate_page, leak_page, identify_page],
        )

        # 刷新模型列表
        def refresh_models():
            return {
                gen_model: gr.update(choices=get_model_choices()),
                leak_model: gr.update(choices=get_model_choices()),
                id_source: gr.update(choices=get_model_choices()),
                id_leaked: gr.update(choices=get_leaked_model_choices()),
            }

        gen_refresh.click(
            refresh_models, outputs=[gen_model, leak_model, id_source, id_leaked]
        )
        leak_refresh.click(
            refresh_models, outputs=[gen_model, leak_model, id_source, id_leaked]
        )
        id_refresh.click(
            refresh_models, outputs=[gen_model, leak_model, id_source, id_leaked]
        )

        # 图像生成
        def do_generate(model, class_label, num, seed, steps):
            if not MODULES_AVAILABLE:
                return [], "错误: 功能模块未加载"
            images, status = generate_images(
                model, int(class_label), int(num), int(seed), int(steps)
            )
            return images, status

        gen_btn.click(
            do_generate,
            inputs=[gen_model, gen_class, gen_count, gen_seed, gen_steps],
            outputs=[gen_gallery, gen_status],
        )

        # 泄露模拟
        def do_simulate(model, client, output):
            if not MODULES_AVAILABLE:
                return "错误: 功能模块未加载"
            result = simulate_leak(model, int(client), output)
            return result

        leak_btn.click(
            do_simulate,
            inputs=[leak_model, leak_client, leak_output],
            outputs=[leak_result],
        )

        # 所有者识别
        def do_identify(leaked, source):
            if not MODULES_AVAILABLE:
                return "-", "-", [], "错误: 功能模块未加载"
            owner, conf, top5, status = identify_owner(leaked, source)
            return owner, conf, top5, status

        id_btn.click(
            do_identify,
            inputs=[id_leaked, id_source],
            outputs=[id_owner, id_confidence, id_top5, id_status],
        )

    return app


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FedTracker WebUI")
    parser.add_argument("--port", type=int, default=7860, help="本地服务端口")
    parser.add_argument("--share", action="store_true", help="启用Gradio公网分享")
    parser.add_argument("--auth", type=str, help="设置用户名:密码 (如 admin:123456)")
    args = parser.parse_args()

    app = create_app()

    launch_kwargs = {
        "server_name": "0.0.0.0",
        "server_port": args.port,
        "share": args.share,
    }

    if args.auth:
        username, password = args.auth.split(":")
        launch_kwargs["auth"] = (username, password)
        print(f"已启用身份验证 - 用户名: {username}")

    print(f"启动 WebUI...")
    print(f"本地访问: http://localhost:{args.port}")
    if args.share:
        print("正在生成公网链接...")
    print("")

    app.launch(**launch_kwargs)
