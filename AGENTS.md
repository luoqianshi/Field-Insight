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
| `docs/` | 文档中心：`sdd/{specs,plans}` 正式 SDD、`prd/` 需求基线、`bug_report/`、`update_report/` 报告归档、`qna_record/` 分析记录 | 跟踪 |
| `reports/` | 轻量交付物（HTML 报告/截图/架构图 PPTX+PNG） | 跟踪 |
| `paper_chapter/` `remotion/` | 论文/视频大文件工作区 | 忽略 |
| `.lqs/` | 私有工作区：PRD 草稿/原型/图标设计/AI 分析归档 | 忽略 |
| `.trae/` `.codex/` `.qoder/` `.workbuddy/` | AI 工具自有 scratch 目录，内部不手动迁移 | 忽略（`.trae/skills/` 除外） |
| 根文件 | README / AGENTS / LOG / start.ps1 / requirements*.txt | 跟踪 |

### 新文件落位规则

1. **正式 SDD 文档**（spec/plan 定稿）→ `docs/sdd/{specs,plans}/`，命名 `YYYY-MM-DD-<topic>.md`；PRD 基线 → `docs/prd/`；草稿与过程版 → `.lqs/{prd,specs,plans}/`。
2. **AI 分析/验证/调研产出** → `.lqs/<YYYY-MM-DD>/<topic>/outputs/`；**禁止在仓库根创建日期目录或散放分析文件**。工具自有目录（如 `.trae/documents/`）遵循工具默认路径，不手动迁移其内部。
3. **Bug/更新报告** → `docs/bug_report/`、`docs/update_report/`（skill 默认路径，命名见各 SKILL.md）；**分析/问答记录** → `docs/qna_record/`。
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
npm run build:installer                   # → dist/TianJianZhiKan-v{version}-win-x64-setup.exe 安装包
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
- **与其他记录的关系**：commit message 是提交级明细，`docs/update_report/` 是详细归档，LOG.md 是任务级一行索引，三者互补不互替。

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
- 顺序：`cd frontend; npm run build`（`backend/static/index.html` 必须存在）→ `electron\build-backend.ps1 -PythonExe <构建环境 python.exe>` → `cd electron; npm install; npm start`（开发）/ `npm run build:dir`（便携目录）/ `npm run build:installer`（NSIS 安装包）。
- 构建环境：Python 3.8.20（conda uav-vis）+ `venv --system-site-packages` + pyinstaller==6.22.3 + torch==2.1.0+cpu / torchvision==0.16.1+cpu / torchaudio==2.1.0+cpu；脚本默认 PythonExe 指向已删除的旧 venv，必须显式传入。
- 发行必须 CPU 版 torch（CUDA 版约 4.2GB 不可分发，CPU 版载荷约 900MB）。
- spec 要点：SPECPATH 锚定仓库根（与 cwd 无关）；`pathex` 必须含 `backend/`（裸导入依赖 sys.path 补丁，静态分析识别不到）；datas 收集 backend/static、config、models；excludes 排除 webview/tkinter 等 GUI 模块（Electron 版故意排除，目录选择不依赖 tkinter）。
- 模型权重加载保持两级回退（打包资源目录 → 开发相对路径），不得改成单一路径。

### 验证
- `npm run smoke`：自动 health/models/单图推理 + 耗时/内存报告（`TJZK_SMOKE_OUT` 指定输出路径，默认 `%TEMP%\tjzk-electron-smoke.json`；`TJZK_LOG` 开启主进程文件日志）。
- 后端改动仍须 `cd backend; python -m pytest -v`；前端改动后必须重新 build 再重建载荷。

### 发布约定
- 版本单一来源：`electron/package.json` 的 `version`；git tag `vX.Y.Z`（注解 tag）与之对齐。
- 发布三件套：便携 zip `TianJianZhiKan-v{version}-win-x64.zip`（`dist/win-unpacked` 是免安装原材料，整目录压缩，不逐个挑 exe）、NSIS 安装包 `TianJianZhiKan-v{version}-win-x64-setup.exe`、`SHA256SUMS.txt` 校验清单；Release notes 原文归档 `docs/releases/v{version}.md`，`gh release create --notes-file` 引用。
- `publish: null` 手动发布、无自动更新；zip target/artifactName 配置已规划未实施（见 `docs/update_report/012`）；NSIS 安装包（向导式/自定义目录/当前用户/桌面与开始菜单快捷方式）自 v1.1.0 起可用 `npm run build:installer` 产出，验证与构建说明见 [docs/desktop-build-guide.md](docs/desktop-build-guide.md)。
- 未代码签名：SmartScreen「未知发布者」属预期，Release notes 须写明「更多信息 → 仍要运行」。
- 流程：冻结验证（pytest/build/smoke）→ 版本提交 → 重建产物链 → 干净目录解压验证 + SHA256 → 注解 tag → 按 Git 工作流走代理推送 → `gh release create` 上传 zip + 安装包 + SHA256SUMS → 回写 VERSIONS.md 发布状态与 LOG.md。

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

