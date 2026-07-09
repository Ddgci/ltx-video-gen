"""プロンプト前処理（LTX 用）"""

from __future__ import annotations

# 参照画像なしのときだけ、プロンプトに薄く足す日本ヒント
JAPAN_HINT = "Japanese setting, left-side traffic, realistic"


def prepare_ltx_prompt(prompt: str, *, has_reference: bool) -> str:
    """
    LTX 用プロンプト調整。

    参照画像あり → 動き・行動だけ書く（見た目は画像に任せる）
    参照画像なし → 最低限の日本ヒントを追加
    """
    prompt = prompt.strip()
    if has_reference:
        return prompt
    if "japan" in prompt.lower() or "日本" in prompt:
        return prompt
    return f"{prompt}, {JAPAN_HINT}"
