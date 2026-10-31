#!/usr/bin/env python3
"""Build calling/console_commands.json from the installed HOI4 1.19 command doc."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = Path(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\documentation\console_commands_documentation.md")
OUT = ROOT / "calling" / "console_commands.json"
SKIP = {
    "Console Commands",
    "Table of Content",
    "All Console Commands",
    "All Tweakable Variables",
}


def parse(text: str) -> list[dict]:
    section = "command"
    current = None
    rows = []

    def flush():
        nonlocal current
        if not current:
            return
        current["description"] = " ".join(current["description"]).strip()
        rows.append(current)
        current = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            title = line[3:].strip()
            if title == "All Tweakable Variables":
                flush()
                section = "tweak"
                continue
            if title in SKIP:
                flush()
                continue
            flush()
            current = {
                "name": title,
                "section": section,
                "aliases": [],
                "arguments": "",
                "description": [],
                "in_release": True,
                "type": "",
            }
            continue
        if current is None:
            continue
        if line.startswith("* Aliases:"):
            current["aliases"] = [p.strip() for p in line.split(":", 1)[1].split(",") if p.strip()]
        elif line.startswith("* Arguments:"):
            current["arguments"] = line.split(":", 1)[1].strip()
        elif line.startswith("* Type:"):
            current["type"] = line.split(":", 1)[1].strip()
        elif line.startswith("* Not available"):
            current["in_release"] = False
        elif line.startswith("*"):
            continue
        elif line.strip() and not line.startswith("#") and not line.startswith("```"):
            current["description"].append(line.strip().strip('"'))
    flush()
    return rows


def main() -> int:
    if not DOC.is_file():
        print("missing", DOC, file=sys.stderr)
        return 2
    rows = parse(DOC.read_text(encoding="utf-8"))
    OUT.write_text(
        json.dumps(
            {
                "source": "Hearts of Iron IV/documentation/console_commands_documentation.md",
                "game": "1.19.4",
                "commands": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} commands to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