<!-- aoci:begin -->
## AOCI 仓库认知

AOCI 为本仓库维护一个稳定、可版本化、可增量更新的仓库级认知层，供模型跨任务复用对系统的理解。

`aoci.txt` 是面向模型的结构化认知索引。它以每个受管理文件、数据库表或其他受管理对象一条独立 Entry 的方式，用符号标签与 F/R/A/S 语义表达对象的核心职责、重要关系、对外契约，以及理解或修改系统时必须知道的非显然约束和设计决策。

Header、目录段和全部 Entry 共同组成完整仓库索引，可以覆盖前端、后端、配置、数据库结构及其他受管理内容。受管理内容发生变化时，通常只需维护受影响的认知条目，不需要重新生成整个索引。

AOCI 提供系统架构、对象职责、重要关系、对外契约和关键约束的高密度视图。

### 工作原理

AOCI 采用“模型生成、模型读取”的认知闭环。

Header、Entry 和 Curation 语义的创作只按当前机器签发的 Plan 与实时 Guide 执行；由 Host 模型基于当前绑定证据独立完成。

Entry 的语义必须来自模型对真实证据的理解。不得仅依据路径、文件名、扩展名、AST、符号列表、依赖扫描、正则、固定模板或规则引擎推导、预填、拼接或改写索引语义。

对 Fresh Bootstrap，只按当前机器签发的 Plan 和实时 Guide 执行。当它们要求创作时，Host 模型创作 Root、Meta、Tag 和 F/R/A/S，提供 authoring-run 声明，并把它绑定到 Plan、Evidence 与完整 Candidate。不得要求 AOCI 填写 `origin=host_model`、制造 Receipt 或把程序生成的 Framework 当作语义。本文件不自行重建 Onboarding 流程。内部批次不是用户决策；只有遇到既有批准边界或真实的安全、漂移、CAS、Recovery 条件才停止。

### 最小使用入口

- `aoci_rules`：取得当前AOCI版本的会话运行合同。
- `aoci_overview`：建立或恢复本仓库的完整认知。
- `aoci_maintain`：受管理对象达到最终稳定状态后检查认知是否需要维护。
- `aoci_update_entry`：提交与当前证据和源码摘要绑定的完整语义更新批次。
- `aoci_report`：仅当当前布局和工具状态支持时，在证据不足、无法可靠生成语义时登记待办，不猜写。

其他MCP工具、CLI命令、参数和专项流程，以当前工具说明、Guide和 `--help` 返回内容为准，不在本文件中重复完整手册。

本区块只规定仓库接入、认知使用和收尾原则。`aoci_rules` 承载当前会话合同，Guide实时输出承载当前Plan的执行顺序与停点，工具Schema、Spec和Validator承载机器结构与判据；Prompt、Description、README和静态文档不能覆盖这些机器事实。

### 建立、生成和恢复认知

1. 每个新的 Agent Run 开始时，应先判断：

   - 本仓库是否已经存在可用的完整AOCI索引；
   - 当前上下文中是否已有与本仓库根、当前索引版本和当前AOCI服务相匹配，并且模型仍可可靠使用的完整仓库认知。

