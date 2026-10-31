#!/usr/bin/env python3
"""Phase 2fl: deepen NewFallback / ReplaceFallback / ArmyGroupFallback fields beyond +0x54.

RO only — Capstone field-map from Serialize/Deserialize/IsValid/Execute/Clone.
No Post. No tool-gate. allow_post stays False. NEVER 5x.
"""
from __future__ import annotations

import json
import re
import struct
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import cmd_layout
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2fl_newfallback_fields.json"
SUMMARY = ROOT / "reports" / "phase2fl_summary.json"
DOC = ROOT / "docs" / "PHASE2FL_NEWFALLBACK_FIELDS.md"
PARENT_SHA = "24ac836"
GS_HOURS = 0x484

TARGETS = {
    "COrderNewFallbackCommand": cmd_layout.ORDERS["COrderNewFallbackCommand"],
    "COrderReplaceFallbackCommands": {
        "vt": cmd_layout.ORDER_REPLACE_FALLBACK["vt"],
        "size": cmd_layout.ORDER_REPLACE_FALLBACK["size"],
        "factory": cmd_layout.ORDER_REPLACE_FALLBACK["factory"],
        "clone": cmd_layout.ORDER_REPLACE_FALLBACK["clone"],
        "serialize": cmd_layout.ORDER_REPLACE_FALLBACK["serialize"],
        "deserialize": cmd_layout.ORDER_REPLACE_FALLBACK["deserialize"],
        "execute": cmd_layout.ORDER_REPLACE_FALLBACK["execute"],
        "isvalid": cmd_layout.ORDER_REPLACE_FALLBACK["isvalid"],
        "type_id": cmd_layout.ORDER_REPLACE_FALLBACK["type_id"],
        "factory_idx": cmd_layout.ORDER_REPLACE_FALLBACK["factory_idx"],
    },
    "CSetSelectedArmyGroupFallback": {
        "vt": cmd_layout.ARMY_GROUP_FALLBACK["vt"],
        "size": cmd_layout.ARMY_GROUP_FALLBACK["size"],
        "factory": cmd_layout.ARMY_GROUP_FALLBACK["factory"],
        "clone": cmd_layout.ARMY_GROUP_FALLBACK["clone"],
        "serialize": cmd_layout.ARMY_GROUP_FALLBACK["serialize"],
        "deserialize": cmd_layout.ARMY_GROUP_FALLBACK["deserialize"],
        "execute": cmd_layout.ARMY_GROUP_FALLBACK["execute"],
        "isvalid": cmd_layout.ARMY_GROUP_FALLBACK["isvalid"],
        "type_id": cmd_layout.ARMY_GROUP_FALLBACK["type_id"],
        "factory_idx": cmd_layout.ARMY_GROUP_FALLBACK["factory_idx"],
    },
}

# Also disasm NewFront for sibling pattern (same order family, richer fields)
SIBLING = {
    "COrderNewFrontCommand": cmd_layout.ORDERS["COrderNewFrontCommand"],
}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def live_meta(b, base, pid):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + GS_HOURS)
    d = datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(hours))
    return {
        "pid": pid,
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never change speed)",
        "scenario": "ITA@1x NewFallback subject field deepen (no Post)",
        "cmdline_expect": "-gdpr-compliant -start_tag=ITA -start_speed=1",
    }


def disasm_fn(md, b, base, rva, n=0x280, max_insn=160):
    raw = b.read(base + rva, n)
    lines = []
    for insn in md.disasm(raw, base + rva):
        lines.append({
            "rva": hex(insn.address - base),
            "mnem": insn.mnemonic,
            "op": insn.op_str,
            "bytes": insn.bytes.hex(),
        })
        if insn.mnemonic == "ret" and len(lines) > 4:
            break
        if len(lines) >= max_insn:
            break
    return lines


# Match [reg + disp] / [reg + disp*scale + disp] memory ops; collect disp in subject range
MEM_RE = re.compile(
    r"\[(r(?:ax|bx|cx|dx|si|di|bp|8|9|10|11|12|13|14|15)|e(?:ax|bx|cx|dx|si|di|bp))"
    r"(?:\s*\+\s*(?:r(?:ax|bx|cx|dx|si|di|bp|8|9|10|11|12|13|14|15)\*?[1248]?))?"
    r"(?:\s*\+\s*(0x[0-9a-f]+|\d+))?\]",
    re.I,
)
DISP_ONLY = re.compile(
    r"\[(r(?:ax|bx|cx|dx|si|di|bp|8|9|10|11|12|13|14|15))"
    r"\s*\+\s*(0x[0-9a-f]+)\]",
    re.I,
)
BYTE_DISP = re.compile(
    r"(?:byte|word|dword|qword)\s+ptr\s+\[(r(?:ax|bx|cx|dx|si|di|bp|8|9|10|11|12|13|14|15))"
    r"\s*\+\s*(0x[0-9a-f]+)\]",
    re.I,
)


