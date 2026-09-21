const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const isWin = process.platform === 'win32';
const npmCmd = isWin ? 'npm.cmd' : 'npm';

function getPythonCmd() {
  const candidates = isWin
    ? [
        path.join(__dirname, 'backend', 'venv', 'Scripts', 'python.exe'),
        path.join(__dirname, 'venv', 'Scripts', 'python.exe'),
        'python',
      ]
    : [
        path.join(__dirname, 'backend', 'venv', 'bin', 'python'),
        path.join(__dirname, 'venv', 'bin', 'python'),
        'python3',
      ];

  const hasUvicorn = (pyPath) => {
    try {
      execSync(`"${pyPath}" -m uvicorn --version`, { stdio: 'ignore' });
      return true;
    } catch (e) {
      return false;
    }
  };

  for (const p of candidates) {
    if (p === 'python' || p === 'python3') return p;   // system fallback
    if (fs.existsSync(p) && hasUvicorn(p)) return p;
  }
  return isWin ? 'python' : 'python3';
}

const pythonCmd = getPythonCmd();

// Kill any stale processes on ports 8000 / 3000 before starting
function cleanPorts() {
  if (!isWin) return;
  try {
    const out = execSync('netstat -ano', { encoding: 'utf-8' });
    const pids = new Set();
    out.split('\n').forEach(line => {
      if (line.includes(':8000') || line.includes(':3000')) {
        const m = line.trim().match(/LISTENING\s+(\d+)/);
        if (m && m[1] && m[1] !== '0' && m[1] !== String(process.pid))
          pids.add(m[1]);
      }
    });
    pids.forEach(pid => {
      try { execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' }); } catch (_) {}
    });
  } catch (_) {}
}

cleanPorts();

console.log('==================================================================');
console.log('  METRIX-LM  |  Unified Dev Runner');
console.log('==================================================================');
console.log(`  [PYTHON]   ${pythonCmd}`);
console.log('  [BACKEND]  FastAPI  -> http://localhost:8000');
console.log('  [FRONTEND] React    -> http://localhost:3000');
console.log('  Press Ctrl+C to stop both servers.');
console.log('------------------------------------------------------------------');

// ── 1. FastAPI Backend ────────────────────────────────────────────────────────
const backendArgs = [
  '-m', 'uvicorn', 'app.main:app',
  '--host', '127.0.0.1',
  '--port', '8000',
  '--reload',
];

// IMPORTANT: Use shell:false so Node.js handles quoting of the python path
// correctly even when the path contains spaces (e.g. "C:\Legal lens\...").
// shell:true passes args to cmd.exe which splits on spaces.
const backend = spawn(pythonCmd, backendArgs, {
  cwd: path.join(__dirname, 'backend'),
  stdio: 'inherit',
  shell: false,   // Node handles quoting — safe for paths with spaces
});

// ── 2. React / Vite Frontend ──────────────────────────────────────────────────
// Use shell:true for npm only (it's a .cmd on Windows, not a binary) but
// suppress the DEP0190 path-concatenation deprecation warning via env flag.
const frontend = spawn(npmCmd, ['run', 'dev'], {
  cwd: path.join(__dirname, 'frontend'),
  stdio: 'inherit',
  shell: true,
  env: { ...process.env, NODE_NO_WARNINGS: '1' },
});

// ── Error handlers ────────────────────────────────────────────────────────────
backend.on('error', err => console.error('[BACKEND  ERROR]', err.message));
frontend.on('error', err => console.error('[FRONTEND ERROR]', err.message));

backend.on('exit', (code, signal) => {
  if (code !== 0 && signal !== 'SIGTERM' && signal !== 'SIGINT')
    console.error(`[BACKEND] Exited unexpectedly (code=${code} signal=${signal})`);
});

// ── Graceful shutdown (Ctrl+C) ────────────────────────────────────────────────
function shutdown() {
  console.log('\n[STOP] Shutting down METRIX-LM servers...');
  if (isWin) {
    // Windows: kill process trees so child uvicorn workers also die
    try { execSync(`taskkill /F /T /PID ${backend.pid}`,  { stdio: 'ignore' }); } catch (_) {}
    try { execSync(`taskkill /F /T /PID ${frontend.pid}`, { stdio: 'ignore' }); } catch (_) {}
  } else {
    backend.kill('SIGTERM');
    frontend.kill('SIGTERM');
  }
  process.exit(0);
}

process.on('SIGINT',  shutdown);
process.on('SIGTERM', shutdown);

