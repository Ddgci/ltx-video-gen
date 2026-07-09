# 公開リポジトリ運用

開発用（private）と配布用（public）を分けて運用します。

| リポジトリ | 用途 | URL |
|-----------|------|-----|
| `ai-video-gen` | 開発（private） | https://github.com/Ddgci/ai-video-gen |
| `ltx-video-gen` | 公開配布（public） | https://github.com/Ddgci/ltx-video-gen |

## 初回セットアップ

1. [GitHub CLI](https://cli.github.com/) をインストール
2. ログイン:

```powershell
gh auth login
```

3. 公開リポジトリ作成 + 初回 push:

```powershell
cd wan-video-gen
.\scripts\publish-public.ps1
```

## 2回目以降（公開したいとき）

```powershell
# private で開発・コミット
git push origin main

# 公開版を更新
.\scripts\publish-public.ps1
```

または:

```powershell
git push public main
```

## Git リモート

| 名前 | 向き先 |
|------|--------|
| `origin` | private 開発リポジトリ |
| `public` | public 配布リポジトリ |

```powershell
git remote -v
```

## GitHub Releases

公開版のタグ付きリリースは **public リポジトリ** 側で作成します。

```powershell
git tag v1.0.0
git push public v1.0.0
gh release create v1.0.0 --repo Ddgci/ltx-video-gen --title "v1.0.0" --notes "初回公開"
```

## 注意

- private の `origin` に push しても public 側は自動更新されません
- public に載せたくないファイルは `.gitignore` で除外（`.env`, `.venv` など）
- 参照画像は個人の写真を含む場合、public push 前に内容を確認してください