def extract_field_disps(lines, size: int, this_regs=("rcx", "rbx", "rdi", "rsi", "r12", "r13", "r14", "r15")):
    """Collect displacements likely referring into the command object (0x08..size)."""
    hits = defaultdict(list)
    imm_tags = []
    for ln in lines:
        op = ln["op"]
        mnem = ln["mnem"]
        # serialize token immediates (mov edx, imm / mov r8d, imm) common in Paradox ser
        if mnem.startswith("mov") and re.search(r"\b(0x[0-9a-f]{3,4})\b", op, re.I):
            for m in re.finditer(r"\b(0x[0-9a-f]{3,4})\b", op, re.I):
                v = int(m.group(1), 16)
                if 0x100 <= v <= 0x7FFF:
                    imm_tags.append({"rva": ln["rva"], "imm": hex(v), "op": op, "mnem": mnem})
        for rx in (DISP_ONLY, BYTE_DISP):
            for m in rx.finditer(op):
                reg = m.group(1).lower()
                disp = int(m.group(2), 16)
                if reg in this_regs and 0x08 <= disp < max(size + 0x20, 0x80):
                    hits[disp].append({
                        "rva": ln["rva"],
                        "mnem": mnem,
                        "op": op,
                        "reg": reg,
                    })
    # collapse
    fields = []
    for disp in sorted(hits):
        refs = hits[disp]
        kinds = sorted({r["mnem"] for r in refs})
        fields.append({
            "off": disp,
            "off_hex": hex(disp),
            "ref_count": len(refs),
            "mnems": kinds,
            "sample_refs": refs[:6],
            "in_object": disp < size,
        })
    return fields, imm_tags[:40]


def classify_disp(disp: int, known_front: dict) -> str:
    """Heuristic label from sibling NewFront + common order layout — NOT invent of semantics."""
    # Known NewFront fields for comparison only
    front_inv = {v: k for k, v in (known_front or {}).items()}
    if disp in front_inv:
        return f"sibling_NewFront.{front_inv[disp]}"
    if disp == 0x54:
        return "fallback_flag_or_id (IsValid-proven 2fi)"
    if disp == 0x28:
        return "subject_slot_a_candidate (handle/vec/ptr family)"
    if disp == 0x30:
        return "subject_slot_b_candidate"
    if disp == 0x38:
        return "subject_slot_c_candidate"
    if disp == 0x40:
        return "subject_slot_d_candidate"
    if disp == 0x48:
        return "subject_slot_e_candidate"
    if disp == 0x50:
        return "subject_slot_f_candidate"
    return "unlabeled"


