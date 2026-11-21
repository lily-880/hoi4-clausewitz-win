# -*- coding: utf-8 -*-
"""Read-only repo scan: remaining-field evidence, NewFront clips, path +0x70 writers, type-2 names."""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
OUT = ROOT / "research" / "t197_evidence_index.json"

KEYWORDS = [
    r"vertex_province",
    r"OI_PATH",
    r"\+0x70",
    r"0x10b0d90",
    r"COrderNewFront",
    r"COrderSetPath",
    r"ORDER_DEFENSIVE_LINE",
    r"ORDER_OFFENSIVE_LINE",
    r"ORDER_FALLBACK",
    r"GetOrderType",
    r"axis_province",
    r"plans\.status",
    r"order\.type",
    r"order\.eta",
    r"in_supply",
    r"in_combat",
    r"combat_id",
    r"already_spotted",
    r"visibility\.spotted",
    r"front_invalidated",
    r"front_cannot_hold",
    r"missing_divisions",
    r"shortages\.manpower",
    r"shortages\.equipment",
    r"world\.crises",
    r"world\.visible_units",
    r"assigned_to",
    r"CSetArmyLeader",
    r"CCreateUnitLeader",
    r"wars\.start",
]

INTERESTING_FILES = []


def iter_files():
    for root in (ROOT / "calling", ROOT / "research"):
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.suffix.lower() not in {".py", ".md", ".json", ".txt"}:
                continue
            if p.stat().st_size > 4_000_000:
                continue
            yield p


def main():
    hits = {k: [] for k in KEYWORDS}
    # also collect clip filenames related to newfront / setpath / execute / type
    clips = []
    triage = {}
    for p in iter_files():
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        low = text
        if any(s in p.name.lower() for s in ("newfront", "setpath", "getordertype", "type2", "t194", "t190_unverified", "t188")):
            if p.suffix in {".txt", ".json", ".md"} and p.stat().st_size < 500_000:
                clips.append(rel)
        for kw in KEYWORDS:
            if re.search(kw, low):
                # grab a short snippet for high-value files
                if len(hits[kw]) < 12:
                    hits[kw].append(rel)

    # extract t190 triage if present
    for name in (
        "research/t190_unverified_triage.json",
        "research/t190_unverified_fields.json",
        "research/t190_inventory_sha256.json",
    ):
        p = ROOT / name
        if p.exists() and p.suffix == ".json":
            try:
                triage[name] = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                triage[name] = {"error": str(e)}

    # inventory unverified notes
    inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
    rows = []
    if inv.exists():
        for ln in inv.read_text(encoding="utf-8").splitlines():
            if ln.startswith("| ") and "未验证" in ln:
                parts = [x.strip() for x in ln.strip("|").split("|")]
                if len(parts) >= 3:
                    rows.append({"name": parts[0], "note": parts[2]})

    out = {
        "hits": hits,
        "related_files_sample": sorted(set(clips))[:80],
        "inventory_unverified": rows,
        "triage_keys": {k: list(v)[:30] if isinstance(v, dict) else type(v).__name__ for k, v in triage.items()},
    }
    # shrink triage to useful field entries if structure known
    useful = {}
    for name, obj in triage.items():
        if not isinstance(obj, dict):
            continue
        # keep if looks like field map
        useful[name] = obj
    out["triage"] = useful

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    # compact stdout: inventory notes + top files per key for the work items
    compact = {
        "inventory_unverified": rows,
        "path_files": hits.get(r"OI_PATH", []) + hits.get(r"0x10b0d90", []) + hits.get(r"COrderNewFront", []),
        "type_files": hits.get(r"ORDER_DEFENSIVE_LINE", []) + hits.get(r"GetOrderType", []),
        "axis_files": hits.get(r"axis_province", []),
        "order_files": hits.get(r"order\.type", []) + hits.get(r"order\.eta", []),
        "supply_files": hits.get(r"in_supply", []),
        "combat_files": hits.get(r"in_combat", []) + hits.get(r"combat_id", []),
        "visible_files": hits.get(r"world\.visible_units", []) + hits.get(r"visibility\.spotted", []),
        "shortage_files": hits.get(r"shortages\.manpower", []) + hits.get(r"front_cannot_hold", []) + hits.get(r"missing_divisions", []),
        "crisis_files": hits.get(r"world\.crises", []),
        "war_files": hits.get(r"front_invalidated", []) + hits.get(r"wars\.start", []),
        "leader_files": hits.get(r"assigned_to", []) + hits.get(r"CSetArmyLeader", []),
        "related_files_sample": out["related_files_sample"],
        "triage_top_keys": {k: (list(v.keys())[:25] if isinstance(v, dict) else type(v).__name__) for k, v in useful.items()},
    }
    print(json.dumps(compact, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
