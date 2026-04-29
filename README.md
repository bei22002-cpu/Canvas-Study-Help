# Canvas Study Help

An AI-powered study assistant that connects your Canvas LMS account to Claude AI.  
Get instant answers about assignments, grades, deadlines, and course content — with a color-coded calendar and calendar export.

---

## 🖥️ Node.js / Electron Desktop App (Tray)

> **Easiest way to run — no Python required.**  
> The Electron app sits in your system tray / menu bar and starts everything automatically.

### Prerequisites

| Requirement | Version |
|---|---|
| [Node.js](https://nodejs.org) | 18 LTS or newer |
| npm | bundled with Node.js |

### Install & Run

```bash
# 1. Clone the repo
git clone https://github.com/bei22002-cpu/Canvas-Study-Help.git
cd Canvas-Study-Help

# 2. Install dependencies (first time only)
npm install

# 3. Launch the tray app
npm start
```

That's it. A tray / menu-bar icon appears. **Right-click** it and choose **Open Canvas Study Help** to open the app window.

### Developer mode (opens DevTools automatically)

```bash
npm run dev
```

### Lint the source

```bash
npm run lint
```

### Build a distributable installer

```bash
# Creates an unpacked folder in out/ (fast, good for testing)
npm run pack

# Creates a platform-specific installer (DMG / NSIS / AppImage)
npm run dist
```

> **Icon assets** — `assets/tray-icon.png` (colored, 32×32) and  
> `assets/tray-iconTemplate.png` (white-on-transparent, macOS template) are  
> placeholder icons. Replace them with your own 32×32 PNG to customize the tray icon.  
> For a full installer, also provide `assets/icon.icns` (macOS), `assets/icon.ico` (Windows).

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `CANVAS_PROXY_PORT` | `3001` | Port for the built-in Canvas API proxy |
| `CANVAS_UI_PORT` | `4173` | Port for the built-in static file server |

### How it works (Electron)

```
npm start
  │
  ├─► Built-in Node.js proxy  (port 3001)  ← replaces canvas-proxy.py
  ├─► Built-in static server  (port 4173)  ← serves canvas-app.html
  └─► Electron tray icon
        └─► Right-click → Open  → BrowserWindow → http://127.0.0.1:4173
```

The main process lives in `src/main/index.js`. A preload script  
(`src/preload/preload.js`) bridges the renderer and main process safely with  
`contextIsolation: true` and `nodeIntegration: false`.

### Troubleshooting

**macOS — icon missing or app won't quit**  
The app hides its Dock icon intentionally (it's tray-only). Look for the icon  
in the **menu bar** (top-right of your screen). If macOS blocks the app:
```bash
xattr -rd com.apple.quarantine /Applications/Canvas\ Study\ Help.app
```
Or right-click the `.app` → **Open** the first time.

**Windows — tray icon not visible**  
Windows sometimes hides tray icons. Click the **^** (Show hidden icons) arrow  
in the system tray to find it, then drag it to always show.

**Linux — tray icon doesn't appear**  
Most GNOME desktops need the  
[AppIndicator extension](https://extensions.gnome.org/extension/615/appindicator-support/)  
to show tray icons. KDE, XFCE, and most other desktops work out of the box.  
Also ensure `libgtk-3-0` and `libnotify4` are installed:
```bash
sudo apt install libgtk-3-0 libnotify4 libnss3 libxss1 libgconf-2-4
```

**Port already in use**  
```bash
CANVAS_PROXY_PORT=3002 CANVAS_UI_PORT=4174 npm start
```

**Nothing happens after `npm start`**  
Check the terminal for error output. On Linux, make sure you're not running  
as root (Electron refuses to run as root).

---

## Quick Start (Recommended — no Python required)

1. **Download the app** for your operating system from the [Releases page](https://github.com/bei22002-cpu/Canvas-Study-Help/releases).
2. **Run it:**
   - **Windows:** Double-click `CanvasStudyHelp.exe`
   - **macOS:** Open `CanvasStudyHelp.app` (right-click → Open the first time — see [macOS note](#macos-gatekeeper))
   - **Linux:** `chmod +x CanvasStudyHelp-Linux && ./CanvasStudyHelp-Linux`
3. Your browser opens automatically to the Canvas Study interface.
4. Enter your Canvas domain, Canvas access token, and Anthropic API key — click **Connect to Canvas**.

That's it. The proxy server starts automatically; no Terminal needed.

---

## Start on Login (Optional)

To have Canvas Study Help launch every time you log in:

```bash
# Enable
python3 launcher.py --enable-autostart

# Disable
python3 launcher.py --disable-autostart

# Check status
python3 launcher.py --autostart-status
```

Or using the standalone helper:
```bash
python3 autostart.py --enable
python3 autostart.py --disable
python3 autostart.py --status
```

---

## Running from Source (developers)

```bash
# Clone
git clone https://github.com/bei22002-cpu/Canvas-Study-Help.git
cd Canvas-Study-Help

# No extra dependencies — uses Python standard library only
python3 launcher.py

# Flags
python3 launcher.py --no-browser          # don't auto-open browser
python3 launcher.py --enable-autostart    # set up start on login
```

To run only the proxy (advanced):
```bash
python3 canvas-proxy.py
# or with custom port/host:
CANVAS_PROXY_PORT=3002 python3 canvas-proxy.py
```

---

## Building the Installable App

Requires Python 3.8+ and `pip`.

### macOS / Linux
```bash
bash build.sh
# Output: dist/CanvasStudyHelp  (Linux) or dist/CanvasStudyHelp.app  (macOS)
```

### Windows
```
build.bat
# Output: dist\CanvasStudyHelp.exe
```

The build scripts create a virtual environment, install PyInstaller, and produce a single self-contained executable — no Python installation needed on the target machine.

---

## Automated Builds (GitHub Actions)

Pushing a version tag (e.g. `v1.0.0`) automatically builds all three platforms and attaches them to a GitHub Release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

You can also trigger a build manually from the **Actions** tab → **Build Installers** → **Run workflow**.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `CANVAS_PROXY_PORT` | `3001` | Port for the Canvas API proxy |
| `CANVAS_PROXY_HOST` | `localhost` | Host the proxy binds to |
| `CANVAS_UI_PORT` | `4173` | Port for the UI static server |
| `CANVAS_OPEN_BROWSER` | `1` | Set to `0` to skip auto-opening the browser |

---

## What You Need

- **Canvas Access Token** — Canvas → Account → Settings → New Access Token
- **Anthropic API Key** — [console.anthropic.com](https://console.anthropic.com) (free trial available)

Credentials are stored locally in your browser's `localStorage` only — never sent to any server we control.

---

## Troubleshooting

### "Proxy not running" error
- If using the app: restart it (quit and reopen).
- If running from source: make sure `python3 launcher.py` is running.
- Check that nothing else is using port 3001: `lsof -i :3001` (macOS/Linux) or `netstat -ano | findstr 3001` (Windows).
- Change the port: `CANVAS_PROXY_PORT=3002 python3 launcher.py`

### "Port already in use"
The launcher automatically finds a free port for the UI server.  For the proxy, stop any other process on port 3001 or set `CANVAS_PROXY_PORT` to another value.

### macOS Gatekeeper
The first time you open the app you may see *"Cannot be opened because it is from an unidentified developer"*.  
→ Right-click the app → **Open** → **Open** (you only need to do this once).  
→ Or: `xattr -rd com.apple.quarantine CanvasStudyHelp.app`

### Windows antivirus / SmartScreen
Windows Defender SmartScreen may show a warning for unsigned executables.  
→ Click **More info** → **Run anyway**.

### Linux: browser doesn't open
Make sure `xdg-open` is installed and a default browser is set.  
The URL is printed in the terminal — you can paste it manually.

### Firewall prompts
The app only connects to `localhost` — it never opens external ports.  It does make outbound HTTPS calls to your school's Canvas server and to `api.anthropic.com`.  Allow those if your firewall asks.

---

## Features

- 🤖 **AI Assistant** — ask Claude anything about your courses using live Canvas data
- 📅 **Color-coded Calendar** — view assignments by month or list, filter by course
- 📤 **Calendar Export** — download `.ics` files for Google Calendar, Apple Calendar, or Outlook
- 🔒 **Credentials stored locally** — nothing leaves your computer except direct calls to Canvas and Anthropic
- 🖥️ **Cross-platform** — Windows, macOS, Linux

---

## Architecture

```
launcher.py          ← entry point; starts everything
  │
  ├─► canvas-proxy.py (port 3001)   ← CORS proxy for Canvas API calls
  │     Forwards requests to your school's Canvas server with proper auth headers
  │
  └─► static file server (port 4173)  ← serves canvas-app.html
        Opens browser → http://127.0.0.1:4173/canvas-app.html

autostart.py         ← OS-specific start-on-login helper
canvas-study.spec    ← PyInstaller build spec
build.sh / build.bat ← convenience build scripts
```
