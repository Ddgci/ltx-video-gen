# wan-video-gen setup (Windows)
$ErrorActionPreference = "Stop"

Write-Host "=== wan-video-gen setup ===" -ForegroundColor Cyan

if (-not (Test-Path ".venv")) {
    Write-Host "Creating venv..."
    python -m venv .venv
}

Write-Host "Installing dependencies..."
& .\.venv\Scripts\pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "Created .env"
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Install ComfyUI:  .\scripts\install_comfyui.ps1"
Write-Host "  2. Download models:  .\scripts\download_models.ps1"
Write-Host "  3. Start ComfyUI:    .\scripts\start_comfyui.ps1   (keep this terminal open)"
Write-Host "  4. Start Web UI:     .\scripts\start_ui.ps1        (Gradio, port 7860)"
Write-Host "  5. Check connection: python scripts\generate.py check"
