const { contextBridge, ipcRenderer } = require('electron');

// Safe IPC API bridge for Renderer process (React App)
contextBridge.exposeInMainWorld('electronAPI', {
  isElectron: true,
  platform: process.platform,
  onNavigate: (callback) => ipcRenderer.on('navigate', (_event, value) => callback(value))
});
