# AI Router Global Autostart

This small Windows-only VS Code extension starts the local `ai-provider-router` server after VS Code starts, regardless of which workspace is open.

The extension does not read provider API keys, does not call Cline, and does not choose a paid model. It only launches the existing PowerShell starter for the configured router project. The starter checks the local health endpoint and uses a named mutex to avoid duplicate server starts.

## Install

Package this folder as a VSIX with `npx @vscode/vsce package --no-dependencies`, then install the generated VSIX from VS Code using `Extensions: Install from VSIX...`.

## Configure once

After installation, run `AI Router: Configure Project Path` from the Command Palette and select the `ai-provider-router` folder. The default path is `%USERPROFILE%\\ai-provider-router`.

The extension starts automatically after VS Code starts when `aiRouterGlobalAutostart.enabled` is true. It uses port `8787` by default. The commands `AI Router: Start Now`, `AI Router: Show Status`, and `AI Router: Stop Managed Server` are also available.

## Safety

The server is bound to `127.0.0.1` by the existing starter. Provider secrets remain in the router project's `.env`; they are not copied into VS Code settings or the extension. Cline remains a manual client only.
