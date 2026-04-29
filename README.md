# Canvas Study Help

An AI-powered study assistant that connects your Canvas LMS account to Claude AI.  
Get instant answers about assignments, grades, deadlines, and course content — with a color-coded calendar and calendar export.

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
