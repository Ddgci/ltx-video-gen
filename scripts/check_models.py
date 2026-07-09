#!/usr/bin/env python3
"""
モデルファイルの整合性チェックスクリプト

各モデルファイルが存在するか、サイズが正常か、
safetensors のヘッダーが読めるかを確認する。
"""

import sys
from pathlib import Path

# ComfyUI のモデルフォルダ
COMFYUI_DIR = Path(__file__).resolve().parent.parent.parent / "ComfyUI"

# 期待されるモデルファイルと最小サイズ (bytes)
EXPECTED_MODELS = {
    "LTX-Video 2 - Checkpoint (FP8)": {
        "path": "models/checkpoints/ltx-2-19b-distilled-fp8.safetensors",
        "min_size_gb": 9.0,
    },
    "LTX-Video 2 - Checkpoint (FP16)": {
        "path": "models/checkpoints/ltx-2-19b-distilled.safetensors",
        "min_size_gb": 30.0,
        "optional": True,
    },
    "LTX-Video 2 - Text Encoder": {
        "path": "models/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors",
        "min_size_gb": 5.0,
    },
}


def check_safetensors_header(filepath: Path) -> tuple[bool, str]:
    """safetensors ファイルのヘッダーが読めるか確認"""
    try:
        import struct
        with filepath.open("rb") as f:
            header_size_bytes = f.read(8)
            if len(header_size_bytes) < 8:
                return False, "ファイルが小さすぎる（8バイト未満）"
            header_size = struct.unpack("<Q", header_size_bytes)[0]
            if header_size > 100_000_000:  # 100MB以上のヘッダーはおかしい
                return False, f"ヘッダーサイズ異常: {header_size} bytes"
            header_data = f.read(min(header_size, 1024))  # 最初の1KBだけ読む
            if not header_data.startswith(b"{"):
                return False, "ヘッダーが JSON ではない"
        return True, "OK"
    except Exception as e:
        return False, str(e)


def format_size(size_bytes: int) -> str:
    gb = size_bytes / (1024 ** 3)
    if gb >= 1:
        return f"{gb:.2f} GB"
    mb = size_bytes / (1024 ** 2)
    return f"{mb:.0f} MB"


def main():
    print(f"=== モデルファイル チェック ===")
    print(f"ComfyUI: {COMFYUI_DIR}")
    print()

    all_ok = True

    for name, info in EXPECTED_MODELS.items():
        filepath = COMFYUI_DIR / info["path"]
        min_size = int(info["min_size_gb"] * 1024 ** 3)

        print(f"[{name}]")
        print(f"  パス: {filepath}")

        if not filepath.exists():
            if info.get("optional"):
                print(f"  状態: − 未インストール（任意）")
            else:
                print(f"  状態: ✗ ファイルが存在しない")
                all_ok = False
            print()
            continue

        size = filepath.stat().st_size
        print(f"  サイズ: {format_size(size)}")

        if size < min_size:
            print(f"  状態: ✗ サイズが小さい（最低 {info['min_size_gb']} GB 必要）")
            print(f"         ダウンロードが途中で止まった可能性があります")
            all_ok = False
            print()
            continue

        header_ok, header_msg = check_safetensors_header(filepath)
        if not header_ok:
            print(f"  状態: ✗ ファイル破損 — {header_msg}")
            all_ok = False
        else:
            print(f"  状態: ✓ 正常")

        print()

    print("=" * 40)
    if all_ok:
        print("全モデル正常です。")
    else:
        print("問題のあるモデルがあります。再ダウンロードしてください。")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
