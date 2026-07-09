"""
設定管理モジュール

config.yaml を読み込み、モデルごとの設定と ComfyUI 接続先を Config にまとめる。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .reference_utils import resolve_comfyui_dir


@dataclass
class ModelConfig:
    """1つの AI モデルに対する設定"""

    name: str
    width: int
    height: int
    num_frames: int
    fps: int
    steps: int
    cfg: float
    seed: int
    workflow_path: Path
    prompt_node_id: str
    negative_prompt_node_id: str
    seed_node_id: str
    seed_field: str
    latent_node_id: str
    fps_node_id: str
    cfg_node_id: str = ""
    audio_latent_node_id: str = ""
    checkpoint_name: str = ""
    text_encoder_name: str = ""
    i2v_workflow_path: Path | None = None
    i2v_latent_node_id: str = ""   # LTXVImgToVideo ノード ID
    image_node_id: str = ""        # LoadImage ノード ID
    image_strength: float = 0.75   # 参照画像の効き具合（LTX I2V）


@dataclass
class Config:
    """アプリケーション全体の設定"""

    comfyui_host: str
    comfyui_port: int
    active_model: str
    models: dict[str, ModelConfig]
    output_dir: Path
    references_dir: Path
    comfyui_install_dir: Path | None
    comfyui_dir: Path
    batch_prompts_file: Path
    batch_delay_seconds: float

    @property
    def comfyui_url(self) -> str:
        return f"http://{self.comfyui_host}:{self.comfyui_port}"

    @property
    def current_model(self) -> ModelConfig:
        return self.models[self.active_model]

    def get_model(self, name: str) -> ModelConfig:
        if name not in self.models:
            raise ValueError(f"不明なモデル: {name}。利用可能: {list(self.models.keys())}")
        return self.models[name]


def load_config(config_path: str | Path = "config.yaml") -> Config:
    load_dotenv()
    config_path = Path(config_path)
    with config_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    models: dict[str, ModelConfig] = {}
    for key, m in raw["models"].items():
        models[key] = ModelConfig(
            name=m["name"],
            width=m["width"],
            height=m["height"],
            num_frames=m["num_frames"],
            fps=m["fps"],
            steps=m["steps"],
            cfg=m["cfg"],
            seed=m["seed"],
            workflow_path=config_path.parent / m["workflow_path"],
            prompt_node_id=m["prompt_node_id"],
            negative_prompt_node_id=m["negative_prompt_node_id"],
            seed_node_id=m["seed_node_id"],
            seed_field=m.get("seed_field", "seed"),
            latent_node_id=m["latent_node_id"],
            fps_node_id=m["fps_node_id"],
            cfg_node_id=m.get("cfg_node_id", ""),
            audio_latent_node_id=m.get("audio_latent_node_id", ""),
            checkpoint_name=m.get("checkpoint_name", ""),
            text_encoder_name=m.get("text_encoder_name", ""),
            i2v_workflow_path=(
                config_path.parent / m["i2v_workflow_path"]
                if m.get("i2v_workflow_path")
                else None
            ),
            i2v_latent_node_id=m.get("i2v_latent_node_id", ""),
            image_node_id=m.get("image_node_id", ""),
            image_strength=float(m.get("image_strength", 0.75)),
        )

    install_raw = raw["comfyui"].get("install_dir", "")
    comfyui_install_dir = (
        (config_path.parent / install_raw).resolve()
        if install_raw
        else None
    )

    return Config(
        comfyui_host=os.getenv("COMFYUI_HOST", raw["comfyui"]["host"]),
        comfyui_port=int(os.getenv("COMFYUI_PORT", raw["comfyui"]["port"])),
        active_model=raw.get("active_model", "ltx"),
        models=models,
        output_dir=config_path.parent / raw["output"]["dir"],
        references_dir=config_path.parent / raw.get("references", {}).get("dir", "references"),
        comfyui_install_dir=comfyui_install_dir,
        comfyui_dir=resolve_comfyui_dir(config_path, comfyui_install_dir),
        batch_prompts_file=config_path.parent / raw["batch"]["prompts_file"],
        batch_delay_seconds=raw["batch"]["delay_seconds"],
    )
