"""Windows Startup folder shortcut management for autostart."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

APP_AUTOSTART_NAME = "AbbonaMunicipale Bot"


def get_startup_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA non disponibile")
    return (
        Path(appdata)
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )


def get_shortcut_path() -> Path:
    return get_startup_dir() / f"{APP_AUTOSTART_NAME}.lnk"


def _ps_escape(value: str) -> str:
    return value.replace("'", "''")


def _run_powershell(script: str) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            err = completed.stderr.strip() or completed.stdout.strip()
            return False, err or "Errore PowerShell non specificato"
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _get_launch_target_and_args() -> tuple[Path, str, Path, Path | None]:
    if getattr(sys, "frozen", False):
        target = Path(sys.executable)
        args = "--autostart"
        working_dir = target.parent
    else:
        target = Path(sys.executable)
        script_path = Path(__file__).resolve().parents[1] / "main.py"
        args = f"\"{script_path}\" --autostart"
        working_dir = script_path.parent.parent

    icon_path = Path(__file__).resolve().parents[2] / "assets" / "icon.ico"
    if not icon_path.exists():
        icon_path = None

    return target, args, working_dir, icon_path


def is_autostart_enabled() -> bool:
    return get_shortcut_path().exists()


def set_autostart_enabled(enabled: bool) -> tuple[bool, str]:
    shortcut_path = get_shortcut_path()

    if not enabled:
        try:
            if shortcut_path.exists():
                shortcut_path.unlink()
            return True, ""
        except Exception as exc:
            return False, str(exc)

    target, args, working_dir, icon_path = _get_launch_target_and_args()

    script = [
        "$WshShell = New-Object -ComObject WScript.Shell",
        f"$Shortcut = $WshShell.CreateShortcut('{_ps_escape(str(shortcut_path))}')",
        f"$Shortcut.TargetPath = '{_ps_escape(str(target))}'",
        f"$Shortcut.Arguments = '{_ps_escape(args)}'",
        f"$Shortcut.WorkingDirectory = '{_ps_escape(str(working_dir))}'",
    ]
    if icon_path:
        script.append(f"$Shortcut.IconLocation = '{_ps_escape(str(icon_path))}'")
    script.append("$Shortcut.Save()")

    return _run_powershell("; ".join(script))
