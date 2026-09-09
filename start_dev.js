const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const isWin = process.platform === 'win32';
const npmCmd = isWin ? 'npm.cmd' : 'npm';

function getPythonCmd() {
  const venvWin = path.join(__dirname, 'venv', 'Scripts', 'python.exe');
  const venvBackendWin = path.join(__dirname, 'backend', 'venv', 'Scripts', 'python.exe');
  const venvUnix = path.join(__dirname, 'venv', 'bin', 'python');
  const venvBackendUnix = path.join(__dirname, 'backend', 'venv', 'bin', 'python');

  // Verify uvicorn is installed in the venv before using it
  const hasUvicorn = (pyPath) => {
    try {
      execSync(`"${pyPath}" -m uvicorn --version`, { stdio: 'ignore' });
      return true;
    } catch (e) {
      return false;
    }
  };

  if (isWin) {
    if (fs.existsSync(venvBackendWin) && hasUvicorn(venvBackendWin)) return venvBackendWin;
    if (fs.existsSync(venvWin) && hasUvicorn(venvWin)) return venvWin;
    return 'python';
  } else {
    if (fs.existsSync(venvBackendUnix) && hasUvicorn(venvBackendUnix)) return venvBackendUnix;
    if (fs.existsSync(venvUnix) && hasUvicorn(venvUnix)) return venvUnix;
    return 'python3';
  }
}

const pythonCmd = getPythonCmd();

// Automatically clean up stale zombie processes on ports 8000 and 3000 before starting
function cleanPorts() {
  if (isWin) {
    try {
      const output = execSync('netstat -ano', { encoding: 'utf-8' });
      const pids = new Set();
      output.split('\n').forEach(line => {
        if (line.includes(':8000') || line.includes(':3000') || line.includes(':3001')) {
          const match = line.trim().match(/LISTENING\s+(\d+)/);
          if (match && match[1] && match[1] !== '0' && match[1] !== process.pid.toString()) {
            pids.add(match[1]);
          }
        }
      });
      pids.forEach(pid => {
        try {
          execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' });
        } catch (e) {}
      });
    } catch (e) {}
  }
}

cleanPorts();

console.log('==================================================================');
console.log('🚀 METRIX-LM UNIFIED SINGLE-COMMAND DEV RUNNER');
console.log('==================================================================');
console.log(`[PYTHON EXEC] Using: ${pythonCmd}`);
console.log('[BACKEND]  FastAPI REST API -> http://localhost:8000');
console.log('[FRONTEND] React Web Portal -> http://localhost:3000');
console.log('------------------------------------------------------------------');

// 1. Spawn FastAPI Backend Server with auto-reload
const backend = spawn(`"${pythonCmd}"`, ['-m', 'uvicorn', 'app.main:app', '--port', '8000', '--reload'], {
  cwd: path.join(__dirname, 'backend'),
  stdio: 'inherit',
  shell: true
});

// 2. Spawn React Vite Frontend Server
const frontend = spawn(npmCmd, ['run', 'dev'], {
  cwd: path.join(__dirname, 'frontend'),
  stdio: 'inherit',
  shell: true
});

backend.on('error', (err) => {
  console.error('[BACKEND ERROR]:', err);
});

frontend.on('error', (err) => {
  console.error('[FRONTEND ERROR]:', err);
});

process.on('SIGINT', () => {
  console.log('\n[STOP] Shutting down METRIX-LM servers...');
  backend.kill();
  frontend.kill();
  process.exit();
});
