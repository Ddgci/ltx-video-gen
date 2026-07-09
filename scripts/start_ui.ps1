# 動画生成 Web UI を起動（Gradio）
$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path $PSScriptRoot -Parent
Set-Location $ProjectDir

$Python = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "venv がありません。先に .\setup.ps1 を実行してください。" -ForegroundColor Red
    exit 1
}

Write-Host "=== 動画生成 UI 起動 ===" -ForegroundColor Cyan
Write-Host "ComfyUI (別プロセス): http://127.0.0.1:8188"
Write-Host "この UI:              http://127.0.0.1:7860"
Write-Host ""
Write-Host "※ ComfyUI 本体 = ComfyUI\main.py / このツール = wan-video-gen\app.py（別物）"
Write-Host ""

& $Python app.py
