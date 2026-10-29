import { spawn, execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

// Detect Python executable: .venv, venv, or system python
let pythonCmd = 'python';
const venvWin = path.join(rootDir, '.venv', 'Scripts', 'python.exe');
const venvPosix = path.join(rootDir, '.venv', 'bin', 'python');

if (fs.existsSync(venvWin)) {
  pythonCmd = venvWin;
} else if (fs.existsSync(venvPosix)) {
  pythonCmd = venvPosix;
}

const args = ['-m', 'uvicorn', 'main:app', '--reload', '--port', '8000'];

const proc = spawn(pythonCmd, args, {
  cwd: rootDir,
  stdio: 'inherit',
});

const killProcessTree = () => {
  if (!proc || !proc.pid) return;
  try {
    if (process.platform === 'win32') {
      execSync(`taskkill /PID ${proc.pid} /T /F`, { stdio: 'ignore' });
    } else {
      proc.kill('SIGTERM');
    }
  } catch (e) {
    // Process already terminated
  }
};

process.on('SIGINT', () => {
  killProcessTree();
  process.exit(0);
});

process.on('SIGTERM', () => {
  killProcessTree();
  process.exit(0);
});

process.on('exit', () => {
  killProcessTree();
});

proc.on('close', (code) => {
  process.exit(code || 0);
});
