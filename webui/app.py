# -*- coding: UTF-8 -*-
"""
FedTracker WebUI - 深色主题界面
卡片式导航的现代化界面设计
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
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.gradio-container { max-width: 100% !important; padding: 0 !important; background: var(--bg-primary) !important; }

#header { background: var(--bg-secondary); border-bottom: 1px solid var(--border-color); padding: 20px 40px; text-align: center; }
#header h1 { font-size: 28px; font-weight: 700; background: var(--accent-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; }
#header p { color: var(--text-secondary); font-size: 14px; margin-top: 4px; }

.gradio-dropdown, .gradio-textbox, .gradio-number, .gradio-slider {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 12px !important;
}

.gradio-dropdown:hover, .gradio-textbox:hover, .gradio-number:hover { border-color: var(--accent-primary) !important; }
.gradio-dropdown input, .gradio-textbox input, .gradio-number input { color: var(--text-primary) !important; }
.gradio-dropdown label, .gradio-textbox label, .gradio-number label { color: var(--text-secondary) !important; font-size: 13px !important; margin-bottom: 8px !important; }

.gradio-button { border-radius: 12px !important; font-weight: 600 !important; transition: all 0.3s !important; }
.primary-btn, button.primary { background: var(--accent-gradient) !important; border: none !important; color: white !important; box-shadow: 0 4px 14px rgba(124, 58, 237, 0.4) !important; }
.primary-btn:hover, button.primary:hover { transform: translateY(-2px) !important; box-shadow: 0 6px 20px rgba(124, 58, 237, 0.6) !important; }

.gradio-accordion { background: var(--bg-secondary) !important; border: 1px solid var(--border-color) !important; border-radius: 12px !important; }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); }
::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent-primary); }
"""

CSS = DARK_THEME_CSS


