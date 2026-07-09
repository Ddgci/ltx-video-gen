# 設計書

## 概要

本ツールは、ローカル GPU 上で AI モデルを動かし、テキストから動画を自動生成するアプリケーションです。

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
│  │ wan_video_gen│                │  AI モデル         │   │
│  │ (Python)     │                │  - Wan 2.1 1.3B  │   │
│  │              │                │  - LTX-Video 2   │   │
│  └──────────────┘                └──────────────────┘   │
│                                                         │
│  ┌──────────────┐                                       │
│  │  output/     │ ← 生成された動画が保存される              │
│  └──────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

---

## コンポーネント構成

```
wan-video-gen/
├── app.py                          [エントリポイント] Web UI + ComfyUI 自動起動
├── config.yaml                     [設定] モデル・解像度・接続先の定義
│
├── src/wan_video_gen/              [コアロジック]
│   ├── __init__.py                 パッケージ定義
│   ├── config.py                   設定ファイルの読み込み
│   ├── comfy_client.py             ComfyUI API 通信・WebSocket 進捗監視
│   ├── generator.py                動画生成の実行フロー
│   └── batch_runner.py             CSV 一括生成
│
├── workflows/                      [ワークフロー定義]
│   ├── wan_t2v_1.3b.template.json  Wan 2.1 用
│   └── ltx_t2v_distilled.template.json  LTX-Video 2 用
│
├── scripts/                        [セットアップ・運用]
│   ├── generate.py                 CLI インターフェース
│   ├── install_comfyui.ps1         ComfyUI インストール
│   ├── start_comfyui.ps1           ComfyUI 手動起動
│   └── download_models.ps1         モデルダウンロード
│
├── prompts/example.csv             バッチ生成用サンプル
├── output/                         生成動画の出力先
└── docs/                           ドキュメント
```

---

## 動画生成フロー

```
[ユーザー]
    │
    │ ① プロンプト入力 + 「動画を生成」ボタン
    ▼
[app.py (Gradio Web UI)]
    │
    │ ② GenerationRequest を作成
    ▼
[generator.py - VideoGenerator]
    │
    │ ③ ワークフロー JSON にパラメータを注入
    │    - プロンプト
    │    - シード値
    │    - 解像度・フレーム数
    ▼
[comfy_client.py - ComfyUIClient]
    │
    │ ④ HTTP POST /prompt でキューに投入
    ▼
[ComfyUI サーバー (port 8188)]
    │
    │ ⑤ AI モデルで動画を生成（GPU 処理）
    │    - テキストエンコード（UMT5 / Gemma 3）
    │    - サンプリング（KSampler / SamplerCustom）
    │    - VAE デコード（潜在空間 → ピクセル）
    │    - 動画ファイル書き出し
    │
    │ ⑥ WebSocket で進捗通知
    │    "progress": { "value": 15, "max": 30 }
    ▼
[comfy_client.py]
    │
    │ ⑦ 完了検知 → HTTP GET /view でファイルダウンロード
    ▼
[generator.py]
    │
    │ ⑧ output/ フォルダに保存
    ▼
[app.py]
    │
    │ ⑨ 動画プレビュー + 情報表示
    ▼
[ユーザーのブラウザに動画が表示される]
```

---

## 使用技術スタック

### AI モデル

| モデル | 開発元 | パラメータ数 | 特徴 |
|--------|--------|-------------|------|
| **Wan 2.1 T2V 1.3B** | Wan-AI (Alibaba系) | 13億 | 高品質・日本語対応・汎用 |
| **LTX-Video 2 Distilled** | Lightricks | 190億 (FP8量子化) | 高速(8steps)・英語特化 |

### フレームワーク・ライブラリ

| 技術 | 用途 | バージョン |
|------|------|-----------|
| **ComfyUI** | AI モデル実行エンジン | 0.27+ |
| **PyTorch** | GPU 計算フレームワーク | 2.5+ (CUDA 12.4) |
| **Gradio** | Web UI フレームワーク | 6.x |
| **Python** | メイン言語 | 3.10+ |
| **websocket-client** | WebSocket 通信 | 1.6+ |
| **requests** | HTTP 通信 | 2.31+ |
| **PyYAML** | 設定ファイル読み込み | 6.0+ |

### AI パイプライン詳細

```
テキスト入力
    │
    ▼
[Text Encoder]
    Wan: UMT5-XXL (FP8) — 多言語対応の大規模言語モデル
    LTX: Gemma 3 12B (FP4) — Google の軽量言語モデル
    │
    ▼
[Diffusion Model / Sampler]
    Wan: Wan2.1 DiT 1.3B — 拡散変換モデル (30 steps, CFG=6)
    LTX: LTX-Video 19B Distilled — 蒸留済み拡散モデル (8 steps, CFG=1)
    │
    ▼
[VAE Decoder]
    潜在空間の数値データ → 実際のピクセル（映像フレーム）に変換
    │
    ▼
[Video Encoder]
    フレーム列 → MP4 動画ファイル (H.264)
```

---

## 設定ファイル (config.yaml) の構造

```yaml
active_model: "wan"          # デフォルトモデル

comfyui:
  host: "127.0.0.1"          # ComfyUI のアドレス
  port: 8188                  # ComfyUI のポート

models:
  wan:                        # Wan 2.1 の設定
    name: "Wan 2.1 T2V 1.3B"
    width: 832                # 生成する動画の横幅
    height: 480               # 高さ
    num_frames: 81            # フレーム数 (81 ÷ 16fps = 約5秒)
    fps: 16
    steps: 30                 # サンプリング回数（多い=高品質・遅い）
    cfg: 6.0                  # プロンプトへの忠実度
    ...

  ltx:                        # LTX-Video 2 の設定
    name: "LTX-Video 2 Distilled"
    width: 768
    height: 512
    num_frames: 97            # (97 ÷ 24fps = 約4秒)
    fps: 24
    steps: 8                  # 蒸留モデルなので少ないステップで OK
    cfg: 1.0
    ...
```

---

## 通信プロトコル

### ComfyUI API

| エンドポイント | メソッド | 用途 |
|---------------|---------|------|
| `/system_stats` | GET | 接続確認 |
| `/prompt` | POST | ワークフロー投入 |
| `/history/{prompt_id}` | GET | 生成結果取得 |
| `/view?filename=...` | GET | ファイルダウンロード |
| `ws://host:port/ws` | WebSocket | リアルタイム進捗 |

### WebSocket メッセージ

```json
{"type": "progress", "data": {"value": 15, "max": 30}}
{"type": "executing", "data": {"node": "3", "prompt_id": "xxx"}}
{"type": "executing", "data": {"node": null, "prompt_id": "xxx"}}  ← 完了
```

---

## VRAM 使用量の目安

| モデル | 解像度 | VRAM 使用量 |
|--------|--------|------------|
| Wan 2.1 1.3B | 832×480 | 約 8〜10 GB |
| Wan 2.1 1.3B | 1280×720 | 約 11〜12 GB |
| LTX-Video 2 FP8 | 768×512 | 約 10〜12 GB |


