'use strict';

/**
 * Preload script — runs in a sandboxed context before the renderer.
 *
 * Exposes a minimal, safe API surface to the renderer via contextBridge.
 * Node.js / Electron internals are NOT accessible in the renderer because
 * nodeIntegration is disabled and contextIsolation is enabled.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  /** True when running inside the Electron shell (vs. a plain browser) */
  isElectron: true,

  /** Electron / Node / Chromium version strings */
  versions: {
    electron: process.versions.electron,
    node: process.versions.node,
    chrome: process.versions.chrome,
  },

  /**
   * Forward one-way IPC messages to the main process.
   * Only whitelisted channels are accepted to prevent misuse.
   */
  send: (channel, ...args) => {
    const ALLOWED = ['app:quit', 'app:reload'];
    if (ALLOWED.includes(channel)) {
      ipcRenderer.send(channel, ...args);
    }
  },
});
