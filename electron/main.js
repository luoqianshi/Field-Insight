// Electron 主进程（可行性验证用）
// 职责：单实例 → 拉起纯后端 → 解析端口 → 载入本地页面 → 退出时回收子进程树
const { app, BrowserWindow, dialog, nativeImage, Menu, ipcMain, screen } = require('electron');
const { spawn, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const http = require('http');

// 去掉 Electron 默认的 File/Edit/View/Window/Help 菜单栏（Windows/Linux 整行隐藏）
Menu.setApplicationMenu(null);

const T0 = Date.now();
const isSmoke = process.argv.includes('--smoke');

// Windows 上 GUI 子系统的进程不会把 console 输出接到父控制台，这里提供可选的文件日志
const LOG_FILE = process.env.TJZK_LOG || null;
function dbg(msg) {
  if (!LOG_FILE) return;
  try {
    fs.appendFileSync(LOG_FILE, `[${new Date().toISOString()}] ${msg}\n`);
  } catch (_) {}
}
dbg('boot pid=' + process.pid + ' smoke=' + isSmoke + ' packaged=' + app.isPackaged + ' resources=' + process.resourcesPath);
process.on('uncaughtException', (e) => dbg('uncaught ' + (e && e.stack)));
process.on('unhandledRejection', (e) => dbg('unhandled ' + e));

let backendProc = null;
let backendPort = null;
let win = null;
let quitting = false;
let restarting = false; // 存储迁移后主动重启后端期间，抑制「意外退出」报错
const timings = {};

if (!app.requestSingleInstanceLock()) {
  dbg('single-instance-lock=false → quit');
  app.quit();
} else {
  dbg('single-instance-lock=true');
}

function backendExe() {
  // 打包态：resources\backend\...；开发态：electron\backend-dist\...
  const candidates = [
    path.join(process.resourcesPath || '', 'backend', 'TianJianZhiKanBackend.exe'),
    path.join(__dirname, 'backend-dist', 'TianJianZhiKanBackend', 'TianJianZhiKanBackend.exe'),
  ];
  return candidates.find((p) => fs.existsSync(p)) || candidates[0];
}

function startBackend() {
  return new Promise((resolve, reject) => {
    const exe = backendExe();
    if (!fs.existsSync(exe)) {
      reject(new Error('找不到后端可执行文件：' + exe));
      return;
    }
    backendProc = spawn(exe, ['--port', '0'], {
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
      // 冻结态后端读不到 electron/package.json，由壳把版本号透传给「设置 → 关于」
      env: { ...process.env, TJZK_APP_VERSION: app.getVersion() },
    });
    dbg('backend spawn pid=' + backendProc.pid + ' exe=' + exe);
    timings.backend_spawn_ms = Date.now() - T0;

    let buf = '';
    let settled = false;
    const finish = (err, port) => {
      if (settled) return;
      settled = true;
      err ? reject(err) : resolve(port);
    };

    backendProc.stdout.on('data', (d) => {
      buf += d.toString();
      let idx;
      while ((idx = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, idx).trim();
        buf = buf.slice(idx + 1);
        if (line.startsWith('BACKEND_PORT ')) {
          backendPort = parseInt(line.split(' ')[1], 10);
        } else if (line === 'BACKEND_READY') {
          timings.backend_ready_ms = Date.now() - T0;
          dbg('backend ready port=' + backendPort + ' in ' + timings.backend_ready_ms + 'ms');
          finish(null, backendPort);
        }
      }
    });
    backendProc.stderr.on('data', (d) => process.stderr.write('[backend] ' + d.toString()));
    backendProc.on('error', (err) => finish(err));
    backendProc.on('exit', (code, sig) => {
      timings.backend_exit = { code, sig };
      if (!quitting && !restarting) {
        finish(new Error(`后端进程意外退出（code=${code}, signal=${sig}）`));
        if (win) {
          dialog.showErrorBox('后端已停止', '内置服务异常退出，请重启应用。\n退出码：' + code);
        }
      }
    });
    setTimeout(() => finish(new Error('后端 60 秒内未就绪')), 60000);
  });
}

function killBackendTree() {
  if (!backendProc) return;
  try {
    backendProc.stdin.end(); // 触发后端的 stdin 看门狗
  } catch (_) {}
  const pid = backendProc.pid;
  // 兜底：Windows 上按进程树强杀（后端可能已派生 worker）
  spawnSync('taskkill', ['/PID', String(pid), '/T', '/F'], { windowsHide: true });
  backendProc = null;
}

function httpJson(port, method, urlPath, body, headers) {
  return new Promise((resolve, reject) => {
    const req = http.request(
      { host: '127.0.0.1', port, method, path: urlPath, headers: headers || {}, timeout: 300000 },
      (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => {
          if (res.statusCode !== 200) return reject(new Error('HTTP ' + res.statusCode + ': ' + data.slice(0, 200)));
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            reject(e);
          }
        });
      }
    );
    req.on('error', reject);
    req.on('timeout', () => req.destroy(new Error('请求超时')));
    if (body) req.write(body);
    req.end();
  });
}

