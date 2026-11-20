# AGENTS.md

面向 AI 编码代理的项目指引。在本仓库内执行任何开发、测试、提交任务前，先通读本文件。

## 项目概览

- **田间智瞰**：基于无人机（UAV）图像的大田农作物智能监测系统，覆盖 数据管理 → 数据处理 → 数据集管理 → 算法广场 四模块。
- **后端**：Flask（Python，推荐 conda 环境 `uav-vis`），入口 `backend/app.py`，端口 5000，同时托管 API 与前端静态资源。
- **前端**：Vue 3 + Vite + Tailwind + Pinia，源码在 `frontend/`，构建产物输出到 `backend/static/`（该目录不入库，由构建生成）。
- 详细架构见 [README.md](README.md) 与 `docs/sdd/`。

## 目录规范（Web 全栈 + 桌面双端）

### 目录地图

| 目录 | 用途 | Git |
|---|---|---|
| `backend/` | Flask 后端，Web/桌面共享（FROZEN 门控双根配置） | 跟踪 |
| `frontend/` | Vue 3 前端，Web/桌面共享；构建产物 → `backend/static/` | 跟踪 |
| `electron/` | 桌面壳唯一方案（main/preload/载荷 spec/构建脚本）；产物目录 gitignore | 源码应跟踪 |
| `config/` `models/` `data/` `output/` `datasets/` `results/` | 运行目录，由 `backend/config.py` 锚定仓库根，**禁止移动/改名** | config 跟踪，其余忽略 |
| `docs/sdd/{specs,plans,prd}` | 正式 SDD 文档唯一跟踪目录 | 跟踪 |
| `reports/` | 轻量交付物（HTML 报告/截图/架构图 PPTX+PNG） | 跟踪 |
| `paper_chapter/` `remotion/` | 论文/视频大文件工作区 | 忽略 |
| `.lqs/` | 私有工作区：PRD 草稿/原型/图标设计/bug 与更新报告/AI 分析归档 | 忽略 |
| `.trae/` `.codex/` `.qoder/` `.workbuddy/` | AI 工具自有 scratch 目录，内部不手动迁移 | 忽略（`.trae/skills/` 除外） |
| 根文件 | README / AGENTS / LOG / start.ps1 / requirements*.txt | 跟踪 |

### 新文件落位规则

1. **正式 SDD**（spec/plan/PRD 定稿）→ `docs/sdd/{specs,plans,prd}/`，命名 `YYYY-MM-DD-<topic>.md`；草稿与过程版 → `.lqs/{prd,specs,plans}/`。
2. **AI 分析/验证/调研产出** → `.lqs/<YYYY-MM-DD>/<topic>/outputs/`；**禁止在仓库根创建日期目录或散放分析文件**。工具自有目录（如 `.trae/documents/`）遵循工具默认路径，不手动迁移其内部。
3. **Bug/更新报告** → `.lqs/bug_report/`、`.lqs/update_report/`（skill 默认路径，命名见各 SKILL.md）。
4. **报告交付物** → `reports/`（轻量 HTML/PNG/PPTX 可跟踪）；大媒体（视频/论文图批）→ `remotion/`、`paper_chapter/`（忽略）。
5. **静态资源**：Web 运行图标 → `frontend/public/`；内联图标 → `Icon.vue`；设计源稿 → `.lqs/icon_design/`；桌面图标 → `electron/build/`。**禁止在 `frontend/assets/` 或仓库根放非运行时资源。**
6. **测试图片/fixture** → `backend/tests/` 或 `.lqs/imgs/`，禁止仓库根。
7. **构建中间产物** → 各子项目内已忽略目录（如 `electron/backend-dist/`）或项目外 build 目录，禁止污染仓库根。

### Git 卫生

- `.gitignore` 运行目录必须根锚定（`/data/` 而非 `data/`），防止误忽略 `frontend/src/views/data/` 等同名子目录（R-FS-02）。
- 禁止跟踪：运行日志、分享 zip、大图片/gif、模型权重、运行数据、私有草稿（根 `LOG.md` 为改动日志文档，属跟踪例外，见「改动日志」章节）。
- 提交前 `git status --porcelain` 冻结范围、精确 add（见下方 Git 工作流）。

## 常用命令（Windows / PowerShell）

```powershell
# 一键启动（检查环境 + 按需构建前端 + 启动 :5000）
.\start.ps1

# 后端开发
conda activate uav-vis
python -m backend.app                 # Flask http://localhost:5000

# 前端开发（热更新 http://localhost:3000，/api 代理到 :5000）
cd frontend
npm install
npm run dev

# 前端构建（改动后需重新 build，产物 -> backend/static/）
cd frontend
npm run build

# 后端测试（在 backend/ 目录下执行）
cd backend
python -m pytest -v

# 桌面端（Electron，细则见「桌面端研发细则」章节）
cd frontend; npm run build                # 载荷前置：backend/static/index.html
powershell -NoProfile -ExecutionPolicy Bypass -File electron\build-backend.ps1 -PythonExe <构建环境 python.exe>
cd electron; npm install; npm start       # 开发运行（加载 backend-dist 载荷）
npm run smoke                             # 冒烟测试
npm run build:dir                         # → dist/win-unpacked 便携目录
```

