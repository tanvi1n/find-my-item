import express from 'express';
import { spawn, ChildProcess } from 'child_process';
import http from 'http';
import path from 'path';

const app = express();
const PORT = 3000;
const FLASK_PORT = 5005;

let flaskProcess: ChildProcess | null = null;
let isFlaskReady = false;

function startFlaskBackend() {
  console.log(`Starting Python Flask backend on port ${FLASK_PORT}...`);
  flaskProcess = spawn('python3', ['app.py'], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      FLASK_PORT: String(FLASK_PORT),
    },
    stdio: 'inherit',
  });

  flaskProcess.on('error', (err) => {
    console.error('Failed to spawn Python Flask process:', err);
  });

  flaskProcess.on('exit', (code, signal) => {
    console.log(`Flask backend process exited with code ${code} and signal ${signal}`);
    isFlaskReady = false;
  });

  // Poll until Flask is listening
  const checkInterval = setInterval(() => {
    const req = http.get(`http://127.0.0.1:${FLASK_PORT}/`, (res) => {
      isFlaskReady = true;
      clearInterval(checkInterval);
      console.log(`Flask backend confirmed ready on port ${FLASK_PORT}.`);
    });
    req.on('error', () => {
      // Waiting for Flask to bind
    });
    req.end();
  }, 300);

  setTimeout(() => {
    clearInterval(checkInterval);
  }, 10000);
}

startFlaskBackend();

// Reverse-proxy all incoming HTTP requests directly to the Flask backend
app.use((req, res) => {
  const options: http.RequestOptions = {
    hostname: '127.0.0.1',
    port: FLASK_PORT,
    path: req.originalUrl || req.url,
    method: req.method,
    headers: {
      ...req.headers,
      host: req.headers.host || `localhost:${PORT}`,
      'x-forwarded-for': req.ip || req.socket.remoteAddress || '',
      'x-forwarded-proto': req.protocol,
    },
  };

  const proxyReq = http.request(options, (proxyRes) => {
    // Forward status and headers (including set-cookie for Flask sessions)
    res.writeHead(proxyRes.statusCode || 500, proxyRes.headers);
    proxyRes.pipe(res, { end: true });
  });

  proxyReq.on('error', (err) => {
    if (!isFlaskReady) {
      res.status(503).send(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>Find-My-Item - Initializing</title>
          <meta http-equiv="refresh" content="2">
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .box { text-align: center; max-width: 480px; padding: 2rem; background: #1e293b; border-radius: 12px; border: 1px solid #334155; }
            h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
            p { color: #94a3b8; font-size: 0.95rem; line-height: 1.5; }
          </style>
        </head>
        <body>
          <div class="box">
            <h1>Campus Recovery Engine Initializing...</h1>
            <p>Connecting Flask backend and SQLite database. This page will refresh automatically in 2 seconds.</p>
          </div>
        </body>
        </html>
      `);
    } else {
      console.error('Proxy communication error with Flask:', err);
      res.status(502).send('Gateway Error communicating with Find-My-Item backend.');
    }
  });

  req.pipe(proxyReq, { end: true });
});

const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`Find-My-Item Reverse Proxy active on http://0.0.0.0:${PORT} -> Flask :${FLASK_PORT}`);
});

function cleanup() {
  console.log('Shutting down Find-My-Item services...');
  if (flaskProcess) {
    flaskProcess.kill('SIGTERM');
  }
  server.close(() => {
    process.exit(0);
  });
}

process.on('SIGTERM', cleanup);
process.on('SIGINT', cleanup);
