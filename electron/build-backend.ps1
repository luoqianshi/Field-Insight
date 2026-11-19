# 一键重建 Electron 后端载荷（PyInstaller onedir → electron\backend-dist\TianJianZhiKanBackend\）
# 用法（仓库根或任意 cwd 均可，spec 已锚定 SPECPATH）：
#   powershell -NoProfile -ExecutionPolicy Bypass -File electron\build-backend.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File electron\build-backend.ps1 -PythonExe <构建环境 python.exe>
#
# 构建环境要求（与旧 D:\UAVDesktopBuild\venv 实测版本对齐）：
#   Python 3.8.20（conda uav-vis）基础上建 venv：
#     C:\Users\lqs\.conda\envs\uav-vis\python.exe -m venv --system-site-packages <venv目录>
#     <venv目录>\Scripts\pip install pyinstaller==6.22.3 torch==2.1.0+cpu torchvision==0.16.1+cpu torchaudio==2.1.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu
#   旧 venv 已随 D:\UAVDesktopBuild 清理删除，重建环境后用 -PythonExe 传入。
#
# 前置：backend\static\index.html 必须存在（前端构建产物，cd frontend; npm run build）。
param(
  [string]$PythonExe = "D:\UAVDesktopBuild\venv\Scripts\python.exe",
  [string]$DistPath = "",
  [string]$WorkPath = ""
)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
if ($DistPath -eq "") { $DistPath = Join-Path $PSScriptRoot "backend-dist" }
if ($WorkPath -eq "") { $WorkPath = Join-Path $PSScriptRoot "backend-build" }

if (-not (Test-Path (Join-Path $RepoRoot "backend\static\index.html"))) {
  throw "缺少 backend\static\index.html，请先构建前端：cd frontend; npm run build"
}
if (-not (Test-Path $PythonExe)) {
  throw "PythonExe 不存在：$PythonExe（按脚本头部注释重建构建环境后用 -PythonExe 传入）"
}

Push-Location $RepoRoot
try {
  & $PythonExe -m PyInstaller (Join-Path $PSScriptRoot "desktop_backend.spec") --distpath $DistPath --workpath $WorkPath --noconfirm
  if ($LASTEXITCODE -ne 0) { throw "PyInstaller 失败，退出码 $LASTEXITCODE" }
} finally {
  Pop-Location
}

$exe = Join-Path $DistPath "TianJianZhiKanBackend\TianJianZhiKanBackend.exe"
if (-not (Test-Path $exe)) { throw "产物缺失：$exe" }
$files = Get-ChildItem (Join-Path $DistPath "TianJianZhiKanBackend") -Recurse -File
$size = ($files | Measure-Object -Property Length -Sum).Sum
"OK: $exe"
"Files: $($files.Count), Size: {0:N1} MB" -f ($size / 1MB)