function makeJpeg() {
  // 用 Electron nativeImage 生成 480x640 纯色图，不依赖外部图片文件
  const w = 480, h = 640;
  const buf = Buffer.alloc(w * h * 4);
  for (let i = 0; i < w * h; i++) {
    buf[i * 4] = 40;      // B
    buf[i * 4 + 1] = 120; // G
    buf[i * 4 + 2] = 60;  // R
    buf[i * 4 + 3] = 255; // A
  }
  return nativeImage.createFromBitmap(buf, { width: w, height: h }).toJPEG(90);
}

function multipart(jpeg) {
  const boundary = '----ElectronSmoke' + Date.now();
  const head = Buffer.from(
    `--${boundary}\r\nContent-Disposition: form-data; name="image"; filename="smoke.jpg"\r\n` +
      `Content-Type: image/jpeg\r\n\r\n`
  );
  const tail = Buffer.from(`\r\n--${boundary}--\r\n`);
  return { boundary, body: Buffer.concat([head, jpeg, tail]) };
}

function procWorkingSetMb(pid) {
  try {
    const r = spawnSync(
      'powershell',
      ['-NoProfile', '-Command', `[math]::Round((Get-Process -Id ${pid} -ErrorAction SilentlyContinue).WorkingSet64/1MB)`],
      { encoding: 'utf8', windowsHide: true }
    );
    const v = parseInt((r.stdout || '').trim(), 10);
    return Number.isFinite(v) ? v : null;
  } catch (_) {
    return null;
  }
}

async function runSmoke(port) {
  const result = { timings, pid: process.pid, backendPid: backendProc ? backendProc.pid : null };
  try {
    const health = await httpJson(port, 'GET', '/api/health');
    result.health = health.data;
  } catch (e) {
    result.health_error = String(e.message || e);
  }
  try {
    const models = await httpJson(port, 'GET', '/api/models');
    result.models = { count: (models.data.models || []).length, current: models.data.current_model };
  } catch (e) {
    result.models_error = String(e.message || e);
  }
  const m = multipart(makeJpeg());
  const t = Date.now();
  try {
    const r = await httpJson(
      port,
      'POST',
      '/api/detect',
      m.body,
      { 'Content-Type': 'multipart/form-data; boundary=' + m.boundary, 'Content-Length': m.body.length }
    );
    result.infer = {
      ms: Date.now() - t,
      success: r.success,
      detection_count: (r.data || {}).detection_count,
      model: ((r.data || {}).model_info || {}).name,
    };
  } catch (e) {
    result.infer = { ms: Date.now() - t, error: String(e.message || e) };
  }
  result.memory = app.getAppMetrics().map((p) => ({
    type: p.type,
    pid: p.pid,
    working_set_mb: Math.round((p.memory.workingSetSize || 0) / 1024),
  }));
  result.electron_total_mb = result.memory.reduce((s, p) => s + p.working_set_mb, 0);
  result.backend_memory_mb = procWorkingSetMb(backendProc.pid);
  result.window_visible_ms = timings.window_visible_ms;
  const out = process.env.TJZK_SMOKE_OUT || path.join(os.tmpdir(), 'tjzk-electron-smoke.json');
  fs.writeFileSync(out, JSON.stringify(result, null, 2), 'utf-8');
  console.log('SMOKE_JSON ' + JSON.stringify(result));
  console.log('SMOKE_OUT ' + out);
  dbg('smoke done → ' + out);
  quitting = true;
  killBackendTree();
  setTimeout(() => app.quit(), 300);
}

