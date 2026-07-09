# Download LTX-Video 2 models for ComfyUI
$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path $PSScriptRoot -Parent
$ComfyDir = Join-Path (Split-Path $ProjectDir -Parent) "ComfyUI"

if (-not (Test-Path (Join-Path $ComfyDir "main.py"))) {
    Write-Host "ComfyUI not found at: $ComfyDir" -ForegroundColor Red
    Write-Host "Run first: .\scripts\install_comfyui.ps1"
    exit 1
}

& (Join-Path $ProjectDir ".venv\Scripts\pip.exe") install huggingface_hub -q
$Hf = Join-Path $ProjectDir ".venv\Scripts\hf.exe"

function Download-Model($Repo, $File, $DestDir, $DestName) {
    $dest = Join-Path $DestDir $DestName
    if (Test-Path $dest) {
        Write-Host "[skip] $DestName"
        return
    }
    New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
    Write-Host "[download] $DestName"
    & $Hf download $Repo $File --local-dir $DestDir
    $downloaded = Join-Path $DestDir $File
    if ((Test-Path $downloaded) -and ($downloaded -ne $dest)) {
        Move-Item -Force $downloaded $dest
    }
}

Write-Host "=== Download LTX-Video 2 (FP8) ===" -ForegroundColor Cyan
Write-Host "Target: $ComfyDir"
Set-Location $ComfyDir

Download-Model "Lightricks/LTX-2" "ltx-2-19b-distilled-fp8.safetensors" `
    (Join-Path $ComfyDir "models\checkpoints") "ltx-2-19b-distilled-fp8.safetensors"

Write-Host ""
Write-Host "=== LTX FP16 (optional, ~38GB) ===" -ForegroundColor Cyan
Download-Model "Lightricks/LTX-2" "ltx-2-19b-distilled.safetensors" `
    (Join-Path $ComfyDir "models\checkpoints") "ltx-2-19b-distilled.safetensors"

Download-Model "Comfy-Org/ltx-2" `
    "split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors" `
    (Join-Path $ComfyDir "models\text_encoders") "gemma_3_12B_it_fp4_mixed.safetensors"

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "参照画像は wan-video-gen\references\ に jpg/png を置いてください。" -ForegroundColor Yellow
