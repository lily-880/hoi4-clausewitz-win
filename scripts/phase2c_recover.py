#!/usr/bin/env python3
"""Phase 2c: static G_GAMESTATE candidate recovery + command-name RTTI sweep.

Read-only. Does NOT enable writes. Writes research/re-dumps/phase2c_recover.json.
"""
from __future__ import annotations

import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

from pe import PE  # noqa: E402
from msvc_rtti import catalog, exact_type, scan_type_names, demangle_simple  # noqa: E402
from stringscan import find_ascii_all, rip_lea_xrefs, data_pointer_slots  # noqa: E402


# Proven from Phase 2
GS_VT = 0x279F0F0
GS_VT2 = 0x279F148
CGS_VT = 0x279F168
CTOR_LEAS = [0x1D78AE, 0x1DA5A6]


def text_blob(pe: PE):
    text = next(s for s in pe.sections if s.name == ".text")
    return text, pe.data[text.raw_ptr : text.raw_ptr + text.raw_size]


def find_rip_stores_near(pe: PE, center_rva: int, window: int = 0x200) -> list:
    """Find MOV [rip+disp32], r64 near center_rva (global stores of 'this').

    Encodings:
      48 89 05/0D/15/1D/25/2D/35/3D  disp32   mov [rip+disp], rAX..RDI
      4C 89 05/...                             mov [rip+disp], r8..r15
    """
    text, blob = text_blob(pe)
    start = max(0, center_rva - text.virtual_address - window)
    end = min(len(blob) - 7, center_rva - text.virtual_address + window)
    hits = []
    for i in range(start, end):
        b0, b1, b2 = blob[i], blob[i + 1], blob[i + 2]
        if b0 not in (0x48, 0x4C) or b1 != 0x89:
            continue
        if (b2 & 0xC7) != 0x05:
            continue
        disp = struct.unpack_from("<i", blob, i + 3)[0]
        insn_rva = text.virtual_address + i
        next_rva = insn_rva + 7
        target = (next_rva + disp) & 0xFFFFFFFF
        # Prefer .data / writable globals
        sec = next(
            (
                s
                for s in pe.sections
                if s.virtual_address
                <= target
                < s.virtual_address + max(s.virtual_size, s.raw_size)
            ),
            None,
        )
        hits.append(
            {
                "insn_rva": hex(insn_rva),
                "store_rva": hex(target),
                "section": sec.name if sec else None,
                "rex": b0,
                "modrm": b2,
                "near": hex(center_rva),
            }
        )
    return hits


def find_lea_of_vtable(pe: PE, vt_rva: int, max_hits: int = 40) -> list:
    """LEA reg, [rip+disp] resolving to vt_rva (ctors set vptr this way)."""
    return rip_lea_xrefs(pe, vt_rva, max_hits=max_hits)


def classify_session_requirement() -> dict:
    return {
        "lobby_or_menu": "CGameState / CCurrentGameState heap objects usually ABSENT; live-gs returns 0 hits — expected.",
        "in_campaign": "Load a save or start a game until the map is visible; then re-run live-gs / session-probe.",
        "idler_signal": "Presence of CInGameIdler heap vptr is a strong 'in-campaign' signal; CGameIdler alone may be menu.",
    }


def command_rtti_sweep(pe: PE) -> dict:
    """Broader name sweep — CCommandQueue may be absent; look for related types."""
    needles = [
        "CCommandQueue",
        "CCommand",
        "CommandQueue",
        "CPdxCommand",
        "CGameCommand",
        "CQueuedCommand",
        "CNetCommand",
        "CConsoleCmd",
    ]
    out = {}
    for n in needles:
        tds = scan_type_names(pe, n, limit=30)
        # keep exact-ish
        filtered = [td for td in tds if demangle_simple(td["name"]) == n or n in demangle_simple(td["name"])]
        if not filtered:
            # still record substring hits count
            out[n] = {"exact_or_contains": [], "substring_hit_count": len(tds), "sample": [td["name"] for td in tds[:8]]}
            continue
        entries = []
        for td in filtered[:8]:
            info = exact_type(pe, demangle_simple(td["name"])) or {}
            entries.append(
                {
                    "name": td["name"],
                    "td_rva": hex(td["td_rva"]),
                    "cols": [hex(c) for c in (info.get("cols") or [])[:8]],
                    "vtables": [
                        {
                            "vtable_rva": hex(v["vtable_rva"]),
                            "col_ptr_slot": hex(v["col_ptr_slot"]),
                        }
                        for v in (info.get("vtables") or [])[:6]
                    ],
                }
            )
        out[n] = {"exact_or_contains": entries, "substring_hit_count": len(tds)}
    # plain strings
    plain = {}
    for s in (b"PostCommand", b"CommandQueue", b"CCommandQueue", b"ExecuteCommand", b"QueueCommand"):
        rvas = find_ascii_all(pe, s)
        plain[s.decode()] = [hex(r) for r in rvas[:12]]
    return {"rtti": out, "plain_strings": plain, "FN_CMD_QUEUE_POST": None, "policy": "DISABLED until independently verified"}


