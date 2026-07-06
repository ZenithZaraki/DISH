const { app, BrowserWindow } = require("electron");
const path = require("path");
const fs = require("fs");
const { exec } = require("child_process");
const axios = require("axios");

const FRONTEND_URL = "http://localhost:5173";
const BACKEND_HEALTH = "http://127.0.0.1:8000/__bootcheck__";

const FRONTEND_PORT = "5173";
const BACKEND_PORT = "8000";

// ─────────────────────────────────────────────
// PORTABLE PATHS
// ─────────────────────────────────────────────

const BASEPATH = path.resolve(__dirname, "..");

const BACKEND_DIR = path.join(BASEPATH, "safu_dish_backend");
const FRONTEND_DIR = path.join(BASEPATH, "safu_dish_frontend");
const USERDATA_DIR = path.join(BASEPATH, "userdata");

const VENV_DIR = path.join(BACKEND_DIR, "venv");
const VENV_SCRIPTS = path.join(VENV_DIR, "Scripts");
const VENV_PYTHON = path.join(VENV_SCRIPTS, "python.exe");

const NODE_DIR = path.join(BASEPATH, "node");
const NODE_EXE = path.join(NODE_DIR, "node.exe");
const NPM_CMD = path.join(NODE_DIR, "npm.cmd");

const TEMP_DIR = path.join(USERDATA_DIR, "temp");
const CACHE_DIR = path.join(USERDATA_DIR, "cache");
const PYCACHE_DIR = path.join(USERDATA_DIR, "pycache");

let mainWindow;
let cleanupStarted = false;

// ─────────────────────────────────────────────
// BASIC FILE/FOLDER HELPERS
// ─────────────────────────────────────────────

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function validatePortablePaths() {
  ensureDir(USERDATA_DIR);
  ensureDir(TEMP_DIR);
  ensureDir(CACHE_DIR);
  ensureDir(PYCACHE_DIR);

  ensureDir(path.join(BACKEND_DIR, "logs"));
  ensureDir(path.join(BACKEND_DIR, "telemetry"));
  ensureDir(path.join(BACKEND_DIR, "telemetry_graphs"));

  const checks = [
    ["Backend folder", BACKEND_DIR],
    ["Frontend folder", FRONTEND_DIR],
    ["Userdata folder", USERDATA_DIR],
    ["Backend venv Python", VENV_PYTHON],
    ["Portable node.exe", NODE_EXE],
    ["Portable npm.cmd", NPM_CMD],
    ["Frontend package.json", path.join(FRONTEND_DIR, "package.json")],
  ];

  for (const [label, target] of checks) {
    if (!fs.existsSync(target)) {
      throw new Error(`${label} not found: ${target}`);
    }
  }
}

// ─────────────────────────────────────────────
// SHARED PORTABLE ENVIRONMENT
// ─────────────────────────────────────────────

function portableEnv() {
  return {
    ...process.env,

    // Critical:
    // npm.cmd internally calls "node", so NODE_DIR must be on PATH.
    PATH: `${NODE_DIR};${VENV_SCRIPTS};${process.env.PATH || ""}`,

    DISH_PORTABLE: "1",
    DISH_ROOT: BASEPATH,
    DISH_USERDATA: USERDATA_DIR,

    PYTHONNOUSERSITE: "1",
    PYTHONPYCACHEPREFIX: PYCACHE_DIR,

    TEMP: TEMP_DIR,
    TMP: TEMP_DIR,

    HF_HOME: path.join(CACHE_DIR, "huggingface"),
    TRANSFORMERS_CACHE: path.join(CACHE_DIR, "huggingface", "transformers"),
    TORCH_HOME: path.join(CACHE_DIR, "torch"),
    XDG_CACHE_HOME: CACHE_DIR,
  };
}

// ─────────────────────────────────────────────
// COMMAND RUNNER
// ─────────────────────────────────────────────

function runCommand(command, options = {}) {
  return exec(command, {
    windowsHide: false,
    env: portableEnv(),
    ...options,
  }, (error) => {
    if (error) {
      console.error(`[COMMAND ERROR] ${error.message}`);
    }
  });
}

// ─────────────────────────────────────────────
// START BACKEND
// ─────────────────────────────────────────────

function startBackend() {
  console.log("[BOOT] Launching backend terminal...");

  const cmd =
    `start "DISH Backend" /MIN /D "${BACKEND_DIR}" cmd.exe /k ` +
    `""${VENV_PYTHON}" -m uvicorn main:app --host 127.0.0.1 --port ${BACKEND_PORT} --reload"`;

  runCommand(cmd, { cwd: BACKEND_DIR });
}