def analyze_target(md, b, base, name, meta, sibling_fields=None):
    size = meta.get("size") or 0x60
    fns = {
        "serialize": meta.get("serialize"),
        "deserialize": meta.get("deserialize"),
        "isvalid": meta.get("isvalid"),
        "execute": meta.get("execute"),
        "clone": meta.get("clone"),
    }
    out = {
        "name": name,
        "size": size,
        "size_hex": hex(size),
        "vt": hex(meta["vt"]),
        "type_id": hex(meta.get("type_id") or 0),
        "factory": hex(meta.get("factory") or 0),
        "fns": {k: hex(v) if v else None for k, v in fns.items()},
        "per_fn": {},
        "union_disps_in_object": [],
        "proven_fields": {},
        "candidate_fields": {},
    }
    union = {}
    all_tags = []
    for kind, rva in fns.items():
        if not rva:
            continue
        lines = disasm_fn(md, b, base, rva)
        fields, tags = extract_field_disps(lines, size)
        out["per_fn"][kind] = {
            "rva": hex(rva),
            "insn_count": len(lines),
            "disasm_head": [f"{x['rva']}: {x['mnem']} {x['op']}" for x in lines[:24]],
            "disasm_tail": [f"{x['rva']}: {x['mnem']} {x['op']}" for x in lines[-8:]],
            "field_disps": fields,
            "ser_imm_tags": tags[:20],
        }
        all_tags.extend(tags)
        for f in fields:
            if f["in_object"]:
                union.setdefault(f["off"], {"off": f["off"], "off_hex": f["off_hex"], "seen_in": [], "mnems": set()})
                union[f["off"]]["seen_in"].append(kind)
                union[f["off"]]["mnems"].update(f["mnems"])

    for off, u in sorted(union.items()):
        entry = {
            "off": off,
            "off_hex": hex(off),
            "seen_in": u["seen_in"],
            "mnems": sorted(u["mnems"]),
            "label_hint": classify_disp(off, sibling_fields or {}),
        }
        out["union_disps_in_object"].append(entry)
        # Proven: already known OR appears in isvalid+serialize/deserialize
        if off == 0x54 or (
            "isvalid" in u["seen_in"]
            and ("serialize" in u["seen_in"] or "deserialize" in u["seen_in"])
        ):
            out["proven_fields"][hex(off)] = entry
        elif len(u["seen_in"]) >= 2 or "serialize" in u["seen_in"] or "deserialize" in u["seen_in"]:
            out["candidate_fields"][hex(off)] = entry

    # unique ser tags
    tag_counts = defaultdict(int)
    for t in all_tags:
        tag_counts[t["imm"]] += 1
    out["ser_imm_tag_histogram"] = dict(sorted(tag_counts.items(), key=lambda x: -x[1])[:24])
    return out


def apply_catalog_updates(analysis: dict) -> dict:
    """Return catalog field maps to write — only proven (+ strong multi-fn ser/deser). No invent names."""
    updates = {}
    nf = analysis["targets"]["COrderNewFallbackCommand"]
    rf = analysis["targets"]["COrderReplaceFallbackCommands"]
    ag = analysis["targets"]["CSetSelectedArmyGroupFallback"]

    def build_fields(obj, prior_known):
        fields = dict(prior_known)
        # keep proven 0x54
        fields.setdefault("fallback_flag_or_id", 0x54)
        # add other proven/candidate with neutral names by offset
        for hex_off, entry in {**obj.get("proven_fields", {}), **obj.get("candidate_fields", {})}.items():
            off = entry["off"]
            if off == 0x54:
                continue
            # Prefer sibling-aligned names when NewFront has same off AND ser/deser saw it
            hint = entry.get("label_hint") or ""
            if hint.startswith("sibling_NewFront."):
                name = hint.split(".", 1)[1]
                # only adopt if seen in serialize or deserialize (not execute-only)
                if "serialize" in entry["seen_in"] or "deserialize" in entry["seen_in"]:
                    fields[name] = off
                else:
                    fields[f"off_{hex_off}"] = off
            else:
                # neutral catalog key — semantics TBD
                if "serialize" in entry["seen_in"] or "deserialize" in entry["seen_in"] or "isvalid" in entry["seen_in"]:
                    fields[f"off_{hex_off}"] = off
        return fields

    # NewFallback prior
    updates["ORDERS.COrderNewFallbackCommand"] = build_fields(
        nf, {"fallback_flag_or_id": 0x54}
    )
    updates["ORDER_REPLACE_FALLBACK"] = build_fields(
        rf, {"fallback_flag_or_id": 0x54}
    )
    # Army group: already has +0x28/+0x30; deepen if more
    ag_fields = {"army_group": 0x28, "fallback_flag": 0x30}
    for hex_off, entry in {**ag.get("proven_fields", {}), **ag.get("candidate_fields", {})}.items():
        off = entry["off"]
        if off in (0x28, 0x30):
            continue
        if "serialize" in entry["seen_in"] or "deserialize" in entry["seen_in"] or "isvalid" in entry["seen_in"]:
            ag_fields[f"off_{hex_off}"] = off
    updates["ARMY_GROUP_FALLBACK"] = ag_fields
    return updates


