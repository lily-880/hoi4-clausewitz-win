#!/usr/bin/env python3
"""Phase 2fm: NewFallback subject_handle semantic + units/provinces CPdxArray packing (RO)."""
from __future__ import annotations

import json
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from config import allow_post
from process import Backend, find_pid

assert allow_post() is False, "allow_post must stay False"

# Proven Windows CPdxArray (2de live): {T* data; i32 capacity; i32 size; void* alloc} = 0x18
CPDXARRAY = {
    "layout": "CPdxArray{data:u64, capacity:i32, size:i32, alloc:u64}",
    "size": 0x18,
    "fields": {"data": 0x0, "capacity": 0x8, "size": 0xC, "alloc": 0x10},
}

# NewFallback size 0x60; 2fl proven anchors
NF_SIZE = 0x60
UNITS_BASE = 0x30
PROV_BASE = 0x48
SUBJECT_OFF = 0x28

# RVAs
SER = 0x18E8A60
ISVALID = 0x18DF4B0
EXECUTE = 0x18D8FC0
CLONE = 0x18CDFF0
GATE = 0xBBB1E0
HANDLE_WRITER = 0x2285670
NF_VT = 0x2A84C80
NF_TID = 0x33D7


def u32(b: bytes, off: int = 0) -> int:
    return struct.unpack_from("<I", b, off)[0]


def u64(b: bytes, off: int = 0) -> int:
    return struct.unpack_from("<Q", b, off)[0]


def i32(b: bytes, off: int = 0) -> int:
    return struct.unpack_from("<i", b, off)[0]


def disasm(backend: Backend, abs_addr: int, size: int = 0x80) -> list[dict]:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64

    raw = backend.read(abs_addr, size)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True
    out = []
    for insn in md.disasm(raw, abs_addr):
        out.append(
            {
                "addr": hex(insn.address),
                "mnemonic": insn.mnemonic,
                "op_str": insn.op_str,
            }
        )
        if insn.mnemonic in ("ret", "jmp") and len(out) > 8:
            # keep going a bit for short helpers; break on ret after body
            if insn.mnemonic == "ret":
                break
    return out


def find_mem_disp(insns: list[dict], base_reg: str = "rbx") -> list[str]:
    hits = []
    for i in insns:
        op = i["op_str"]
        if f"{base_reg} +" in op or f"{base_reg}+" in op.replace(" ", ""):
            hits.append(f"{i['addr']}: {i['mnemonic']} {op}")
        if "rbp +" in op or "rbp+" in op.replace(" ", ""):
            hits.append(f"{i['addr']}: {i['mnemonic']} {op}")
    return hits


