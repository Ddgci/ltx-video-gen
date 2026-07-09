# 設計書

## 概要

ローカル GPU 上で **LTX-Video 2 Distilled** を ComfyUI 経由で動かし、**参照画像（見た目）** と **プロンプト（動き）** から動画を生成するアプリケーションです。

| モード | 条件 | ワークフロー |
|--------|------|-------------|
| **T2V** | 参照画像なし | `ltx_t2v_distilled.template.json` |
| **I2V** | 参照画像あり | `ltx_i2v_distilled.template.json` |

利用モデルは `ltx`（FP8）と `ltx_fp16`（FP16）の2種類のみ。Wan 等の旧モデルは含みません。

---

## システム構成図

```
┌──────────────────────────────────────────────────────────────┐
│                        ユーザーの PC                            │
│                                                              │
│  ┌──────────────┐   HTTP/WS    ┌────────────────────────┐   │
│  │  Web UI      │◄────────────►│  ComfyUI (port 8188)   │   │
│  │  Gradio      │              │  LTX + Gemma 3 推論     │   │
│  │  app.py      │              └───────────┬────────────┘   │
│  │  port 7860   │                          │ GPU             │
│  └──────┬───────┘                          │                 │
│         │ import                           │                 │
│         ▼                                  ▼                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  src/wan_video_gen/                                   │   │
│  │  config / generator / comfy_client / reference_utils  │   │
│  │  prompt_enhancer / prompt_utils / batch_runner         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  references/  … 参照画像（I2V 用、ユーザーが追加）               │
│  output/      … 生成動画                                      │
│  workflows/   … ComfyUI ワークフロー JSON テンプレート          │
└──────────────────────────────────────────────────────────────┘

../ComfyUI/           … AI エンジン本体（別フォルダ、自動検出）
  models/checkpoints/ … LTX チェックポイント
  models/text_encoders/ … Gemma 3 12B

Ollama (port 11434)   … 任意。UI の「Gemma で英語に拡張」用（gemma:7b）
```

`app.py` 起動時は ComfyUI 未接続なら **自動起動** を試みます（`../ComfyUI/main.py` 等を検出）。

---

## コンポーネント構成

```
wan-video-gen/
├── app.py                          Gradio Web UI・ComfyUI 自動起動
├── config.yaml                     モデル・解像度・ノード ID・パス
├── .env                            COMFYUI_HOST / COMFYUI_PORT（任意）
│
├── src/wan_video_gen/
│   ├── __init__.py
│   ├── config.py                   config.yaml 読み込み・ModelConfig
│   ├── comfy_client.py             HTTP / WebSocket / 画像アップロード
│   ├── generator.py                T2V/I2V 切替・ワークフロー注入・保存
│   ├── prompt_enhancer.py          Ollama API で英語プロンプト拡張
│   ├── prompt_utils.py             prepare_ltx_prompt（日本ヒント等）
│   ├── reference_utils.py          参照画像一覧・ComfyUI パス解決
│   └── batch_runner.py             CSV 一括生成
│
├── workflows/
│   ├── ltx_t2v_distilled.template.json
│   └── ltx_i2v_distilled.template.json
│
├── references/                     参照画像（サブフォルダ可、再帰検索）
├── prompts/example.csv             バッチ生成サンプル
├── output/                         生成動画の既定保存先
│
├── scripts/
│   ├── generate.py                 CLI（generate / batch / check）
│   ├── check_models.py             モデルファイル存在確認
│   ├── download_models.ps1
│   ├── install_comfyui.ps1
│   ├── start_comfyui.ps1
│   └── start_ui.ps1
│
└── docs/
    ├── manual.md
    └── architecture.md             本ファイル
```

### ComfyUI インストール先の解決順

`reference_utils.resolve_comfyui_dir()` が次の順で `main.py` を探します。

1. `config.yaml` の `comfyui.install_dir`（空ならスキップ）
2. `wan-video-gen` の隣 `../ComfyUI`
3. `~/Projects/ComfyUI`
4. `wan-video-gen/ComfyUI`

---

## 動画生成フロー

### Web UI（`app.py`）

```
[ユーザー]
    │ 参照画像（任意）+ プロンプト + パラメータ
    ▼
[app.py]
    │ pick_reference_path（アップロード優先 → フォルダ選択）
    │ enhance_prompt（任意・Ollama gemma:7b）
    │ prepare_ltx_prompt（参照あり→そのまま / なし→日本ヒント追加）
    ▼
[VideoGenerator.generate]
    │ check_connection()
    │ シード解決（-1 → ランダム）
    │ _patch_workflow()
    ▼
[ComfyUIClient]
    │ I2V: POST /upload/image で参照画像を送信
    │ POST /prompt でワークフロー投入
    │ WebSocket で進捗待ち
    │ GET /view で動画ダウンロード
    ▼
[output/]  mp4 保存 → UI プレビュー
```

### ワークフロー注入（`_patch_workflow`）

| 対象 | 内容 |
|------|------|
| LoadImage（ノード 71） | I2V 時、アップロード済み画像名 |
| CLIPTextEncode（ノード 6） | プロンプト |
| CLIPTextEncode（ノード 7） | ネガティブ（常に空文字） |
| RandomNoise（ノード 123） | `noise_seed` |
| CFGGuider（ノード 127） | `cfg`（LTX は 1.0） |
| LTXVImgToVideo（ノード 72） | I2V: width / height / length / strength |
| EmptyLTXVLatentVideo（ノード 70） | T2V: width / height / length |
| LTXVEmptyLatentAudio（ノード 115） | frames_number / frame_rate |
| CheckpointLoaderSimple 等 | `ckpt_name` / `text_encoder` をモデル別に差し替え |
| CreateVideo / LTXVConditioning | fps / frame_rate |