def patch_cmd_layout(updates: dict) -> list[str]:
    """Patch first-class field maps in cmd_layout.py. Returns change notes."""
    path = ROOT / "calling" / "cmd_layout.py"
    text = path.read_text(encoding="utf-8")
    notes = []

    # ORDERS NewFallback fields block
    nf_fields = updates["ORDERS.COrderNewFallbackCommand"]
    nf_block = (
        '        # Phase 2fl: deepen beyond +0x54 from ser/deser/isvalid/execute disasm (no invent)\n'
        f'        "fields": {json.dumps(nf_fields)},\n'
        '        "fields_note": "2fl: offs from Capstone mem-disp union; fallback_flag_or_id@+0x54 IsValid-proven; '
        'other off_* are ser/deser/isvalid-referenced slots — semantics TBD, posting DISABLED",\n'
    )
    old_nf = re.search(
        r'    "COrderNewFallbackCommand": \{.*?"fields_note": "[^"]*",\n',
        text,
        re.S,
    )
    if not old_nf:
        # try narrower replace of fields + fields_note only inside NewFallback
        pat = re.compile(
            r'(    "COrderNewFallbackCommand": \{.*?)'
            r'(        # Phase 2fi field polish.*?\n)?'
            r'(        "fields": \{[^}]*\},?\n)'
            r'(        "fields_note": "[^"]*",\n)?',
            re.S,
        )
        m = pat.search(text)
        if not m:
            notes.append("WARN: could not locate ORDERS.COrderNewFallbackCommand fields block")
        else:
            text = pat.sub(m.group(1) + nf_block, text, count=1)
            notes.append(f"patched ORDERS.COrderNewFallbackCommand fields={nf_fields}")
    else:
        # fallback: replace fields dict for NewFallback specifically
        pat = re.compile(
            r'(    "COrderNewFallbackCommand": \{.*?)'
            r'(        # Phase 2fi field polish[^\n]*\n)?'
            r'        "fields": \{[^}]*\},\n'
            r'(        "fields_note": "[^"]*",\n)?',
            re.S,
        )
        text2, n = pat.subn(r"\1" + nf_block, text, count=1)
        if n:
            text = text2
            notes.append(f"patched ORDERS.COrderNewFallbackCommand fields={nf_fields}")
        else:
            notes.append("WARN: NewFallback fields patch failed")

    # ORDER_REPLACE_FALLBACK
    rf_fields = updates["ORDER_REPLACE_FALLBACK"]
    rf_block = (
        '    "fields": '
        + json.dumps(rf_fields)
        + ',\n'
        '    "fields_note": "2fl: shared ser/deser/isvalid w/ NewFallback; offs from Capstone; posting DISABLED",\n'
    )
    pat_rf = re.compile(
        r'(ORDER_REPLACE_FALLBACK = \{.*?)'
        r'    "fields": \{[^}]*\},\n'
        r'(    "fields_note": "[^"]*",\n)?',
        re.S,
    )
    text2, n = pat_rf.subn(r"\1" + rf_block, text, count=1)
    if n:
        text = text2
        notes.append(f"patched ORDER_REPLACE_FALLBACK fields={rf_fields}")
    else:
        notes.append("WARN: ORDER_REPLACE_FALLBACK patch failed")

    # ARMY_GROUP_FALLBACK
    ag_fields = updates["ARMY_GROUP_FALLBACK"]
    # keep named keys for known; format nicely
    ag_lit = "{\n"
    for k, v in ag_fields.items():
        if k == "army_group":
            ag_lit += f'        "army_group": {hex(v)},  # army_subjects.army_group_fallback_recipe\n'
        elif k == "fallback_flag":
            ag_lit += f'        "fallback_flag": {hex(v)},\n'
        else:
            ag_lit += f'        "{k}": {hex(v)},  # 2fl Capstone\n'
    ag_lit += "    }"
    pat_ag = re.compile(
        r'(ARMY_GROUP_FALLBACK = \{.*?)"fields": \{[^}]*\}',
        re.S,
    )
    text2, n = pat_ag.subn(r'\1"fields": ' + ag_lit, text, count=1)
    if n:
        text = text2
        notes.append(f"patched ARMY_GROUP_FALLBACK fields={ag_fields}")
    else:
        notes.append("WARN: ARMY_GROUP_FALLBACK patch failed")

    path.write_text(text, encoding="utf-8")
    return notes


