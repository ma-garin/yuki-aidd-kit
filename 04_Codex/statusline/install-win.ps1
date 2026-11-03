# Codex CLI の4行ステータス（Windows 版）を導入する。Windows Terminal + Python 3.11 以降。
# - 本体を ~/.local/share/codex-statusline/ に置く（原本 codex_status.py と Windows 版の 2 本）
# - PowerShell プロファイルに codex 関数を足す（関数はスクリプトより優先される。既存行があれば置き換える）
# 使い方: powershell -ExecutionPolicy Bypass -File 04_Codex/statusline/install-win.ps1
$ErrorActionPreference = 'Stop'
$src = $PSScriptRoot
$dst = Join-Path $HOME '.local\share\codex-statusline'
New-Item -ItemType Directory -Force $dst | Out-Null
foreach ($f in 'codex_status.py', 'codex_status_win.py', 'README.md') {
  $t = Join-Path $dst $f
  if (Test-Path $t) { Copy-Item $t "$t.previous" -Force }
  Copy-Item (Join-Path $src $f) $t -Force
}
# PowerShell 5.1 は外部コマンドへの引数から内側の引用符を落とすので、-c に引用符を含めない
$py = $null
# 版付きの名前を先に探す（Store 版は python3.12.exe が実体で、python・python3 はスタブや Git Bash 用の別物のことがある）
foreach ($name in 'python3.14', 'python3.13', 'python3.12', 'python3.11', 'py', 'python', 'python3') {
  # Microsoft Store のスタブ（実体の無い python3 等）は stderr に出すだけなので、失敗として飛ばす
  try {
    $ErrorActionPreference = 'Continue'
    if (Get-Command $name -ErrorAction SilentlyContinue) { $py = (& $name -c "import sys;print(sys.executable)" 2>$null) }
  } catch { $py = $null } finally { $ErrorActionPreference = 'Stop' }
  if ($py) { break }  # WindowsApps の実体はリパースポイントで Test-Path が偽になるので存在確認しない
}
if (-not $py) { throw 'python が見つかりません。Python 3.11 以降を入れてから再実行してください' }
$ver = [version]((& $py --version) -replace '^Python\s+', '')
if ($ver -lt [version]'3.11') { throw "Python 3.11 以降が必要です（現在 $ver）" }
$marker = '# codex-statusline (aidd-kit)'
$line = "function codex { & `"$py`" `"$dst\codex_status_win.py`" @args }  $marker"
foreach ($prof in @($PROFILE.CurrentUserCurrentHost, ($PROFILE.CurrentUserCurrentHost -replace 'WindowsPowerShell', 'PowerShell'))) {
  New-Item -ItemType Directory -Force (Split-Path $prof) | Out-Null
  $body = if (Test-Path $prof) { @(Get-Content $prof -Encoding UTF8 | Where-Object { $_ -notlike "*$marker*" }) } else { @() }
  Set-Content $prof -Value ($body + $line) -Encoding UTF8
  Write-Output "プロファイル: $prof"
}
Write-Output "導入済み: $dst"
Write-Output '新しい PowerShell タブで codex を実行してください（標準表示で起動するなら $env:CODEX_STATUS_DISABLE=1）。'
