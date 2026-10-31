#!/usr/bin/env python3
"""Checks for the natural-language console translator."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "calling"))
import nl_console

CASES = [
    ("瞬间建造", "ic"),
    ("给自己500政治点", "pp 500"),
    ("100万人力", "manpower 1000000"),
    ("切换到德国", "tag GER"),
    ("吞并立陶宛", "annex LIT"),
    ("和苏联白和", "wp SOV"),
    ("传送到 758", "tp 758"),
    ("战争迷雾", "fow"),
    ("省份提示", "tdebug"),
    ("观察者", "observe"),
    ("外交全接受", "yesman"),
    ("研究全部", "research all"),
    ("把 10 州给波兰", "setowner POL 10"),
    ("指挥点 250", "cp 250"),
    ("三军经验 80", "xp 80"),
    ("fa", "fa"),
    ("自由国策", "ff"),
    ("ae 1000 infantry_equipment", "ae 1000 infantry_equipment"),
]


def main() -> int:
    failed = 0
    for text, expect in CASES:
        got = nl_console.translate(text)
        if got["line"] != expect:
            print(f"FAIL {text!r}\n  expect {expect}\n  got    {got['line']}\n  {got['detail']}")
            failed += 1
        else:
            print(f"ok   {text} -> {got['line']}")
    if failed:
        print(f"{failed} failed")
        return 1
    print(f"{len(CASES)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