// ─────────────────────────────────────────────
// START FRONTEND
// ─────────────────────────────────────────────

function startFrontend() {
  console.log("[BOOT] Launching frontend terminal...");

  const cmd =
    `start "DISH Frontend" /MIN /D "${FRONTEND_DIR}" cmd.exe /k ` +
    `""${NPM_CMD}" run dev"`;

  runCommand(cmd, { cwd: FRONTEND_DIR });
}

// ─────────────────────────────────────────────
// WAIT HELPERS
// ─────────────────────────────────────────────

async function waitForUrl(url, maxRetries = 60, delayMs = 1000) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const res = await axios.get(url, { timeout: 800 });
      if (res.status >= 200 && res.status < 500) {
        return true;
      }
    } catch {
      // Not ready yet. The machine is thinking, or pretending to.
    }

    await new Promise((resolve) => setTimeout(resolve, delayMs));
  }

  return false;
}

async function waitForBackend(maxRetries = 60, delayMs = 1000) {
  return waitForUrl(BACKEND_HEALTH, maxRetries, delayMs);
}

async function waitForFrontend(maxRetries = 60, delayMs = 1000) {
  return waitForUrl(FRONTEND_URL, maxRetries, delayMs);
}

// ─────────────────────────────────────────────
// CREATE ELECTRON WINDOW
// ─────────────────────────────────────────────

async function createWindow() {
  try {
    validatePortablePaths();
  } catch (error) {
    console.error("[BOOT ERROR]", error.message);

    mainWindow = new BrowserWindow({
      width: 1000,
      height: 700,
      backgroundColor: "#0b0c0f",
      title: "DISH Core - Boot Error",
      frame: true,
      webPreferences: {
        contextIsolation: true,
        nodeIntegration: false,
      },
    });

    const html = `
      <body style="background:#0b0c0f;color:#ff5555;font-family:monospace;padding:2rem;">
        <h1>DISH failed portable path validation.</h1>
        <pre>${String(error.message).replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>
      </body>
    `;

    mainWindow.loadURL(`data:text/html,${encodeURIComponent(html)}`);
    return;
  }

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    backgroundColor: "#0b0c0f",
    title: "DISH Core",
    icon: path.join(__dirname, "assets", "dish_orbit.ico"),
    frame: true,
    transparent: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "src", "splash.html"));

  startBackend();
  startFrontend();

  const backendReady = await waitForBackend();

  if (!backendReady) {
    mainWindow.loadURL(
      "data:text/html," +
      encodeURIComponent(
        `<body style="background:#111;color:red;font-family:monospace;padding:2rem;">
          <h1>Backend failed to start.</h1>
          <p>Check the DISH Backend terminal.</p>
        </body>`
      )
    );
    return;
  }

  const frontendReady = await waitForFrontend();

  if (!frontendReady) {
    mainWindow.loadURL(
      "data:text/html," +
      encodeURIComponent(
        `<body style="background:#111;color:orange;font-family:monospace;padding:2rem;">
          <h1>Frontend failed to start.</h1>
          <p>Check the DISH Frontend terminal.</p>
        </body>`
      )
    );
    return;
  }

  mainWindow.loadURL(FRONTEND_URL);
}

// ─────────────────────────────────────────────
// CLEANUP ON EXIT
// ─────────────────────────────────────────────

function cleanup() {
  if (cleanupStarted) return;
  cleanupStarted = true;

  console.log("[SHUTDOWN] Cleaning up DISH child processes...");

  exec(
    `taskkill /FI "WINDOWTITLE eq DISH Backend*" /F /T >nul 2>&1`,
    () => console.log("[OK] Backend console closed.")
  );

  exec(
    `taskkill /FI "WINDOWTITLE eq DISH Frontend*" /F /T >nul 2>&1`,
    () => console.log("[OK] Frontend console closed.")
  );

  // Conservative-ish sweep. Still a broom, not a scalpel.
  exec(
    `taskkill /F /IM vite.exe /IM npm.exe /IM uvicorn.exe /T >nul 2>&1`,
    () => console.log("[OK] Remaining DISH child tools purged.")
  );
}

// ─────────────────────────────────────────────
// APP EVENTS
// ─────────────────────────────────────────────

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  cleanup();
  app.quit();
});

app.on("before-quit", () => {
  cleanup();
});

process.on("SIGINT", () => {
  cleanup();
  process.exit(0);
});

process.on("SIGTERM", () => {
  cleanup();
  process.exit(0);
});