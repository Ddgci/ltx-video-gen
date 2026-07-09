"""
プロンプト自動拡張（LTX-Video 2 向け）

参照画像があるときは「動き・行動」中心に英語化する。
"""

from __future__ import annotations

import requests

OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "gemma:7b"

SYSTEM_PROMPT = """\
You are a prompt engineer for LTX-Video 2 AI video generation.

Rules:
- Output ONLY the expanded prompt in English (translate Japanese input)
- LTX works best with 50+ words, detailed and cinematic
- Focus on: actions over time, camera movement, physics, pacing, audio ambience
- Use present tense, smooth motion, realistic physics
- Do NOT add quotation marks around the output
"""

REFERENCE_EXTRA = """
- A reference image already fixes the scene look (roads, cars, buildings, signs).
- Do NOT describe static scenery, country, or architecture — only motion and events.
- Describe what HAPPENS: vehicle movement, collisions, turns, people, timing.
"""

NO_REFERENCE_EXTRA = """
- Include setting briefly (Japanese road/intersection if relevant).
- Describe both environment and motion.
"""


class OllamaError(RuntimeError):
    pass


def check_ollama_available(url: str = OLLAMA_URL) -> bool:
    try:
        resp = requests.get(f"{url}/api/tags", timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def enhance_prompt(
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    url: str = OLLAMA_URL,
    has_reference: bool = False,
) -> str:
    if not user_prompt.strip():
        return ""

    extra = REFERENCE_EXTRA if has_reference else NO_REFERENCE_EXTRA
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + extra},
        {"role": "user", "content": user_prompt.strip()},
    ]

    try:
        resp = requests.post(
            f"{url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 350},
            },
            timeout=60,
        )
        resp.raise_for_status()
    except requests.ConnectionError:
        raise OllamaError(
            "Ollama に接続できません。PowerShell で「ollama serve」を実行してください。"
        )
    except requests.RequestException as exc:
        raise OllamaError(f"Ollama エラー: {exc}")

    content = resp.json().get("message", {}).get("content", "").strip()
    if not content:
        raise OllamaError("Ollama から空の応答が返りました")
    if content.startswith('"') and content.endswith('"'):
        content = content[1:-1]
    return content
