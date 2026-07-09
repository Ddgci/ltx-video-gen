# LTX 動画生成ツール

パソコンの GPU を使って、**参照画像**と**プロンプト**から AI が動画を自動生成するアプリです。

- **見た目**（日本の道路・車内・標識など）→ `references/` の写真
- **動き・シーン**（右折、衝突、カメラなど）→ プロンプト（英語推奨）

モデルは **LTX-Video 2**（FP8 / FP16）のみ。完全ローカル動作です。

**操作の詳しい説明（画面・作り方・注意点）→ [docs/manual.md](docs/manual.md)**

---

## 必要なもの

| 項目 | スペック |
|------|---------|
| OS | Windows 10 / 11 |
| GPU | NVIDIA RTX（VRAM **12GB 以上**推奨） |
| RAM | 16GB 以上 |
| ストレージ | **約 20GB**（必須モデル）。FP16 追加で **+約 40GB** |
| Python | 3.10 以上 |
| （任意）Ollama | プロンプトの英語自動拡張（Gemma 7B） |

---

## クイックスタート

```powershell
cd wan-video-gen

# 1. 初回のみ
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\scripts\install_comfyui.ps1
.\scripts\download_models.ps1
python scripts\check_models.py

# 2. 毎回
.\scripts\start_comfyui.ps1    # ターミナル1（閉じない）
.\scripts\start_ui.ps1           # ターミナル2 → ブラウザが開く
```

1. `references/street/` などに参照写真を入れる  
2. UI で写真を選び、プロンプトに動きを書く  
3. 「動画を生成」

---

## セットアップ（詳細）

### ステップ 1: Python

```powershell
python --version   # 3.10 以上
```

### ステップ 2: プロジェクト

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

`Activate.ps1` が拒否されたら:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

### ステップ 3: ComfyUI

```powershell
.\scripts\install_comfyui.ps1
```

`wan-video-gen` の **隣のフォルダ**（`../ComfyUI`）にインストールされます。

### ステップ 4: AI モデル

| ファイル | 配置先 | 必須 |
|---------|--------|------|
| `ltx-2-19b-distilled-fp8.safetensors` | `ComfyUI\models\checkpoints\` | **必須** |
| `gemma_3_12B_it_fp4_mixed.safetensors` | `ComfyUI\models\text_encoders\` | **必須** |
| `ltx-2-19b-distilled.safetensors` | `ComfyUI\models\checkpoints\` | 任意（FP16） |

```powershell
.\scripts\download_models.ps1
python scripts\check_models.py
```

**参照画像は DL 不要** — `wan-video-gen\references\` に自分で jpg/png を置きます。

### ステップ 5: （任意）Ollama

```powershell
ollama pull gemma:7b
ollama serve
```

UI の「Gemma で英語に拡張」が使えるようになります。

---

## モデル

| | LTX FP8 | LTX FP16 |
|---|---------|----------|
| 用途 | 試作・日常 | 本番・高品質 |
| VRAM | 少なめで動きやすい | 多めが必要 |
| デフォルト解像度 | 768×432 | 768×480 |
| デフォルト長さ | 49 フレーム | 65 フレーム |

---

## フォルダ構成

```
Projects/
├── wan-video-gen/          ← このリポジトリ（Git 管理）
│   ├── app.py              Web UI
│   ├── references/         参照画像（日本の道路など）
│   ├── output/             生成動画
│   ├── workflows/          LTX ワークフロー
│   └── docs/manual.md      操作マニュアル
│
└── ComfyUI/                ← 別インストール（Git 不要）
    ├── main.py
    └── models/
        ├── checkpoints/    LTX 本体
        └── text_encoders/  Gemma
```

---

## CLI

```powershell
python scripts\generate.py check
python scripts\generate.py generate "The car turns right..." --image references\street\photo.jpg
python scripts\generate.py --model ltx_fp16 generate "..."
```

---

## よくあるトラブル

| 症状 | 対処 |
|------|------|
| ComfyUI 未接続 | `.\scripts\start_comfyui.ps1` |
| Port 8188 already in use | 既に起動済み。2重起動しない |
| VRAM 不足・ComfyUI 落ちる | FP8 に変更、解像度を下げる |
| 400 Bad Request | `python scripts\check_models.py` |
| 日本っぽくない | `references/` に日本の実写を追加 |
| Gemma 拡張失敗 | `ollama serve` |

詳細は [docs/manual.md](docs/manual.md) のトラブルシューティングを参照。

---

## ライセンス

MIT
