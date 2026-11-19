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
| 根文件 | README / AGENTS / DEPLOYMENT / start.ps1 / requirements*.txt | 跟踪 |

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
- 禁止跟踪：日志、分享 zip、大图片/gif、模型权重、运行数据、私有草稿。
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
```

## 代码约定

- 后端 API 统一响应信封：`{"success": bool, "data": <data>|null, "message": str}`。
- 注册中心类（模型/架次/处理任务）使用 YAML 持久化，单图处理失败只做错误隔离记录，不得因单张失败中断整批。
- 前端使用浅色主题，主色 Emerald `#10B981`，Gradio 风格极简布局；禁止玻璃拟态、霓虹光效、脉冲动画；图标用 SVG（stroke-width=1.5），不用 emoji。
- 不修改 `backend/api/` 既有路由文件的签名；新增接口优先新增文件或扩展 Blueprint。
- 提交信息遵循 Conventional Commits：`feat|fix|docs|style|refactor|perf|test|build|ci|chore(scope): 描述`，描述可用中文，使用现在时祈使语气。

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
