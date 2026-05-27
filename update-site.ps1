# 一鍵更新「入校試用 需求庫」網站
# 用法：雙擊「更新網站.cmd」，或在 PowerShell 執行  .\update-site.ps1
# 流程：產生 data.json → 看變更 → commit → push → GitHub Actions 自動發布

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try { [Console]::InputEncoding = [System.Text.Encoding]::UTF8 } catch {}

Set-Location $PSScriptRoot

Write-Host "=== 入校試用 需求庫：更新網站 ===" -ForegroundColor Cyan
Write-Host ("資料夾：" + $PSScriptRoot)
Write-Host ""

Write-Host "[1/4] 重新產生 site/data.json ..." -ForegroundColor Yellow
python site/build.py
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "✗ build.py 失敗，已中止（沒有提交任何東西）。請看上面的錯誤訊息。" -ForegroundColor Red
    Read-Host "按 Enter 關閉"
    exit 1
}

$changes = git status --porcelain
if (-not $changes) {
    Write-Host ""
    Write-Host "沒有任何變更，網站已是最新，不需更新。" -ForegroundColor Green
    Read-Host "按 Enter 關閉"
    exit 0
}

Write-Host ""
Write-Host "本次變更：" -ForegroundColor Yellow
git status --short
Write-Host ""

$msg = Read-Host "輸入這次更新說明（直接按 Enter 用預設）"
if ([string]::IsNullOrWhiteSpace($msg)) {
    $msg = "更新需求清單 " + (Get-Date -Format "yyyy-MM-dd HH:mm")
}

Write-Host ""
Write-Host "[2/4] git add ..." -ForegroundColor Yellow
git add -A
Write-Host "[3/4] git commit ..." -ForegroundColor Yellow
git commit -m $msg
Write-Host "[4/4] git push ..." -ForegroundColor Yellow
git push
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "✗ push 失敗（可能是網路或登入問題）。變更已存成本機 commit，稍後重跑此腳本或手動 git push 即可。" -ForegroundColor Red
    Read-Host "按 Enter 關閉"
    exit 1
}

Write-Host ""
Write-Host "✓ 完成！約 20–30 秒後重新整理頁面即可看到更新：" -ForegroundColor Green
Write-Host "  https://textbookforwork.github.io/v1-trial-insight/" -ForegroundColor Green
Write-Host ""
Read-Host "按 Enter 關閉"
