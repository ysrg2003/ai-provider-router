const fs = require("fs");
const http = require("http");
const path = require("path");
const cp = require("child_process");
const vscode = require("vscode");

let managedProcess = null;
let output;

function log(message) {
  if (output) {
    output.appendLine(`[${new Date().toISOString()}] ${message}`);
  }
}

function configuredProjectPath() {
  const configured = vscode.workspace
    .getConfiguration("aiRouterGlobalAutostart")
    .get("projectPath", "");
  if (configured && configured.trim()) {
    return configured.trim();
  }
  const fallback = process.env.USERPROFILE
    ? path.join(process.env.USERPROFILE, "ai-provider-router")
    : "";
  return fallback;
}

function port() {
  return Number(
    vscode.workspace
      .getConfiguration("aiRouterGlobalAutostart")
      .get("port", 8787),
  );
}

function scriptPath(projectPath) {
  return path.join(projectPath, "scripts", "start_router_windows.ps1");
}

function isValidProject(projectPath) {
  return Boolean(
    projectPath &&
      fs.existsSync(scriptPath(projectPath)) &&
      fs.existsSync(path.join(projectPath, ".venv", "Scripts", "ai-router.exe")),
  );
}

function startServer() {
  if (managedProcess && !managedProcess.killed) {
    log(`Managed process already running with PID ${managedProcess.pid}.`);
    return;
  }

  const projectPath = configuredProjectPath();
  if (!isValidProject(projectPath)) {
    const message =
      "AI Router project was not found. Configure its path with: AI Router: Configure Project Path";
    log(`${message} Path: ${projectPath || "<empty>"}`);
    vscode.window.showWarningMessage(message);
    return;
  }

  const child = cp.spawn(
    "powershell.exe",
    [
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-File",
      scriptPath(projectPath),
      "-Port",
      String(port()),
    ],
    {
      cwd: projectPath,
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  managedProcess = child;
  log(`Starting router from ${projectPath} on port ${port()}.`);
  child.stdout.on("data", (data) => log(String(data).trimEnd()));
  child.stderr.on("data", (data) => log(`stderr: ${String(data).trimEnd()}`));
  child.on("error", (error) => {
    log(`Process error: ${error.message}`);
    vscode.window.showErrorMessage(`AI Router failed to start: ${error.message}`);
  });
  child.on("exit", (code, signal) => {
    log(`Starter process exited with code ${code ?? "null"}${signal ? ` signal ${signal}` : ""}.`);
    managedProcess = null;
  });
}

function stopServer() {
  if (!managedProcess || managedProcess.killed || !managedProcess.pid) {
    vscode.window.showInformationMessage(
      "No AI Router process is managed by this VS Code window. The server may already be stopped or was started elsewhere.",
    );
    return;
  }
  const pid = managedProcess.pid;
  cp.spawn("taskkill.exe", ["/PID", String(pid), "/T", "/F"], {
    windowsHide: true,
    stdio: "ignore",
  });
  managedProcess = null;
  log(`Stopped managed process tree ${pid}.`);
}

function checkHealth() {
  const request = http.get(
    { hostname: "127.0.0.1", port: port(), path: "/health", timeout: 2000 },
    (response) => {
      let body = "";
      response.setEncoding("utf8");
      response.on("data", (chunk) => (body += chunk));
      response.on("end", () => {
        if (response.statusCode === 200) {
          vscode.window.showInformationMessage(`AI Router is healthy on port ${port()}.`);
          log(`Health OK: ${body}`);
        } else {
          vscode.window.showWarningMessage(`AI Router health returned HTTP ${response.statusCode}.`);
          log(`Health HTTP ${response.statusCode}: ${body}`);
        }
      });
    },
  );
  request.on("error", () => {
    vscode.window.showWarningMessage(`AI Router is not reachable on port ${port()}.`);
    log(`Health check failed on port ${port()}.`);
  });
  request.on("timeout", () => request.destroy());
}

async function configureProjectPath() {
  const picked = await vscode.window.showOpenDialog({
    canSelectFiles: false,
    canSelectFolders: true,
    canSelectMany: false,
    openLabel: "Use AI Router Project",
    title: "Select ai-provider-router folder",
  });
  if (!picked || !picked[0]) {
    return;
  }
  const selected = picked[0].fsPath;
  await vscode.workspace
    .getConfiguration("aiRouterGlobalAutostart")
    .update("projectPath", selected, vscode.ConfigurationTarget.Global);
  vscode.window.showInformationMessage(`AI Router project path saved: ${selected}`);
  startServer();
}

function activate(context) {
  output = vscode.window.createOutputChannel("AI Router Global Autostart");
  context.subscriptions.push(output);
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "aiRouterGlobalAutostart.configureProjectPath",
      configureProjectPath,
    ),
    vscode.commands.registerCommand("aiRouterGlobalAutostart.startNow", startServer),
    vscode.commands.registerCommand("aiRouterGlobalAutostart.showStatus", checkHealth),
    vscode.commands.registerCommand("aiRouterGlobalAutostart.stopServer", stopServer),
  );

  const enabled = vscode.workspace
    .getConfiguration("aiRouterGlobalAutostart")
    .get("enabled", true);
  if (enabled) {
    startServer();
  }
}

function deactivate() {
  stopServer();
}

module.exports = { activate, deactivate };
