from pathlib import Path

# --- new helper ---
Path("calling/country_tags.py").write_text(r'''"""Map CCountry indices to three-letter tags.

HOI4 numbers countries in the same order as files under
common/country_tags (vanilla: 00_countries.txt then
zz_dynamic_countries.txt). Index 0 is unused. Live 2026-11-13
on 1.19.4 Windows: GS_COUNTRIES size 440 == 1 + 364 static + 75
dynamic; 15=SPR, 38=CHI, 44=ETH, 68=USA matched the running
process (including after console `tag`).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

_TAG_LINE = re.compile(r'^([A-Z0-9]{3})\s*=\s*"([^"]+)"')
_cache: Optional[List[Optional[str]]] = None
_cache_dir: Optional[str] = None


def _game_dir() -> Optional[Path]:
    try:
        import config
        raw = config.game_dir() if callable(getattr(config, "game_dir", None)) else getattr(config, "game_dir", None)
        if raw:
            p = Path(raw)
            if p.is_dir():
                return p
    except Exception:
        return None
    return None


def load_country_tag_table(game_dir: Optional[Path] = None, force: bool = False) -> List[Optional[str]]:
    """Return a list where table[index] is the three-letter tag, or None."""
    global _cache, _cache_dir
    root = Path(game_dir) if game_dir else _game_dir()
    key = str(root) if root else ""
    if not force and _cache is not None and _cache_dir == key:
        return _cache
    table: List[Optional[str]] = [None]  # index 0 unused
    if root:
        folder = root / "common" / "country_tags"
        if folder.is_dir():
            for path in sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".txt"):
                for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                    s = line.strip()
                    if not s or s.startswith("#") or re.match(r"dynamic_tags\s*=", s, re.I):
                        continue
                    m = _TAG_LINE.match(s)
                    if m:
                        table.append(m.group(1))
    _cache = table
    _cache_dir = key
    return table


def tag_for_index(index: Optional[int], game_dir: Optional[Path] = None) -> Optional[str]:
    if not isinstance(index, int) or index < 0:
        return None
    table = load_country_tag_table(game_dir)
    if index >= len(table):
        return None
    return table[index]
''', encoding="utf-8")

# --- hook into resolve_player_country ---
gs = Path("calling/gamestate.py")
text = gs.read_text(encoding="utf-8")
if "from country_tags import" not in text:
    old = "import offsets as O\n"
    new = "import offsets as O\nfrom country_tags import tag_for_index\n"
    if old not in text:
        raise SystemExit("import anchor not found")
    text = text.replace(old, new, 1)

old = '''        "legacy_gs_0x518": None,
        "observed_gs_0x520": None,
        "human_flag_indices": [],
        "reason": None,
'''
new = '''        "legacy_gs_0x518": None,
        "observed_gs_0x520": None,
        "human_flag_indices": [],
        "tag": None,
        "reason": None,
'''
if old not in text:
    raise SystemExit("out init anchor not found")
text = text.replace(old, new, 1)

old = '''    cptr = _u64_at(p, countries["data"] + out["player_index"] * 8)
    out["country_ptr"] = hex(cptr) if cptr else None
    if not cptr:
        out["ok"] = False
        out["reason"] = "null country"
    return out
'''
new = '''    cptr = _u64_at(p, countries["data"] + out["player_index"] * 8)
    out["country_ptr"] = hex(cptr) if cptr else None
    if not cptr:
        out["ok"] = False
        out["reason"] = "null country"
        return out
    out["tag"] = tag_for_index(out["player_index"])
    return out
'''
if old not in text:
    raise SystemExit("resolve return anchor not found")
text = text.replace(old, new, 1)

# also expose on probe_player_armies / campaign verified
# probe already copies player_resolve; add player_tag_letter next to player_tag
old = '''    tag = resolved.get("player_index")
    out["player_tag"] = tag
'''
new = '''    tag = resolved.get("player_index")
    out["player_tag"] = tag
    out["player_tag_letter"] = resolved.get("tag")
'''
if old not in text:
    raise SystemExit("probe player_tag anchor not found")
text = text.replace(old, new, 1)

old = '''        out["fields"]["player_tag_raw"] = tag
        out["verified"]["player_tag"] = tag
        out["verified"]["player_source"] = resolved.get("source")
'''
new = '''        out["fields"]["player_tag_raw"] = tag
        out["fields"]["player_tag_letter"] = resolved.get("tag")
        out["verified"]["player_tag"] = tag
        out["verified"]["player_tag_letter"] = resolved.get("tag")
        out["verified"]["player_source"] = resolved.get("source")
'''
if old not in text:
    raise SystemExit("campaign verified anchor not found")
text = text.replace(old, new, 1)

gs.write_text(text, encoding="utf-8")
import py_compile
py_compile.compile("calling/country_tags.py", doraise=True)
py_compile.compile("calling/gamestate.py", doraise=True)
print("patched ok")
