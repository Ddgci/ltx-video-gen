# Publish current main branch to the public distribution repository.
#
# Setup (once):
#   1. Install GitHub CLI: https://cli.github.com/
#   2. gh auth login
#   3. Run this script from the project root
#
# Private dev repo : origin  -> github.com/Ddgci/ai-video-gen (private)
# Public dist repo : public -> github.com/Ddgci/ltx-video-gen (public)

$ErrorActionPreference = "Stop"

$PublicOwner = "Ddgci"
$PublicRepo = "ltx-video-gen"
$PublicUrl = "https://github.com/$PublicOwner/$PublicRepo.git"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Set-Location $ProjectRoot

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) が見つかりません。https://cli.github.com/ からインストールして gh auth login してください。"
}

gh auth status 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "gh にログインしていません。PowerShell で gh auth login を実行してください。"
}

Write-Host "=== Public リポジトリ確認: $PublicOwner/$PublicRepo ===" -ForegroundColor Cyan

$repoExists = $false
try {
    gh repo view "$PublicOwner/$PublicRepo" --json name 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $repoExists = $true }
} catch {
    $repoExists = $false
}

if (-not $repoExists) {
    Write-Host "Public リポジトリを作成します..." -ForegroundColor Yellow
    gh repo create "$PublicOwner/$PublicRepo" `
        --public `
        --description "LTX-Video 2 local video generator (public distribution)" `
        --disable-wiki `
        --disable-issues
    if ($LASTEXITCODE -ne 0) {
        Write-Error "リポジトリ作成に失敗しました。"
    }
}

$remotes = git remote
if ($remotes -notcontains "public") {
    git remote add public $PublicUrl
    Write-Host "remote 'public' を追加: $PublicUrl"
} else {
    git remote set-url public $PublicUrl
}

Write-Host "main を public に push します..." -ForegroundColor Cyan
git push public main

Write-Host ""
Write-Host "完了: https://github.com/$PublicOwner/$PublicRepo" -ForegroundColor Green
Write-Host "開発は origin (private)、公開は public リモートへ push してください。"
