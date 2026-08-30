const { spawn } = require('child_process');
const path = require('path');

console.log('==================================================================');
console.log('🚀 METRIX-LM UNIFIED SINGLE-TERMINAL RUNNER');
console.log('==================================================================');
console.log('[BACKEND] Launching FastAPI REST API on http://localhost:8000 ...');
console.log('[FRONTEND] Launching React Web Application on http://localhost:3000 ...');
console.log('------------------------------------------------------------------');

const isWin = process.platform === 'win32';
const npmCmd = isWin ? 'npm.cmd' : 'npm';
const pythonCmd = isWin ? 'python' : 'python3';

// 1. Spawn FastAPI Backend Server
const backend = spawn(pythonCmd, ['-m', 'uvicorn', 'app.main:app', '--port', '8000'], {
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
