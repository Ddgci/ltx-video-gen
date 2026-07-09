"""
ComfyUI API クライアント

ComfyUI サーバーへの接続、ワークフロー投入、
WebSocket での進捗監視、生成結果の取得を行う。
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

import requests


class ComfyUIError(RuntimeError):
    """ComfyUI との通信や生成で発生したエラー"""
    pass


# 進捗コールバックの型: (進捗率 0.0〜1.0, 説明テキスト) を受け取る関数
ProgressCallback = Callable[[float, str], None]


class ComfyUIClient:
    """ComfyUI サーバーとの通信を管理するクライアント"""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # クライアント ID: WebSocket で自分の生成結果だけ受け取るために使用
        self.client_id = str(uuid.uuid4())

    def _connection_lost_message(self) -> str:
        return (
            f"ComfyUI への接続が切れました ({self.base_url})。\n"
            "生成中に ComfyUI が停止した可能性があります。\n"
            "・LTX モデルは VRAM 不足で落ちやすいです（Wan 1.3B を試してください）\n"
            "・ComfyUI を再起動してから UI の「ComfyUI 起動」を押してください"
        )

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """HTTP リクエスト。接続エラーは ComfyUIError に変換する"""
        try:
            resp = requests.request(method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.ConnectionError as exc:
            raise ComfyUIError(self._connection_lost_message()) from exc
        except requests.RequestException as exc:
            raise ComfyUIError(f"ComfyUI 通信エラー: {exc}") from exc

    @property
    def ws_url(self) -> str:
        """WebSocket 接続用 URL を組み立てる"""
        host = self.base_url.replace("http://", "").replace("https://", "")
        return f"ws://{host}/ws?clientId={self.client_id}"

    def check_connection(self) -> None:
        """ComfyUI が起動しているか確認（接続できなければ例外）"""
        last_status: str | None = None
        # ComfyUI 0.27 では /system_stats が 500 になることがあるため複数試す
        for path in ("/queue", "/object_info", "/"):
            try:
                resp = requests.get(f"{self.base_url}{path}", timeout=self.timeout)
                if resp.status_code == 200:
                    return
                last_status = f"{path} → HTTP {resp.status_code}"
            except requests.ConnectionError as exc:
                raise ComfyUIError(
                    f"ComfyUI に接続できません ({self.base_url})。"
                    " ComfyUI が起動しているか確認してください。"
                ) from exc
            except requests.RequestException as exc:
                last_status = str(exc)

        detail = f" ({last_status})" if last_status else ""
        raise ComfyUIError(
            f"ComfyUI に接続できません ({self.base_url})。{detail}"
        )

    def queue_prompt(self, workflow: dict[str, Any]) -> str:
        """
        ワークフローを ComfyUI のキューに投入する。

        戻り値: prompt_id（生成ジョブの一意な ID）
        """
        payload = {"prompt": workflow, "client_id": self.client_id}
        try:
            resp = requests.post(
                f"{self.base_url}/prompt",
                json=payload,
                timeout=self.timeout,
            )
        except requests.ConnectionError as exc:
            raise ComfyUIError(self._connection_lost_message()) from exc
        except requests.RequestException as exc:
            raise ComfyUIError(f"ComfyUI 通信エラー: {exc}") from exc

        if resp.status_code != 200:
            raise ComfyUIError(self._format_prompt_error(resp))

        data = resp.json()
        if "error" in data:
            raise ComfyUIError(self._format_prompt_error(resp))

        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise ComfyUIError(f"prompt_id が返りませんでした: {data}")
        return prompt_id

    def _format_prompt_error(self, resp: requests.Response) -> str:
        """ComfyUI /prompt の 400 応答を読みやすいメッセージに変換"""
        try:
            data = resp.json()
        except ValueError:
            return f"プロンプト送信失敗: HTTP {resp.status_code} {resp.text[:500]}"

        lines = [f"ComfyUI ワークフローエラー (HTTP {resp.status_code})"]
        err = data.get("error", {})
        if err.get("message"):
            lines.append(f"原因: {err['message']}")
        if err.get("type"):
            lines.append(f"種別: {err['type']}")

        node_errors = data.get("node_errors", {})
        for node_id, info in node_errors.items():
            class_type = info.get("class_type", "?")
            for item in info.get("errors", []):
                msg = item.get("message", "")
                detail = item.get("details", "")
                lines.append(f"ノード {node_id} ({class_type}): {msg} — {detail}")

        if "clip_vision_h.safetensors" in resp.text:
            lines.append(
                "対処: I2V 用モデル clip_vision_h.safetensors が未配置です。\n"
                "  .\\scripts\\download_models.ps1 を実行してください。"
            )

        return "\n".join(lines)

    def wait_for_completion_ws(
        self,
        prompt_id: str,
        on_progress: ProgressCallback | None = None,
        max_wait: float = 3600.0,
    ) -> dict[str, Any]:
        """
        WebSocket でリアルタイム進捗を受け取りながら完了を待つ。

        ComfyUI は生成中に以下のメッセージを送ってくる:
        - "progress": サンプリングの現在ステップ / 最大ステップ
        - "executing": 現在実行中のノード（None なら完了）
        - "execution_error": エラー発生

        websocket-client が未インストールの場合はポーリングにフォールバック。
        """
        try:
            import websocket
        except ImportError:
            # websocket-client が無い場合は HTTP ポーリングで代替
            return self.wait_for_completion(prompt_id, on_progress=on_progress, max_wait=max_wait)

        ws = websocket.create_connection(self.ws_url, timeout=max_wait)
        start_time = time.time()
        completed = False

        try:
            while time.time() - start_time < max_wait:
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                except websocket.WebSocketConnectionClosedException:
                    break

                # バイナリデータ（プレビュー画像等）はスキップ
                if isinstance(raw, bytes):
                    continue

                msg = json.loads(raw)
                msg_type = msg.get("type")
                data = msg.get("data", {})

                if msg_type == "progress":
                    # サンプリング進捗: value=現在ステップ, max=総ステップ数
                    value = data.get("value", 0)
                    max_val = data.get("max", 1)
                    if on_progress and max_val > 0:
                        step_progress = value / max_val
                        elapsed = time.time() - start_time
                        # 残り時間の推定
                        if value > 0:
                            eta = (elapsed / value) * (max_val - value)
                            eta_str = f" | 残り約{int(eta)}秒"
                        else:
                            eta_str = ""
                        on_progress(
                            step_progress,
                            f"ステップ {value}/{max_val}{eta_str}",
                        )

                elif msg_type == "executing":
                    # node が None = 全ノード実行完了
                    node = data.get("node")
                    if node is None and data.get("prompt_id") == prompt_id:
                        completed = True
                        break

                elif msg_type == "execution_error":
                    raise ComfyUIError(f"実行エラー: {data}")

        except websocket.WebSocketException as exc:
            raise ComfyUIError(self._connection_lost_message()) from exc
        finally:
            try:
                ws.close()
            except Exception:
                pass

        if not completed:
            # WebSocket が切れたが完了通知が来なかった → ComfyUI クラッシュの可能性
            try:
                self.check_connection()
            except ComfyUIError:
                raise ComfyUIError(self._connection_lost_message())
            # サーバーは生きているが WS だけ切れた → ポーリングで結果取得を試みる
            return self.wait_for_completion(prompt_id, on_progress=on_progress, max_wait=max_wait)

        return self._fetch_history(prompt_id)

    def wait_for_completion(
        self,
        prompt_id: str,
        poll_interval: float = 2.0,
        max_wait: float = 3600.0,
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """HTTP ポーリングで完了を待つ（WebSocket が使えない場合のフォールバック）"""
        deadline = time.time() + max_wait
        start_time = time.time()

        while time.time() < deadline:
            resp = self._request("GET", f"/history/{prompt_id}")
            history = resp.json()

            if prompt_id in history:
                entry = history[prompt_id]
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    messages = status.get("messages", [])
                    raise ComfyUIError(f"生成エラー: {messages}")
                return entry

            elapsed = time.time() - start_time
            if on_progress:
                on_progress(0.0, f"待機中... ({int(elapsed)}秒経過)")

            time.sleep(poll_interval)

        raise ComfyUIError(f"タイムアウト ({max_wait}秒): prompt_id={prompt_id}")

    def _fetch_history(self, prompt_id: str) -> dict[str, Any]:
        """生成完了後に履歴から結果を取得する"""
        resp = self._request("GET", f"/history/{prompt_id}")
        history = resp.json()
        if prompt_id in history:
            entry = history[prompt_id]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                messages = status.get("messages", [])
                raise ComfyUIError(f"生成エラー: {messages}")
            return entry
        raise ComfyUIError(f"履歴が見つかりません: {prompt_id}")

    def get_output_files(self, history_entry: dict[str, Any]) -> list[dict[str, Any]]:
        """生成履歴から出力ファイル情報を抽出する"""
        outputs = history_entry.get("outputs", {})
        files: list[dict[str, Any]] = []
        for node_output in outputs.values():
            for key in ("gifs", "videos", "images"):
                for item in node_output.get(key, []):
                    files.append(item)
        return files

    def download_file(self, file_info: dict[str, Any], dest: Path) -> Path:
        """ComfyUI サーバーから生成ファイルをダウンロードして保存する"""
        params = {
            "filename": file_info["filename"],
            "subfolder": file_info.get("subfolder", ""),
            "type": file_info.get("type", "output"),
        }
        resp = self._request("GET", f"/view?{urlencode(params)}")

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        return dest

    def upload_image(self, image_path: Path) -> str:
        """
        参照画像を ComfyUI の input フォルダにアップロードする。

        戻り値: ComfyUI 上のファイル名（LoadImage ノードで使用）
        """
        if not image_path.exists():
            raise ComfyUIError(f"参照画像が見つかりません: {image_path}")

        suffix = image_path.suffix.lower()
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(suffix, "image/png")

        with image_path.open("rb") as f:
            files = {"image": (image_path.name, f, mime)}
            data = {"type": "input", "overwrite": "true"}
            resp = self._request("POST", "/upload/image", files=files, data=data)

        result = resp.json()
        name = result.get("name")
        if not name:
            raise ComfyUIError(f"画像アップロード失敗: {result}")
        return name


def load_workflow(path: Path) -> dict[str, Any]:
    """ComfyUI ワークフロー JSON ファイルを読み込む"""
    with path.open(encoding="utf-8") as f:
        return json.load(f)