def main():
    dump = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
    exe = dump if os.path.isfile(dump) else os.environ.get("HOI4_EXE")
    if not exe or not os.path.isfile(exe):
        import config

        exe = config.binary_path(required=True)
    print("Scanning", exe, file=sys.stderr)
    pe = PE(exe)

    # 1) LEA sites of CGameState vtables
    lea_primary = find_lea_of_vtable(pe, GS_VT)
    lea_secondary = find_lea_of_vtable(pe, GS_VT2)
    lea_cgs = find_lea_of_vtable(pe, CGS_VT)

    # 2) RIP stores near those LEAs and near known ctor LEAs
    store_hits = []
    centers = [h["insn_rva"] for h in lea_primary[:15]] + CTOR_LEAS
    for c in centers:
        store_hits.extend(find_rip_stores_near(pe, c, window=0x180))
    # dedupe by store_rva
    by_store = {}
    for h in store_hits:
        if h["section"] not in (".data", ".bss", None):
            # keep .data primarily; some globals sit in .data; skip .rdata
            if h["section"] == ".rdata":
                continue
        by_store.setdefault(h["store_rva"], []).append(h)
    # rank: stores appearing near multiple ctor sites
    candidates = []
    for store_rva, hs in by_store.items():
        sec = hs[0]["section"]
        if sec not in (".data",):
            continue
        candidates.append(
            {
                "global_rva_candidate": store_rva,
                "section": sec,
                "store_sites": hs[:8],
                "n_stores_seen": len(hs),
                "status": "STATIC_CANDIDATE_UNVERIFIED",
                "note": "Must live-verify: slot holds ptr whose vptr == CGameState vtable, countries/player heuristics OK",
            }
        )
    candidates.sort(key=lambda x: -x["n_stores_seen"])

    # 3) Also: data slots that already hold ImageBase+something pointing patterns — skip
    # Cross-check: any candidate that is also written as qword init 0 in file
    for c in candidates:
        rva = int(c["global_rva_candidate"], 16)
        raw = pe.read_rva(rva, 8)
        c["file_qword"] = raw.hex() if raw else None

    cmd = command_rtti_sweep(pe)

    # Expand catalog for CurrentGameState / GameIdler if missing from static_scan
    extra = {}
    for name in ("CCurrentGameState", "CGameIdler", "CCommand", "CConsoleCmdManager"):
        info = exact_type(pe, name)
        if info:
            extra[name] = {
                "name_rva": hex(info["name_rva"]),
                "td_rva": hex(info["td_rva"]),
                "cols": [hex(x) for x in info["cols"][:8]],
                "vtables": [
                    {
                        "vtable_rva": hex(v["vtable_rva"]),
                        "col_ptr_slot": hex(v["col_ptr_slot"]),
                    }
                    for v in info["vtables"][:6]
                ],
            }

    out = {
        "exe": exe,
        "method": "LEA(vtable)->nearby MOV [rip],reg store sites in .data as G_* candidates",
        "session_requirement": classify_session_requirement(),
        "vtable_lea_xrefs": {
            "CGameState_primary": [{**h, "insn_rva": hex(h["insn_rva"])} for h in lea_primary[:20]],
            "CGameState_secondary": [{**h, "insn_rva": hex(h["insn_rva"])} for h in lea_secondary[:10]],
            "CCurrentGameState_primary": [{**h, "insn_rva": hex(h["insn_rva"])} for h in lea_cgs[:10]],
        },
        "G_GAMESTATE_static_candidates": candidates[:30],
        "extra_rtti": extra,
        "command_queue": cmd,
        "write_policy": "CLAUSEWITZ_ALLOW_WRITE ignored; FN_CMD_QUEUE_POST remains null/disabled",
    }
    path = os.path.join(ROOT, "research", "re-dumps", "phase2c_recover.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({
        "wrote": path,
        "n_gs_lea": len(lea_primary),
        "n_candidates": len(candidates),
        "top_candidates": [c["global_rva_candidate"] for c in candidates[:8]],
        "command_queue_post": None,
    }, indent=2))


if __name__ == "__main__":
    main()
