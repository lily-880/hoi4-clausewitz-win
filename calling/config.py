"""Path and platform resolution for Windows HOI4 installs."""
from __future__ import annotations

import os
import platform
import re

WINDOWS = platform.system() == "Windows"
EXE_NAME = "hoi4.exe" if WINDOWS else "hoi4"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Target pin for this fork's offset work
TARGET_VERSION = "1.19.4.0"
TARGET_VERSION_NAME = "Operation Postern"

_STEAM_DIRS = [
    r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV",
    r"C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV",
    r"C:\Program Files\Steam\steamapps\common\Hearts of Iron IV",
    r"D:\SteamLibrary\steamapps\common\Hearts of Iron IV",
    r"E:\SteamLibrary\steamapps\common\Hearts of Iron IV",
    os.path.expanduser(r"~\Steam\steamapps\common\Hearts of Iron IV"),
]


def _extra_steam_libraries():
    roots = [
        r"C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf",
        r"D:\STEAM\steam\steamapps\libraryfolders.vdf",
        r"D:\Steam\steamapps\libraryfolders.vdf",
    ]
    out = []
    for vdf in roots:
        try:
            with open(vdf, encoding="utf-8", errors="replace") as f:
                text = f.read()
            for m in re.finditer(r'"path"\s+"([^"]+)"', text):
                out.append(
                    os.path.join(
                        m.group(1).replace("\\\\", os.sep),
                        "steamapps",
                        "common",
                        "Hearts of Iron IV",
                    )
                )
        except OSError:
            continue
    return out


def find_game_dir():
    env = os.environ.get("HOI4_PATH")
    if env and os.path.isdir(env):
        return env
    for d in _STEAM_DIRS + _extra_steam_libraries():
        if os.path.isdir(d):
            return d
    return None


def game_dir(required=True):
    d = find_game_dir()
    if d is None and required:
        raise RuntimeError(
            "Could not find Hearts of Iron IV. Set HOI4_PATH to the game directory, e.g.\n"
            '  set HOI4_PATH=D:\\STEAM\\steam\\steamapps\\common\\Hearts of Iron IV'
        )
    return d


def binary_path(required=True):
    d = game_dir(required)
    if d is None:
        return None
    for name in (EXE_NAME, "hoi4.exe", "hoi4"):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    if required:
        raise RuntimeError("found game directory but no executable: %s" % d)
    return None


def read_launcher_version(game=None):
    """Best-effort version string from launcher-settings.json or similar."""
    game = game or find_game_dir()
    if not game:
        return None
    candidates = [
        os.path.join(game, "launcher-settings.json"),
        os.path.join(game, "launcher", "launcher-settings.json"),
    ]
    import json
    for p in candidates:
        try:
            data = json.load(open(p, encoding="utf-8"))
            for key in ("rawVersion", "version", "gameVersion", "exePath"):
                if key in data and isinstance(data[key], str) and data[key].strip():
                    return data[key].strip()
            # nested
            if "version" in data and isinstance(data["version"], dict):
                v = data["version"].get("version") or data["version"].get("name")
                if v:
                    return str(v)
        except (OSError, ValueError, TypeError):
            continue
    # fallback: checksum file / steam_appid presence only
    return None


# --- write / post gates (default OFF; posting DISABLED until checklist closed) ---
import os as _os

def allow_write() -> bool:
    return _os.environ.get('CLAUSEWITZ_ALLOW_WRITE', '').strip() in ('1', 'true', 'TRUE', 'yes')


def allow_post() -> bool:
    """Separate from allow_write. Requires CLAUSEWITZ_ALLOW_POST=1 AND Strategic-only tool-gate marker.

    Marker path: research/strategic_only_tool_gate.OPEN (G5). Env alone is never enough.
    NEVER_POST families (speed/HourlyTick/Ping/Pause) remain forbidden by callers.
    """
    if _os.environ.get('CLAUSEWITZ_ALLOW_POST', '').strip() not in ('1', 'true', 'TRUE', 'yes'):
        return False
    marker = _os.path.join(ROOT, 'research', 'strategic_only_tool_gate.OPEN')
    return _os.path.isfile(marker)


def assert_post_allowed() -> None:
    if not allow_post():
        raise RuntimeError(
            'Command posting DISABLED (CLAUSEWITZ_ALLOW_POST gate + checklist). Read-only only.'
        )