def patch_army_subjects(updates: dict) -> list[str]:
    path = ROOT / "calling" / "army_subjects.py"
    text = path.read_text(encoding="utf-8")
    notes = []
    nf = updates["ORDERS.COrderNewFallbackCommand"]
    # rebuild fallback_order_recipe body with all offs
    lines = [
        'def fallback_order_recipe(fallback_flag_or_id: int = 1) -> dict[str, Any]:',
        '    """COrderNewFallbackCommand / COrderReplaceFallbackCommands — RO docs only."""',
        '    return {',
        '        "fallback_flag_or_id_off": 0x54,',
        '        "fallback_flag_or_id": fallback_flag_or_id,',
    ]
    for k, v in nf.items():
        if k == "fallback_flag_or_id":
            continue
        lines.append(f'        "{k}_off": {hex(v)},  # 2fl Capstone — semantics TBD')
    lines += [
        '        "note": "2fl: +0x54 IsValid-proven; other offs from ser/deser/isvalid mem-disp; '
        'battle-plan subject semantics TBD; posting DISABLED",',
        '        "posting": "DISABLED",',
        '    }',
        '',
    ]
    new_fn = "\n".join(lines)
    pat = re.compile(
        r"def fallback_order_recipe\(fallback_flag_or_id: int = 1\) -> dict\[str, Any\]:.*?"
        r"(?=\ndef )",
        re.S,
    )
    text2, n = pat.subn(new_fn + "\n\n", text, count=1)
    if n:
        path.write_text(text2, encoding="utf-8")
        notes.append("patched army_subjects.fallback_order_recipe")
    else:
        notes.append("WARN: fallback_order_recipe patch failed")
    return notes


