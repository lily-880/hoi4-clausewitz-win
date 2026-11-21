# -*- coding: utf-8 -*-
from __future__ import annotations
import json, re
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
OUT = ROOT / "research" / "t197_key_extracts.json"


def read(rel, maxn=200000):
    p = ROOT / rel
    if not p.exists():
        return None
    t = p.read_text(encoding="utf-8", errors="ignore")
    return t if len(t) <= maxn else t[:maxn] + "\n...[truncated]..."


def windows(text, pats, radius=350, limit=4):
    if not text:
        return []
    out = []
    for pat in pats:
        for m in re.finditer(pat, text, re.I):
            a = max(0, m.start() - radius)
            b = min(len(text), m.end() + radius)
            out.append({"pat": pat, "at": m.start(), "text": text[a:b]})
            if len(out) >= limit:
                return out
    return out


def main():
    ev = {}

    # t190 triage: conclusion + per-field if not huge
    triage_path = ROOT / "research/t190_unverified_triage.json"
    triage = json.loads(triage_path.read_text(encoding="utf-8"))
    ev["t190_conclusion"] = triage.get("conclusion")
    ev["t190_not_memory"] = triage.get("not_memory")
    ev["t190_blocked"] = triage.get("blocked_or_boundary")
    ev["t190_pursuable"] = triage.get("independently_pursuable_on_this_snapshot")
    # unverified field entries: keep only remaining ones, shrink
    remaining = {
        "world.plans.type", "world.plans.vertex_province_ids", "world.plans.axis_province_ids",
        "world.plans.status", "world.own_units.order.type", "world.own_units.order.target_province_ids",
        "world.own_units.order.eta", "world.own_units.supply.in_supply", "world.own_units.supply.ratio",
        "world.own_units.supply.isolated", "world.own_units.in_combat", "world.own_units.combat_id",
        "world.visible_units", "world.visible_units.relation_to_player",
        "world.visible_units.visibility.spotted", "world.visible_units.visibility.confidence",
        "world.combats.combat_id", "world.crises.kind", "world.wars.front_invalidated",
        "world.shortages.equipment.demanded", "world.shortages.manpower.needed",
        "world.shortages.manpower.front_cannot_hold", "world.shortages.missing_divisions",
    }
    uv = triage.get("unverified") or {}
    slim = {}
    if isinstance(uv, dict):
        for k, v in uv.items():
            if k in remaining or k.startswith("world.combats") or k.startswith("world.crises") or k.startswith("world.shortages") or k.startswith("world.visible") or k.startswith("world.own_units") or k.startswith("world.plans") or k.startswith("world.wars"):
                if isinstance(v, dict):
                    slim[k] = {ik: (str(iv)[:400] if not isinstance(iv, (dict, list)) else iv) for ik, iv in list(v.items())[:12]}
                else:
                    slim[k] = v
    elif isinstance(uv, list):
        ev["t190_unverified_list_len"] = len(uv)
        ev["t190_unverified_sample"] = uv[:5]
    ev["t190_unverified_slim"] = slim

    # NewFront execute / isvalid clips: look for path copy, 0x70, 0x10b0d90
    for rel in [
        "research/_t194_clip_COrderNewFrontCommand_execute_0x18d9070.txt",
        "research/_t194_clip_COrderNewFrontCommand_isvalid_0x18df550.txt",
        "research/_t194_clip_COrderSetPathCommand_isvalid_0x18dff70.txt",
        "research/_t194_clip_COrderSetPathCommand_execute_0x18daf60.txt",
        "research/t194_bind_cmds.json",
        "research/t193_bind_newfront.json",
        "research/t194_type_jump.json",
        "research/t188_plan_writers.json",
    ]:
        text = read(rel)
        ev[rel] = {
            "exists": text is not None,
            "len": len(text or ""),
            "windows": windows(text or "", [
                r"0x70", r"0x10b0d90", r"path", r"0x50", r"0x258", r"380896",
                r"ORDER_", r"type 2", r"0x224", r"0x90", r"axis", r"status",
                r"scheduled_member", r"Attach", r"c402a0", r"new instance",
            ], radius=280, limit=8),
        }
        if rel.endswith(".json") and text:
            try:
                ev[rel]["json_keys"] = list(json.loads(Path(ROOT, rel).read_text(encoding="utf-8")).keys())[:40]
            except Exception:
                pass

    # dump first 80 lines of NewFront execute (most important)
    nf = ROOT / "research/_t194_clip_COrderNewFrontCommand_execute_0x18d9070.txt"
    if nf.exists():
        ev["newfront_execute_head"] = "\n".join(nf.read_text(encoding="utf-8", errors="ignore").splitlines()[:120])
        ev["newfront_execute_all_if_short"] = nf.read_text(encoding="utf-8", errors="ignore") if nf.stat().st_size < 40000 else None
    nfi = ROOT / "research/_t194_clip_COrderNewFrontCommand_isvalid_0x18df550.txt"
    if nfi.exists() and nfi.stat().st_size < 30000:
        ev["newfront_isvalid_full"] = nfi.read_text(encoding="utf-8", errors="ignore")

    OUT.write_text(json.dumps(ev, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

    # compact print
    compact = {
        "t190_conclusion": ev.get("t190_conclusion"),
        "t190_not_memory": ev.get("t190_not_memory"),
        "t190_blocked_keys": list(ev["t190_blocked"].keys()) if isinstance(ev.get("t190_blocked"), dict) else ev.get("t190_blocked"),
        "t190_pursuable": ev.get("t190_pursuable"),
        "t190_unverified_fields": list((ev.get("t190_unverified_slim") or {}).keys()),
        "newfront_execute_head": ev.get("newfront_execute_head"),
        "newfront_isvalid_len": len(ev.get("newfront_isvalid_full") or ""),
    }
    # print slim field one-liners
    slim_out = {}
    for k, v in (ev.get("t190_unverified_slim") or {}).items():
        if isinstance(v, dict):
            # prefer status/reason/offset/note keys
            bits = []
            for ik in v:
                bits.append(f"{ik}={str(v[ik])[:160]}")
            slim_out[k] = " | ".join(bits)[:400]
        else:
            slim_out[k] = str(v)[:300]
    compact["field_notes"] = slim_out
    print(json.dumps(compact, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
