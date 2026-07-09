# Start ComfyUI API server
$ErrorActionPreference = "Stop"

$ComfyDir = Join-Path (Split-Path $PSScriptRoot -Parent | Split-Path -Parent) "ComfyUI"
if (-not (Test-Path (Join-Path $ComfyDir "main.py"))) {
    $ComfyDir = Join-Path $env:USERPROFILE "Projects\ComfyUI"
}

if (-not (Test-Path (Join-Path $ComfyDir "main.py"))) {
    Write-Host "ComfyUI not found at: $ComfyDir" -ForegroundColor Red
    Write-Host "Run first: .\scripts\install_comfyui.ps1"
    exit 1
}

Write-Host "Starting ComfyUI at http://127.0.0.1:8188" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop."
Write-Host ""

Set-Location $ComfyDir
& .\venv\Scripts\python.exe main.py --listen 127.0.0.1 --port 8188
