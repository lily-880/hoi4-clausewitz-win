#!/usr/bin/env python3
"""Correct 2fl NewFallback field map after NewFront ser bleed; patch catalogs + reports."""
from __future__ import annotations

import json
import re
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from config import allow_post
from process import Backend, find_pid

assert allow_post() is False

FIELDS = {
    "subject_handle": 0x28,
    "units_data": 0x30,
    "units_count": 0x3c,
    "provinces_data": 0x48,
    "fallback_flag_or_id": 0x54,
}
FIELDS_NOTE = (
    "2fl: Capstone on shared ser@0x18e8a60/deser@0x18e2500/isvalid@0x18df4b0 + NewFallback "
    "exec@0x18d8fc0; do NOT confuse with following NewFront ser@0x18e8af0 (int3-padded). "
    "units_end/cap between +0x30..+0x40 and provinces size/cap between +0x48..+0x50 TBD; "
    "posting DISABLED"
)
AG_FIELDS = {"army_group": 0x28, "fallback_flag": 0x30}

# --- cmd_layout ---
cl = ROOT / "calling" / "cmd_layout.py"
text = cl.read_text(encoding="utf-8")
nf_fields_lit = json.dumps(FIELDS)
nf_block = (
    "        # Phase 2fl: deepen beyond +0x54 from NewFallback ser/deser/isvalid/exec "
    "(no NewFront bleed)\n"
    f'        "fields": {nf_fields_lit},\n'
    f'        "fields_note": "{FIELDS_NOTE}",\n'
)
pat = re.compile(
    r'(    "COrderNewFallbackCommand": \{.*?)'
    r"(        # Phase 2f[il][^\n]*\n)?"
    r'        "fields": \{.*?\},\n'
    r'(        "fields_note": ".*?",\n)?',
    re.S,
)
text2, n = pat.subn(r"\1" + nf_block, text, count=1)
assert n == 1, f"NewFallback patch failed n={n}"
text = text2

rf_block = (
    f'    "fields": {nf_fields_lit},\n'
    f'    "fields_note": "{FIELDS_NOTE}",\n'
)
pat_rf = re.compile(
    r"(ORDER_REPLACE_FALLBACK = \{.*?)"
    r'    "fields": \{.*?\},\n'
    r'(    "fields_note": ".*?",\n)?',
    re.S,
)
text2, n = pat_rf.subn(r"\1" + rf_block, text, count=1)
assert n == 1, f"ReplaceFallback patch failed n={n}"
text = text2

ag_lit = (
    "{\n"
    '        "army_group": 0x28,  # army_subjects.army_group_fallback_recipe\n'
    '        "fallback_flag": 0x30,\n'
    "    }"
)
pat_ag = re.compile(r'(ARMY_GROUP_FALLBACK = \{.*?)"fields": \{.*?\}', re.S)
text2, n = pat_ag.subn(r'\1"fields": ' + ag_lit, text, count=1)
assert n == 1, f"AG patch failed n={n}"
cl.write_text(text2, encoding="utf-8")
print("cmd_layout patched")

# --- army_subjects ---
asp = ROOT / "calling" / "army_subjects.py"
at = asp.read_text(encoding="utf-8")
new_fn = '''def fallback_order_recipe(fallback_flag_or_id: int = 1,
                          subject_handle: list[int] | tuple[int, int] | None = None,
                          unit_handles: list[list[int]] | None = None,
                          province_ids: list[int] | None = None) -> dict[str, Any]:
    """COrderNewFallbackCommand / COrderReplaceFallbackCommands — RO docs only.

    Phase 2fl field map from shared serialize@0x18e8a60 (not NewFront@0x18e8af0).
    """
    return {
        "subject_handle_off": 0x28,
        "subject_handle": list(subject_handle) if subject_handle is not None else None,
        "units_data_off": 0x30,
        "units_count_off": 0x3c,
        "unit_handles": [list(h) for h in (unit_handles or [])],
        "units_count": len(unit_handles or []),
        "provinces_data_off": 0x48,
        "province_ids": list(province_ids or []),
        "fallback_flag_or_id_off": 0x54,
        "fallback_flag_or_id": fallback_flag_or_id,
        "serialize_tokens": {"unit_handle": 0x28A3, "province_array": 0x174, "header": 0x3F},
        "note": "2fl: IsValid=gate(this+0x28)+flag@+0x54; vectors must be game-alloc; posting DISABLED",
        "posting": "DISABLED",
    }

'''
pat = re.compile(
    r"def fallback_order_recipe\(fallback_flag_or_id: int = 1\) -> dict\[str, Any\]:.*?(?=\ndef )",
    re.S,
)
# may already be partially patched with different signature
pat2 = re.compile(
    r"def fallback_order_recipe\([\s\S]*?\) -> dict\[str, Any\]:.*?(?=\ndef )",
    re.S,
)
at2, n = pat.subn(new_fn + "\n", at, count=1)
if n != 1:
    at2, n = pat2.subn(new_fn + "\n", at, count=1)