### CLI（`scripts/generate.py`）

| コマンド | 説明 |
|---------|------|
| `check` | ComfyUI 接続確認 |
| `generate <prompt>` | 1 本生成（`--image` で I2V、`--model` で FP8/FP16） |
| `batch --csv` | CSV から順次生成（参照画像列は未対応） |

---

## LTX パイプライン（ComfyUI ワークフロー）

```
[テキストプロンプト]
    ▼
LTXAVTextEncoderLoader（Gemma 3 12B）+ CheckpointLoaderSimple（LTX 19B）
    ▼
CLIPTextEncode → LTXVConditioning
    │
    ├─ T2V: EmptyLTXVLatentVideo
    └─ I2V: LoadImage → LTXVImgToVideo（strength で見た目の固定度）
    │
    ▼
LTXVEmptyLatentAudio + LTXVConcatAVLatent（映像+音声潜在）
    ▼
CFGGuider + RandomNoise + KSamplerSelect + ManualSigmas
    ▼
SamplerCustomAdvanced（Distilled・8 steps）
    ▼
LTXVSeparateAVLatent → VAEDecodeTiled + LTXVAudioVAEDecode
    ▼
CreateVideo → SaveVideo（mp4）
```

---

## 使用技術

### AI モデル（ComfyUI 側）

| キー | チェックポイント | テキストエンコーダ |
|------|-----------------|-------------------|
| `ltx` | `ltx-2-19b-distilled-fp8.safetensors` | `gemma_3_12B_it_fp4_mixed.safetensors` |
| `ltx_fp16` | `ltx-2-19b-distilled.safetensors` | 同上 |

### フレームワーク

| 技術 | 用途 |
|------|------|
| ComfyUI 0.27+ | ワークフロー実行 |
| PyTorch + CUDA | GPU 推論 |
| Gradio 6.x | Web UI |
| requests / websocket-client | ComfyUI 通信 |
| Ollama + `gemma:7b` | プロンプト英語拡張（任意・UI 専用） |

---

## config.yaml の構造

```yaml
active_model: "ltx"          # 既定モデルキー

comfyui:
  host: "127.0.0.1"
  port: 8188
  install_dir: ""            # 空なら自動検出

references:
  dir: "references"

models:
  ltx:                       # FP8
    checkpoint_name: "ltx-2-19b-distilled-fp8.safetensors"
    workflow_path: "workflows/ltx_t2v_distilled.template.json"
    i2v_workflow_path: "workflows/ltx_i2v_distilled.template.json"
    image_node_id: "71"      # LoadImage
    i2v_latent_node_id: "72" # LTXVImgToVideo
    latent_node_id: "70"     # EmptyLTXVLatentVideo（T2V）
    prompt_node_id: "6"
    # width / height / num_frames / fps / steps / cfg / image_strength など

  ltx_fp16:                  # FP16（別チェックポイント、同ワークフロー）

output:
  dir: "output"

batch:
  prompts_file: "prompts/example.csv"
  delay_seconds: 2
```

環境変数 `COMFYUI_HOST` / `COMFYUI_PORT` で接続先を上書き可能（`.env`）。

---

## ComfyUI API

| エンドポイント | メソッド | 用途 |
|---------------|---------|------|
| `/queue` | GET | 接続確認（優先） |
| `/object_info` | GET | 接続確認（フォールバック） |
| `/` | GET | 接続確認（フォールバック） |
| `/upload/image` | POST | I2V 用参照画像アップロード |
| `/prompt` | POST | ワークフロー投入 |
| `/history/{prompt_id}` | GET | 生成結果メタデータ |
| `/view?filename=...` | GET | 出力ファイル取得 |
| `ws://host:port/ws?clientId=...` | WebSocket | 進捗・完了通知 |

> ComfyUI 0.27 では `/system_stats` が HTTP 500 になることがあるため、接続確認では使いません。

### WebSocket イベント（主要）

```json
{"type": "progress", "data": {"value": 3, "max": 8}}
{"type": "executing", "data": {"node": "129", "prompt_id": "..."}}
{"type": "executing", "data": {"node": null, "prompt_id": "..."}}
```

`node: null` で実行完了とみなし、`/history` から出力を取得します。

---

## データ構造

### GenerationRequest（`generator.py`）

| フィールド | 説明 |
|-----------|------|
| `prompt` | 動き・シーンの説明 |
| `negative_prompt` | CLI/バッチ用（UI では未使用、ワークフロー上は空） |
| `seed` | `-1` でランダム |
| `reference_image` | パス。あれば I2V |
| `image_strength` | 参照の効き具合（`None` なら config 既定 0.75） |
| `output_name` | 保存ファイル名（拡張子なし） |

### GenerationResult

`prompt`, `seed`, `output_path`, `prompt_id`, `model_name`

---

## VRAM の目安

| 設定 | 目安 |
|------|------|
| LTX FP8, 768×432, 49f, I2V | 比較的動作しやすい |
| LTX FP16, 768×480, 65f, I2V | VRAM 不足（OOM）しやすい |

I2V は参照画像のエンコード分、T2V より VRAM を多く使います。

---

## 関連ドキュメント

- [manual.md](manual.md) — 画面・作り方・注意点
- [README.md](../README.md) — セットアップ
