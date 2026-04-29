#!/usr/bin/env python3
"""
Cross-platform autostart helper for Canvas Study Help.

Usage (standalone):
    python3 autostart.py --enable          # start on login
    python3 autostart.py --disable         # remove from login
    python3 autostart.py --status          # check current state

Or use via the launcher:
    python3 launcher.py --enable-autostart
    python3 launcher.py --disable-autostart
    python3 launcher.py --autostart-status
"""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

APP_NAME = "CanvasStudyHelp"
APP_DISPLAY = "Canvas Study Help"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _exe_args() -> list:
    """
    Return the command + arguments list that re-launches this app.

    - Frozen (PyInstaller): ['/path/to/CanvasStudyHelp']
    - Dev mode:             ['/path/to/python3', '/path/to/launcher.py']
    """
    if getattr(sys, "frozen", False):
        return [sys.executable]
    launcher = Path(__file__).with_name("launcher.py")
    return [sys.executable, str(launcher)]


# ---------------------------------------------------------------------------
# Windows  (HKCU\...\Run registry key)
# ---------------------------------------------------------------------------
def _win_enable() -> None:
    import winreg  # noqa: PLC0415 (Windows-only)

    cmd = subprocess.list2cmdline(_exe_args())  # properly quoted
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    )
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
    winreg.CloseKey(key)
    print(f"[Windows] Added '{APP_NAME}' to HKCU\\…\\Run.")


def _win_disable() -> None:
    import winreg  # noqa: PLC0415

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        print(f"[Windows] Removed '{APP_NAME}' from autostart.")
    except FileNotFoundError:
        print(f"[Windows] '{APP_NAME}' was not registered — nothing to remove.")


def _win_status() -> bool:
    import winreg  # noqa: PLC0415

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False


# ---------------------------------------------------------------------------
# macOS  (LaunchAgent plist)
# ---------------------------------------------------------------------------
def _mac_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"com.{APP_NAME.lower()}.plist"


def _mac_enable() -> None:
    path = _mac_plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    args_xml = "\n    ".join(f"<string>{part}</string>" for part in _exe_args())
    log_dir = Path.home() / "Library" / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{APP_NAME.lower()}</string>
    <key>ProgramArguments</key>
    <array>
    {args_xml}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>{log_dir}/{APP_NAME}.log</string>
    <key>StandardErrorPath</key>
    <string>{log_dir}/{APP_NAME}.log</string>
</dict>
</plist>
"""
    path.write_text(plist)
    subprocess.run(["launchctl", "load", str(path)], check=False)
    print(f"[macOS] LaunchAgent installed: {path}")


def _mac_disable() -> None:
    path = _mac_plist_path()
    if path.exists():
        subprocess.run(["launchctl", "unload", str(path)], check=False)
        path.unlink()
        print("[macOS] LaunchAgent removed.")
    else:
        print("[macOS] No LaunchAgent found — nothing to remove.")


def _mac_status() -> bool:
    return _mac_plist_path().exists()


# ---------------------------------------------------------------------------
# Linux  (XDG autostart .desktop entry)
# ---------------------------------------------------------------------------
def _linux_desktop_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(xdg) / "autostart" / f"{APP_NAME.lower()}.desktop"


def _linux_enable() -> None:
    path = _linux_desktop_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    exec_line = " ".join(_exe_args())
    desktop = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_DISPLAY}\n"
        f"Exec={exec_line}\n"
        "Hidden=false\n"
        "NoDisplay=false\n"
        "X-GNOME-Autostart-enabled=true\n"
        f"Comment={APP_DISPLAY} — starts proxy and opens browser\n"
    )
    path.write_text(desktop)
    print(f"[Linux] Autostart entry installed: {path}")


def _linux_disable() -> None:
    path = _linux_desktop_path()
    if path.exists():
        path.unlink()
        print("[Linux] Autostart entry removed.")
    else:
        print("[Linux] No autostart entry found — nothing to remove.")


def _linux_status() -> bool:
    return _linux_desktop_path().exists()


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
_HANDLERS = {
    "Windows": (_win_enable, _win_disable, _win_status),
    "Darwin": (_mac_enable, _mac_disable, _mac_status),
    "Linux": (_linux_enable, _linux_disable, _linux_status),
}


def _get_handlers():
    name = platform.system()
    h = _HANDLERS.get(name)
    if h is None:
        raise RuntimeError(f"Autostart is not supported on '{name}'")
    return h


def enable() -> None:
    _get_handlers()[0]()


def disable() -> None:
    _get_handlers()[1]()


def status() -> bool:
    return _get_handlers()[2]()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"Manage {APP_DISPLAY} start-on-login",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--enable", action="store_true", help="Enable start on login")
    group.add_argument("--disable", action="store_true", help="Disable start on login")
    group.add_argument("--status", action="store_true", help="Print autostart status")
    args = parser.parse_args()

    try:
        if args.enable:
            enable()
        elif args.disable:
            disable()
        else:
            enabled = status()
            print(f"Autostart: {'enabled' if enabled else 'disabled'}")
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