def create_ui():
    model_dirs = find_model_dirs("./result")
    default_model = model_dirs[0] if model_dirs else None

    with gr.Blocks(css=CSS, theme=gr.themes.Base()) as demo:
        with gr.Column():
            gr.HTML("""
                <div id="header">
                    <h1>FedTracker 水印追踪系统</h1>
                    <p>联邦学习扩散模型所有权验证与可追溯平台</p>
                </div>
            """)

            # 首页 - 三个功能卡片
            with gr.Column(visible=True) as home_page:
                gr.HTML("""
                    <div id="hero" style="text-align: center; padding: 60px 20px;">
                        <h2 style="font-size: 42px; font-weight: 800; color: #ffffff; margin-bottom: 16px;">欢迎使用 FedTracker</h2>
                        <p style="font-size: 18px; color: #a0a0a0; max-width: 700px; margin: 0 auto 48px;">
                            专业的联邦学习水印追踪系统，支持扩散模型的图片生成、泄漏模拟与所有者识别。
                        </p>
                    </div>
                """)

                with gr.Row():
                    # 卡片1：图片生成
                    with gr.Column():
                        gr.HTML("""
                            <div style="background: #1a1a1a; border: 1px solid #333; border-radius: 24px; padding: 40px 32px; text-align: center; min-height: 340px;">
                                <div style="width: 64px; height: 64px; background: linear-gradient(135deg, rgba(124,58,237,0.15) 0%, rgba(168,85,247,0.15) 100%); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 32px; margin: 0 auto 20px;">🎨</div>
                                <div style="font-size: 24px; font-weight: 700; color: #ffffff; margin-bottom: 12px;">图片生成</div>
                                <div style="font-size: 15px; line-height: 1.6; color: #a0a0a0; margin-bottom: 20px;">
                                    从训练好的扩散模型生成高质量图片，支持自定义类标、推理步数和水印触发器。
                                </div>
                            </div>
                        """)
                        gen_btn = gr.Button("开始生成 →", size="lg", variant="primary")

                    # 卡片2：泄漏模拟
                    with gr.Column():
                        gr.HTML("""
                            <div style="background: #1a1a1a; border: 1px solid #333; border-radius: 24px; padding: 40px 32px; text-align: center; min-height: 340px;">
                                <div style="width: 64px; height: 64px; background: linear-gradient(135deg, rgba(124,58,237,0.15) 0%, rgba(168,85,247,0.15) 100%); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 32px; margin: 0 auto 20px;">🔍</div>
                                <div style="font-size: 24px; font-weight: 700; color: #ffffff; margin-bottom: 12px;">泄漏模拟</div>
                                <div style="font-size: 15px; line-height: 1.6; color: #a0a0a0; margin-bottom: 20px;">
                                    模拟联邦学习场景中的客户端模型泄漏，测试追踪系统的鲁棒性。
                                </div>
                            </div>
                        """)
                        leak_btn = gr.Button("开始模拟 →", size="lg", variant="primary")

                    # 卡片3：所有者识别
                    with gr.Column():
                        gr.HTML("""
                            <div style="background: #1a1a1a; border: 1px solid #333; border-radius: 24px; padding: 40px 32px; text-align: center; min-height: 340px;">
                                <div style="width: 64px; height: 64px; background: linear-gradient(135deg, rgba(124,58,237,0.15) 0%, rgba(168,85,247,0.15) 100%); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 32px; margin: 0 auto 20px;">🎯</div>
                                <div style="font-size: 24px; font-weight: 700; color: #ffffff; margin-bottom: 12px;">所有者识别</div>
                                <div style="font-size: 15px; line-height: 1.6; color: #a0a0a0; margin-bottom: 20px;">
                                    基于指纹匹配技术识别泄漏模型的所有者，提供精确的归属判定和置信度评分。
                                </div>
                            </div>
                        """)
                        identify_btn = gr.Button(
                            "开始识别 →", size="lg", variant="primary"
                        )

            # 页面1：图片生成
            with gr.Column(visible=False) as generation_page:
                with gr.Row():
                    # 左侧边栏：参数设置
                    with gr.Column(scale=1, min_width=300):
                        gr.HTML("""
                            <div style="background: #1a1a1a; border-radius: 16px; padding: 24px; margin-bottom: 20px;">
                                <h3 style="margin: 0 0 20px 0; color: #fff; font-size: 16px;">⚙️ 模型设置</h3>
                            </div>
                        """)

                        model_dropdown = gr.Dropdown(
                            choices=model_dirs,
                            value=default_model,
                            label="选择模型",
                            info="从训练好的模型中选择",
                            interactive=True,
                        )

                        with gr.Accordion("🔧 高级设置", open=False):
                            class_label = gr.Number(
                                value=0, label="类标签", info="目标类别 (CIFAR: 0-9)"
                            )
                            num_images = gr.Number(
                                value=4, label="生成数量", info="一次生成的图片数"
                            )
                            num_steps = gr.Number(
                                value=100, label="推理步数", info="去噪步骤 (50-1000)"
                            )
                            seed = gr.Number(
                                value=42, label="随机种子", info="可重复性控制"
                            )
                            trigger_check = gr.Checkbox(
                                label="生成水印图片",
                                value=False,
                                info="使用触发器类生成",
                            )
                            device = gr.Radio(
                                choices=["cuda", "cpu"], value="cuda", label="计算设备"
                            )

                        generate_btn = gr.Button(
                            "🚀 开始生成", size="lg", variant="primary"
                        )
                        back_btn1 = gr.Button(
                            "← 返回首页", size="lg", variant="secondary"
                        )

                    # 右侧：输出区域
                    with gr.Column(scale=2):
                        # 上方：图片展示
                        gr.HTML(
                            '<h3 style="color: #fff; margin-bottom: 16px;">📷 生成结果</h3>'
                        )
                        output_gallery = gr.Gallery(
                            label="生成的图片",
                            show_label=False,
                            columns=4,
                            rows=2,
                            height=400,
                            object_fit="contain",
                        )

                        # 下方：状态和路径
                        gr.HTML(
                            '<h3 style="color: #fff; margin: 20px 0 16px;">📊 状态信息</h3>'
                        )
                        status_output = gr.Textbox(
                            lines=3,
                            interactive=False,
                            placeholder="点击「开始生成」按钮...",
                        )

                        output_path = gr.Textbox(
                            value="图片将保存到：./webui/static/outputs/",
                            interactive=False,
                            show_label=False,
                        )

            # 页面2：泄漏模拟
            with gr.Column(visible=False) as leak_page:
                with gr.Row():
                    # 左侧：参数设置
                    with gr.Column(scale=1, min_width=300):
                        gr.HTML("""
                            <div style="background: #1a1a1a; border-radius: 16px; padding: 24px; margin-bottom: 20px;">
                                <h3 style="margin: 0 0 20px 0; color: #fff; font-size: 16px;">⚙️ 模拟配置</h3>
                            </div>
                        """)

                        leak_model = gr.Dropdown(
                            choices=[
                                m for m in model_dirs if has_trace_data(f"./result/{m}")
                            ],
                            label="选择源模型",
                            info="包含追踪数据的模型",
                        )

                        client_idx = gr.Dropdown(
                            label="客户端索引", info="选择要模拟的客户端"
                        )

                        leak_output = gr.Textbox(
                            label="输出文件名",
                            value="leaked_model.pth",
                            info="泄漏模型保存名",
                        )

                        simulate_btn = gr.Button(
                            "🎭 开始模拟", size="lg", variant="primary"
                        )
                        back_btn2 = gr.Button(
                            "← 返回首页", size="lg", variant="secondary"
                        )

                    # 右侧：输出区域
                    with gr.Column(scale=2):
                        gr.HTML(
                            '<h3 style="color: #fff; margin-bottom: 16px;">📋 模拟结果</h3>'
                        )
                        leak_result = gr.Textbox(
                            lines=10,
                            interactive=False,
                            placeholder="点击「开始模拟」按钮...",
                        )

            # 页面3：所有者识别
            with gr.Column(visible=False) as identify_page:
                with gr.Row():
                    # 左侧：输入设置
                    with gr.Column(scale=1, min_width=300):
                        gr.HTML("""
                            <div style="background: #1a1a1a; border-radius: 16px; padding: 24px; margin-bottom: 20px;">
                                <h3 style="margin: 0 0 20px 0; color: #fff; font-size: 16px;">⚙️ 识别配置</h3>
                            </div>
                        """)

                        leaked_model = gr.Dropdown(
                            choices=find_leaked_models(LEAK_TEST_DIR),
                            label="泄漏模型",
                            info="选择泄漏的模型文件",
                        )

                        refresh_btn = gr.Button("🔄 刷新列表", size="sm")

                        source_model = gr.Dropdown(
                            choices=[
                                m for m in model_dirs if has_trace_data(f"./result/{m}")
                            ],
                            label="源模型",
                            info="包含追踪数据的模型",
                        )

                        identify_btn2 = gr.Button(
                            "🎯 开始识别", size="lg", variant="primary"
                        )
                        back_btn3 = gr.Button(
                            "← 返回首页", size="lg", variant="secondary"
                        )

                    # 右侧：输出区域
                    with gr.Column(scale=2):
                        gr.HTML(
                            '<h3 style="color: #fff; margin-bottom: 16px;">🏆 识别结果</h3>'
                        )
                        identify_result = gr.Textbox(
                            lines=8,
                            interactive=False,
                            placeholder="点击「开始识别」按钮...",
                        )

                        confidence = gr.Number(label="置信度评分", interactive=False)

        # 页面切换函数
        def show_generation():
            return {
                home_page: gr.Column(visible=False),
                generation_page: gr.Column(visible=True),
                leak_page: gr.Column(visible=False),
                identify_page: gr.Column(visible=False),
            }

        def show_leak():
            return {
                home_page: gr.Column(visible=False),
                generation_page: gr.Column(visible=False),
                leak_page: gr.Column(visible=True),
                identify_page: gr.Column(visible=False),
            }

        def show_identify():
            return {
                home_page: gr.Column(visible=False),
                generation_page: gr.Column(visible=False),
                leak_page: gr.Column(visible=False),
                identify_page: gr.Column(visible=True),
            }

        def show_home():
            return {
                home_page: gr.Column(visible=True),
                generation_page: gr.Column(visible=False),
                leak_page: gr.Column(visible=False),
                identify_page: gr.Column(visible=False),
            }

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

        # 首页按钮事件
        gen_btn.click(
            show_generation,
            inputs=[],
            outputs=[home_page, generation_page, leak_page, identify_page],
        )
        leak_btn.click(
            show_leak,
            inputs=[],
            outputs=[home_page, generation_page, leak_page, identify_page],
        )
        identify_btn.click(
            show_identify,
            inputs=[],
            outputs=[home_page, generation_page, leak_page, identify_page],
        )

        # 返回首页按钮
        back_btn1.click(
            show_home,
            inputs=[],
            outputs=[home_page, generation_page, leak_page, identify_page],
        )
        back_btn2.click(
            show_home,
            inputs=[],
            outputs=[home_page, generation_page, leak_page, identify_page],
        )
        back_btn3.click(
            show_home,
            inputs=[],
            outputs=[home_page, generation_page, leak_page, identify_page],
        )

        # 下拉框联动
        leak_model.change(update_client_list, [leak_model], [client_idx])
        refresh_btn.click(refresh_leaked, [], [leaked_model])

        # 生成功能
        def generate_wrapper(model_name, class_lbl, num_img, steps, sd, trigger, dev):
            if not model_name:
                return None, "❌ 请先选择模型", ""

            model_dir = f"./result/{model_name}"
            output_base = get_default_output_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path_dir = osp.join(output_base, f"gen_{timestamp}")

            trigger_class = None
            if trigger:
                args_path = osp.join(model_dir, "args.txt")
                if osp.exists(args_path):
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
                return None, f"❌ 生成失败：{error}", ""

            if images:
                os.makedirs(output_path_dir, exist_ok=True)
                paths = save_images(images, output_path_dir)
                return (
                    paths,
                    f"✅ 成功生成 {len(images)} 张图片",
                    f"保存路径：{output_path_dir}",
                )

            return None, "❌ 未生成图片", ""

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
            [output_gallery, status_output, output_path],
        )

        # 泄漏模拟功能
        def simulate_wrapper(model, client, output_name):
            if not model:
                return "❌ 请选择源模型"
            if client is None:
                return "❌ 请选择客户端索引"

            os.makedirs(LEAK_TEST_DIR, exist_ok=True)
            checkpoint = f"./result/{model}/model_final.pth"
            trace_dir = f"./result/{model}/trace_data"
            output = osp.join(LEAK_TEST_DIR, output_name)

            result, error = simulate_client_leak(
                checkpoint, trace_dir, int(client), output
            )

            if error:
                return f"❌ 模拟失败：{error}"

            return f"✅ 模拟成功！\n泄漏模型已保存至：{output}"

        simulate_btn.click(
            simulate_wrapper, [leak_model, client_idx, leak_output], [leak_result]
        )

        # 所有者识别功能
        def identify_wrapper(leaked, source):
            if not leaked:
                return "❌ 请选择泄漏模型", 0
            if not source:
                return "❌ 请选择源模型", 0

            leaked_path = osp.join(LEAK_TEST_DIR, leaked)
            trace_dir = f"./result/{source}/trace_data"

            client, conf, error = identify_owner(leaked_path, trace_dir)

            if error:
                return f"❌ 识别失败：{error}", 0

            result = f"""✅ 所有者识别成功！

━━━━━━━━━━━━━━━━━━━━━━
📋 结果详情
━━━━━━━━━━━━━━━━━━━━━━
🆔 客户端ID：{client}
📊 置信度：{conf:.2%}

💡 说明：该泄漏模型最可能属于客户端 {client}"""

            return result, float(conf)

        identify_btn2.click(
            identify_wrapper,
            [leaked_model, source_model],
            [identify_result, confidence],
        )

    return demo


def main():
    parser = argparse.ArgumentParser(description="FedTracker WebUI - 深色主题")
    parser.add_argument("--port", type=int, default=7860, help="服务端口")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="服务主机")
    parser.add_argument("--share", action="store_true", help="创建公网分享链接")
    args = parser.parse_args()

    demo = create_ui()
    print(f"\n{'=' * 60}")
    print(f"FedTracker WebUI - 深色主题")
    print(f"{'=' * 60}")
    print(f"本地访问：http://{args.host}:{args.port}")
    if args.share:
        print(f"公网链接将自动生成...")
    print(f"{'=' * 60}\n")

    demo.launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