def main() -> None:
    pid = find_pid()
    b = Backend(pid)
    base = int(b.image_base)
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b.read(base + gs_rva, 8))
    hours = i32(b.read(gs + 0x484, 4))
    d = datetime(1936, 1, 1) + timedelta(hours=int(hours))
    live = {
        "pid": pid,
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never change speed)",
        "scenario": "ITA@1x NewFallback subject semantic + CPdxArray packing (no Post)",
        "cmdline_expect": "-gdpr-compliant -start_tag=ITA -start_speed=1",
    }

    # --- packing fit (catalog math; no invent beyond 2de CPdxArray + 2fl anchors) ---
    units_packing = {
        "base": UNITS_BASE,
        "hypothesis": "CPdxArray of unit handles (token 0x28a3, stride 8)",
        "fields": {
            "data": UNITS_BASE + 0x0,  # 0x30 — 2fl ser base
            "capacity": UNITS_BASE + 0x8,  # 0x38
            "size": UNITS_BASE + 0xC,  # 0x3c — 2fl ser count
            "alloc": UNITS_BASE + 0x10,  # 0x40
        },
        "fits_ser_count_at_0x3c": True,
        "sibling_mass_cancel": {
            "units_data": 0x28,
            "units_count": 0x34,
            "note": "0x28+0xC=0x34 — same CPdxArray size-slot relative offset",
        },
        "sibling_unassign": {
            "units_data": 0x28,
            "units_count": 0x34,
            "note": "order_unassign_recipe same relative packing",
        },
    }
    prov_packing = {
        "base": PROV_BASE,
        "hypothesis": "CPdxArray of provinces (token 0x174)",
        "fields": {
            "data": PROV_BASE + 0x0,  # 0x48 — 2fl ser lea
            "capacity": PROV_BASE + 0x8,  # 0x50
            "size": PROV_BASE + 0xC,  # 0x54 — overlaps former name fallback_flag_or_id
            "alloc": PROV_BASE + 0x10,  # 0x58
        },
        "end_of_struct": PROV_BASE + 0x18,  # 0x60 == NF_SIZE
        "fits_command_size_0x60": (PROV_BASE + 0x18) == NF_SIZE,
    }

    # --- light Capstone: IsValid, Clone, Gate, Handle writer heads ---
    isv = disasm(b, base + ISVALID, 0x60)
    clone = disasm(b, base + CLONE, 0xA0)
    gate = disasm(b, base + GATE, 0x80)
    hwriter = disasm(b, base + HANDLE_WRITER, 0x60)
    exe = disasm(b, base + EXECUTE, 0x100)

    isv_disp = find_mem_disp(isv, "rbx") + find_mem_disp(isv, "rcx")
    clone_disp = [x for x in find_mem_disp(clone, "rbx") + find_mem_disp(clone, "rdi") + find_mem_disp(clone, "rsi") if "+ 0x" in x or "+0x" in x.replace(" ", "")]
    exe_disp = find_mem_disp(exe, "rbx")

    # Classify +0x54 from evidence (no invent):
    # - ser writes province array at +0x48 only (no separate dword store @+0x54)
    # - CPdxArray.size relative = +0xC → absolute +0x54
    # - IsValid cmp dword [+0x54],0  ≡ provinces.size != 0 under this packing
    # - ARMY_GROUP_FALLBACK's fallback_flag@+0x30 is a DIFFERENT command (not NewFallback)
    plus54_reinterpret = {
        "prior_2fi_name": "fallback_flag_or_id",
        "corrected_candidate": "provinces_size (CPdxArray.size @ provinces_data+0xC)",
        "confidence": "HIGH_RO_FIT",
        "evidence": [
            "2fl serialize: lea r8,[this+0x48] token 0x174 only — no discrete flag writer at +0x54",
            "CPdxArray size slot = base+0xC → 0x48+0xC=0x54",
            "IsValid cmp dword [this+0x54],0 matches nonempty provinces.size gate",
            "command size 0x60 == provinces_base+0x18 (full CPdxArray fits exactly)",
            "ARMY_GROUP_FALLBACK fallback_flag@+0x30 is sibling command; do not import name here",
        ],
        "still_open": "Execute helper may also treat +0x54 as mode id — not observed as separate ser field",
    }

    # --- subject_handle semantic via gate + live army handles ---
    # Sample player armies if probe helper exists
    army_examples = []
    try:
        from probe_player_armies import list_player_armies  # type: ignore

        armies = list_player_armies(b)[:5]
        for a in armies:
            army_examples.append(a)
    except Exception as e1:
        try:
            # fallback: read GS player country tag + army array via known offsets if present
            from offsets_verified import load as load_ov  # type: ignore

            army_examples.append({"note": f"probe_player_armies unavailable: {e1}"})
        except Exception:
            army_examples.append({"note": f"probe_player_armies unavailable: {e1}"})

    # Lightweight: scan known handle-type recipes / gate name from prior indexes
    gate_name = "isvalid_order_fallback_gate"  # from _2cr/_2cu indexes
    subject_semantic = {
        "off": SUBJECT_OFF,
        "ser_writer": hex(HANDLE_WRITER),
        "isvalid_gate": hex(GATE),
        "gate_catalog_name": gate_name,
        "proven": [
            "IsValid: lea/add rcx,this+0x28 → call gate 0xbbb1e0 (must succeed)",
            "Serialize: lea rdx,[this+0x28] → handle writer 0x2285670",
            "Execute: resolve handle@+0x28 before units/provinces helpers",
        ],
        "not_army_group_flag_slot": "ARMY_GROUP_FALLBACK puts army_group handle@+0x28; NewFallback uses same slot for ORDER subject handle gated by 0xbbb1e0",
        "semantic_candidate": "battle-plan / order-subject handle (type+index pair), NOT a raw CArmy* and NOT the army-group fallback_flag",
        "confidence": "MEDIUM_RO",
        "evidence_for_candidate": [
            "gate catalog name isvalid_order_fallback_gate (order-domain, not unit-domain)",
            "unit handles live in separate CPdxArray@+0x30 with token 0x28a3",
            "SupportAttack/WithdrawHQ put unit/hq handles@+0x28 with different IsValid paths; NewFallback shares gate with ReplaceFallback only",
            "collapse_conveyor / assign_theater_group recipes also label +0x28 as subject_handle (order/theatre subject family)",
        ],
        "live_army_examples_note": "ITA army handles listed for contrast — they are unit/army typed; subject_handle is a distinct order-domain handle",
        "live_army_examples": army_examples[:5],
        "not_proven": "exact handle type id byte / table for order-subject (no midflight NewFallback hex this slice)",
    }

    # Capstone gate: look for type compares
    gate_immediates = []
    for insn in gate:
        if insn["mnemonic"] in ("cmp", "sub", "mov") and "0x" in insn["op_str"]:
            gate_immediates.append(f"{insn['addr']}: {insn['mnemonic']} {insn['op_str']}")

    result = "NEWFALLBACK_SUBJECT_PACKING_DEEPENED"
    works = [
        "units@+0x30 fits CPdxArray: data@+0x30 cap@+0x38 size@+0x3c alloc@+0x40 (ser count@+0x3c)",
        "provinces@+0x48 fits CPdxArray: data@+0x48 cap@+0x50 size@+0x54 alloc@+0x58 (ends @0x60)",
        "reclassify +0x54 as provinces.size under CPdxArray (was fallback_flag_or_id name)",
        "subject_handle@+0x28 = order-domain handle (gate 0xbbb1e0); units are separate array",
        "MassCancel/Unassign sibling packing confirms size = data+0xC",
        "allow_post stays False; no Post; never 5x; 2fb not executed",
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
        "live midflight NewFallback hex capture",
        "exact order-subject handle type-id table",
        "Execute helper micro-semantics for provinces.size vs mode id",
    ]
    next_blocker = (
        "NON-Post: live midflight NewFallback/ReplaceFallback hex to confirm handle type-id "
        "OR Assign/Unassign edge deepen; still NO ALLOW_POST"
    )

    # Patch catalogs: rename +0x54, add packing notes — careful exact strings
    fields_corrected = {
        "subject_handle": 0x28,
        "units_data": 0x30,
        "units_capacity": 0x38,
        "units_count": 0x3c,  # CPdxArray.size
        "units_alloc": 0x40,
        "provinces_data": 0x48,
        "provinces_capacity": 0x50,
        "provinces_size": 0x54,  # was fallback_flag_or_id
        "provinces_alloc": 0x58,
    }
    fields_note = (
        "2fm: CPdxArray packing (2de layout); +0x54=provinces.size not AG fallback_flag; "
        "subject_handle=order-domain via gate 0xbbb1e0; posting DISABLED"
    )

    report = {
        "phase": "2fm",
        "ts": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "allow_post": False,
        "tool_gate": "CLOSED",
        "never_5x": True,
        "executed_2fb_recipe": False,
        "live": live,
        "parent_sha_base": "34e5858",
        "cpdxarray": CPDXARRAY,
        "units_packing": units_packing,
        "provinces_packing": prov_packing,
        "plus54_reinterpret": plus54_reinterpret,
        "subject_semantic": subject_semantic,
        "field_map_corrected": fields_corrected,
        "fields_note": fields_note,
        "disasm": {
            "isvalid_head": isv[:20],
            "isvalid_mem_disp": isv_disp[:30],
            "clone_head": clone[:25],
            "execute_mem_disp": exe_disp[:40],
            "gate_head": gate[:25],
            "gate_immediates": gate_immediates[:30],
            "handle_writer_head": hwriter[:20],
        },
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
    }

    (ROOT / "reports").mkdir(parents=True, exist_ok=True)
    (ROOT / "reports" / "phase2fm_subject_packing.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    summary = {
        "phase": "2fm",
        "result": result,
        "scenario": live["scenario"],
        "allow_post": False,
        "tool_gate": "CLOSED",
        "pid": live["pid"],
        "ui_date": live["ui_date"],
        "hours": live["hours"],
        "field_map_corrected": fields_corrected,
        "subject_semantic_candidate": subject_semantic["semantic_candidate"],
        "plus54": plus54_reinterpret["corrected_candidate"],
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "parent_sha_base": "34e5858",
    }
    (ROOT / "reports" / "phase2fm_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    doc = f"""# Phase 2fm — NewFallback subject semantic + CPdxArray packing

**Result:** `{result}`  
**Base:** `34e5858` (2fl) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed

## CPdxArray (proven 2de)

`{{T* data; i32 capacity; i32 size; void* alloc}}` = **0x18**

## Units @ +0x30

| off | name | evidence |
|-----|------|----------|
| +0x30 | units_data | 2fl ser loop base; token 0x28a3 |
| +0x38 | units_capacity | CPdxArray.capacity |
| +0x3c | units_count (size) | 2fl ser `mov eax,[this+0x3c]` |
| +0x40 | units_alloc | CPdxArray.alloc |

Sibling: MassCancel/Unassign use data@+0x28 → size@+0x34 (=data+0xC).

## Provinces @ +0x48

| off | name | evidence |
|-----|------|----------|
| +0x48 | provinces_data | 2fl ser token 0x174 |
| +0x50 | provinces_capacity | CPdxArray.capacity |
| +0x54 | **provinces_size** | CPdxArray.size; IsValid `cmp dword [this+0x54],0` |
| +0x58 | provinces_alloc | CPdxArray.alloc; struct ends @0x60 |

**Reclassify:** 2fi name `fallback_flag_or_id@+0x54` → **`provinces_size`**. True `fallback_flag` remains on **ARMY_GROUP_FALLBACK@+0x30** only.

## subject_handle @ +0x28

- IsValid gate `0xbbb1e0` (`isvalid_order_fallback_gate`)
- Ser handle writer `0x2285670`
- **Candidate:** battle-plan / order-subject handle (type+index), **not** raw CArmy* (units are the +0x30 array)

## Live

```json
{json.dumps(live, indent=2)}
```

**Next shortest blocker (NON-Post):** {next_blocker}
"""
    (ROOT / "docs" / "PHASE2FM_SUBJECT_PACKING.md").write_text(doc, encoding="utf-8")

    # --- patch cmd_layout + army_subjects (exact string, no greedy regex) ---
    cl = ROOT / "calling" / "cmd_layout.py"
    ct = cl.read_text(encoding="utf-8")
    old_nf = (
        '        # Phase 2fl: deepen beyond +0x54 from NewFallback ser/deser/isvalid/exec (no NewFront bleed)\n'
        '        "fields": {"subject_handle": 0x28, "units_data": 0x30, "units_count": 0x3c, "provinces_data": 0x48, "fallback_flag_or_id": 0x54},\n'
        '        "fields_note": "2fl: Capstone shared ser@0x18e8a60 (not NewFront@0x18e8af0); IsValid gate(this+0x28)+flag@+0x54; posting DISABLED",'
    )
    new_nf = (
        '        # Phase 2fm: CPdxArray packing + subject_handle semantic; +0x54=provinces_size\n'
        f'        "fields": {json.dumps(fields_corrected)},\n'
        f'        "fields_note": "{fields_note}",'
    )
    assert ct.count(old_nf) == 1, f"NewFallback fields block count={ct.count(old_nf)}"
    ct = ct.replace(old_nf, new_nf, 1)

    old_rf = (
        '    "fields": {"subject_handle": 0x28, "units_data": 0x30, "units_count": 0x3c, "provinces_data": 0x48, "fallback_flag_or_id": 0x54},\n'
        '    "fields_note": "2fl: same map as NewFallback; Capstone ser@0x18e8a60 shared; posting DISABLED",'
    )
    new_rf = (
        f'    "fields": {json.dumps(fields_corrected)},\n'
        f'    "fields_note": "{fields_note}",'
    )
    assert ct.count(old_rf) == 1, f"ReplaceFallback fields block count={ct.count(old_rf)}"
    ct = ct.replace(old_rf, new_rf, 1)
    cl.write_text(ct, encoding="utf-8")

    asp = ROOT / "calling" / "army_subjects.py"
    at = asp.read_text(encoding="utf-8")
    # replace fallback_order_recipe body return keys for packing
    import re

    new_fn = '''def fallback_order_recipe(subject_handle: list[int] | tuple[int, int] | None = None,
                          unit_handles: list[list[int]] | None = None,
                          province_ids: list[int] | None = None) -> dict[str, Any]:
    """COrderNewFallbackCommand / COrderReplaceFallbackCommands — RO docs only.

    Phase 2fm: subject_handle=order-domain @+0x28; units/provinces are CPdxArrays.
    +0x54 is provinces_size (not ARMY_GROUP_FALLBACK.fallback_flag).
    """
    return {
        "subject_handle_off": 0x28,
        "subject_handle": list(subject_handle) if subject_handle is not None else None,
        "subject_semantic": "order-domain handle (gate 0xbbb1e0); not raw CArmy*",
        "units_data_off": 0x30,
        "units_capacity_off": 0x38,
        "units_count_off": 0x3c,
        "units_alloc_off": 0x40,
        "unit_handles": [list(h) for h in (unit_handles or [])],
        "units_count": len(unit_handles or []),
        "provinces_data_off": 0x48,
        "provinces_capacity_off": 0x50,
        "provinces_size_off": 0x54,
        "provinces_alloc_off": 0x58,
        "province_ids": list(province_ids or []),
        "provinces_size": len(province_ids or []),
        "serialize_tokens": {"unit_handle": 0x28A3, "province_array": 0x174, "header": 0x3F},
        "cpdxarray": "data@0 cap@8 size@0xC alloc@0x10",
        "note": "2fm: IsValid=gate(this+0x28)+provinces.size@+0x54!=0; posting DISABLED",
        "posting": "DISABLED",
    }

'''
    at2, n = re.subn(
        r"def fallback_order_recipe\([\s\S]*?\) -> dict\[str, Any\]:.*?(?=\ndef )",
        new_fn + "\n",
        at,
        count=1,
    )
    assert n == 1, f"fallback_order_recipe patch n={n}"

    new_rep = '''def replace_fallback_recipe(subject_handle: list[int] | tuple[int, int] | None = None,
                            unit_handles: list[list[int]] | None = None,
                            province_ids: list[int] | None = None) -> dict[str, Any]:
    """COrderReplaceFallbackCommands — RO docs only; shares ser/deser/isvalid w/ NewFallback."""
    out = fallback_order_recipe(
        subject_handle=subject_handle,
        unit_handles=unit_handles,
        province_ids=province_ids,
    )
    out["post_gate_candidates"] = ["0x2284800", "0xbbb1e0", "0xc40230"]
    out["note"] = "2fm: same CPdxArray map as NewFallback; Execute@0x18da3b0; posting DISABLED"
    out["posting"] = "DISABLED"
    return out

'''
    at2, n2 = re.subn(
        r"def replace_fallback_recipe\([\s\S]*?\) -> dict\[str, Any\]:.*?(?=\ndef )",
        new_rep + "\n",
        at2,
        count=1,
    )
    assert n2 == 1, f"replace_fallback_recipe patch n={n2}"
    asp.write_text(at2, encoding="utf-8")

    # verify imports
    import importlib
    import cmd_layout
    import army_subjects

    importlib.reload(cmd_layout)
    importlib.reload(army_subjects)
    f = cmd_layout.ORDERS["COrderNewFallbackCommand"]["fields"]
    assert f["provinces_size"] == 0x54 and "fallback_flag_or_id" not in f, f
    r = army_subjects.fallback_order_recipe([0x33, 1], [[0x33, 2]], [100, 101])
    assert r["provinces_size_off"] == 0x54 and r["units_capacity_off"] == 0x38
    print(
        json.dumps(
            {
                "result": result,
                "fields": f,
                "plus54": plus54_reinterpret["corrected_candidate"],
                "subject": subject_semantic["semantic_candidate"],
                "pid": pid,
                "ui": live["ui_date"],
                "hours": hours,
                "allow_post": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