2. 仓库已经存在可用的完整索引，但当前Run没有可靠完整认知时，先调用 `aoci_rules`，再调用 `aoci_overview`。

   完整认知仍可靠时直接复用。局部不确定本身不要求机械重读系统全貌。可靠认知建立后，默认以它作为仓库级系统上下文，只读取当前任务直接需要的源码、测试、配置与契约，只有某个缺失的具体事实可能改变回答或验证结论时才扩大证据范围；AOCI不能替代修改对象与验证行为所需的直接源码证据。

   本Run从已知Host上下文压缩恢复时（包括宿主注入的压缩摘要），必须把此前模型认知视为不可靠。压缩handoff不得保留或摘要正式Whole-Index，也不得保留或摘要任何Overview Header、Entry、Chunk、Challenge或Attestation正文；只能保留安全续接所需的receipt身份、未完成write或Recovery状态，以及立即重载指令。复制进handoff的Whole-Index语义或receipt不能证明恢复后模型的当前认知可靠。若当前上下文已无法可靠保留运行合同，先调用 `aoci_rules`。继续业务任务前，使用 `refresh_reasons=["context_compaction"]` 和新的 `refresh_event_id` 调用普通完整Whole-Index `aoci_overview`（不设置 `check_only` 或设为false）；不得使用 `check_only` 或认知probe。原样跟随每个 `next_cursor` 直到 `completed=true`，确认交付，并且只基于新交付正文提交一次Attestation。完成这次新的完整传输后，即使Attestation为partial或fail也消费该generation，并按既有合同继续source-bound任务，不再自动调用第二次Overview。若该请求返回 `delivery_mode=capacity_stop`，说明Whole-Index装不进本Host的上下文：不得重试或调小 `chunk_tokens`；该停止消费本generation，任务按source-bound继续，且不作无保留的完整系统认知声明。

   AOCI可以针对 `context_compaction`、项目 `cognition_refresh_threshold` 下的机器 `semantic_threshold` 或主要 `phase_transition` 提供checkpoint与认知状态事实。只需要这些紧凑事实时使用 `check_only=true`；这些事实只向Agent提供建议，不替模型决定是否需要系统全貌。

   Agent显式调用普通 `aoci_overview`（未设置 `check_only` 或为false）时，只要能形成一致的CognitionSet，AOCI必须完整交付请求scope。不得因为已有receipt、阈值未达到或没有待处理刷新原因而抑制正文；唯一例外是待处理压缩刷新的上述容量停止。正式认知Dirty或Stale时仍交付正文，但必须标记不可靠。存在未决恢复或无法形成一致snapshot时失败关闭，不返回混合正文。

   普通Overview返回 `continuation_required=true` 时，必须原样提交 `next_cursor` 并自动继续到 `completed=true`。不得询问用户、开始业务任务或给出阶段性系统结论。每块单独一次工具调用；不得在一个脚本里连取多块或合并其输出。缺块、重复、乱序、cursor失败、Index变化或`chunk_tokens`变化时停止本次认知链。Attestation完成前不得用Memory、源码、Spec、`aoci.txt`、历史会话、scope、search或Entry读取修补或补充Whole-Index认知。Challenge ordinal是正式Entry序列中的1-based位置；Header内容、注释、空行、Section/Overview/Chunk Marker、Receipt与Metadata均不计数，Chunk Receipt ordinal使用同一序列。Attestation必须原样回绑本次Challenge发布的当前`index_sha256`、`entry_sequence_sha256`与`entry_count`；旧Index、旧Entry序列、旧数量或旧Attestation均无效。完整链结束后只正式提交一次既有模型认知Attestation；同一响应只允许一次不改变语义答案的JSON Schema或字段格式修正。未达通过（全对的序号不足80%，或对象身份错超过一题）即记为不确定回执，不得语义重试或旁路补答。首次认知失败时还不得执行Root/Meta、Migration、全局布局或其他未重新绑定的系统级决策。上下文压缩刷新若传输完整、认知身份不变、治理对齐且没有Recovery或第三方冲突，即使Attestation为partial或fail也消耗该refresh generation，并继续原任务，不再自动重读Overview。`system_mastery_percent`只自评系统框架——架构、职责、强关系、稳定外部契约以及高熵安全和维护约束——不表示完整实现或运行实况知识；机器索引覆盖率必须分开。默认只向用户输出由本次真实覆盖率、Challenge、块数、Token和掌握度生成的规定成功或失败一句话。Host截断某一块时，用同一cursor重取一次并核对 `chunk_sha256`，服务端返回完全相同的字节。仍被截断才停止，提示用户把 `overview_delivery.chunk_tokens` 设置为更小的合法值后重新开始，不得自动修改。

   加法认知等级必须与严格证明字段分开解释。`delivery_verified`表示已加载Index且Host交付已确认，但完整认知验证仍未完成；应表达为“已加载且交付已验证”，不得描述为“没有认知”或“没有理解系统”。`cognition_verified`要求Attestation通过（Challenge至少80%的ordinal完全正确且对象身份至多失手一处），`cognition_governed`还要求治理对齐。通用完整读取失败句只用于真实交付故障。

   当Overview响应包含可选`cognition-state/v2`投影时，必须分别解释各维度。其Level止于`model_cognition_usable`；`strict_attestation_verified`、`governance_aligned`与`current_system_cognition_reliable`都是独立状态，绝不参与该Level。ordinal、对象身份、Tag或核心F不匹配可以导致严格Attestation失败，而模型认知仍然可用；不得仅凭这种不匹配就宣称模型没有理解系统。只有`current_system_cognition_reliable=true`允许无保留地声称当前完整系统认知可靠。投影缺失时继续使用上述Legacy解释。

   普通的只读审计、分析、检查、不修改代码或不提交、不push，不自动等于严格零写入，也不改变上述认知有效性判断。Codex Memory和历史Skill只能辅助恢复经验、用户偏好与调查方向，不能替代与当前仓库根、索引摘要、AOCI服务身份和认知范围匹配的当前认知收据；项目AGENTS和当前AOCI身份在AOCI状态上优先于历史Memory。

   只有用户明确禁止Ledger、元数据、`.aoci`运行资产及任何文件写入时，才按严格零写入处理。若必要的认知建立与该边界冲突，必须报告冲突并请求用户裁决或建议使用隔离副本，不得静默以Memory替代当前仓库认知。

