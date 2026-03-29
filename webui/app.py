# -*- coding: UTF-8 -*-
"""
FedTracker WebUI - 深色主题界面
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

DARK_CSS = """
:root {
    --bg-primary: #0f0f0f;
    --bg-secondary: #1a1a1a;
    --bg-tertiary: #232323;
    --text-primary: #ffffff;
    --text-secondary: #a0a0a0;
    --accent: #7c3aed;
}
body { background: var(--bg-primary) !important; color: var(--text-primary) !important; }
.gradio-container { max-width: 100% !important; }
.gradio-dropdown, .gradio-textbox, .gradio-number { background: var(--bg-tertiary) !important; border: 1px solid #333 !important; border-radius: 8px !important; }
.gradio-dropdown input, .gradio-textbox input, .gradio-number input { color: var(--text-primary) !important; }
"""


def create_ui():
    model_dirs = find_model_dirs("./result")
    default_model = model_dirs[0] if model_dirs else None

    with gr.Blocks(css=DARK_CSS, theme=gr.themes.Base()) as demo:
        # 顶部标题
        gr.HTML(
            '<div style="text-align: center; padding: 20px; background: #1a1a1a; border-bottom: 1px solid #333;"><h1 style="color: #7c3aed; margin: 0;">FedTracker 水印追踪系统</h1><p style="color: #a0a0a0; margin: 5px 0;">联邦学习扩散模型所有权验证与可追溯平台</p></div>'
        )

        # ========== 首页 ==========
        with gr.Column(visible=True) as home_page:
            gr.HTML(
                '<div style="text-align: center; padding: 40px 20px;"><h2 style="color: #fff; margin-bottom: 10px;">欢迎使用 FedTracker</h2><p style="color: #a0a0a0;">选择功能开始使用</p></div>'
            )

            with gr.Row():
                # 卡片1
                with gr.Column():
                    gr.HTML(
                        '<div style="background: #1a1a1a; border: 1px solid #333; border-radius: 16px; padding: 30px; text-align: center; min-height: 250px;"><div style="font-size: 40px; margin-bottom: 15px;">🎨</div><h3 style="color: #fff; margin-bottom: 10px;">图片生成</h3><p style="color: #a0a0a0; font-size: 14px;">从训练好的扩散模型生成高质量图片</p></div>'
                    )
                    gen_btn = gr.Button("开始生成 →", size="lg", variant="primary")

                # 卡片2
                with gr.Column():
                    gr.HTML(
                        '<div style="background: #1a1a1a; border: 1px solid #333; border-radius: 16px; padding: 30px; text-align: center; min-height: 250px;"><div style="font-size: 40px; margin-bottom: 15px;">🔍</div><h3 style="color: #fff; margin-bottom: 10px;">泄漏模拟</h3><p style="color: #a0a0a0; font-size: 14px;">模拟联邦学习中的客户端模型泄漏</p></div>'
                    )
                    leak_btn = gr.Button("开始模拟 →", size="lg", variant="primary")

                # 卡片3
                with gr.Column():
                    gr.HTML(
                        '<div style="background: #1a1a1a; border: 1px solid #333; border-radius: 16px; padding: 30px; text-align: center; min-height: 250px;"><div style="font-size: 40px; margin-bottom: 15px;">🎯</div><h3 style="color: #fff; margin-bottom: 10px;">所有者识别</h3><p style="color: #a0a0a0; font-size: 14px;">识别泄漏模型的所有者</p></div>'
                    )
                    identify_btn = gr.Button("开始识别 →", size="lg", variant="primary")

        # ========== 图片生成页面 ==========
        with gr.Column(visible=False) as generation_page:
            with gr.Row():
                # 左侧边栏
                with gr.Column(scale=1, min_width=280):
                    gr.HTML(
                        '<h3 style="color: #fff; margin-bottom: 15px;">⚙️ 模型设置</h3>'
                    )

                    model_dropdown = gr.Dropdown(
                        choices=model_dirs,
                        value=default_model,
                        label="选择模型",
                        interactive=True,
                    )

                    with gr.Accordion("高级设置", open=False):
                        class_label = gr.Number(value=0, label="类标签")
                        num_images = gr.Number(value=4, label="生成数量")
                        num_steps = gr.Number(value=100, label="推理步数")
                        seed = gr.Number(value=42, label="随机种子")
                        trigger_check = gr.Checkbox(label="生成水印图片", value=False)
                        device = gr.Radio(
                            choices=["cuda", "cpu"], value="cuda", label="计算设备"
                        )

                    generate_btn = gr.Button(
                        "🚀 开始生成", size="lg", variant="primary"
                    )
                    back_btn1 = gr.Button("← 返回首页", size="lg")

                # 右侧输出
                with gr.Column(scale=2):
                    gr.HTML(
                        '<h3 style="color: #fff; margin-bottom: 15px;">📷 生成结果</h3>'
                    )
                    output_gallery = gr.Gallery(
                        label="图片", show_label=False, columns=4, rows=2, height=350
                    )
                    status_output = gr.Textbox(lines=2, interactive=False, label="状态")
                    output_path = gr.Textbox(
                        value="保存路径：./webui/static/outputs/",
                        interactive=False,
                        show_label=False,
                    )

        # ========== 泄漏模拟页面 ==========
        with gr.Column(visible=False) as leak_page:
            with gr.Row():
                # 左侧
                with gr.Column(scale=1, min_width=280):
                    gr.HTML(
                        '<h3 style="color: #fff; margin-bottom: 15px;">⚙️ 模拟配置</h3>'
                    )

                    leak_model = gr.Dropdown(
                        choices=[
                            m for m in model_dirs if has_trace_data(f"./result/{m}")
                        ],
                        label="源模型",
                    )
                    client_idx = gr.Dropdown(label="客户端索引")
                    leak_output = gr.Textbox(
                        value="leaked_model.pth", label="输出文件名"
                    )

                    simulate_btn = gr.Button(
                        "🎭 开始模拟", size="lg", variant="primary"
                    )
                    back_btn2 = gr.Button("← 返回首页", size="lg")

                # 右侧
                with gr.Column(scale=2):
                    gr.HTML(
                        '<h3 style="color: #fff; margin-bottom: 15px;">📋 模拟结果</h3>'
                    )
                    leak_result = gr.Textbox(lines=10, interactive=False, label="结果")

        # ========== 所有者识别页面 ==========
        with gr.Column(visible=False) as identify_page:
            with gr.Row():
                # 左侧
                with gr.Column(scale=1, min_width=280):
                    gr.HTML(
                        '<h3 style="color: #fff; margin-bottom: 15px;">⚙️ 识别配置</h3>'
                    )

                    leaked_model = gr.Dropdown(
                        choices=find_leaked_models(LEAK_TEST_DIR), label="泄漏模型"
                    )
                    refresh_btn = gr.Button("🔄 刷新列表", size="sm")

                    source_model = gr.Dropdown(
                        choices=[
                            m for m in model_dirs if has_trace_data(f"./result/{m}")
                        ],
                        label="源模型",
                    )

                    identify_btn2 = gr.Button(
                        "🎯 开始识别", size="lg", variant="primary"
                    )
                    back_btn3 = gr.Button("← 返回首页", size="lg")

                # 右侧
                with gr.Column(scale=2):
                    gr.HTML(
                        '<h3 style="color: #fff; margin-bottom: 15px;">🏆 识别结果</h3>'
                    )
                    identify_result = gr.Textbox(
                        lines=8, interactive=False, label="结果"
                    )
                    confidence = gr.Number(label="置信度", interactive=False)

        # ========== 页面切换函数 ==========
        # 不要返回新的 gr.Column 对象，而是使用 gr.update()
        def to_generation():
            return [
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
            ]

        def to_leak():
            return [
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
            ]

        def to_identify():
            return [
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True),
            ]

        def to_home():
            return [
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
            ]

        def update_client_list(model_name):
            if model_name:
                clients = get_client_list(f"./result/{model_name}/trace_data")
                return gr.Dropdown(
                    choices=clients, value=clients[0] if clients else None
                )
            return gr.Dropdown(choices=[], value=None)

        def refresh_leaked():
            return gr.Dropdown(choices=find_leaked_models(LEAK_TEST_DIR))

        # ========== 按钮事件绑定 ==========
        # 首页按钮
        gen_btn.click(
            to_generation,
            inputs=[],
            outputs=[home_page, generation_page, leak_page, identify_page],
        )
        leak_btn.click(
            to_leak,
            inputs=[],
            outputs=[home_page, generation_page, leak_page, identify_page],
        )
        identify_btn.click(
            to_identify,
            inputs=[],
            outputs=[home_page, generation_page, leak_page, identify_page],
        )

        # 返回首页
        back_btn1.click(
            to_home,
            inputs=[],
            outputs=[home_page, generation_page, leak_page, identify_page],
        )
        back_btn2.click(
            to_home,
            inputs=[],
            outputs=[home_page, generation_page, leak_page, identify_page],
        )
        back_btn3.click(
            to_home,
            inputs=[],
            outputs=[home_page, generation_page, leak_page, identify_page],
        )

        # 下拉框联动
        leak_model.change(update_client_list, [leak_model], [client_idx])
        refresh_btn.click(refresh_leaked, [], [leaked_model])

        # ========== 功能实现 ==========
        def do_generate(model_name, class_lbl, num_img, steps, sd, trigger, dev):
            if not model_name:
                return None, "❌ 请选择模型", ""

            model_dir = f"./result/{model_name}"
            output_base = get_default_output_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = osp.join(output_base, f"gen_{timestamp}")

            trigger_class = None
            if trigger:
                args_path = osp.join(model_dir, "args.txt")
                if osp.exists(args_path):
                    with open(args_path, "r") as f:
                        for line in f:
                            if "trigger_class" in line and "=" in line:
                                try:
                                    trigger_class = eval(line.split("=", 1)[1].strip())
                                except:
                                    trigger_class = int(line.split("=", 1)[1].strip())
                                break
                if trigger_class is None:
                    trigger_class = num_img

            images, error = generate_images(
                model_dir,
                int(class_lbl),
                int(num_img),
                int(steps),
                int(sd),
                trigger_class if trigger else None,
                dev,
            )

            if error:
                return None, f"❌ 失败：{error}", ""

            if images:
                os.makedirs(output_dir, exist_ok=True)
                paths = save_images(images, output_dir)
                return paths, f"✅ 成功生成 {len(images)} 张", f"保存至：{output_dir}"

            return None, "❌ 未生成图片", ""

        def do_simulate(model, client, output_name):
            if not model:
                return "❌ 请选择源模型"
            if client is None:
                return "❌ 请选择客户端"

            os.makedirs(LEAK_TEST_DIR, exist_ok=True)
            checkpoint = f"./result/{model}/model_final.pth"
            trace_dir = f"./result/{model}/trace_data"
            output = osp.join(LEAK_TEST_DIR, output_name)

            result, error = simulate_client_leak(
                checkpoint, trace_dir, int(client), output
            )

            if error:
                return f"❌ 失败：{error}"

            return f"✅ 成功！保存至：{output}"

        def do_identify(leaked, source):
            if not leaked:
                return "❌ 请选择泄漏模型", 0
            if not source:
                return "❌ 请选择源模型", 0

            leaked_path = osp.join(LEAK_TEST_DIR, leaked)
            trace_dir = f"./result/{source}/trace_data"

            client, conf, error = identify_owner(leaked_path, trace_dir)

            if error:
                return f"❌ 失败：{error}", 0

            return (
                f"✅ 识别成功！\n\n客户端ID：{client}\n置信度：{conf:.2%}\n\n该模型属于客户端 {client}",
                float(conf),
            )

        generate_btn.click(
            do_generate,
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
        simulate_btn.click(
            do_simulate, [leak_model, client_idx, leak_output], [leak_result]
        )
        identify_btn2.click(
            do_identify, [leaked_model, source_model], [identify_result, confidence]
        )

    return demo


def main():
    parser = argparse.ArgumentParser(description="FedTracker WebUI")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()

    demo = create_ui()
    print(f"\n{'=' * 60}")
    print("FedTracker WebUI - 深色主题")
    print(f"{'=' * 60}")
    print(f"本地访问：http://localhost:{args.port}")
    if args.share:
        print("公网链接将自动生成...")
    print(f"{'=' * 60}\n")

    demo.launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