// 原生文件夹选择对话框：冻结载荷排除 tkinter，桌面态目录选择走 OS 对话框（Web 态仍走后端通道）
ipcMain.handle('tjzk:pick-folder', async () => {
  const options = { title: '选择文件夹', properties: ['openDirectory'] };
  const result = win ? await dialog.showOpenDialog(win, options) : await dialog.showOpenDialog(options);
  const picked = result.filePaths && result.filePaths[0];
  return { cancelled: result.canceled, path: picked ? picked.replace(/\\/g, '/') : null };
});

// 存储迁移完成后重启后端：杀旧进程树 → 重新拉起 → 按新端口重载原路由
ipcMain.handle('tjzk:restart-backend', async () => {
  if (restarting) return { success: false, message: '正在重启中' };
  restarting = true;
  dbg('restart-backend requested');
  try {
    let oldPath = '/';
    try {
      const u = new URL(win.webContents.getURL());
      oldPath = u.pathname + u.search + u.hash;
    } catch (_) {}
    killBackendTree();
    const port = await startBackend();
    if (win) await win.loadURL(`http://127.0.0.1:${port}${oldPath}`);
    dbg('restart-backend done port=' + port + ' path=' + oldPath);
    return { success: true };
  } catch (e) {
    dbg('restart-backend failed: ' + (e && e.stack ? e.stack : e));
    dialog.showErrorBox('服务重启失败', '数据位置已切换，但服务重启失败，请重启应用。\n' + String(e && e.message ? e.message : e));
    return { success: false, message: String(e && e.message ? e.message : e) };
  } finally {
    restarting = false;
  }
});

app.on('second-instance', () => {
  if (win) {
    if (win.isMinimized()) win.restore();
    win.focus();
  }
});

app.whenReady().then(async () => {
  dbg('whenReady at ' + (Date.now() - T0) + 'ms');
  try {
    const port = await startBackend();
    timings.window_created_ms = Date.now() - T0;
    // 按主显示器工作区自适应：1920×1080 → 1440×900；1366×768 笔记本 → 约 1286×648，避免窗口超出屏幕
    const area = screen.getPrimaryDisplay().workAreaSize;
    const width = Math.max(1024, Math.min(1440, area.width - 80));
    const height = Math.max(620, Math.min(900, area.height - 80));
    // 最小尺寸按规范 1100×760，但小屏笔记本放不下时回退到初始尺寸，避免窗口超出工作区
    const minWidth = Math.min(1100, width);
    const minHeight = Math.min(760, height);
    win = new BrowserWindow({
      width,
      height,
      minWidth,
      minHeight,
      center: true,
      show: false,
      title: '田间智瞰',
      backgroundColor: '#F9FAFB',
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });
    // 无菜单栏形态下补全 F11 全屏切换（Windows 习惯键位）
    win.webContents.on('before-input-event', (event, input) => {
      if (input.type === 'keyDown' && input.key === 'F11') {
        win.setFullScreen(!win.isFullScreen());
        event.preventDefault();
      }
    });
    win.once('ready-to-show', () => {
      win.show();
      timings.window_visible_ms = Date.now() - T0;
      dbg('window visible at ' + timings.window_visible_ms + 'ms');
    });
    win.webContents.on('did-finish-load', () => {
      timings.page_loaded_ms = Date.now() - T0;
      dbg('page loaded at ' + timings.page_loaded_ms + 'ms url=' + win.webContents.getURL());
    });
    win.webContents.on('did-fail-load', (_e, code, desc, url) => dbg('did-fail-load ' + code + ' ' + desc + ' ' + url));
    win.webContents.on('render-process-gone', (_e, d) => dbg('renderer-gone ' + JSON.stringify(d)));
    win.on('closed', () => {
      win = null;
      if (!isSmoke) app.quit();
    });
    await win.loadURL(`http://127.0.0.1:${port}`);
    if (isSmoke) {
      await new Promise((r) => setTimeout(r, 600));
      await runSmoke(port);
    }
  } catch (e) {
    dbg('startup failed: ' + (e && e.stack ? e.stack : e));
    dialog.showErrorBox('启动失败', String(e && e.message ? e.message : e));
    quitting = true;
    killBackendTree();
    app.quit();
  }
});

app.on('before-quit', () => {
  quitting = true;
  killBackendTree();
});

app.on('window-all-closed', () => {
  app.quit();
});