## 代码约定

- 后端 API 统一响应信封：`{"success": bool, "data": <data>|null, "message": str}`。
- 注册中心类（模型/架次/处理任务）使用 YAML 持久化，单图处理失败只做错误隔离记录，不得因单张失败中断整批。
- 前端使用浅色主题，主色 Emerald `#10B981`，Gradio 风格极简布局；禁止玻璃拟态、霓虹光效、脉冲动画；图标用 SVG（stroke-width=1.5），不用 emoji。
- 不修改 `backend/api/` 既有路由文件的签名；新增接口优先新增文件或扩展 Blueprint。
- 提交信息遵循 Conventional Commits：`feat|fix|docs|style|refactor|perf|test|build|ci|chore(scope): 描述`，描述可用中文，使用现在时祈使语气。

## 改动日志（LOG.md，强制）

根 `LOG.md` 是仓库级 AI 操作改动日志，用于快速 Review「之前做过哪些改动」。

- **触发**：任何 AI 工具（TRAE/Codex/Qoder/WorkBuddy 等）在本仓库产生文件改动（代码/配置/文档/构建脚本）的任务，完成后必须向 `LOG.md` 追加一行日志。纯只读问答、调研、规划且未落盘任何文件改动的会话不记录。
- **格式**：`- [YYYY-MM-DD HH:mm] type(scope): 一句话摘要`。时间为任务完成时的本地时间（Asia/Shanghai）；type 遵循 Conventional Commits；摘要 ≤50 字，说清「改了什么」，可附关键文件/模块名。
- **粒度**：每个用户任务一条；同一任务内多次编辑、多个提交合并为一条，不按文件逐条记录。
- **写入**：追加到文件末尾（时间正序）；历史条目不改不删，纠错以新条目说明。
- **Git**：`LOG.md` 纳入版本控制（属改动文档而非运行日志），与该任务改动一并提交。
- **与其他记录的关系**：commit message 是提交级明细，`.lqs/update_report/` 是详细归档，LOG.md 是任务级一行索引，三者互补不互替。

## 桌面端研发细则（Electron）

桌面端唯一方案为 Electron（2026-11-19 定案，PyWebView 过渡方案废弃）。Web/桌面共享 `backend/` 与 `frontend/`，以 FROZEN 门控区分形态；修改共享代码时必须同时考虑两态行为。

### 结构与进程编排契约
- 壳源码：`electron/main.js`（编排/冒烟/`tjzk:pick-folder` 原生目录选择 IPC）、`preload.js`（只读 `window.tjzk` 环境信息 + `pickFolder` 桥）、`desktop_backend.py`（纯后端入口）、`desktop_backend.spec`（PyInstaller onedir 载荷）、`build-backend.ps1`（载荷重建）、`build/app.ico`（桌面图标）。
- 编排链（修改 main.js / desktop_backend.py 时必须同步维护）：单实例锁 → spawn 后端 exe `--port 0` → 解析 stdout 协议 `BACKEND_PORT <port>` / `BACKEND_READY` → 载入 `http://127.0.0.1:<port>`；60 秒就绪超时。
- 退出回收：stdin 看门狗（父进程死亡后端自动退出）+ `taskkill /PID <pid> /T /F` 兜底，杜绝孤儿进程。
- 窗口：1440×900（min 1100×760），标题「田间智瞰」；`Menu.setApplicationMenu(null)` 隐藏默认菜单栏；contextIsolation=true、nodeIntegration=false。
- 后端 exe 查找：打包态 `resources/backend/TianJianZhiKanBackend.exe`，开发态 `electron/backend-dist/TianJianZhiKanBackend/`。