assert n == 1, f"fallback_order_recipe patch failed n={n}"

new_rep = '''def replace_fallback_recipe(subject_handle: list[int] | tuple[int, int] | None = None,
                            unit_handles: list[list[int]] | None = None,
                            province_ids: list[int] | None = None,
                            fallback_flag_or_id: int = 1) -> dict[str, Any]:
    """COrderReplaceFallbackCommands — RO docs only; shares ser/deser/isvalid w/ NewFallback."""
    out = fallback_order_recipe(
        fallback_flag_or_id=fallback_flag_or_id,
        subject_handle=subject_handle,
        unit_handles=unit_handles,
        province_ids=province_ids,
    )
    out["post_gate_candidates"] = ["0x2284800", "0xbbb1e0", "0xc40230"]
    out["note"] = "2fl: same field map as NewFallback; Execute@0x18da3b0; posting DISABLED"
    out["posting"] = "DISABLED"
    return out

'''
old_rep = re.compile(
    r"def replace_fallback_recipe\([\s\S]*?\) -> dict\[str, Any\]:.*?(?=\ndef )",
    re.S,
)
at2, n2 = old_rep.subn(new_rep + "\n", at2, count=1)
print("replace_fallback_recipe patch", n2)
asp.write_text(at2, encoding="utf-8")

# --- live ---
pid = find_pid()
b = Backend(pid)
base = int(b.image_base)
ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
gs = struct.unpack("<Q", b.read(base + gs_rva, 8))[0]
hours = struct.unpack("<i", b.read(gs + 0x484, 4))[0]
d = datetime(1936, 1, 1) + timedelta(hours=int(hours))
live = {
    "pid": pid,
    "hours": hours,
    "ui_date": d.strftime("%Y-%m-%d %H:00"),
    "speed_policy": "pause-or-1x only (never change speed)",
    "scenario": "ITA@1x NewFallback subject field deepen (no Post)",
    "cmdline_expect": "-gdpr-compliant -start_tag=ITA -start_speed=1",
}

prev_path = ROOT / "reports" / "phase2fl_newfallback_fields.json"
prev = json.loads(prev_path.read_text(encoding="utf-8")) if prev_path.exists() else {}
ser_head = (
    ((prev.get("targets") or {}).get("COrderNewFallbackCommand") or {})
    .get("per_fn", {})
    .get("serialize", {})
    .get("disasm_head")
)
isv_head = (
    ((prev.get("targets") or {}).get("COrderNewFallbackCommand") or {})
    .get("per_fn", {})
    .get("isvalid", {})
    .get("disasm_head")
)
exe_head = (
    ((prev.get("targets") or {}).get("COrderNewFallbackCommand") or {})
    .get("per_fn", {})
    .get("execute", {})
    .get("disasm_head")
)

result = "NEWFALLBACK_FIELDS_DEEPENED"
works = [
    "Capstone NewFallback shared ser@0x18e8a60 (stop before NewFront@0x18e8af0 bleed)",
    "IsValid: gate(this+0x28)=0xbbb1e0 + dword@+0x54!=0",
    "Execute NewFallback: resolve handle@+0x28; helper(units@+0x30, provinces@+0x48)",
    f"fields {FIELDS}",
    "ORDER_REPLACE_FALLBACK shares ser/deser/isvalid; same field map",
    "ARMY_GROUP_FALLBACK unchanged (army_group@+0x28, fallback_flag@+0x30)",
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
    "units_end/cap exact packing between +0x30..+0x40",
    "provinces size/cap packing between +0x48..+0x50",
    "live midflight NewFallback hex capture",
    "subject_handle semantic (order vs army-group vs country)",
]
next_blocker = (
    "NON-Post: recover subject_handle semantic + units/provinces vector packing "
    "OR Assign/Unassign edge deepen; still NO ALLOW_POST"
)

