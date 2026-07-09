# AI 動画生成ツール

パソコンの GPU を使って、テキスト（文章）から AI が動画を自動生成するアプリです。  
ブラウザで操作でき、プロンプト（作りたい動画の説明文）を入力するだけで動画が作れます。

---

## これは何？

- 「猫がビーチを歩く映像」のような文章を入力すると、**AI が数分で動画を生成**します
- 完全にローカル（自分のPC内）で動くため、インターネットに画像が送られることはありません
- 2つの AI モデルを切り替えて使えます

---

## 必要なもの

| 項目 | 必要スペック |
|------|-------------|
| **OS** | Windows 10 または 11 |
| **GPU** | NVIDIA GeForce RTX シリーズ（VRAM 12GB 以上推奨） |
| **メモリ (RAM)** | 16GB 以上 |
| **ストレージ** | 20GB 以上の空き容量（モデルファイルが大きい） |
| **Python** | バージョン 3.10 以上 |

> RTX 4070 Ti (12GB) で動作確認済み。RTX 3060 12GB でも動きます。

---

## セットアップ手順（初回のみ）

### ステップ 1: Python の確認

PowerShell を開いて以下を実行:

```powershell
python --version
```

`Python 3.10.x` のように表示されれば OK です。  
表示されない場合は [python.org](https://www.python.org/downloads/) からインストールしてください。  
インストール時に **「Add Python to PATH」にチェック** を入れてください。

---

### ステップ 2: プロジェクトのセットアップ

```powershell
cd C:\Users\<あなたのユーザー名>\Projects\wan-video-gen
```

仮想環境の作成と依存パッケージのインストール:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

> **「.venv\Scripts\Activate.ps1 を実行できません」と出た場合:**
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
> ```
> を先に実行してから再度 `.\.venv\Scripts\Activate.ps1` を実行してください。

---

### ステップ 3: ComfyUI のインストール

ComfyUI は AI モデルを動かすためのエンジンです。

```powershell
.\scripts\install_comfyui.ps1
```

完了まで 10〜20 分かかります（PyTorch のダウンロードが大きいため）。

---

### ステップ 4: AI モデルのダウンロード

動画を生成する AI モデル本体をダウンロードします。  
合計 **約 8GB** あるので、時間がかかります。

#### Wan 2.1（日本語対応・高品質）— 必須

```powershell
curl.exe -L -o "..\ComfyUI\models\diffusion_models\wan2.1_t2v_1.3B_fp16.safetensors" "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors"

curl.exe -L -o "..\ComfyUI\models\vae\wan_2.1_vae.safetensors" "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors"

curl.exe -L -o "..\ComfyUI\models\text_encoders\umt5_xxl_fp8_e4m3fn_scaled.safetensors" "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"
```

#### LTX-Video 2 Distilled（高速生成）— オプション

```powershell
New-Item -ItemType Directory -Force -Path "..\ComfyUI\models\checkpoints"

curl.exe -L -o "..\ComfyUI\models\checkpoints\ltx-2-19b-distilled-fp8.safetensors" "https://huggingface.co/Lightricks/LTX-2/resolve/main/ltx-2-19b-distilled-fp8.safetensors"

curl.exe -L -o "..\ComfyUI\models\text_encoders\gemma_3_12B_it_fp4_mixed.safetensors" "https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors"
```

---

### ステップ 5: 起動

```powershell
cd C:\Users\<あなたのユーザー名>\Projects\wan-video-gen
.\.venv\Scripts\Activate.ps1
python app.py
```

これだけで:
1. ComfyUI が自動的に起動します
2. ブラウザが自動で開きます（http://127.0.0.1:7860）
3. プロンプトを入力して「動画を生成」ボタンを押すと、動画が作られます

---

## 普段の使い方（2回目以降）

毎回やることはこれだけ:

```powershell
cd C:\Users\<あなたのユーザー名>\Projects\wan-video-gen
.\.venv\Scripts\Activate.ps1
python app.py
```

ブラウザが開いたら、プロンプトを書いて「動画を生成」を押す。  
完了すると右側に動画が表示されます。

---

## AI モデルの比較

| | Wan 2.1 | LTX-Video 2 Distilled |
|---|---|---|
| **速度** | 2〜5分 | 30秒〜1分 |
| **画質** | ◎ とても良い | ○ 良い |
| **対応言語** | 英語・日本語・中国語 | 英語のみ |
| **解像度** | 832×480 | 768×512 |
| **動画の長さ** | 約5秒 | 約4秒 |
| **用途** | 品質重視 | 試作・量産 |

---

## プロンプトの書き方

### Wan 2.1（日本語 OK）

```
晴れた日のビーチを歩く猫、シネマティックなライティング
```

```
A cat walking on a sunny beach, cinematic lighting, 4k quality
```

### LTX-Video 2（英語・長文推奨）

```
A fluffy orange cat walks along a sunny beach with crystal clear water.
The camera follows from behind at a low angle. Gentle waves lap at the shore.
Cinematic lighting with warm golden tones. Shot on 35mm film.
```

> **コツ:** LTX は長く詳しく書くほど良い結果になります。

---

## コマンドライン（CLI）での使い方

ブラウザを使わず、コマンドでも動画を生成できます:

```powershell
# Wan で生成
python scripts/generate.py generate "猫がビーチを歩く"

# LTX で生成
python scripts/generate.py --model ltx generate "A cat on a beach, cinematic"

# CSV から一括生成
python scripts/generate.py batch --csv prompts/example.csv
```

---

## よくあるトラブル

| 症状 | 原因と対処 |
|------|-----------|
| 「ComfyUI に接続できません」 | ComfyUI が起動していない → `python app.py` で自動起動を待つ |
| 「モデルが見つからない」 | ダウンロードが完了していない → ステップ4 をやり直す |
| 「VRAM 不足」 | 解像度が高すぎる → UI で横幅/高さを下げる |
| 10% で止まる | 正常動作。生成中は進捗バーが動くのを待つ（2〜5分） |
| `Activate.ps1 を実行できない` | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` を実行 |
| `python が見つからない` | Python をインストールして PATH を通す |

---

## フォルダ構成

```
wan-video-gen/
├── app.py                 ← メイン（これを実行する）
├── config.yaml            ← 設定ファイル
├── requirements.txt       ← 必要なパッケージ一覧
├── scripts/               ← セットアップ用スクリプト
├── workflows/             ← ComfyUI ワークフロー定義
├── prompts/               ← バッチ用プロンプト CSV
├── src/wan_video_gen/     ← Python コード本体
├── output/                ← 生成された動画の保存先
└── docs/                  ← ドキュメント
```

---

## ライセンス

MIT
