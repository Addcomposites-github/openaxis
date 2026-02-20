const { app, BrowserWindow, ipcMain, Menu } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess;

// Python backend management
function startPythonBackend() {
  const isPackaged = app.isPackaged;

  let command, args;

  if (isPackaged) {
    // Packaged mode: use PyInstaller-frozen backend from extraResources
    const resourcePath = process.resourcesPath;
    const backendExe = process.platform === 'win32'
      ? path.join(resourcePath, 'backend', 'openaxis-server.exe')
      : path.join(resourcePath, 'backend', 'openaxis-server');

    command = backendExe;
    args = [];
    console.log(`[OpenAxis] Starting packaged backend: ${command}`);
  } else {
    // Development mode: run server.py with Python
    command = process.platform === 'win32' ? 'python' : 'python3';
    args = [path.join(__dirname, '..', '..', 'backend', 'server.py')];
    console.log(`[OpenAxis] Starting dev backend: ${command} ${args.join(' ')}`);
  }

  pythonProcess = spawn(command, args, {
    env: { ...process.env, OPENAXIS_PACKAGED: isPackaged ? '1' : '0' },
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`Python Backend: ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`Python Backend Error: ${data}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python backend exited with code ${code}`);
  });

  pythonProcess.on('error', (err) => {
    console.error(`Failed to start backend: ${err.message}`);
  });
}

function stopPythonBackend() {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 1000,
    minWidth: 1200,
    minHeight: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    title: 'OpenAxis',
    backgroundColor: '#0f172a',
    show: false, // Don't show until ready
  });

  // Load the app
  // Check if we're in development by trying to load from dev server
  const isDev = !app.isPackaged;

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Handle window close
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Create application menu
  createMenu();
}

function createMenu() {
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'New Project',
          accelerator: 'CmdOrCtrl+N',
          click: () => {
            mainWindow.webContents.send('menu-action', 'new-project');
          },
        },
        {
          label: 'Open Project',
          accelerator: 'CmdOrCtrl+O',
          click: () => {
            mainWindow.webContents.send('menu-action', 'open-project');
          },
        },
        {
          label: 'Save Project',
          accelerator: 'CmdOrCtrl+S',
          click: () => {
            mainWindow.webContents.send('menu-action', 'save-project');
          },
        },
        { type: 'separator' },
        {
          label: 'Import Geometry',
          accelerator: 'CmdOrCtrl+I',
          click: () => {
            mainWindow.webContents.send('menu-action', 'import-geometry');
          },
        },
        {
          label: 'Export G-code',
          accelerator: 'CmdOrCtrl+E',
          click: () => {
            mainWindow.webContents.send('menu-action', 'export-gcode');
          },
        },
        { type: 'separator' },
        { role: 'quit' },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'delete' },
        { type: 'separator' },
        { role: 'selectAll' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Robot',
      submenu: [
        {
          label: 'Connect',
          click: () => {
            mainWindow.webContents.send('menu-action', 'robot-connect');
          },
        },
        {
          label: 'Disconnect',
          click: () => {
            mainWindow.webContents.send('menu-action', 'robot-disconnect');
          },
        },
        { type: 'separator' },
        {
          label: 'Home',
          click: () => {
            mainWindow.webContents.send('menu-action', 'robot-home');
          },
        },
        {
          label: 'Enable Motors',
          click: () => {
            mainWindow.webContents.send('menu-action', 'robot-enable');
          },
        },
        {
          label: 'Disable Motors',
          click: () => {
            mainWindow.webContents.send('menu-action', 'robot-disable');
          },
        },
      ],
    },
    {
      label: 'Process',
      submenu: [
        {
          label: 'Generate Toolpath',
          accelerator: 'CmdOrCtrl+G',
          click: () => {
            mainWindow.webContents.send('menu-action', 'generate-toolpath');
          },
        },
        {
          label: 'Simulate',
          accelerator: 'CmdOrCtrl+Shift+S',
          click: () => {
            mainWindow.webContents.send('menu-action', 'simulate');
          },
        },
        { type: 'separator' },
        {
          label: 'Start Manufacturing',
          click: () => {
            mainWindow.webContents.send('menu-action', 'start-manufacturing');
          },
        },
        {
          label: 'Pause',
          click: () => {
            mainWindow.webContents.send('menu-action', 'pause');
          },
        },
        {
          label: 'Stop',
          click: () => {
            mainWindow.webContents.send('menu-action', 'stop');
          },
        },
      ],
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'Documentation',
          click: () => {
            require('electron').shell.openExternal('https://openaxis.github.io/openaxis');
          },
        },
        {
          label: 'GitHub Repository',
          click: () => {
            require('electron').shell.openExternal('https://github.com/openaxis/openaxis');
          },
        },
        { type: 'separator' },
        {
          label: 'About OpenAxis',
          click: () => {
            mainWindow.webContents.send('menu-action', 'about');
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// App lifecycle
app.whenReady().then(() => {
  startPythonBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  stopPythonBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopPythonBackend();
});

// IPC Handlers for communication with renderer
ipcMain.handle('python-request', async (event, args) => {
  // Forward requests to Python backend via HTTP or WebSocket
  // For now, return placeholder
  return { status: 'ok', data: null };
});

ipcMain.handle('get-app-path', () => {
  return app.getPath('userData');
});

ipcMain.handle('get-version', () => {
  return app.getVersion();
});