report = {
    "phase": "2fl",
    "ts": datetime.now(timezone.utc).isoformat(),
    "result": result,
    "allow_post": False,
    "tool_gate": "CLOSED",
    "never_5x": True,
    "executed_2fb_recipe": False,
    "live": live,
    "parent_sha_base": "24ac836",
    "method_note": (
        "First auto-pass mixed NewFront ser@0x18e8af0 after int3 padding; corrected map uses "
        "only 0x18e8a60..0x18e8ae2 (NewFallback/ReplaceFallback shared serialize)."
    ),
    "shared_ser_deser_isvalid_new_vs_replace": True,
    "serialize_rva": "0x18e8a60",
    "deserialize_rva": "0x18e2500",
    "isvalid_rva": "0x18df4b0",
    "serialize_tokens": {"header": "0x3f", "unit_handle": "0x28a3", "province_array": "0x174"},
    "isvalid_gate": "0xbbb1e0",
    "field_map_proven": FIELDS,
    "fields_note": FIELDS_NOTE,
    "army_group_fallback_fields": AG_FIELDS,
    "disasm_evidence": {
        "serialize_head": ser_head,
        "isvalid_head": isv_head,
        "execute_newfallback_head": exe_head,
        "corrected_ser_summary": [
            "lea rdx,[this+0x28]; call handle_writer",
            "count=[this+0x3c]; base=[this+0x30]; token 0x28a3 stride 8",
            "lea r8,[this+0x48]; token 0x174; jmp province_array_writer",
        ],
    },
    "rejected_sibling_bleed_names": {
        "sub_group@0x30": "was NewFront; here +0x30 is units_data ptr",
        "units_data@0x38": "NewFront-only (ser continues at 0x18e8af0)",
        "units_count@0x44": "NewFront-only",
        "path@0x50": "NewFront-only; overflows NewFallback size 0x60 if treated as 0x18 vector",
    },
    "works": works,
    "stubbed": stubbed,
    "next_shortest_blocker": next_blocker,
}
(ROOT / "reports").mkdir(parents=True, exist_ok=True)
prev_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
summary = {
    "phase": "2fl",
    "result": result,
    "scenario": live["scenario"],
    "allow_post": False,
    "tool_gate": "CLOSED",
    "pid": live["pid"],
    "ui_date": live["ui_date"],
    "hours": live["hours"],
    "newfallback_fields": FIELDS,
    "replace_fallback_fields": FIELDS,
    "army_group_fallback_fields": AG_FIELDS,
    "shared_ser_deser_isvalid": True,
    "works": works,
    "stubbed": stubbed,
    "next_shortest_blocker": next_blocker,
    "parent_sha_base": "24ac836",
}
(ROOT / "reports" / "phase2fl_summary.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

doc = f"""# Phase 2fl — NewFallback subject fields beyond +0x54

**Result:** `{result}`  
**Base:** `24ac836` (2fk) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed

## Method

Live Capstone on ITA@1x for shared **Serialize `0x18e8a60` / Deserialize `0x18e2500` / IsValid `0x18df4b0`**
(NewFallback ≡ ReplaceFallback) plus NewFallback **Execute `0x18d8fc0`**.

Important: bytes after `int3` padding at `0x18e8ae3` belong to **COrderNewFrontCommand** serialize (`0x18e8af0`) — first auto-pass mixed those in; corrected map rejects that bleed.

## Proven field map (size `0x60`)

| off | name | evidence |
|-----|------|----------|
| +0x28 | `subject_handle` | IsValid `add rcx,0x28` → gate `0xbbb1e0`; ser handle writer; exec resolve |
| +0x30 | `units_data` | ser loop base; deser token `0x28a3` push; exec `lea rdx,[this+0x30]` |
| +0x3c | `units_count` | ser `mov eax,[this+0x3c]` loop count |
| +0x48 | `provinces_data` | ser token `0x174` province-array writer; exec `lea r8,[this+0x48]` |
| +0x54 | `fallback_flag_or_id` | IsValid `cmp dword [this+0x54],0` (2fi) |

Serialize tokens: header `0x3f` · unit `0x28a3` · province array `0x174`.

`ARMY_GROUP_FALLBACK` unchanged: `army_group@+0x28`, `fallback_flag@+0x30`.

## Live

```json
{json.dumps(live, indent=2)}
```

**Next shortest blocker (NON-Post):** {next_blocker}

Script: `scripts/phase2fl_newfallback_fields.py`
"""
(ROOT / "docs" / "PHASE2FL_NEWFALLBACK_FIELDS.md").write_text(doc, encoding="utf-8")

import importlib
import cmd_layout
import army_subjects

importlib.reload(cmd_layout)
importlib.reload(army_subjects)
print("ORDERS fields", cmd_layout.ORDERS["COrderNewFallbackCommand"]["fields"])
print("REPLACE fields", cmd_layout.ORDER_REPLACE_FALLBACK["fields"])
print("AG fields", cmd_layout.ARMY_GROUP_FALLBACK["fields"])
print(
    "recipe keys",
    list(
        army_subjects.fallback_order_recipe(1, [0x33, 1], [[0x33, 2]], [100]).keys()
    ),
)
print(
    json.dumps(
        {"result": result, "fields": FIELDS, "pid": pid, "ui": live["ui_date"], "hours": hours},
        indent=2,
    )
)
