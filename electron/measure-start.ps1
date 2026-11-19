# Desktop startup measurement (works for packaged Electron and pywebview build)
#   powershell -NoProfile -ExecutionPolicy Bypass -File measure-start.ps1 -Exe <abs path> -AppArgs "--smoke"
# Polls MainWindowHandle every 50ms to record time-to-window-visible, then reports leftovers.
param(
  [Parameter(Mandatory = $true)][string]$Exe,
  [string]$AppArgs = "",
  [string]$UserDataDir = "",
  [switch]$CloseOnVisible,
  [int]$TimeoutSec = 180
)

$ErrorActionPreference = "Stop"
$ud = $UserDataDir
$argList = @()
if ($AppArgs -ne "") { $argList += $AppArgs }
if ($ud -ne "") {
  New-Item -ItemType Directory -Path $ud -Force | Out-Null
  $argList += "--user-data-dir=$ud"
}

$t0 = [Diagnostics.Stopwatch]::StartNew()
if ($argList.Count -gt 0) {
  $p = Start-Process -FilePath $Exe -ArgumentList $argList -PassThru
} else {
  $p = Start-Process -FilePath $Exe -PassThru
}
$visibleMs = $null
while (-not $p.HasExited) {
  if ($null -eq $visibleMs) {
    $proc = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
    if ($proc -and $proc.MainWindowHandle -ne 0) {
      $visibleMs = [math]::Round($t0.Elapsed.TotalMilliseconds)
      "WINDOW_VISIBLE_MS $visibleMs"
      if ($CloseOnVisible) { $proc.CloseMainWindow() | Out-Null }
    }
  }
  Start-Sleep -Milliseconds 50
  if ($t0.Elapsed.TotalSeconds -gt $TimeoutSec) { "TIMEOUT"; break }
}
$t0.Stop()
"APP_EXIT wall_ms=" + [math]::Round($t0.Elapsed.TotalMilliseconds)
if ($null -eq $visibleMs) { "WINDOW_VISIBLE_MS null (no window handle captured)" }
Start-Sleep -Milliseconds 800
"--- leftover processes ---"
$left = Get-Process TianJianZhiKanBackend, TianJianZhiKan, electron -ErrorAction SilentlyContinue
if ($left) { $left | Select-Object Id, ProcessName | Format-Table -AutoSize } else { "none" }
