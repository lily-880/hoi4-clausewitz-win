#!/usr/bin/env python3
"""Phase 2k: READ-ONLY continue CCommand Execute/soft-call graph for FN_CMD_QUEUE_POST.

Focus: 2-hop soft callees, store-like patterns near CCommand LEAs, more RTTI names,
light country typed-array sweep for status enrichment. NEVER posts/writes. No full-heap.
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
        out.append({"slot": hex(i * 8), "method_rva": hex(mrva) if mrva is not None else None})
    return out


def characterize_fn(pe: PE, fn_rva: int, nbytes: int = 128) -> dict:
    off = pe.rva_to_off(fn_rva)
    if off is None:
        return {"fn_rva": hex(fn_rva), "error": "bad"}
    raw = pe.data[off : off + nbytes]
    info = {
        "fn_rva": hex(fn_rva),
        "head": raw[:24].hex(),
        "calls": [],
        "rip_globals": [],
        "field_loads": [],
        "field_stores": [],
        "vt_calls": [],
        "new_like": False,
        "ret_early": False,
    }
    i = 0
    while i < len(raw) - 7:
        b = raw[i]
        if b == 0xC3:
            info["ret_early"] = i < 16
            break
        if b == 0xE8:
            rel = struct.unpack_from("<i", raw, i + 1)[0]
            info["calls"].append(hex((fn_rva + i + 5 + rel) & 0xFFFFFFFF))
            i += 5
            continue
        if raw[i : i + 2] in (b"\x48\x8b", b"\x4c\x8b") and (raw[i + 2] & 0xC7) == 0x05:
            rel = struct.unpack_from("<i", raw, i + 3)[0]
            info["rip_globals"].append(hex((fn_rva + i + 7 + rel) & 0xFFFFFFFF))
            i += 7
            continue
        # mov r64, [r64+disp32] load
        if raw[i] == 0x48 and raw[i + 1] == 0x8B and (raw[i + 2] & 0xC0) == 0x80:
            disp = struct.unpack_from("<i", raw, i + 3)[0]
            info["field_loads"].append(hex(disp if disp >= 0 else (disp & 0xFFFFFFFF)))
            i += 7
            continue
        # mov [r64+disp32], r64  store  48 89 8x
        if raw[i] == 0x48 and raw[i + 1] == 0x89 and (raw[i + 2] & 0xC0) == 0x80:
            disp = struct.unpack_from("<i", raw, i + 3)[0]
            info["field_stores"].append(hex(disp if disp >= 0 else (disp & 0xFFFFFFFF)))
            i += 7
            continue
        # mov [r64+disp8], r64
        if raw[i] == 0x48 and raw[i + 1] == 0x89 and (raw[i + 2] & 0xC0) == 0x40:
            info["field_stores"].append(hex(raw[i + 3]))
            i += 4
            continue
        if b == 0xFF:
            modrm = raw[i + 1]
            if ((modrm >> 3) & 7) == 2:
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
    # Heuristic: tiny leaf that only does alloc/string often has few stores and calls CRT
    if len(info["calls"]) <= 2 and len(info["field_stores"]) == 0 and not info["vt_calls"]:
        info["new_like"] = True
    return info


def nearby_calls(pe: PE, insn_rva: int, before: int = 0x30, after: int = 0x100) -> list:
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


def nearby_stores(pe: PE, insn_rva: int, before: int = 0x20, after: int = 0xC0) -> list:
    """Find mov [reg+disp], r64 near an insn (possible enqueue store)."""
    text, blob = text_blob(pe)
    base = text.virtual_address
    off = insn_rva - base
    lo = max(0, off - before)
    hi = min(len(blob) - 7, off + after)
    stores = []
    i = lo
    while i < hi:
        if blob[i] == 0x48 and blob[i + 1] == 0x89:
            modrm = blob[i + 2]
            mod = (modrm >> 6) & 3
            if mod == 1:
                stores.append({"at": hex(base + i), "disp": hex(blob[i + 3]), "form": "disp8",
                               "delta": (base + i) - insn_rva})
                i += 4
                continue
            if mod == 2:
                disp = struct.unpack_from("<i", blob, i + 3)[0]
                stores.append({"at": hex(base + i), "disp": hex(disp if disp >= 0 else disp & 0xFFFFFFFF),
                               "form": "disp32", "delta": (base + i) - insn_rva})
                i += 7
                continue
        i += 1
    return stores


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
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()

    exe = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
    if not os.path.isfile(exe):
        import config
        exe = config.binary_path(required=True)
    pe = PE(exe)

    out = {
        "phase": "2k",
        "read_only": True,
        "policy": "FN_CMD_QUEUE_POST DISABLED until independently proven; never write/post on guess",
        "FN_CMD_QUEUE_POST": None,
        "prior_dead_ends": [
            "idler+0x530 = CGameApplication setter (not queue)",
            "CSession typed = CDummyServer only",
            "no CCommandQueue RTTI",
            "OEC type-id registry 0x2284800/0x2282810 global 0x34ffbf0 = factory NOT queue",
            "soft tops 0x12ad90/0x1db710 SSO helpers; 0x25a009c/0x25a00d8 destroy/refcount",
        ],
    }

    # --- 2-hop soft graph from CCommand LEAs (exclude known helpers) ---
    known_helpers = {
        0x12AD90, 0x1DB710, 0x25A009C, 0x25A00D8, 0x25C7C74,
        0x2284800, 0x2282810, 0x22888A0,
    }
    cmd_leas = rip_lea_xrefs(pe, CMD_VT, max_hits=80)
    hop1 = Counter()
    store_near_lea = []
    for x in cmd_leas[:60]:
        ir = x["insn_rva"]
        for c in nearby_calls(pe, ir, before=0x28, after=0xC0):
            hop1[c["tgt"]] += 1
        stores = nearby_stores(pe, ir, before=0x10, after=0xA0)
        if stores:
            store_near_lea.append({
                "lea_rva": hex(ir),
                "stores": stores[:6],
                "nearby_e8": [c["tgt"] for c in nearby_calls(pe, ir, before=0x10, after=0x80)[:6]],
            })
    out["CCommand_lea_xref_count"] = len(cmd_leas)
    out["hop1_soft_top"] = [{"tgt": t, "hits": n} for t, n in hop1.most_common(20)]
    out["store_sites_near_CCommand_lea"] = store_near_lea[:25]

    # Characterize hop1 excluding known helpers; then hop2 from those
    hop1_shapes = []
    hop2 = Counter()
    candidates = []
    for t, n in hop1.most_common(24):
        r = int(t, 16)
        ch = characterize_fn(pe, r, 144)
        ch["hits"] = n
        ch["known_helper"] = r in known_helpers
        hop1_shapes.append(ch)
        if r in known_helpers or ch.get("new_like") or ch.get("ret_early"):
            continue
        # hop2: follow this fn's E8s
        for c2 in ch.get("calls") or []:
            hop2[c2] += 1
        # candidate: has field_stores AND (rip_global or vt_call) — possible enqueue into object
        if ch.get("field_stores") and (ch.get("rip_globals") or ch.get("vt_calls") or len(ch.get("calls") or []) >= 2):
            candidates.append({
                "fn_rva": t,
                "hits": n,
                "stores": (ch.get("field_stores") or [])[:8],
                "loads": (ch.get("field_loads") or [])[:8],
                "rip": (ch.get("rip_globals") or [])[:6],
                "calls": (ch.get("calls") or [])[:8],
                "vt_calls": (ch.get("vt_calls") or [])[:4],
                "why": "stores+context — NOT promoted; needs live enqueue proof",
            })
    out["hop1_shapes"] = [
        {k: v for k, v in s.items() if k in ("fn_rva", "hits", "known_helper", "new_like", "ret_early",
                                               "calls", "field_stores", "field_loads", "rip_globals", "vt_calls", "head")}
        for s in hop1_shapes[:16]
    ]
    out["enqueue_store_candidates"] = candidates[:12]
    out["hop2_soft_top"] = [{"tgt": t, "hits": n} for t, n in hop2.most_common(16)]
    out["hop2_shapes"] = []
    for t, n in hop2.most_common(10):
        r = int(t, 16)
        if r in known_helpers:
            continue
        ch = characterize_fn(pe, r, 128)
        ch["hits"] = n
        ch["known_helper"] = False
        out["hop2_shapes"].append({
            "fn_rva": t, "hits": n, "new_like": ch.get("new_like"), "ret_early": ch.get("ret_early"),
            "calls": (ch.get("calls") or [])[:6], "stores": (ch.get("field_stores") or [])[:6],
            "loads": (ch.get("field_loads") or [])[:6], "rip": (ch.get("rip_globals") or [])[:4],
            "vt_calls": (ch.get("vt_calls") or [])[:3], "head": ch.get("head"),
        })

    # --- OEC override deeper: follow override method calls for store patterns ---
    oec = recover_plain(pe, "COrderExecuteCommand")
    out["COrderExecuteCommand"] = oec
    oec_deep = []
    if oec.get("found") and oec.get("vtables"):
        ovt = int(oec["vtables"][0]["vtable_rva"], 16)
        cmd_vt = dump_vtable(pe, CMD_VT, 40)
        oslots = dump_vtable(pe, ovt, 40)
        for a, b in zip(cmd_vt, oslots):
            if a.get("method_rva") == b.get("method_rva") or not b.get("method_rva"):
                continue
            mr = int(b["method_rva"], 16)
            ch = characterize_fn(pe, mr, 160)
            # 1-hop from override
            child_shapes = []
            for c in (ch.get("calls") or [])[:8]:
                cr = int(c, 16)
                if cr in known_helpers:
                    child_shapes.append({"fn_rva": c, "known_helper": True})
                    continue
                cc = characterize_fn(pe, cr, 96)
                child_shapes.append({
                    "fn_rva": c,
                    "stores": (cc.get("field_stores") or [])[:4],
                    "rip": (cc.get("rip_globals") or [])[:4],
                    "calls": (cc.get("calls") or [])[:4],
                    "new_like": cc.get("new_like"),
                    "vt_calls": (cc.get("vt_calls") or [])[:2],
                })
            oec_deep.append({
                "slot": a["slot"],
                "override_rva": b["method_rva"],
                "stores": (ch.get("field_stores") or [])[:6],
                "rip": (ch.get("rip_globals") or [])[:4],
                "calls": (ch.get("calls") or [])[:8],
                "children": child_shapes,
            })
    out["oec_override_deep"] = oec_deep[:10]

    # --- Extra RTTI names that might own a queue ---
    rtti_probe = {}
    for plain in (
        "CCommand", "COrderExecuteCommand", "CClientPingCommand",
        "CNetCommand", "CNetworkCommand", "CSyncCommand",
        "CPendingCommand", "CCommandList", "CCommandBuffer",
        "CGameCommand", "CHumanCommand", "CServerCommand",
        "CCommandHandler", "CCommandProcessor", "CCommandDispatcher",
        "CCommandManager", "CConsoleCmdManager", "CChatCommand",
        "CMultiplayerCommand", "CSession", "CDummyServer",
        "CAirWing", "CAirBase", "CStrategicRegion", "CTheater",
        "CCharacter", "CLeader", "CGeneral", "CAdmiral",
        "CEquipment", "CEquipmentVariant", "CUnitLeader",
    ):
        rtti_probe[plain] = recover_plain(pe, plain)
    # substring sweep
    mgr = []
    airish = []
    charish = []
    for h in scan_type_names(pe, "Command", limit=250):
        n = h.get("name") or ""
        if any(k in n for k in ("Manager", "Handler", "Processor", "Dispatcher", "Queue", "Buffer", "List", "Pending")):
            mgr.append(n)
    for needle, bucket in (("Air", airish), ("Character", charish), ("Leader", charish), ("Theater", airish)):
        for h in scan_type_names(pe, needle, limit=80):
            n = h.get("name") or ""
            if n.startswith(".?AV") and len(n) < 80:
                bucket.append(n)
    out["rtti_probe"] = {k: {"found": v.get("found"), "vtables": v.get("vtables")} for k, v in rtti_probe.items()}
    out["command_managerish"] = sorted(set(mgr))[:40]
    out["air_theater_rtti_sample"] = sorted(set(airish))[:30]
    out["character_leader_rtti_sample"] = sorted(set(charish))[:30]

    # String leads: enqueue/store wording
    str_leads = {}
    for label in (
        b"PostCommand", b"post_command", b"PushCommand", b"AddCommand",
        b"Enqueue", b"enqueue", b"command queue", b"Queued command",
        b"SendCommand", b"submit command", b"ExecuteCommand",
        b"Failed to execute",
    ):
        rvas = find_ascii_all(pe, label)
        xrefs = []
        for r in rvas[:3]:
            for x in rip_lea_xrefs(pe, r, max_hits=3):
                xrefs.append({
                    "string_rva": hex(r),
                    "insn_rva": hex(x["insn_rva"]),
                    "nearby_calls": [c["tgt"] for c in nearby_calls(pe, x["insn_rva"])[:6]],
                    "nearby_stores": nearby_stores(pe, x["insn_rva"])[:4],
                })
        str_leads[label.decode("latin1", "replace")] = {
            "count": len(rvas),
            "sample": [hex(r) for r in rvas[:4]],
            "lea_xrefs": xrefs[:6],
        }
    out["string_leads"] = str_leads

    # Live: light country typed-array sweep + confirm no Command arrays
    if args.live:
        live = {"ok": False}
        try:
            import config
            from mem import Proc, find_pid
            from gamestate import detect_session, _pdx_array, _rtti_name_from_vtable, probe_player_armies

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

                # Player country light sweep for typed ptr arrays (status enrichment)
                country_typed = []
                pc = None
                try:
                    gs = sess.get("signals", {}).get("gs_ptr")
                    if gs:
                        gs_i = int(gs, 16) if isinstance(gs, str) else gs
                        blob = p.try_read(gs_i, 0x530)
                        if blob and len(blob) >= 0x520:
                            tag = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT["GS_PLAYER_TAG"])[0]
                            carr = _pdx_array(p, gs_i + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
                            if carr and 0 <= tag < carr["size"]:
                                pc = ru64(carr["data"] + tag * 8)
                                live["player_tag"] = tag
                                live["country_ptr"] = hex(pc) if pc else None
                        try:
                            ap = probe_player_armies(p, pe, gs_i)
                            live["armies_probe"] = {
                                k: ap.get(k)
                                for k in (
                                    "ok",
                                    "armies_count",
                                    "fleets_count",
                                    "div_templates_count",
                                    "divisions_count",
                                )
                                if k in ap
                            }
                        except Exception as e:
                            live["armies_probe_err"] = str(e)
                except Exception as e:
                    live["country_resolve_err"] = str(e)

                if pc:
                    # sweep country+0x100..0x3f0 for PdxArray of typed ptrs
                    for off in range(0x100, 0x400, 8):
                        arr = _pdx_array(p, pc + off)
                        if not arr or not (0 < arr["size"] <= 500 and arr["size"] <= arr["capacity"] <= 2000):
                            continue
                        if not arr["data"] or arr["data"] < 0x10000:
                            continue
                        names = []
                        for i in range(min(arr["size"], 2)):
                            e = ru64(arr["data"] + i * 8)
                            nm = rtti(e) if e else None
                            if nm:
                                names.append(nm)
                        if not names:
                            continue
                        country_typed.append({
                            "off": hex(off),
                            "size": arr["size"],
                            "capacity": arr["capacity"],
                            "first_rtti": names[0],
                            "sample_rtti": names,
                        })
                    live["country_typed_arrays"] = country_typed
                    # highlight interesting not-yet-promoted
                    known_off = {0x1B8, 0x278, 0x290}
                    newish = [x for x in country_typed if int(x["off"], 16) not in known_off]
                    live["country_typed_new_candidates"] = newish

                # Idler: narrow scan for Command* arrays (0..0x600) — no heap
                idler = sess.get("signals", {}).get("idler_ptr")
                if idler:
                    id_i = int(idler, 16) if isinstance(idler, str) else idler
                    cmd_on_idler = []
                    for off in range(0, 0x600, 8):
                        arr = _pdx_array(p, id_i + off)
                        if not arr or not (0 < arr["size"] <= 200 and arr["size"] <= arr["capacity"] <= 1000):
                            continue
                        names = []
                        for i in range(min(arr["size"], 2)):
                            e = ru64(arr["data"] + i * 8)
                            nm = rtti(e) if e else None
                            if nm:
                                names.append(nm)
                        if names and any("Command" in n for n in names):
                            cmd_on_idler.append({"off": hex(off), "size": arr["size"], "names": names})
                    live["idler_command_arrays"] = cmd_on_idler

                p.close()
        except Exception as e:
            live = {"ok": False, "error": str(e)}
        out["live"] = live

    # Verdict — never promote on guess
    store_cand_note = "none"
    if out.get("enqueue_store_candidates"):
        store_cand_note = "%d soft fns with stores+context (unproven)" % len(out["enqueue_store_candidates"])
    out["verdict"] = {
        "FN_CMD_QUEUE_POST": None,
        "posting": "DISABLED",
        "reason": (
            "No enqueue Post proven. 2-hop soft graph + store-near-LEA + OEC deep still "
            "lack a single callee that stores live CCommand* into a queue container. "
            "Prior dead-ends hold (idler+0x530, CDummyServer, no CCommandQueue, type-id registry). "
            "Candidates documented only: %s." % store_cand_note
        ),
    }

    text = json.dumps(out, indent=2)
    print(text)
    path = args.out or os.path.join(ROOT, "research", "re-dumps", "phase2k_cmd_store_graph.json")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
    live = out.get("live") or {}
    summary = {
        "FN_CMD_QUEUE_POST": None,
        "hop1_top": out.get("hop1_soft_top", [])[:5],
        "store_candidates": len(out.get("enqueue_store_candidates") or []),
        "store_sites_near_lea": len(out.get("store_sites_near_CCommand_lea") or []),
        "oec_deep": len(out.get("oec_override_deep") or []),
        "managerish": (out.get("command_managerish") or [])[:8],
        "live_ok": live.get("ok"),
        "country_typed": len(live.get("country_typed_arrays") or []),
        "country_new": live.get("country_typed_new_candidates"),
        "idler_cmd_arr": live.get("idler_command_arrays"),
        "out": path,
    }
    print("---SUMMARY---")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
