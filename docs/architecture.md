# 設計書

## 概要

ローカル GPU 上で **LTX-Video 2** を ComfyUI 経由で動かし、**参照画像（見た目）** と **プロンプト（動き）** から動画を生成するアプリケーションです。

---

## システム構成図

```
┌─────────────────────────────────────────────────────────┐
│                     ユーザーの PC                          │
│                                                         │
│  ┌──────────────┐    HTTP/WS     ┌──────────────────┐   │
│  │  Web UI      │◄──────────────►│   ComfyUI        │   │
│  │  (Gradio)    │  port 7860     │   (AI エンジン)    │   │
│  │  app.py      │                │   port 8188      │   │
│  └──────┬───────┘                └────────┬─────────┘   │
│         │                                 │             │
│         │ Python 呼び出し                   │ GPU 処理     │
│         ▼                                 ▼             │
│  ┌──────────────┐                ┌──────────────────┐   │
│  │ wan_video_gen│                │  LTX-Video 2     │   │
│  │ (Python)     │                │  FP8 / FP16      │   │
│  └──────────────┘                └──────────────────┘   │
│                                                         │
│  references/  ← 参照画像（I2V）                           │
│  output/      ← 生成動画                                  │
└─────────────────────────────────────────────────────────┘

../ComfyUI/  … 別フォルダ（models/checkpoints, text_encoders）
```

---

## コンポーネント構成

```
wan-video-gen/
├── app.py                          Web UI
├── config.yaml                     モデル・解像度・参照画像パス
│
├── src/wan_video_gen/
│   ├── config.py                   設定読み込み
│   ├── comfy_client.py             ComfyUI API / WebSocket
│   ├── generator.py                T2V / I2V 切替・ワークフロー注入
│   ├── prompt_enhancer.py          Ollama (Gemma) でプロンプト拡張
│   ├── prompt_utils.py             LTX 向けプロンプト整形
│   ├── reference_utils.py          参照画像一覧・ComfyUI パス解決
│   └── batch_runner.py             CSV 一括生成
│
├── workflows/
│   ├── ltx_t2v_distilled.template.json   テキストのみ
│   └── ltx_i2v_distilled.template.json   参照画像あり
│
├── references/                     日本の道路・車内など（ユーザー追加）
├── scripts/
│   ├── generate.py                 CLI
│   ├── check_models.py             モデル存在確認
│   ├── download_models.ps1
│   ├── install_comfyui.ps1
│   ├── start_comfyui.ps1
│   └── start_ui.ps1
│
└── output/                         生成動画
```

---

## 動画生成フロー

```
[ユーザー]
    │ 参照画像（任意）+ プロンプト
    ▼
[app.py]
    │ Gemma 拡張（任意）→ prepare_ltx_prompt
    ▼
[generator.py]
    │ 参照画像あり → I2V ワークフロー
    │ 参照画像なし → T2V ワークフロー
    │ 解像度・フレーム・シード・image_strength を JSON に注入
    ▼
[comfy_client.py]  POST /prompt
    ▼
[ComfyUI]  Gemma 3 エンコード → LTX サンプリング → VAE → MP4
    │ WebSocket 進捗
    ▼
[output/]  保存 → UI プレビュー
```

---

## 使用技術

### AI モデル

| モデル | ファイル | 用途 |
|--------|---------|------|
| LTX FP8 | `ltx-2-19b-distilled-fp8.safetensors` | デフォルト・省 VRAM |
| LTX FP16 | `ltx-2-19b-distilled.safetensors` | 高品質（任意） |
| Gemma 3 12B | `gemma_3_12B_it_fp4_mixed.safetensors` | テキストエンコーダ（必須） |

### その他

| 技術 | 用途 |
|------|------|
| ComfyUI 0.27+ | ワークフロー実行 |
| Gradio 6.x | Web UI |
| Ollama + Gemma 7B | プロンプト英語拡張（任意） |

---

## config.yaml（要点）

```yaml
active_model: "ltx"

references:
  dir: "references"

models:
  ltx:      # FP8 — checkpoint + i2v_workflow_path
  ltx_fp16: # FP16 — 別チェックポイント、同ワークフロー
```

I2V 時は `image_node_id`（LoadImage）と `i2v_latent_node_id`（LTXVImgToVideo）にパラメータを流し込みます。

---

## ComfyUI API

| エンドポイント | 用途 |
|---------------|------|
| `/queue` | 接続確認（`/system_stats` は 500 になる版がある） |
| `/prompt` | ワークフロー投入 |
| `/history/{id}` | 結果取得 |
| `/view` | ファイル取得 |
| WebSocket | 進捗 |

---

## VRAM の目安

| 設定 | 目安 |
|------|------|
| LTX FP8, 768×432, 49f, I2V | 動作しやすい |
| LTX FP16, 768×480, 65f, I2V | OOM しやすい |

---

## 関連ドキュメント

- [manual.md](manual.md) — 画面・作り方・注意点
- [README.md](../README.md) — セットアップ
