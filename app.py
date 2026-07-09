"""AI 動画生成 — LTX-Video 2 Web UI"""

from __future__ import annotations

import subprocess
import sys
import time
import webbrowser
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import gradio as gr

from wan_video_gen.config import load_config
from wan_video_gen.comfy_client import ComfyUIError
from wan_video_gen.generator import GenerationRequest, VideoGenerator
from wan_video_gen.prompt_utils import prepare_ltx_prompt
from wan_video_gen.reference_utils import (
    list_reference_images,
    pick_reference_path,
    resolve_comfyui_dir,
)
from wan_video_gen.prompt_enhancer import check_ollama_available, enhance_prompt, OllamaError

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
config = load_config(CONFIG_PATH)
COMFYUI_DIR = resolve_comfyui_dir(CONFIG_PATH, config.comfyui_install_dir)
COMFYUI_PROCESS: subprocess.Popen | None = None

REF_HINT = (
    f"**参照画像フォルダ**: `{config.references_dir}`\n"
    "サブフォルダごとに日本の道路・車内・標識などの写真を追加していけます。\n"
    "見た目は画像、**動きはプロンプト**で指定します。"
)

MODEL_INFO = {
    "ltx": {
        "label": "LTX FP8（高速・省VRAM）",
        "tip": "まずはこちらで試作するのがおすすめ。",
    },
    "ltx_fp16": {
        "label": "LTX FP16（高品質）",
        "tip": "高品質だが VRAM 消費が大きい。落ちたら FP8 に戻す。",
    },
}


def _model_choices() -> list[tuple[str, str]]:
    return [(MODEL_INFO[k]["label"], k) for k in config.models.keys()]


def _ref_choices() -> list[tuple[str, str]]:
    items = list_reference_images(config.references_dir)
    if not items:
        return [("（まだ画像なし — references/ に jpg/png を置く）", "")]
    return [("（選ばない）", "")] + items


