"""
動画生成モジュール（LTX-Video 2）

参照画像 → 見た目を固定（I2V）
プロンプト → 動き・シーンを指定（T2V / I2V 共通）
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from pathlib import Path

from .comfy_client import ComfyUIClient, ComfyUIError, ProgressCallback, load_workflow
from .config import Config, ModelConfig


@dataclass
class GenerationRequest:
    """動画生成リクエスト"""

    prompt: str
    negative_prompt: str = ""
    seed: int = -1
    output_name: str | None = None
    reference_image: str | None = None  # 見た目参照（あれば I2V）
    image_strength: float | None = None  # 参照の効き具合（None = config 既定）


@dataclass
class GenerationResult:
    prompt: str
    seed: int
    output_path: Path
    prompt_id: str
    model_name: str


class VideoGenerator:
    def __init__(self, config: Config, model_key: str | None = None) -> None:
        self.config = config
        self.model_key = model_key or config.active_model
        self.model_config = config.get_model(self.model_key)
        self.client = ComfyUIClient(config.comfyui_url)
        self._t2v_workflow = load_workflow(self.model_config.workflow_path)
        self._i2v_workflow = None
        if self.model_config.i2v_workflow_path and self.model_config.i2v_workflow_path.exists():
            self._i2v_workflow = load_workflow(self.model_config.i2v_workflow_path)

    def _select_base_workflow(self, request: GenerationRequest) -> dict:
        if request.reference_image:
            if not self._i2v_workflow:
                raise ComfyUIError("参照画像用の I2V ワークフローが見つかりません。")
            return copy.deepcopy(self._i2v_workflow)
        return copy.deepcopy(self._t2v_workflow)

    def _resolve_seed(self, seed: int) -> int:
        if seed < 0:
            return random.randint(0, 2**32 - 1)
        return seed

    def _patch_workflow(self, request: GenerationRequest, seed: int) -> dict:
        workflow = self._select_base_workflow(request)
        mc = self.model_config
        use_i2v = bool(request.reference_image)

        if use_i2v and mc.image_node_id and mc.image_node_id in workflow:
            uploaded = self.client.upload_image(Path(request.reference_image))
            workflow[mc.image_node_id]["inputs"]["image"] = uploaded

        if mc.prompt_node_id in workflow:
            workflow[mc.prompt_node_id]["inputs"]["text"] = request.prompt

        if mc.negative_prompt_node_id in workflow:
            workflow[mc.negative_prompt_node_id]["inputs"]["text"] = ""

        if mc.seed_node_id in workflow:
            workflow[mc.seed_node_id]["inputs"][mc.seed_field] = seed

        if mc.cfg_node_id and mc.cfg_node_id in workflow:
            workflow[mc.cfg_node_id]["inputs"]["cfg"] = mc.cfg

        strength = request.image_strength if request.image_strength is not None else mc.image_strength

        if use_i2v and mc.i2v_latent_node_id and mc.i2v_latent_node_id in workflow:
            i2v = workflow[mc.i2v_latent_node_id]["inputs"]
            i2v["width"] = mc.width
            i2v["height"] = mc.height
            i2v["length"] = mc.num_frames
            i2v["strength"] = strength
        elif mc.latent_node_id in workflow:
            latent = workflow[mc.latent_node_id]["inputs"]
            latent["width"] = mc.width
            latent["height"] = mc.height
            latent["length"] = mc.num_frames

        if mc.audio_latent_node_id and mc.audio_latent_node_id in workflow:
            audio = workflow[mc.audio_latent_node_id]["inputs"]
            audio["frames_number"] = mc.num_frames
            audio["frame_rate"] = mc.fps

        for node in workflow.values():
            if node.get("class_type") == "CreateVideo":
                node["inputs"]["fps"] = mc.fps
            if node.get("class_type") == "LTXVConditioning":
                node["inputs"]["frame_rate"] = mc.fps

        for node in workflow.values():
            inputs = node.get("inputs", {})
            if mc.checkpoint_name and "ckpt_name" in inputs and isinstance(inputs["ckpt_name"], str):
                inputs["ckpt_name"] = mc.checkpoint_name
            if mc.text_encoder_name and "text_encoder" in inputs and isinstance(inputs["text_encoder"], str):
                inputs["text_encoder"] = mc.text_encoder_name

        return workflow

    def generate(
        self,
        request: GenerationRequest,
        on_progress: ProgressCallback | None = None,
    ) -> GenerationResult:
        self.client.check_connection()
        seed = self._resolve_seed(request.seed)
        workflow = self._patch_workflow(request, seed)

        prompt_id = self.client.queue_prompt(workflow)
        print(f"  [{self.model_config.name}] キュー投入: {prompt_id} (seed={seed})")

        history = self.client.wait_for_completion_ws(prompt_id, on_progress=on_progress)

        files = self.client.get_output_files(history)
        if not files:
            raise ComfyUIError("出力ファイルが見つかりません。")

        file_info = files[0]
        ext = Path(file_info["filename"]).suffix or ".mp4"
        name = request.output_name or f"{self.model_key}_{seed}"
        dest = self.config.output_dir / f"{name}{ext}"

        self.client.download_file(file_info, dest)
        return GenerationResult(
            prompt=request.prompt,
            seed=seed,
            output_path=dest,
            prompt_id=prompt_id,
            model_name=self.model_config.name,
        )
