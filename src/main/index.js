'use strict';

const { app, BrowserWindow, Tray, Menu, nativeImage, shell } = require('electron');
const path = require('path');
const http = require('http');
const https = require('https');
const fs = require('fs');
const net = require('net');

// ─── Keep global references to prevent garbage-collection ──────────────────
let tray = null;
let mainWindow = null;
let proxyServer = null;
let staticServer = null;

const PROXY_PORT = parseInt(process.env.CANVAS_PROXY_PORT || '3001', 10);
const STATIC_PORT = parseInt(process.env.CANVAS_UI_PORT || '4173', 10);
const IS_DEV = process.argv.includes('--dev');
const IS_MAC = process.platform === 'darwin';

// ─── Single-instance lock ───────────────────────────────────────────────────
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    // Focus existing window if another instance is launched
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// ─── Canvas API proxy (Node.js port of canvas-proxy.py) ────────────────────

/**
 * Validate that a Canvas domain string is a safe external hostname.
 * Rejects private/loopback IPs and anything that isn't a plain hostname
 * to prevent SSRF attacks against internal services.
 */
function isValidCanvasDomain(domain) {
  if (!domain || domain.length > 253) return false;
  // No embedded protocol, path, credentials, or port
  if (/[/:@?#]/.test(domain)) return false;
  // Must look like a valid DNS hostname
  if (!/^[a-zA-Z0-9]([a-zA-Z0-9\-.]*[a-zA-Z0-9])?$/.test(domain)) return false;
  // Block loopback and private-network addresses
  if (/^(localhost|127\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.|0\.0\.0\.0)/i.test(domain)) return false;
  if (/^::1$|^fc[0-9a-f]{2}:|^fd[0-9a-f]{2}:/i.test(domain)) return false;
  return true;
}

function createProxyServer() {
  const server = http.createServer((req, res) => {
    const CORS = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Authorization, X-Canvas-Domain, Content-Type',
    };

    if (req.method === 'OPTIONS') {
      res.writeHead(200, CORS);
      res.end();
      return;
    }

    if (req.method !== 'GET') {
      res.writeHead(405, CORS);
      res.end(JSON.stringify({ error: 'Method not allowed' }));
      return;
    }

    const domain = (req.headers['x-canvas-domain'] || '').trim();
    const auth   = (req.headers['authorization']   || '').trim();

    if (!domain || !auth) {
      res.writeHead(400, { ...CORS, 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Missing X-Canvas-Domain or Authorization header' }));
      return;
    }

    if (!isValidCanvasDomain(domain)) {
      res.writeHead(400, { ...CORS, 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Invalid Canvas domain' }));
      return;
    }

    const targetUrl = `https://${domain}${req.url}`;

    const proxyReq = https.request(
      targetUrl,
      { method: 'GET', headers: { Authorization: auth, Accept: 'application/json' } },
      (proxyRes) => {
        const headers = {
          ...CORS,
          'Content-Type': proxyRes.headers['content-type'] || 'application/json',
        };
        if (proxyRes.headers['link']) headers['Link'] = proxyRes.headers['link'];
        res.writeHead(proxyRes.statusCode, headers);
        proxyRes.pipe(res);
      }
    );

    proxyReq.on('error', (err) => {
      if (!res.headersSent) {
        res.writeHead(502, { ...CORS, 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: err.message }));
      }
    });

    proxyReq.end();
  });

  return server;
}

// ─── Static file server (serves canvas-app.html) ───────────────────────────
function createStaticServer() {
  const htmlPath = path.join(__dirname, '..', '..', 'canvas-app.html');

  const server = http.createServer((req, res) => {
    if (req.url === '/' || req.url === '/canvas-app.html') {
      fs.readFile(htmlPath, (err, data) => {
        if (err) {
          res.writeHead(404);
          res.end('canvas-app.html not found');
          return;
        }
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(data);
      });
    } else {
      res.writeHead(404);
      res.end('Not found');
    }
  });

  return server;
}

// ─── Port availability check ────────────────────────────────────────────────
function isPortFree(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(false));
    server.once('listening', () => { server.close(); resolve(true); });
    server.listen(port, '127.0.0.1');
  });
}

// ─── BrowserWindow ──────────────────────────────────────────────────────────
function createWindow() {
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
    return;
  }

  mainWindow = new BrowserWindow({
    width: 1120,
    height: 780,
    minWidth: 820,
    minHeight: 520,
    title: 'Canvas Study Help',
    backgroundColor: '#f7f5f0',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      preload: path.join(__dirname, '..', 'preload', 'preload.js'),
    },
  });

  mainWindow.loadURL(`http://127.0.0.1:${STATIC_PORT}/canvas-app.html`);

  if (IS_DEV) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }

  // Keep external links in the system browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    const isLocal = url.startsWith(`http://127.0.0.1:${STATIC_PORT}`) ||
                    url.startsWith(`http://localhost:${STATIC_PORT}`);
    if (!isLocal) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ─── Tray ────────────────────────────────────────────────────────────────────
function buildTrayMenu() {
  return Menu.buildFromTemplate([
    {
      label: 'Open Canvas Study Help',
      click: createWindow,
    },
    {
      label: 'Reload',
      click: () => {
        if (mainWindow) {
          mainWindow.reload();
        } else {
          createWindow();
        }
      },
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => app.quit(),
    },
  ]);
}

function createTray() {
  // Use template image on macOS for proper dark/light mode support
  const iconFile = IS_MAC ? 'tray-iconTemplate.png' : 'tray-icon.png';
  const iconPath = path.join(__dirname, '..', '..', 'assets', iconFile);
  const icon = nativeImage.createFromPath(iconPath);

  tray = new Tray(icon);
  tray.setToolTip('Canvas Study Help');
  tray.setContextMenu(buildTrayMenu());

  // Open window on double-click (Windows / Linux)
  tray.on('double-click', createWindow);

  // On macOS a left-click also shows the context menu automatically
  if (IS_MAC) {
    tray.on('click', () => tray.popUpContextMenu());
  }
}

// ─── App lifecycle ──────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  // Hide dock icon on macOS — this is a tray-only app
  if (IS_MAC) app.dock.hide();

  // Start the Canvas API proxy (replaces canvas-proxy.py)
  if (await isPortFree(PROXY_PORT)) {
    proxyServer = createProxyServer();
    proxyServer.listen(PROXY_PORT, '127.0.0.1', () => {
      console.log(`[proxy ] running on http://127.0.0.1:${PROXY_PORT}`);
    });
  } else {
    console.log(`[proxy ] port ${PROXY_PORT} already in use — skipping`);
  }

  // Start the static file server for canvas-app.html
  if (await isPortFree(STATIC_PORT)) {
    staticServer = createStaticServer();
    staticServer.listen(STATIC_PORT, '127.0.0.1', () => {
      console.log(`[static] running on http://127.0.0.1:${STATIC_PORT}`);
    });
  } else {
    console.log(`[static] port ${STATIC_PORT} already in use — skipping`);
  }

  createTray();
  console.log('[tray  ] Canvas Study Help is running in the menu bar / system tray');
  console.log('[tray  ] Right-click the tray icon to open the app or quit');
});

// Keep the app alive when all windows are closed (tray-only mode)
app.on('window-all-closed', () => {
  // Intentionally do NOT call app.quit() here so the tray stays active.
  // Quit is handled by the tray context-menu "Quit" item.
});

// macOS: re-open window when app is activated from the dock (fallback)
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

// Clean up servers before quitting
app.on('before-quit', () => {
  if (proxyServer)  proxyServer.close();
  if (staticServer) staticServer.close();
});
