#!/usr/bin/env python3
"""Phase 2e: stronger READ-ONLY hunt for FN_CMD_QUEUE_POST / CCommandQueue.

Compares the Linux Clausewitz-MCP path (CInGameIdler vtable+0x90 -> queue Post)
against Windows PE 1.19.4: call graphs, vtables near CCommand, string xrefs,
idler wrapper decode, CArmy/CDate RTTI.

NEVER sets FN_CMD_QUEUE_POST. NEVER enables writes. Candidates only.
Writes research/re-dumps/phase2e_post_graph.json
"""
from __future__ import annotations

import json
import os
import struct
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

from pe import PE  # noqa: E402
from msvc_rtti import find_col_and_vtable, scan_type_names  # noqa: E402
from stringscan import find_ascii_all, rip_lea_xrefs  # noqa: E402

# Proven Windows static (see WINDOWS_OFFSETS.md)
CMD_VT = 0x279F4A0
IDLER_VT = 0x29E5838
LINUX_POST = 0x2DC1C40  # ELF only — do not copy
LINUX_NOTE = (
    "Linux Clausewitz-MCP 1.19.2: CCommandQueue::Post = img+0x2DC1C40; "
    "queue object from CInGameIdler (G_IDLER), reached via idler vtable+0x90."
)


def text_blob(pe: PE):
    text = next(s for s in pe.sections if s.name == ".text")
    return text, pe.data[text.raw_ptr : text.raw_ptr + text.raw_size]


def dump_vtable(pe: PE, rva: int, n: int = 40) -> list:
    out = []
    for i in range(n):
        off = pe.rva_to_off(rva + i * 8)
        if off is None:
            break
        ptr = struct.unpack_from("<Q", pe.data, off)[0]
        mrva = ptr - pe.image_base if pe.image_base <= ptr < pe.image_base + 0x40000000 else None
        out.append({"slot": hex(i * 8), "method_rva": hex(mrva) if mrva is not None else None})
    return out


def decode_idler_post_wrapper(pe: PE, fn_rva: int) -> dict:
    """CInGameIdler vt+0x90 on Windows: optional log, then jmp [ [this+field].vt + 0x90 ]."""
    off = pe.rva_to_off(fn_rva)
    raw = pe.data[off : off + 160]
    info = {
        "fn_rva": hex(fn_rva),
        "head_hex": raw[:48].hex(),
        "global_loads": [],
        "field_loads": [],
        "helper_calls": [],
        "tail_jmp_vt_slot": None,
        "interpretation": None,
    }
    i = 0
    while i < len(raw) - 7:
        if raw[i] == 0xE8:
            rel = struct.unpack_from("<i", raw, i + 1)[0]
            info["helper_calls"].append(hex((fn_rva + i + 5 + rel) & 0xFFFFFFFF))
            i += 5
            continue
        # mov rcx/rax,[rip+disp32]
        if raw[i : i + 3] in (
            bytes([0x48, 0x8B, 0x0D]),
            bytes([0x48, 0x8B, 0x05]),
            bytes([0x48, 0x8B, 0x15]),
        ):
            rel = struct.unpack_from("<i", raw, i + 3)[0]
            info["global_loads"].append(hex((fn_rva + i + 7 + rel) & 0xFFFFFFFF))
            i += 7
            continue
        # mov rcx,[rdi+disp32] 48 8B 8F
        if raw[i : i + 3] == bytes([0x48, 0x8B, 0x8F]):
            imm = struct.unpack_from("<i", raw, i + 3)[0]
            info["field_loads"].append(hex(imm))
            i += 7
            continue
        # jmp qword ptr [rax+disp32] : 48 FF A0 disp32
        if raw[i : i + 3] == bytes([0x48, 0xFF, 0xA0]):
            imm = struct.unpack_from("<i", raw, i + 3)[0]
            info["tail_jmp_vt_slot"] = hex(imm)
            break
        if raw[i] == 0xC3:
            break
        i += 1
    if info["field_loads"] and info["tail_jmp_vt_slot"] == "0x90":
        info["interpretation"] = (
            "Wrapper: load queue-like object at CInGameIdler+%s, "
            "tail-call that object's vtable+0x90 (Linux-analog Post slot). "
            "FN_CMD_QUEUE_POST = that callee ONLY after live idler+queue typed proof."
            % info["field_loads"][0]
        )
    return info


