#!/usr/bin/env python3
"""Video generation CLI"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from wan_video_gen.batch_runner import run_batch
from wan_video_gen.config import load_config
from wan_video_gen.generator import GenerationRequest, VideoGenerator


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Video Generator (ComfyUI)")
    parser.add_argument("--model", default="ltx", help="Model key: ltx (FP8) / ltx_fp16 (FP16)")
    sub = parser.add_subparsers(dest="command", required=True)

    single = sub.add_parser("generate", help="Generate one video")
    single.add_argument("prompt", help="Prompt text")
    single.add_argument("--image", default=None, help="Reference image path (I2V)")
    single.add_argument("--seed", type=int, default=-1, help="Seed (-1=random)")
    single.add_argument("--output", default=None, help="Output filename (no extension)")

    batch = sub.add_parser("batch", help="Batch generate from CSV")
    batch.add_argument("--csv", default=None, help="CSV file path")

    sub.add_parser("check", help="Check ComfyUI connection")

    args = parser.parse_args()
    config = load_config()

    if args.command == "check":
        from wan_video_gen.comfy_client import ComfyUIClient, ComfyUIError

        client = ComfyUIClient(config.comfyui_url)
        try:
            client.check_connection()
        except ComfyUIError as exc:
            print(f"NG: {exc}", file=sys.stderr)
            print("", file=sys.stderr)
            print("ComfyUI is not running. Start it first:", file=sys.stderr)
            print("  .\\scripts\\start_comfyui.ps1", file=sys.stderr)
            return 1
        print(f"OK: ComfyUI connected ({config.comfyui_url})")
        models = ", ".join(f"{k} ({v.name})" for k, v in config.models.items())
        print(f"Available models: {models}")
        return 0

    model_key = args.model or config.active_model

    if args.command == "generate":
        gen = VideoGenerator(config, model_key)
        result = gen.generate(
            GenerationRequest(
                prompt=args.prompt,
                seed=args.seed,
                output_name=args.output,
                reference_image=args.image,
            )
        )
        print(f"\nDone: {result.output_path}")
        return 0

    if args.command == "batch":
        csv_path = Path(args.csv) if args.csv else None
        result = run_batch(config, csv_path, model_key)
        print(f"\nBatch done: {result.succeeded}/{result.total} succeeded")
        if result.errors:
            print("Failures:")
            for idx, prompt, err in result.errors:
                print(f"  [{idx}] {prompt[:40]}... -> {err}")
        return 0 if result.failed == 0 else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