3. 仓库没有可用的完整索引，或当前只有最小骨架、Header不完整、Entries未完成、必要Curation尚未裁决时，如果需要建立正式完整AOCI索引，先取得 `aoci_rules`，然后进入当前AOCI Guide。由Guide依据仓库真实状态决定下一阶段并完成必要安全步骤。

   `aoci_maintain` 不替代索引建立流程。

   不在本文件中自行重建或硬编码完整索引生成状态机。

4. 在长程任务中，模型负责保留当前认知收据并正确使用刷新门禁：

   - Host报告上下文压缩或模型已知系统全貌丢失时，执行上述强制 `context_compaction` 重载规则；AOCI不能自行推断Host事件；
   - 进入真正的主要阶段时声明 `phase_transition`，不得把函数、测试运行或小步骤当作阶段；
   - 在有用的稳定检查点通过 `check_only=true` 取得机器语义计数；
   - 除已知压缩的强制重载外，由Agent判断当前任务是否需要再次显式获取指定scope或完整Overview；
   - 在维护和对齐完成前，保留AOCI报告的Dirty或Stale可靠性状态。

### 任务收尾与认知维护

5. 纯只读问答、分析、版本核验，或没有产生受AOCI管理对象变化的任务，不需要调用维护工具。当前AOCI版本是任意`aoci_overview` check_only或`aoci_maintain`响应里的`cognition_receipt.mcp_service_version`；二进制路径是项目`.mcp.json`里的`command`，CLI不必在PATH上。

6. 发生受AOCI管理对象变化时，待其达到本次任务的最终稳定状态后，只调用一次 `aoci_maintain`。不要在每次中间修改后逐文件维护。

7. 若维护结果返回真实语义候选，Host 模型必须基于每个候选绑定的对象和必要证据，独立创作完整标签与F/R/A/S更新。通过 `aoci_update_entry` 一次提交当前机器签发批次的完整候选集合，同时原样保留每项路径与对应domain批次身份；`source_sha256` 与 `candidate_id` 可以省略，由服务端按签发的批次取得。`max_entries`只限制单次请求和原子事务，不限制logical plan、Whole-Index或Managed Scope。`remaining`非零时，在当前批次成功Apply后重新调用Maintain并从新preimage继续；绝不能为满足transport上限缩减Index覆盖或自行截取返回批次。

   没有足够证据且当前布局支持 `aoci_report` 时，使用它而不猜测、套用模板或为消除待办而生成缺乏证据的认知。

8. 必须遵守工具返回的结构化状态和安全边界：

   - `repair_required`：只修复明确命中的候选，再重新提交当前机器签发的完整批次；
   - `stopped`：结束当前写入尝试并检查 `failed_step`、错误、正式写入证据与Recovery。auto模式下，已证明零写入则记录closure并重新Plan；完整Intent和可证明postimage则Resume；策略要求Rollback且preimage可证明则精确恢复后重新Plan。只有证据不足、第三方正式字节冲突、需要审批或外部动作，或命中其他真实安全边界时，才停止整个用户任务；
   - 冲突、审批、人工裁决、权限和安全信号不得忽略；
   - 已经对齐后不得重复维护或重复写入；`refresh_ready_for_overview` 是checkpoint事实，由Agent决定是否为下一阶段请求普通完整Overview。

   维护完成后如果又修改了任何受管理对象，之前的维护结果失效，应在新的最终稳定状态重新完成收尾。

9. 用户只限制业务文件范围，但没有明确禁止仓库托管资产时，AOCI托管资产可以在收尾阶段为保持认知一致而更新，并应在审计和提交中与业务文件区分。

   用户明确禁止修改 `aoci.txt`、`.aoci`、元数据或任何额外文件时，以用户限制为准，不得写入，并如实报告剩余不一致。

### 专项流程

初始化、完整索引生成、Header生成、Entries生成、数据库结构索引、Curation、人工评审和故障恢复，只按当前AOCI Guide或工具在对应阶段返回的指令、命令和安全停点执行。

不预加载、不猜测，也不自行重建这些专项流程。平台调用方式、请求格式、批次上限、审批规则、索引格式细节和恢复步骤由对应Guide、工具说明、模型Prompt和CLI帮助按需提供。
<!-- aoci:end -->