### FROZEN 双根配置（backend/config.py）
- `FROZEN = sys.frozen`；RESOURCE_ROOT（只读：backend/static、config 模板、内置权重，PyInstaller `_MEIPASS`）与 PROJECT_ROOT（可写数据根）分离。
- 冻结态可写数据根固定 `%LOCALAPPDATA%\TianJianZhiKan\`（config/models/data/output/datasets/results/logs），与安装位置解耦；**严禁删除该目录**，卸载不删历史数据。
- 非冻结态必须与 Web 开发行为完全一致（锚定仓库根）；新增运行目录一律走 config.py 常量，禁止硬编码路径。
- 冻结态 HOST=127.0.0.1、DEBUG=False；首启把内置 `models.yaml` 播种到用户目录（仅缺失时）。
- `desktop_backend.py` 的 `_MEIPASS`/`sys.frozen` 兼容垫片（部分 onedir 产物属性缺失）不得删除。

### 构建链与环境
- 顺序：`cd frontend; npm run build`（`backend/static/index.html` 必须存在）→ `electron\build-backend.ps1 -PythonExe <构建环境 python.exe>` → `cd electron; npm install; npm start`（开发）/ `npm run build:dir`（便携目录）。
- 构建环境：Python 3.8.20（conda uav-vis）+ `venv --system-site-packages` + pyinstaller==6.22.3 + torch==2.1.0+cpu / torchvision==0.16.1+cpu / torchaudio==2.1.0+cpu；脚本默认 PythonExe 指向已删除的旧 venv，必须显式传入。
- 发行必须 CPU 版 torch（CUDA 版约 4.2GB 不可分发，CPU 版载荷约 900MB）。
- spec 要点：SPECPATH 锚定仓库根（与 cwd 无关）；`pathex` 必须含 `backend/`（裸导入依赖 sys.path 补丁，静态分析识别不到）；datas 收集 backend/static、config、models；excludes 排除 webview/tkinter 等 GUI 模块（Electron 版故意排除，目录选择不依赖 tkinter）。
- 模型权重加载保持两级回退（打包资源目录 → 开发相对路径），不得改成单一路径。

### 验证
- `npm run smoke`：自动 health/models/单图推理 + 耗时/内存报告（`TJZK_SMOKE_OUT` 指定输出路径，默认 `%TEMP%\tjzk-electron-smoke.json`；`TJZK_LOG` 开启主进程文件日志）。
- 后端改动仍须 `cd backend; python -m pytest -v`；前端改动后必须重新 build 再重建载荷。

### 发布约定
- 版本单一来源：`electron/package.json` 的 `version`；git tag `vX.Y.Z`（注解 tag）与之对齐。
- 仅发布 Windows 压缩包 `TianJianZhiKan-v{version}-win-x64.zip`；`dist/win-unpacked` 是免安装原材料，整目录压缩，不逐个挑 exe。
- `publish: null` 手动发布、无自动更新；zip target/artifactName 配置已规划未实施（见 `.lqs/update_report/012`）；NSIS 配置（向导式/自定义目录/当前用户）存在但非当前发布形态。
- 未代码签名：SmartScreen「未知发布者」属预期，Release notes 须写明「更多信息 → 仍要运行」。
- 流程：冻结验证（pytest/build/smoke）→ 版本提交 → 重建产物链 → 干净目录解压验证 + SHA256 → 注解 tag → 按 Git 工作流走代理推送 → `gh release create` 上传 zip + sha256。

### 环境与操作禁忌
- D:\ 根目录有写保护：构建/安装输出放用户目录、`%TEMP%` 或项目外 build 目录；中间产物不得污染仓库根。
- 清理操作不得强杀开发环境进程；被占用文件报告并跳过；不得用吞错误的执行方式；删除走回收站（Remove-Item 受限时用 Microsoft.VisualBasic FileIO SendToRecycleBin），并逐个核实路径真实删除。
- electron-builder rcedit 写图标会撞 Windows Defender 实时扫描文件锁，需延时重试（约 8 秒/次、最多 15 次）；exe 图标显示异常先刷新图标缓存（`ie4uinit.exe -show`）。
- `electron/` 产物（node_modules/dist/backend-dist/backend-build/.cache/*.log）全部 gitignore，不得跟踪。

## Git 工作流（强制：默认走本地系统代理）

远端为 GitHub HTTPS（`https://github.com/luoqianshi/...`），国内网络直连不稳定。**所有需要联网的 Git 命令（`fetch` / `pull` / `push` / `clone` / `ls-remote`）默认必须走本地系统代理**；`add` / `commit` / `log` / `diff` 等纯本地命令不需要代理。

1. **先获取当前系统代理地址**（不要凭记忆硬编码端口，代理端口可能变化；当前参考值 `127.0.0.1:7892`）：

   ```powershell
   $p = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
   if ($p.ProxyEnable -eq 1) { "http://$($p.ProxyServer)" } else { "系统代理未开启" }
   ```

2. **推送前先探测代理端口连通性**，代理未开启时提示用户启动 VPN/代理客户端，不要盲目直连或反复重试：

   ```powershell
   Test-NetConnection -ComputerName 127.0.0.1 -Port 7892 -InformationLevel Quiet
   ```

3. **优先使用单次生效的 `-c` 代理参数**（不写入全局 git config，避免污染其他仓库、代理关闭后配置失效）：

   ```powershell
   git -c http.proxy=http://127.0.0.1:7892 -c https.proxy=http://127.0.0.1:7892 fetch origin
   git -c http.proxy=http://127.0.0.1:7892 -c https.proxy=http://127.0.0.1:7892 push origin master
   ```

   同一会话需要多次联网操作时，可改用会话级环境变量（同样不持久化）：

   ```powershell
   $env:HTTP_PROXY  = "http://127.0.0.1:7892"
   $env:HTTPS_PROXY = "http://127.0.0.1:7892"
   ```

4. **提交前**用 `git status --porcelain` 与 `git diff --stat` 冻结提交范围，精确 `git add` 相关文件，禁止 `git add -A` 裹挟无关改动；禁止提交密钥、`.env`、大体积数据与模型权重。
5. 未经用户明确要求，禁止 `push --force`、修改 git 全局配置、跳过 hooks（`--no-verify`）；推送失败时在同一轮会话内闭环解决，不把 push 步骤甩给用户手动执行。