def main():
    assert allow_post() is False, "allow_post must stay False"
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64

    pid = find_pid()
    assert pid, "hoi4 not running"
    b = Backend(pid)
    base = int(b.image_base)
    live = live_meta(b, base, pid)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = False

    sibling_fields = dict(cmd_layout.ORDERS["COrderNewFrontCommand"].get("fields") or {})
    sibling_analysis = analyze_target(
        md, b, base, "COrderNewFrontCommand", SIBLING["COrderNewFrontCommand"], sibling_fields
    )

    targets = {}
    for name, meta in TARGETS.items():
        targets[name] = analyze_target(md, b, base, name, meta, sibling_fields)

    # Shared-fn sanity: NewFallback and ReplaceFallback share ser/deser/isvalid
    shared_ok = (
        targets["COrderNewFallbackCommand"]["fns"]["serialize"]
        == targets["COrderReplaceFallbackCommands"]["fns"]["serialize"]
        and targets["COrderNewFallbackCommand"]["fns"]["isvalid"]
        == targets["COrderReplaceFallbackCommands"]["fns"]["isvalid"]
    )

    analysis = {
        "phase": "2fl",
        "allow_post": False,
        "tool_gate": "CLOSED",
        "never_5x": True,
        "executed_2fb_recipe": False,
        "live": live,
        "shared_ser_deser_isvalid_new_vs_replace": shared_ok,
        "sibling_NewFront": {
            "fields_doc": sibling_fields,
            "union_disps_in_object": sibling_analysis["union_disps_in_object"],
            "ser_imm_tag_histogram": sibling_analysis["ser_imm_tag_histogram"],
        },
        "targets": targets,
        "parent_sha_base": PARENT_SHA,
    }

    updates = apply_catalog_updates(analysis)
    analysis["catalog_field_updates"] = updates

    # Apply patches to repo sources (on PC copy; we'll sync back)
    notes = []
    notes += patch_cmd_layout(updates)
    notes += patch_army_subjects(updates)
    analysis["patch_notes"] = notes

    # Determine result quality
    nf_new = {k: v for k, v in updates["ORDERS.COrderNewFallbackCommand"].items() if k != "fallback_flag_or_id"}
    if nf_new:
        result = "NEWFALLBACK_FIELDS_DEEPENED"
    else:
        # still document union even if only 0x54
        result = "NEWFALLBACK_FIELDS_CEILING_ONLY_0x54"

    works = [
        "Capstone disasm NewFallback/ReplaceFallback/ArmyGroupFallback ser+deser+isvalid+execute+clone",
        f"shared ser/deser/isvalid New↔Replace confirmed={shared_ok}",
        f"NewFallback fields now {updates['ORDERS.COrderNewFallbackCommand']}",
        f"ORDER_REPLACE_FALLBACK fields now {updates['ORDER_REPLACE_FALLBACK']}",
        f"ARMY_GROUP_FALLBACK fields now {updates['ARMY_GROUP_FALLBACK']}",
        "allow_post stays False; recipe not executed; never 5x",
    ]
    stubbed = [
        "in-process ring embed",
        "2fb recipe execution",
        "ordinary CMove live leaf",
        "SAFE_POST / ALLOW_POST",
        "self-MOVE",
        "tool-gate open",
        "Post inject",
        "path-vector nonempty",
        "NewFallback subject semantic labels beyond offset map (off_* TBD)",
        "live midflight NewFallback hex capture",
    ]
    if result == "NEWFALLBACK_FIELDS_DEEPENED":
        next_blocker = (
            "NON-Post: label off_* NewFallback slots via ser token/RTTI or live midflight hex; "
            "or Assign/Unassign edge deepen; still NO ALLOW_POST"
        )
    else:
        next_blocker = (
            "NON-Post: NewFallback Capstone only reconfirmed +0x54 — next: Assign/Unassign edge deepen "
            "or ser-token name recovery; still NO ALLOW_POST"
        )

    analysis["result"] = result
    analysis["works"] = works
    analysis["stubbed"] = stubbed
    analysis["next_shortest_blocker"] = next_blocker
    analysis["ts"] = datetime.now(timezone.utc).isoformat()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2fl",
                "result": result,
                "scenario": live["scenario"],
                "allow_post": False,
                "tool_gate": "CLOSED",
                "pid": live["pid"],
                "ui_date": live["ui_date"],
                "hours": live["hours"],
                "newfallback_fields": updates["ORDERS.COrderNewFallbackCommand"],
                "replace_fallback_fields": updates["ORDER_REPLACE_FALLBACK"],
                "army_group_fallback_fields": updates["ARMY_GROUP_FALLBACK"],
                "shared_ser_deser_isvalid": shared_ok,
                "works": works,
                "stubbed": stubbed,
                "next_shortest_blocker": next_blocker,
                "patch_notes": notes,
                "parent_sha_base": PARENT_SHA,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Doc
    lines = [
        "# Phase 2fl — NewFallback subject fields beyond +0x54",
        "",
        f"**Result:** `{result}`  ",
        f"**Base:** `{PARENT_SHA}` (2fk) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed",
        "",
        "## Method",
        "",
        "Live Capstone on ITA@1x: Serialize / Deserialize / IsValid / Execute / Clone mem-disp union "
        "for `COrderNewFallbackCommand`, `COrderReplaceFallbackCommands` (shared ser/deser/isvalid), "
        "`CSetSelectedArmyGroupFallback`. Sibling `COrderNewFrontCommand` for pattern compare. "
        "**No invent** — unlabeled slots stay `off_0xNN`.",
        "",
        f"Shared New↔Replace ser/deser/isvalid: **{shared_ok}**",
        "",
        "## Field maps (after 2fl)",
        "",
        f"| layout | fields |",
        f"|--------|--------|",
        f"| `ORDERS.COrderNewFallbackCommand` | `{updates['ORDERS.COrderNewFallbackCommand']}` |",
        f"| `ORDER_REPLACE_FALLBACK` | `{updates['ORDER_REPLACE_FALLBACK']}` |",
        f"| `ARMY_GROUP_FALLBACK` | `{updates['ARMY_GROUP_FALLBACK']}` |",
        "",
        "### NewFallback union disps (in-object)",
        "",
    ]
    for e in targets["COrderNewFallbackCommand"]["union_disps_in_object"]:
        lines.append(
            f"- `{e['off_hex']}` seen_in={e['seen_in']} mnems={e['mnems']} · {e['label_hint']}"
        )
    lines += [
        "",
        "### ReplaceFallback union disps (in-object)",
        "",
    ]
    for e in targets["COrderReplaceFallbackCommands"]["union_disps_in_object"]:
        lines.append(
            f"- `{e['off_hex']}` seen_in={e['seen_in']} mnems={e['mnems']} · {e['label_hint']}"
        )
    lines += [
        "",
        "## Live",
        "",
        "```json",
        json.dumps(live, indent=2),
        "```",
        "",
        f"**Next shortest blocker (NON-Post):** {next_blocker}",
        "",
        "Script: `scripts/phase2fl_newfallback_fields.py`",
    ]
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "phase": "2fl",
        "result": result,
        "allow_post": False,
        "pid": live["pid"],
        "ui_date": live["ui_date"],
        "hours": live["hours"],
        "newfallback_fields": updates["ORDERS.COrderNewFallbackCommand"],
        "replace_fallback_fields": updates["ORDER_REPLACE_FALLBACK"],
        "army_group_fallback_fields": updates["ARMY_GROUP_FALLBACK"],
        "shared_ok": shared_ok,
        "patch_notes": notes,
        "next_shortest_blocker": next_blocker,
    }, indent=2))


if __name__ == "__main__":
    main()
