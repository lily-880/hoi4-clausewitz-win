#!/usr/bin/env python3
"""Phase 2j: READ-ONLY CCommand soft-call / Execute graph hunt for FN_CMD_QUEUE_POST.

Static PE analysis + light live probes (no full-heap). NEVER posts/writes.
FN_CMD_QUEUE_POST stays null unless a single clear Post callee is proven.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

import offsets as O
from pe import PE
from msvc_rtti import scan_type_names, find_col_and_vtable
from stringscan import find_ascii_all, rip_lea_xrefs

CMD_VT = O.PROVEN_STATIC["CCommand_vtable"]
IDLER_VT = O.PROVEN_STATIC["CInGameIdler_vtable"]
APP_VT = O.PROVEN_STATIC["CGameApplication_vtable"]


def text_blob(pe: PE):
    text = next(s for s in pe.sections if s.name == ".text")
    return text, pe.data[text.raw_ptr : text.raw_ptr + text.raw_size]


def dump_vtable(pe: PE, rva: int, n: int = 48) -> list:
    out = []
    for i in range(n):
        off = pe.rva_to_off(rva + i * 8)
        if off is None:
            break
        ptr = struct.unpack_from("<Q", pe.data, off)[0]
        mrva = ptr - pe.image_base if pe.image_base <= ptr < pe.image_base + 0x40000000 else None
        head = ""
        if mrva is not None:
            fo = pe.rva_to_off(mrva)
            if fo is not None:
                head = pe.data[fo : fo + 24].hex()
        out.append({"slot": hex(i * 8), "method_rva": hex(mrva) if mrva is not None else None, "head": head})
    return out


def characterize_fn(pe: PE, fn_rva: int, nbytes: int = 96) -> dict:
    off = pe.rva_to_off(fn_rva)
    if off is None:
        return {"fn_rva": hex(fn_rva), "error": "bad"}
    raw = pe.data[off : off + nbytes]
    info = {
        "fn_rva": hex(fn_rva),
        "size_probe": nbytes,
        "head": raw[:32].hex(),
        "calls": [],
        "rip_globals": [],
        "field_loads": [],
        "vt_calls": [],  # call [reg+imm]
        "ret_early": False,
    }
    i = 0
    while i < len(raw) - 7:
        b = raw[i]
        # ret
        if b == 0xC3:
            info["ret_early"] = i < 16
            break
        # E8 call
        if b == 0xE8:
            rel = struct.unpack_from("<i", raw, i + 1)[0]
            info["calls"].append(hex((fn_rva + i + 5 + rel) & 0xFFFFFFFF))
            i += 5
            continue
        # mov r64, [rip+disp]
        if raw[i : i + 2] in (b"\x48\x8b", b"\x4c\x8b") and (raw[i + 2] & 0xC7) == 0x05:
            rel = struct.unpack_from("<i", raw, i + 3)[0]
            info["rip_globals"].append(hex((fn_rva + i + 7 + rel) & 0xFFFFFFFF))
            i += 7
            continue
        # mov r64, [r64+disp32] 48 8B 8x with mod=10
        if raw[i] == 0x48 and raw[i + 1] == 0x8B and (raw[i + 2] & 0xC0) == 0x80:
            disp = struct.unpack_from("<i", raw, i + 3)[0]
            info["field_loads"].append(hex(disp if disp >= 0 else (disp & 0xFFFFFFFF)))
            i += 7
            continue
        # call qword ptr [rax/rcx/rdx/rbx+imm8] : FF 50/51/52/53 xx  or FF 90/91.. disp32
        if b == 0xFF:
            modrm = raw[i + 1]
            reg_op = (modrm >> 3) & 7
            if reg_op == 2:  # call
                mod = (modrm >> 6) & 3
                rm = modrm & 7
                if mod == 1 and i + 2 < len(raw):
                    info["vt_calls"].append({"rm": rm, "slot": hex(raw[i + 2])})
                    i += 3
                    continue
                if mod == 2 and i + 5 < len(raw):
                    disp = struct.unpack_from("<i", raw, i + 2)[0]
                    info["vt_calls"].append({"rm": rm, "slot": hex(disp)})
                    i += 6
                    continue
        i += 1
    return info


def nearby_calls(pe: PE, insn_rva: int, before: int = 0x30, after: int = 0x120) -> list:
    text, blob = text_blob(pe)
    base = text.virtual_address
    off = insn_rva - base
    lo = max(0, off - before)
    hi = min(len(blob) - 5, off + after)
    calls = []
    for i in range(lo, hi):
        if blob[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", blob, i + 1)[0]
        tgt = (base + i + 5 + rel) & 0xFFFFFFFF
        if base <= tgt < base + text.virtual_size:
            calls.append({"at": hex(base + i), "tgt": hex(tgt), "delta": (base + i) - insn_rva})
    return calls


def find_vt_call_sites(pe: PE, slot: int, limit: int = 40) -> list:
    """Find call [reg+slot] sites in .text (imm8 or imm32). Bounded sample."""
    text, blob = text_blob(pe)
    base = text.virtual_address
    hits = []
    i = 0
    n = len(blob)
    while i < n - 6 and len(hits) < limit:
        if blob[i] != 0xFF:
            i += 1
            continue
        modrm = blob[i + 1]
        if ((modrm >> 3) & 7) != 2:
            i += 1
            continue
        mod = (modrm >> 6) & 3
        if mod == 1 and blob[i + 2] == (slot & 0xFF) and slot < 0x80:
            hits.append({"insn_rva": hex(base + i), "form": "imm8", "slot": hex(slot)})
            i += 3
            continue
        if mod == 2:
            disp = struct.unpack_from("<i", blob, i + 2)[0]
            if disp == slot:
                hits.append({"insn_rva": hex(base + i), "form": "imm32", "slot": hex(slot)})
                i += 6
                continue
        i += 1
    return hits


def rtti_for_vt(pe: PE, vt_rva: int) -> str:
    off = pe.rva_to_off(vt_rva - 8)
    if off is None:
        return ""
    col_va = struct.unpack_from("<Q", pe.data, off)[0]
    col_rva = col_va - pe.image_base
    coff = pe.rva_to_off(col_rva)
    if coff is None:
        return ""
    _, _, _, td_rva = struct.unpack_from("<IIII", pe.data, coff)
    td_off = pe.rva_to_off(td_rva)
    if td_off is None:
        return ""
    return pe.data[td_off + 0x14 : td_off + 0x14 + 96].split(b"\x00", 1)[0].decode("latin1", "replace")


def recover_plain(pe: PE, plain: str) -> dict:
    want = ".?AV%s@@" % plain
    hits = [h for h in scan_type_names(pe, plain, limit=80) if h.get("name") == want]
    if not hits:
        return {"name": plain, "found": False}
    td = hits[0]["td_rva"]
    col = find_col_and_vtable(pe, td)
    return {
        "name": plain,
        "found": True,
        "td_rva": hex(td),
        "vtables": [
            {"vtable_rva": hex(v["vtable_rva"]), "rtti": rtti_for_vt(pe, v["vtable_rva"])}
            for v in col.get("vtables", [])[:4]
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--live", action="store_true", help="also light live probes (no heap)")
    args = ap.parse_args()

    exe = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
    if not os.path.isfile(exe):
        import config

        exe = config.binary_path(required=True)
    pe = PE(exe)

    out = {
        "phase": "2j",
        "read_only": True,
        "policy": "FN_CMD_QUEUE_POST DISABLED until independently proven; candidates only",
        "FN_CMD_QUEUE_POST": None,
        "prior_dead_ends": [
            "idler+0x530 = CGameApplication setter (not queue)",
            "CSession typed = CDummyServer only",
            "no CCommandQueue RTTI",
            "QueueCommand ASCII = IndustrialOrgTrait*QueueCommand subclasses",
        ],
    }

    # --- CCommand vtable characterize ---
    cmd_vt = dump_vtable(pe, CMD_VT, 40)
    out["CCommand_vtable"] = cmd_vt
    # Unique method RVAs and which look non-trivial
    method_chars = {}
    for m in cmd_vt:
        if not m["method_rva"]:
            continue
        r = int(m["method_rva"], 16)
        if r not in method_chars:
            method_chars[r] = characterize_fn(pe, r, 80)
            method_chars[r]["slots"] = []
        method_chars[r]["slots"].append(m["slot"])
    out["CCommand_method_shapes"] = [
        {
            "fn_rva": hex(r),
            "slots": v["slots"],
            "calls": v.get("calls", [])[:6],
            "vt_calls": v.get("vt_calls", [])[:4],
            "field_loads": v.get("field_loads", [])[:6],
            "rip_globals": v.get("rip_globals", [])[:4],
            "ret_early": v.get("ret_early"),
            "head": v.get("head"),
        }
        for r, v in sorted(method_chars.items(), key=lambda kv: min(int(s, 16) for s in kv[1]["slots"]))
    ]

    # Heuristic: Execute-like slots often mid-vtable and non-trivial (have calls / not ret 0)
    # Prior probe showed slot 0x18 / 0x20 large; 0x28 xor al,al ret; 0x30 ret 0
    execute_slot_hyps = []
    for m in cmd_vt:
        if not m["method_rva"]:
            continue
        r = int(m["method_rva"], 16)
        ch = method_chars[r]
        nontrivial = (not ch.get("ret_early")) and (len(ch.get("calls", [])) > 0 or len(ch.get("vt_calls", [])) > 0)
        if nontrivial and int(m["slot"], 16) >= 0x10:
            execute_slot_hyps.append(m["slot"])
    out["execute_slot_hypotheses"] = execute_slot_hyps[:8]

    # Sample call sites for first few Execute-like slots (bounded)
    vt_call_samples = {}
    for slot_hex in execute_slot_hyps[:3]:
        slot = int(slot_hex, 16)
        sites = find_vt_call_sites(pe, slot, limit=25)
        # nearby soft calls after each site
        enriched = []
        for s in sites[:12]:
            ir = int(s["insn_rva"], 16)
            calls = nearby_calls(pe, ir, before=0x10, after=0x80)
            enriched.append({**s, "nearby_e8": calls[:8]})
        vt_call_samples[slot_hex] = enriched
    out["vt_call_sites_sample"] = vt_call_samples

    # Aggregate soft targets near vt-call sites
    soft_near_exec = Counter()
    for sites in vt_call_samples.values():
        for s in sites:
            for c in s.get("nearby_e8") or []:
                soft_near_exec[c["tgt"]] += 1
    out["soft_near_execute_calls"] = [
        {"target_rva": t, "hits": n} for t, n in soft_near_exec.most_common(15)
    ]
    out["soft_near_execute_shapes"] = [
        characterize_fn(pe, int(t, 16), 96)
        for t, _ in soft_near_exec.most_common(8)
    ]

    # --- Soft targets near CCommand LEAs (reconfirm + characterize top) ---
    cmd_leas = rip_lea_xrefs(pe, CMD_VT, max_hits=100)
    soft = Counter()
    for x in cmd_leas:
        for c in nearby_calls(pe, x["insn_rva"], before=0x20, after=0x100):
            soft[c["tgt"]] += 1
    out["CCommand_lea_xref_count"] = len(cmd_leas)
    out["soft_near_CCommand_lea"] = [{"target_rva": t, "hits": n} for t, n in soft.most_common(12)]
    out["soft_near_CCommand_lea_shapes"] = [
        characterize_fn(pe, int(t, 16), 96) for t, _ in soft.most_common(6)
    ]

    # --- CCommandHelper / OrderExecute / Console ---
    types = {}
    for plain in (
        "CCommand",
        "COrderExecuteCommand",
        "CClientPingCommand",
        "CConsoleCmdManager",
        "CCommandHelper",
    ):
        types[plain] = recover_plain(pe, plain)
    # substring sweep for *Command*Manager* / *Command*Handler*
    mgr_hits = []
    for h in scan_type_names(pe, "Command", limit=200):
        n = h.get("name") or ""
        if any(k in n for k in ("Manager", "Handler", "Processor", "Dispatcher", "Queue", "Runner")):
            mgr_hits.append(n)
    out["command_managerish_rtti"] = sorted(set(mgr_hits))[:40]
    out["rtti_types"] = types

    # If COrderExecuteCommand found, dump its vt vs CCommand (override map)
    oec = types.get("COrderExecuteCommand") or {}
    if oec.get("found") and oec.get("vtables"):
        ovt = int(oec["vtables"][0]["vtable_rva"], 16)
        oslots = dump_vtable(pe, ovt, 40)
        diffs = []
        for a, b in zip(cmd_vt, oslots):
            if a.get("method_rva") != b.get("method_rva"):
                diffs.append({"slot": a["slot"], "CCommand": a.get("method_rva"), "COrderExecuteCommand": b.get("method_rva")})
        out["COrderExecuteCommand_overrides"] = diffs[:20]
        # Characterize overridden methods
        out["COrderExecuteCommand_override_shapes"] = [
            characterize_fn(pe, int(d["COrderExecuteCommand"], 16), 96)
            for d in diffs[:6]
            if d.get("COrderExecuteCommand")
        ]

    # String leads (failure / post / enqueue)
    str_leads = {}
    for label in (
        b"Failed to execute",
        b"execute command",
        b"ExecuteCommand",
        b"Posting",
        b"command queue",
        b"Command queued",
        b"AddCommand",
        b"PushCommand",
        b"QueueCommand",
    ):
        rvas = find_ascii_all(pe, label)
        xrefs = []
        for r in rvas[:4]:
            for x in rip_lea_xrefs(pe, r, max_hits=4):
                xrefs.append(
                    {
                        "string_rva": hex(r),
                        "insn_rva": hex(x["insn_rva"]),
                        "nearby_calls": [c["tgt"] for c in nearby_calls(pe, x["insn_rva"])[:6]],
                    }
                )
        str_leads[label.decode("latin1", "replace")] = {
            "count": len(rvas),
            "sample_rvas": [hex(r) for r in rvas[:6]],
            "lea_xrefs": xrefs[:8],
        }
    out["string_leads"] = str_leads

    # Idler wrapper helper (0x22888a0 from 2e) + App vt+0x90 already known
    wrapper_helper = characterize_fn(pe, 0x22888A0, 128)
    out["idler_wrapper_helper_0x22888a0"] = wrapper_helper
    app_vt90 = O.PROVEN_STATIC.get("CGameApplication_vt90_setter", 0x1B14F0)
    out["app_vt90_shape"] = characterize_fn(pe, app_vt90, 96)

    # Global near G_GAMESTATE / G_IDLER: scan .data for names? light: check slots around G_IDLER
    g_gs = O.WINDOWS_GLOBALS.get("G_GAMESTATE") or 0x33DD6B0
    g_id = O.WINDOWS_GLOBALS.get("G_IDLER") or 0x33DDB08
    out["globals_context"] = {
        "G_GAMESTATE": hex(g_gs),
        "G_IDLER": hex(g_id),
        "idler_wrapper_global_load": "0x33dd090",  # from 2e
    }

    # Live light probes
    if args.live:
        live = {"ok": False}
        try:
            import config
            from mem import Proc, find_pid
            from gamestate import detect_session, _pdx_array, _rtti_name_from_vtable

            pid = find_pid(config.EXE_NAME)
            if not pid:
                live["error"] = "hoi4 not running"
            else:
                p = Proc(pid)
                sess = detect_session(p, pe)
                live = {
                    "ok": True,
                    "pid": pid,
                    "session": sess.get("session"),
                    "command_queue": "DISABLED",
                    "FN_CMD_QUEUE_POST": None,
                }
                # Light: read global at idler wrapper load 0x33dd090
                def ru64(a):
                    b = p.try_read(a, 8)
                    return struct.unpack_from("<Q", b, 0)[0] if b and len(b) == 8 else None

                def rtti(ptr):
                    if not ptr:
                        return None
                    vt = ru64(ptr)
                    if not vt or not (p.base <= vt < p.base + p.image_size):
                        return None
                    return _rtti_name_from_vtable(pe, vt - p.base)

                slot = p.base + 0x33DD090
                live["global_0x33dd090"] = {
                    "slot": hex(slot),
                    "value": hex(ru64(slot) or 0),
                    "as_obj_rtti": rtti(ru64(slot)) if ru64(slot) and ru64(slot) > 0x10000 else None,
                }
                # Neighbor globals around G_IDLER / G_GAMESTATE (typed ptrs only)
                neighbors = []
                for rva in range(g_gs - 0x80, g_id + 0x80, 8):
                    if rva < 0:
                        continue
                    val = ru64(p.base + rva)
                    if not val or val < 0x100000:
                        continue
                    if p.base <= val < p.base + p.image_size:
                        continue
                    nm = rtti(val)
                    if nm:
                        neighbors.append({"rva": hex(rva), "rtti": nm})
                live["typed_globals_near_GS_IDLER"] = neighbors
                # GS: look for any array whose elems are CCommand subclasses (already done 2i — recheck narrow)
                gs = sess.get("signals", {}).get("gs_ptr")
                if gs:
                    gs_i = int(gs, 16) if isinstance(gs, str) else gs
                    cmd_arr = []
                    for off in range(0, 0x600, 8):
                        arr = _pdx_array(p, gs_i + off)
                        if not arr or not (0 < arr["size"] <= 500 and arr["size"] <= arr["capacity"] <= 2000):
                            continue
                        if not arr["data"] or arr["data"] < 0x10000:
                            continue
                        names = []
                        for i in range(min(arr["size"], 3)):
                            e = ru64(arr["data"] + i * 8)
                            nm = rtti(e) if e else None
                            if nm:
                                names.append(nm)
                        if names and any("Command" in n for n in names):
                            cmd_arr.append({"off": hex(off), "size": arr["size"], "names": names})
                    live["gs_command_arrays"] = cmd_arr
                p.close()
        except Exception as e:
            live = {"ok": False, "error": str(e)}
        out["live"] = live

    # Verdict
    out["verdict"] = {
        "FN_CMD_QUEUE_POST": None,
        "posting": "DISABLED",
        "reason": (
            "No single callee proven to take CCommand* and enqueue. "
            "Soft targets near CCommand LEAs / Execute vt-calls remain untyped helpers; "
            "prior idler+0x530 path stays REJECTED. Do not promote."
        ),
        "next_leads": [
            "If Execute slot hyp confirmed via COrderExecuteCommand override, chase sole caller that stores CCommand* into a container",
            "Trace CConsoleCmdManager if present (alternate command path)",
            "Avoid promoting multi-hit soft helpers (new/refcount)",
        ],
    }

    text = json.dumps(out, indent=2)
    print(text)
    path = args.out or os.path.join(ROOT, "research", "re-dumps", "phase2j_cmd_execute_graph.json")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
    # short summary to stderr-like via trailing print
    summary = {
        "FN_CMD_QUEUE_POST": None,
        "execute_slot_hyps": out.get("execute_slot_hypotheses"),
        "soft_near_exec_top": out.get("soft_near_execute_calls", [])[:5],
        "soft_near_lea_top": out.get("soft_near_CCommand_lea", [])[:5],
        "managerish": out.get("command_managerish_rtti", [])[:10],
        "oec_overrides": len(out.get("COrderExecuteCommand_overrides") or []),
        "live_ok": (out.get("live") or {}).get("ok"),
        "out": path,
    }
    print("---SUMMARY---")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
