"""参照画像フォルダの管理"""

from __future__ import annotations

from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def resolve_comfyui_dir(config_path: Path, install_dir: Path | None = None) -> Path:
    """ComfyUI インストール先を探す"""
    candidates: list[Path] = []
    if install_dir:
        candidates.append(install_dir)
    project_root = config_path.parent
    candidates.extend([
        project_root.parent / "ComfyUI",
        Path.home() / "Projects" / "ComfyUI",
        project_root / "ComfyUI",
    ])
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / "main.py").exists():
            return resolved
    return candidates[0].resolve()


def list_reference_images(references_dir: Path) -> list[tuple[str, str]]:
    """
    references/ 内の画像一覧（サブフォルダも再帰検索）。

    戻り値: (表示ラベル, 絶対パス)
    """
    if not references_dir.exists():
        references_dir.mkdir(parents=True, exist_ok=True)
        return []

    files: list[Path] = []
    for ext in IMAGE_EXTS:
        files.extend(references_dir.rglob(f"*{ext}"))
        files.extend(references_dir.rglob(f"*{ext.upper()}"))

    files = sorted(set(files), key=lambda p: str(p.relative_to(references_dir)).lower())
    choices: list[tuple[str, str]] = []
    for f in files:
        rel = f.relative_to(references_dir)
        label = str(rel).replace("\\", "/")
        choices.append((label, str(f.resolve())))
    return choices


def pick_reference_path(uploaded: str | None, preset_path: str | None) -> str | None:
    """アップロード優先、なければフォルダ内プリセット"""
    if uploaded:
        return uploaded
    if preset_path and preset_path.strip():
        p = Path(preset_path.strip())
        if p.exists():
            return str(p.resolve())
    return None
