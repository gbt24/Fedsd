# -*- coding: UTF-8 -*-
"""
FedTracker WebUI - Gradio Application.

Main application for:
1. Image generation with trained diffusion models
2. Client leak simulation and tracing
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr
import numpy as np

from modules.utils import (
    scan_models,
    get_cifar10_labels,
    get_cifar100_labels,
    format_bytes,
)
from modules.generation import get_generator
from modules.tracing import get_tracer


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


def create_generation_tab():
    """Create the image generation tab."""

    def on_refresh_models():
        return gr.Dropdown(choices=get_model_choices())

    def on_load_model(selected_model, gpu_id_val):
        if not selected_model:
            return "Please select a model", ""

        models = scan_models("result")
        model_name = selected_model.split(" (")[0]
        model_path = None
        for m in models:
            if m["name"] == model_name:
                model_path = m["path"]
                break

        if model_path is None:
            return f"Model not found: {selected_model}", ""

        generator = get_generator()
        status, info = generator.load_model(model_path, int(gpu_id_val))

        labels_display = ""
        if "num_classes" in info:
            labels = generator.get_class_labels()
            for i, label in enumerate(labels):
                labels_display += f"{i}: {label}\n"

        model_info_str = f"Type: {info.get('model_type', 'N/A')}\nDataset: {info.get('dataset', 'N/A')}\nClasses: {info.get('num_classes', 'N/A')}"

        return model_info_str, labels_display

    def on_generate(
        selected_model,
        class_label_val,
        num_images_val,
        use_trigger_val,
        steps_val,
        seed_val,
        gpu_val,
    ):
        if not selected_model:
            return "Please load a model first", None

        generator = get_generator()

        if generator.model is None:
            models = scan_models("result")
            model_name = selected_model.split(" (")[0]
            model_path = None
            for m in models:
                if m["name"] == model_name:
                    model_path = m["path"]
                    break

            if model_path:
                generator.load_model(model_path, int(gpu_val))

        images, status = generator.generate(
            labels=[int(class_label_val)],
            num_images=int(num_images_val),
            seed=int(seed_val) if seed_val else None,
            num_inference_steps=int(steps_val),
            use_trigger=use_trigger_val,
        )

        return status, images

    def on_save(image, save_path):
        if image is None:
            return "No image to save"

        generator = get_generator()
        filepath = generator.save_images(image, save_path)
        return f"Saved to: {filepath}"

    with gr.Tab("Image Generation"):
        gr.Markdown("### Generate images from trained diffusion models")

        with gr.Row():
            with gr.Column(scale=1):
                model_dropdown = gr.Dropdown(
                    label="Model",
                    choices=get_model_choices(),
                    info="Select a trained model",
                )
                refresh_btn = gr.Button("🔄 Refresh Models", size="sm")

                model_info = gr.Textbox(label="Model Info", lines=3, interactive=False)

                with gr.Accordion("Advanced Settings", open=False):
                    gpu_id = gr.Number(
                        label="GPU ID", value=0, precision=0, info="-1 for CPU"
                    )
                    num_steps = gr.Slider(
                        label="Inference Steps",
                        minimum=100,
                        maximum=2000,
                        value=1000,
                        step=100,
                        info="More steps = higher quality",
                    )
                    seed = gr.Number(
                        label="Seed", value=42, precision=0, info="Random seed"
                    )

            with gr.Column(scale=2):
                with gr.Row():
                    with gr.Column():
                        class_label = gr.Number(
                            label="Class Label",
                            value=0,
                            precision=0,
                            info="Class index",
                        )
                        num_images = gr.Slider(
                            label="Number of Images",
                            minimum=1,
                            maximum=16,
                            value=4,
                            step=1,
                        )
                        use_trigger = gr.Checkbox(
                            label="Use Trigger Class (Watermark)",
                            value=False,
                            info="Generate watermark images",
                        )

                    with gr.Column():
                        class_labels_display = gr.Textbox(
                            label="Available Classes",
                            lines=8,
                            interactive=False,
                            info="Class labels for current model",
                        )

                generate_btn = gr.Button(
                    "🎨 Generate Images", variant="primary", size="lg"
                )
                status_text = gr.Textbox(label="Status", lines=2, interactive=False)
                output_image = gr.Image(
                    label="Generated Images", type="numpy", height=400
                )

                with gr.Row():
                    save_output = gr.Textbox(
                        label="Save Path",
                        value="webui/static/outputs",
                        interactive=True,
                    )
                    save_btn = gr.Button("💾 Save Image", size="sm")
                    save_status = gr.Textbox(
                        label="", interactive=False, show_label=False
                    )

    # Event handlers
    refresh_btn.click(fn=on_refresh_models, outputs=model_dropdown)
    model_dropdown.change(
        fn=on_load_model,
        inputs=[model_dropdown, gpu_id],
        outputs=[model_info, class_labels_display],
    )
    generate_btn.click(
        fn=on_generate,
        inputs=[
            model_dropdown,
            class_label,
            num_images,
            use_trigger,
            num_steps,
            seed,
            gpu_id,
        ],
        outputs=[status_text, output_image],
    )
    save_btn.click(fn=on_save, inputs=[output_image, save_output], outputs=save_status)

    return model_dropdown


def create_tracing_tabs():
    """Create the tracing tabs (leak simulation and owner identification)."""

    def on_refresh_source():
        return gr.Dropdown(choices=get_trace_model_choices())

    def on_load_trace(selected_model):
        if not selected_model:
            return "", "Please select a model"

        models = scan_models("result")
        model_name = selected_model.split(" (")[0]
        model_path = None
        for m in models:
            if m["name"] == model_name:
                model_path = m["path"]
                break

        if model_path is None:
            return "", f"Model not found: {selected_model}"

        trace_path = os.path.join(model_path, "trace_data")
        if not os.path.exists(trace_path):
            return "", "Trace data not found. Train with --fingerprint flag."

        tracer = get_tracer()
        success, msg, info = tracer.load_trace_data(trace_path)

        if success:
            info_str = f"Clients: {info['num_clients']}\nFingerprint Length: {info['lfp_length']}\nLayers: {', '.join(info['embed_layers'][:3])}..."
            return trace_path, info_str
        else:
            return "", f"Error: {msg}"

    def on_simulate(
        source_model, client_idx_val, max_iters_val, lambda_val, output_dir_val
    ):
        if not source_model:
            return "Please select a source model", {}

        models = scan_models("result")
        model_name = source_model.split(" (")[0]
        model_path = None
        for m in models:
            if m["name"] == model_name:
                model_path = m["path"]
                break

        if model_path is None:
            return f"Model not found: {source_model}", {}

        tracer = get_tracer()
        if tracer.local_fingerprints is None:
            return "Please load trace data first", {}

        success, msg, result = tracer.simulate_leak(
            model_path,
            int(client_idx_val),
            gpu_id=0,
            max_iters=int(max_iters_val),
            lambda_factor=lambda_val,
            output_dir=output_dir_val if output_dir_val else None,
        )

        return msg, result

    def on_identify(leaked_path, trace_path, gpu_val):
        if not leaked_path or not trace_path:
            return "Please provide both leaked model path and trace data directory", {}

        tracer = get_tracer()

        success1, msg1, _ = tracer.load_trace_data(trace_path)
        if not success1:
            return f"Error loading trace data: {msg1}", {}

        success2, msg2, result = tracer.identify_owner(leaked_path, gpu_id=int(gpu_val))

        if not success2:
            return msg2, {}

        return msg2, result

    # Leak Simulation Tab
    with gr.Tab("Leak Simulation"):
        gr.Markdown("### Simulate a client model leak")
        gr.Markdown(
            "This simulates the scenario where a client's trained model is leaked."
        )

        with gr.Row():
            with gr.Column(scale=1):
                source_model = gr.Dropdown(
                    label="Source Model",
                    choices=get_trace_model_choices(),
                    info="Select the global model for simulation",
                )
                refresh_source_btn = gr.Button("🔄 Refresh", size="sm")

                trace_dir = gr.Textbox(
                    label="Trace Data Directory",
                    value="",
                    info="Path to trace_data directory",
                )
                load_trace_btn = gr.Button("📂 Load Trace Data")
                trace_info = gr.Textbox(
                    label="Trace Data Info", lines=3, interactive=False
                )

            with gr.Column(scale=1):
                client_idx = gr.Number(
                    label="Client Index",
                    value=0,
                    precision=0,
                    info="Client to simulate leak for",
                )

                with gr.Accordion("Advanced Settings", open=False):
                    max_iters = gr.Slider(
                        label="Max Iterations", minimum=1, maximum=50, value=10, step=1
                    )
                    lambda_factor = gr.Number(
                        label="Lambda Factor", value=0.01, info="Learning rate"
                    )
                    output_dir_simulation = gr.Textbox(
                        label="Output Directory", value=""
                    )

                simulate_btn = gr.Button("🔍 Simulate Leak", variant="primary")
                simulation_progress = gr.Textbox(
                    label="Progress", lines=2, interactive=False
                )
                simulation_result = gr.JSON(label="Simulation Result")

    # Owner Identification Tab
    with gr.Tab("Owner Identification"):
        gr.Markdown("### Identify the owner of a leaked model")

        with gr.Row():
            with gr.Column(scale=1):
                leaked_model_path = gr.Textbox(
                    label="Leaked Model Path",
                    info="Path to the leaked model checkpoint (.pth)",
                )
                identify_trace_dir = gr.Textbox(
                    label="Trace Data Directory",
                    value="",
                    info="Must match the source model",
                )
                load_identify_trace_btn = gr.Button("📂 Load Trace Data")
                identify_trace_info = gr.Textbox(
                    label="Trace Data Info", lines=2, interactive=False
                )

                with gr.Accordion("Advanced Settings", open=False):
                    identify_gpu = gr.Number(label="GPU ID", value=0, precision=0)

                identify_btn = gr.Button("🔎 Identify Owner", variant="primary")

            with gr.Column(scale=2):
                identify_progress = gr.Textbox(
                    label="Progress", lines=2, interactive=False
                )
                identification_result = gr.JSON(label="Identification Result")

    # Event handlers
    refresh_source_btn.click(fn=on_refresh_source, outputs=source_model)
    load_trace_btn.click(
        fn=on_load_trace, inputs=source_model, outputs=[trace_dir, trace_info]
    )
    source_model.change(
        fn=on_load_trace, inputs=source_model, outputs=[trace_dir, trace_info]
    )
    simulate_btn.click(
        fn=on_simulate,
        inputs=[
            source_model,
            client_idx,
            max_iters,
            lambda_factor,
            output_dir_simulation,
        ],
        outputs=[simulation_progress, simulation_result],
    )

    load_identify_trace_btn.click(
        fn=on_load_trace,
        inputs=leaked_model_path,
        outputs=[identify_trace_dir, identify_trace_info],
    )
    identify_btn.click(
        fn=on_identify,
        inputs=[leaked_model_path, identify_trace_dir, identify_gpu],
        outputs=[identify_progress, identification_result],
    )

    return source_model


def create_app():
    """Create the main Gradio application."""
    with gr.Blocks(
        title="FedTracker WebUI",
        theme=gr.themes.Soft(),
        css=".gradio-container { max-width: 1400px !important; }",
    ) as app:
        gr.Markdown(
            """
            # 🎨 FedTracker WebUI
            
            **Federated Learning Watermark System for Ownership Verification**
            
            Use the tabs below to:
            - **Image Generation**: Generate images from trained diffusion models
            - **Leak Simulation**: Simulate client model leaks for testing
            - **Owner Identification**: Identify the owner of a leaked model
            """
        )

        create_generation_tab()
        create_tracing_tabs()

    return app


def main():
    parser = argparse.ArgumentParser(description="FedTracker WebUI")
    parser.add_argument(
        "--port", type=int, default=7860, help="Port to run the server on"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to run the server on"
    )
    parser.add_argument(
        "--share", action="store_true", help="Create a public share link"
    )
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")

    args = parser.parse_args()

    os.makedirs("webui/static/outputs", exist_ok=True)

    app = create_app()

    print(f"\n{'=' * 60}")
    print("FedTracker WebUI")
    print(f"{'=' * 60}")
    print(f"Server running at: http://{args.host}:{args.port}")
    if args.share:
        print("Public share link will be created")
    print(f"{'=' * 60}\n")

    app.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