def start_comfyui_server() -> str:
    global COMFYUI_PROCESS
    from wan_video_gen.comfy_client import ComfyUIClient
    client = ComfyUIClient(config.comfyui_url)
    try:
        client.check_connection()
        return f"接続済み ({config.comfyui_url})"
    except ComfyUIError:
        pass

    try:
        import requests
        if requests.get(f"{config.comfyui_url}/queue", timeout=5).status_code == 200:
            return f"既に起動済み ({config.comfyui_url})"
    except Exception:
        pass

    main_py = COMFYUI_DIR / "main.py"
    venv_python = COMFYUI_DIR / "venv" / "Scripts" / "python.exe"
    if not main_py.exists():
        return f"ComfyUI が見つかりません: {COMFYUI_DIR}"

    python_exe = str(venv_python) if venv_python.exists() else "python"
    COMFYUI_PROCESS = subprocess.Popen(
        [python_exe, str(main_py), "--listen", "127.0.0.1", "--port", str(config.comfyui_port)],
        cwd=str(COMFYUI_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )

    for _ in range(60):
        time.sleep(2)
        try:
            client.check_connection()
            return f"自動起動完了 ({config.comfyui_url})"
        except ComfyUIError:
            continue
    return f"起動タイムアウト — 手動: .\\scripts\\start_comfyui.ps1"


def check_status() -> str:
    from wan_video_gen.comfy_client import ComfyUIClient
    try:
        ComfyUIClient(config.comfyui_url).check_connection()
        comfy = f"ComfyUI: 接続済み"
    except ComfyUIError:
        comfy = "ComfyUI: 未接続"
    ollama = "Ollama: 接続済み" if check_ollama_available() else "Ollama: 未接続"
    return f"{comfy} | {ollama}"


def refresh_refs():
    return gr.update(choices=_ref_choices())


def do_enhance(user_prompt: str, ref_upload, preset_ref: str) -> str:
    if not user_prompt.strip():
        return ""
    ref = pick_reference_path(ref_upload, preset_ref)
    try:
        return enhance_prompt(user_prompt, has_reference=bool(ref))
    except OllamaError as e:
        return f"[拡張失敗] {e}"


def on_model_change(model_key: str):
    if model_key not in config.models:
        model_key = config.active_model
    mc = config.get_model(model_key)
    tip = MODEL_INFO.get(model_key, {}).get("tip", "")
    return mc.width, mc.height, mc.num_frames, mc.image_strength, tip


def generate_video(
    model_key: str,
    prompt: str,
    width: int,
    height: int,
    num_frames: int,
    image_strength: float,
    seed: int,
    output_dir: str,
    use_enhance: bool,
    enhanced_prompt: str,
    ref_upload,
    preset_ref: str,
    progress=gr.Progress(),
) -> tuple[str | None, str]:
    prompt = (prompt or "").strip()
    if not prompt:
        return None, "エラー: プロンプトが空です"

    ref_path = pick_reference_path(ref_upload, preset_ref)
    has_ref = bool(ref_path)

    actual_prompt = prompt
    if use_enhance:
        enhanced = (enhanced_prompt or "").strip()
        if not enhanced or enhanced.startswith("[拡張失敗]"):
            try:
                enhanced = enhance_prompt(prompt, has_reference=has_ref)
            except OllamaError:
                enhanced = ""
        if enhanced and not enhanced.startswith("[拡張失敗]"):
            actual_prompt = enhanced

    actual_prompt = prepare_ltx_prompt(actual_prompt, has_reference=has_ref)

    cfg = load_config(CONFIG_PATH)
    mc = cfg.get_model(model_key)
    mc.width = width
    mc.height = height
    mc.num_frames = num_frames

    out = Path((output_dir or "").strip()) if (output_dir or "").strip() else cfg.output_dir
    out.mkdir(parents=True, exist_ok=True)
    cfg.output_dir = out

    gen = VideoGenerator(cfg, model_key)
    try:
        gen.client.check_connection()
    except ComfyUIError as e:
        return None, f"エラー: {e}\nComfyUI を起動してください。"

    request = GenerationRequest(
        prompt=actual_prompt,
        seed=int(seed),
        output_name=f"{model_key}_{int(time.time())}",
        reference_image=ref_path,
        image_strength=float(image_strength),
    )

    progress(0.05, desc="送信中...")
    t0 = time.time()

    def on_progress(pct: float, desc: str):
        progress(0.1 + pct * 0.85, desc=desc)

    try:
        result = gen.generate(request, on_progress=on_progress)
    except ComfyUIError as e:
        return None, f"エラー: {e}"

    mode = "I2V（参照画像あり）" if has_ref else "T2V（プロンプトのみ）"
    info = (
        f"モデル: {result.model_name}\n"
        f"モード: {mode}\n"
        f"参照画像: {Path(ref_path).name if ref_path else 'なし'}\n"
        f"画像強度: {image_strength:.2f}\n"
        f"シード: {result.seed}\n"
        f"生成時間: {int(time.time() - t0)}秒\n"
        f"ファイル: {result.output_path}\n"
        f"プロンプト: {actual_prompt[:120]}..."
    )
    return str(result.output_path), info


def get_history_videos(output_dir: str) -> list[str]:
    out = Path(output_dir.strip()) if output_dir.strip() else config.output_dir
    if not out.exists():
        return []
    videos = list(out.glob("*.mp4")) + list(out.glob("*.webm"))
    videos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [str(v) for v in videos[:20]]


mc = config.current_model

with gr.Blocks(title="LTX 動画生成") as app:
    gr.Markdown("# LTX-Video 2 動画生成")
    gr.Markdown("**見た目** → 参照画像　｜　**動き・シーン** → プロンプト（英語推奨）")

    with gr.Row():
        status = gr.Textbox(value=check_status, label="接続状態", interactive=False, scale=2)
        gr.Button("ComfyUI 起動").click(fn=start_comfyui_server, outputs=status)

    with gr.Tabs():
        with gr.TabItem("生成"):
            with gr.Row():
                with gr.Column():
                    model_select = gr.Dropdown(
                        choices=_model_choices(),
                        value=config.active_model,
                        label="モデル",
                    )
                    model_tip = gr.Textbox(
                        value=MODEL_INFO.get(config.active_model, {}).get("tip", ""),
                        label="モデルメモ",
                        interactive=False,
                        lines=1,
                    )
                    gr.Markdown(REF_HINT)
                    refresh_btn = gr.Button("参照画像リストを更新", size="sm")
                    preset_ref = gr.Dropdown(
                        choices=_ref_choices(), value="", label="フォルダから選ぶ"
                    )
                    ref_upload = gr.Image(
                        label="またはアップロード",
                        type="filepath",
                        sources=["upload", "clipboard"],
                    )
                    image_strength = gr.Slider(
                        0.3, 1.0, value=mc.image_strength, step=0.05,
                        label="参照画像の強度（高いほど見た目に忠実）",
                    )

                    prompt = gr.Textbox(
                        label="プロンプト（動き・シーンの説明）",
                        placeholder=(
                            "例: The car begins a right turn. A bicycle rapidly approaches "
                            "from the left blind spot and collides with the front-left of the car. "
                            "The rider falls, the car brakes immediately. Smooth motion, educational."
                        ),
                        lines=5,
                    )
                    with gr.Row():
                        use_enhance = gr.Checkbox(label="Gemma で英語に拡張", value=True)
                        enhance_btn = gr.Button("拡張プレビュー")
                    enhanced_prompt = gr.Textbox(
                        label="拡張後（編集可）", lines=3, interactive=True
                    )

                    with gr.Row():
                        width = gr.Slider(256, 1280, value=mc.width, step=64, label="横幅")
                        height = gr.Slider(256, 1280, value=mc.height, step=64, label="高さ")
                    num_frames = gr.Slider(
                        17, 129, value=mc.num_frames, step=8,
                        label="フレーム数（8n+1 推奨）",
                    )
                    seed = gr.Number(value=-1, label="シード（-1=ランダム）", precision=0)
                    output_dir = gr.Textbox(value=str(config.output_dir), label="出力フォルダ")
                    generate_btn = gr.Button("動画を生成", variant="primary", size="lg")

                with gr.Column():
                    output_video = gr.Video(label="生成動画")
                    output_info = gr.Textbox(label="情報", lines=8, interactive=False)

            model_select.change(
                fn=on_model_change,
                inputs=model_select,
                outputs=[width, height, num_frames, image_strength, model_tip],
            )
            refresh_btn.click(fn=refresh_refs, outputs=preset_ref)
            enhance_btn.click(
                fn=do_enhance,
                inputs=[prompt, ref_upload, preset_ref],
                outputs=enhanced_prompt,
            )
            generate_btn.click(
                fn=generate_video,
                inputs=[
                    model_select, prompt, width, height, num_frames, image_strength, seed,
                    output_dir, use_enhance, enhanced_prompt, ref_upload, preset_ref,
                ],
                outputs=[output_video, output_info],
            )

        with gr.TabItem("履歴"):
            history_dir = gr.Textbox(value=str(config.output_dir), label="出力フォルダ")
            history_files = gr.Files(label="最近の動画", file_count="multiple")
            gr.Button("更新").click(fn=get_history_videos, inputs=history_dir, outputs=history_files)

if __name__ == "__main__":
    print("=== LTX 動画生成 ===")
    print(f"ComfyUI: {COMFYUI_DIR}")
    print(f"参照画像: {config.references_dir}")
    print(start_comfyui_server())
    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:7860")).start()
    app.launch(server_name="127.0.0.1", server_port=7860)
