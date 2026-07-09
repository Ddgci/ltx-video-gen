"""
バッチ生成モジュール

CSV ファイルからプロンプト一覧を読み込み、
順番に動画を生成していく。夜間の一括生成などに使用。
"""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .generator import GenerationRequest, GenerationResult, VideoGenerator


@dataclass
class BatchResult:
    """バッチ生成全体の結果"""

    total: int                              # 総プロンプト数
    succeeded: int                          # 成功数
    failed: int                             # 失敗数
    results: list[GenerationResult]         # 成功した生成結果
    errors: list[tuple[int, str, str]]      # (番号, プロンプト, エラー内容)


def load_prompts_csv(path: Path) -> list[GenerationRequest]:
    """
    CSV ファイルからプロンプト一覧を読み込む。

    CSV フォーマット:
        prompt,negative_prompt,seed
        "プロンプト1","ネガティブ1",-1
        "プロンプト2","ネガティブ2",42
    """
    requests: list[GenerationRequest] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            prompt = row.get("prompt", "").strip()
            if not prompt:
                continue
            seed_raw = row.get("seed", "-1").strip()
            seed = int(seed_raw) if seed_raw else -1
            requests.append(
                GenerationRequest(
                    prompt=prompt,
                    negative_prompt=row.get("negative_prompt", "").strip()
                    or "blurry, low quality, distorted",
                    seed=seed,
                    output_name=f"batch_{i:03d}",
                )
            )
    return requests


def run_batch(config: Config, prompts_file: Path | None = None, model_key: str | None = None) -> BatchResult:
    """
    CSV からプロンプトを読み込み、順番に動画を生成する。

    各生成の間に config.batch_delay_seconds 秒の待機を入れる
    （GPU の冷却・VRAM 解放のため）。
    """
    prompts_path = prompts_file or config.batch_prompts_file
    requests = load_prompts_csv(prompts_path)

    if not requests:
        raise ValueError(f"プロンプトが空です: {prompts_path}")

    generator = VideoGenerator(config, model_key)
    results: list[GenerationResult] = []
    errors: list[tuple[int, str, str]] = []

    print(f"バッチ開始: {len(requests)} 件 ({generator.model_config.name})")

    for i, req in enumerate(requests, start=1):
        print(f"\n[{i}/{len(requests)}] {req.prompt[:60]}...")
        try:
            result = generator.generate(req)
            results.append(result)
            print(f"  完了: {result.output_path}")
        except Exception as exc:
            print(f"  失敗: {exc}")
            errors.append((i, req.prompt, str(exc)))

        # 次の生成まで少し待つ（GPU 負荷軽減）
        if i < len(requests):
            time.sleep(config.batch_delay_seconds)

    return BatchResult(
        total=len(requests),
        succeeded=len(results),
        failed=len(errors),
        results=results,
        errors=errors,
    )
