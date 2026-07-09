# ComfyUI + Wan 2.1 setup (Windows)
# Works without git (uses GitHub ZIP download)
$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path $PSScriptRoot -Parent
$ComfyDir = Join-Path (Split-Path $ProjectDir -Parent) "ComfyUI"

function Test-GitAvailable {
    return [bool](Get-Command git -ErrorAction SilentlyContinue)
}

function Install-FromGitHubZip {
    param(
        [string]$Repo,      # e.g. "comfyanonymous/ComfyUI"
        [string]$DestDir,
        [string]$Branch = "master"
    )

    $zipUrl = "https://github.com/$Repo/archive/refs/heads/$Branch.zip"
    $tempZip = Join-Path $env:TEMP ("gh_" + ($Repo -replace "/", "_") + ".zip")
    $extractDir = Join-Path $env:TEMP ("gh_" + ($Repo -replace "/", "_"))

    Write-Host "Downloading $Repo ($Branch)..."
    Invoke-WebRequest -Uri $zipUrl -OutFile $tempZip -UseBasicParsing

    if (Test-Path $extractDir) { Remove-Item -Recurse -Force $extractDir }
    Expand-Archive -Path $tempZip -DestinationPath $extractDir -Force
    Remove-Item $tempZip -Force

    $repoName = ($Repo -split "/")[-1]
    $extracted = Get-ChildItem $extractDir -Directory | Select-Object -First 1

    if (Test-Path $DestDir) { Remove-Item -Recurse -Force $DestDir }
    Move-Item $extracted.FullName $DestDir
    Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
}

function Install-Repo {
    param(
        [string]$Repo,
        [string]$DestDir,
        [string]$Branch = "master"
    )

    if (Test-Path $DestDir) {
        Write-Host "[skip] Already exists: $DestDir"
        return
    }

    if (Test-GitAvailable) {
        Write-Host "Cloning $Repo..."
        git clone --depth 1 -b $Branch "https://github.com/$Repo.git" $DestDir
    } else {
        Write-Host "git not found, downloading ZIP instead..."
        Install-FromGitHubZip -Repo $Repo -DestDir $DestDir -Branch $Branch
    }
}

Write-Host "=== ComfyUI Install ===" -ForegroundColor Cyan
Write-Host "Target: $ComfyDir"

if (-not (Test-GitAvailable)) {
    Write-Host "Note: git is not installed. Using ZIP download." -ForegroundColor Yellow
}

Install-Repo -Repo "comfyanonymous/ComfyUI" -DestDir $ComfyDir -Branch "master"

Set-Location $ComfyDir

if (-not (Test-Path "venv")) {
    Write-Host "Creating venv..."
    python -m venv venv
}

Write-Host "Installing PyTorch (CUDA 12.4)..."
& .\venv\Scripts\pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

Write-Host "Installing ComfyUI requirements..."
& .\venv\Scripts\pip install -r requirements.txt

$VhsDir = Join-Path $ComfyDir "custom_nodes\ComfyUI-VideoHelperSuite"
if (-not (Test-Path $VhsDir)) {
    Write-Host "Installing VideoHelperSuite (video output)..."
    New-Item -ItemType Directory -Force -Path (Split-Path $VhsDir -Parent) | Out-Null
    Install-Repo -Repo "Kosinkadink/ComfyUI-VideoHelperSuite" -DestDir $VhsDir -Branch "main"
    & .\venv\Scripts\pip install -r (Join-Path $VhsDir "requirements.txt")
}

Write-Host ""
Write-Host "Done: ComfyUI installed." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps (from wan-video-gen folder):"
Write-Host "  1. Download models:  .\scripts\download_models.ps1"
Write-Host "  2. Start ComfyUI:    .\scripts\start_comfyui.ps1"
Write-Host "  3. Connection check: python scripts\generate.py check"