def nearby_calls(pe: PE, insn_rva: int, window: int = 0x100) -> list:
    text, blob = text_blob(pe)
    base = text.virtual_address
    off = insn_rva - base
    lo = max(0, off - 0x20)
    hi = min(len(blob) - 5, off + window)
    calls = []
    for i in range(lo, hi):
        if blob[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", blob, i + 1)[0]
        tgt = (base + i + 5 + rel) & 0xFFFFFFFF
        if base <= tgt < base + text.virtual_size:
            calls.append(tgt)
    return calls


def rtti_name_at_vtable(pe: PE, vt_rva: int) -> dict:
    off = pe.rva_to_off(vt_rva - 8)
    if off is None:
        return {"vtable_rva": hex(vt_rva), "error": "bad vt"}
    col_va = struct.unpack_from("<Q", pe.data, off)[0]
    col_rva = col_va - pe.image_base
    coff = pe.rva_to_off(col_rva)
    if coff is None:
        return {"vtable_rva": hex(vt_rva), "error": "no COL", "col_rva": hex(col_rva)}
    sig, _, _, td_rva = struct.unpack_from("<IIII", pe.data, coff)
    td_off = pe.rva_to_off(td_rva)
    name = pe.data[td_off + 0x14 : td_off + 0x14 + 96].split(b"\x00", 1)[0].decode("latin1", "replace")
    return {"vtable_rva": hex(vt_rva), "col_rva": hex(col_rva), "td_rva": hex(td_rva), "name": name, "sig": sig}


def recover_type(pe: PE, plain: str) -> dict:
    hits = [h for h in scan_type_names(pe, plain, limit=40) if h.get("name") == ".?AV%s@@" % plain]
    if not hits:
        return {"name": plain, "found": False}
    td = hits[0]["td_rva"]
    col = find_col_and_vtable(pe, td)
    return {
        "name": plain,
        "found": True,
        "td_rva": hex(td),
        "name_rva": hex(hits[0]["name_rva"]),
        "cols": [hex(c) for c in col.get("cols", [])[:8]],
        "vtables": [
            {"col_rva": hex(v["col_rva"]), "vtable_rva": hex(v["vtable_rva"])}
            for v in col.get("vtables", [])[:6]
        ],
    }


def main() -> int:
    exe = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
    if not os.path.isfile(exe):
        import config

        exe = config.binary_path(required=True)
    pe = PE(exe)

    idler_methods = dump_vtable(pe, IDLER_VT, 48)
    slot_90 = next((m for m in idler_methods if m["slot"] == "0x90"), None)
    wrapper = decode_idler_post_wrapper(pe, int(slot_90["method_rva"], 16)) if slot_90 and slot_90["method_rva"] else {}

    # CCommand construction LEA neighborhood → soft call targets
    cmd_leas = rip_lea_xrefs(pe, CMD_VT, max_hits=80)
    soft = []
    for x in cmd_leas:
        soft.extend(nearby_calls(pe, x["insn_rva"]))
    soft_counts = Counter(soft).most_common(20)

    # String catalogue
    strings = {}
    for label in (
        b"PostCommand",
        b"QueueCommand",
        b"ExecuteCommand",
        b"CCommandQueue",
        b"CommandQueue",
        b"?Post@",
    ):
        rvas = find_ascii_all(pe, label)
        strings[label.decode("latin1")] = {
            "count": len(rvas),
            "sample_rvas": [hex(r) for r in rvas[:12]],
            "lea_xref_count": sum(len(rip_lea_xrefs(pe, r, max_hits=4)) for r in rvas[:8]),
        }

    types = {n: recover_type(pe, n) for n in ("CArmy", "CDate", "CUnit", "CCommand", "CInGameIdler", "CGameIdler")}

    # Dead-end / comparison block
    dead_ends = [
        {
            "lead": ".?AVCCommandQueue@@ / CGameCommandQueue / CPdxCommandQueue",
            "result": "Absent from MSVC RTTI type names",
        },
        {
            "lead": "Mangled ?Post@ / PostCommand ASCII",
            "result": "0 hits (Post not exported under that name)",
        },
        {
            "lead": "CommandQueue ASCII",
            "result": "SDL2 GL CommandQueue red herring only",
        },
        {
            "lead": "QueueCommand / ExecuteCommand ASCII",
            "result": "RTTI fragments of *QueueCommand / *ExecuteCommand CCommand subclasses, not a Post API",
        },
        {
            "lead": "Linux img+0x2DC1C40",
            "result": "ELF-only; Windows idler+0x90 is a different RVA (wrapper), not a copy of Linux Post",
        },
        {
            "lead": "Soft E8 targets near CCommand vtable LEAs (e.g. 0x25a009c)",
            "result": "Common near ctors; likely helpers/refcount — NOT proven Post; do not promote",
        },
        {
            "lead": "Live CInGameIdler heap vptr (this session sample)",
            "result": "May be 0 even with G_GAMESTATE live — cannot yet read Idler+0x530 queue object",
        },
    ]

    out = {
        "policy": "FN_CMD_QUEUE_POST remains null — Phase 2e catalogues only; writes DISABLED",
        "linux_reference": {"post_rva": hex(LINUX_POST), "note": LINUX_NOTE},
        "windows": {
            "CCommand_vtable": hex(CMD_VT),
            "CInGameIdler_vtable": hex(IDLER_VT),
            "CInGameIdler_vtable_dump": idler_methods,
            "idler_vt_plus_0x90_wrapper": wrapper,
            "hypothesized_queue_field_on_idler": (wrapper.get("field_loads") or [None])[0],
            "hypothesized_post_slot_on_queue_object": "vtable+0x90 (tail-call target of wrapper)",
            "CCommand_lea_xref_count": len(cmd_leas),
            "soft_call_targets_near_CCommand_lea": [
                {"target_rva": hex(t), "hits": n} for t, n in soft_counts
            ],
        },
        "strings": strings,
        "rtti_types": types,
        "dead_ends": dead_ends,
        "FN_CMD_QUEUE_POST": None,
        "next_proof_steps": [
            "Find live CInGameIdler (or subclass) object while map UI is active",
            "Read qword at idler+0x530 → queue-like object; RTTI-identify its vtable",
            "Dump that object's vtable+0x90 method; prove it takes CCommand* and enqueues",
            "Only then set FN_CMD_QUEUE_POST to that method RVA (still gate writes)",
        ],
    }

    path = os.path.join(ROOT, "research", "re-dumps", "phase2e_post_graph.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2)

    summary = {
        "FN_CMD_QUEUE_POST": None,
        "idler_plus_0x90": wrapper.get("fn_rva"),
        "queue_field_hyp": out["windows"]["hypothesized_queue_field_on_idler"],
        "tail_vt_slot": wrapper.get("tail_jmp_vt_slot"),
        "CArmy_vtables": [v["vtable_rva"] for v in types["CArmy"].get("vtables", [])],
        "CDate_found": types["CDate"].get("found"),
        "CDate_vtables": types["CDate"].get("vtables"),
        "soft_top": out["windows"]["soft_call_targets_near_CCommand_lea"][:5],
        "dead_ends": len(dead_ends),
        "out": path,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
