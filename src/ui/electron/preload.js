const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electron', {
  // Dialog APIs
  dialog: {
    openFile: (options) => ipcRenderer.invoke('dialog:openFile', options),
    saveFile: (options) => ipcRenderer.invoke('dialog:saveFile', options),
  },

  // Python backend communication
  python: {
    call: (method, args) => ipcRenderer.invoke('python:call', method, args),
  },

  // Project management
  project: {
    create: (data) => ipcRenderer.invoke('project:create', data),
    load: (path) => ipcRenderer.invoke('project:load', path),
    save: (data) => ipcRenderer.invoke('project:save', data),
  },

  // Geometry operations
  geometry: {
    import: (filePath) => ipcRenderer.invoke('geometry:import', filePath),
  },

  // Slicing operations
  slicing: {
    generate: (params) => ipcRenderer.invoke('slicing:generate', params),
  },

  // Simulation
  simulation: {
    start: (config) => ipcRenderer.invoke('simulation:start', config),
    stop: () => ipcRenderer.invoke('simulation:stop'),
  },

  // Motion planning
  motion: {
    planPath: (params) => ipcRenderer.invoke('motion:planPath', params),
  },

  // Process operations
  process: {
    validate: (params) => ipcRenderer.invoke('process:validate', params),
  },

  // Event listeners
  on: (channel, callback) => {
    const subscription = (event, ...args) => callback(...args);
    ipcRenderer.on(channel, subscription);
    return () => ipcRenderer.removeListener(channel, subscription);
  },
});
