#!/usr/bin/env python3
"""Phase 2l: READ-ONLY Post leads — candidate globals, CTheatre nest, Chat/Ping LEAs.

No full-heap. Never posts/writes. FN_CMD_QUEUE_POST stays null unless proven.
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
KNOWN = {
    0x12AD90, 0x1DB710, 0x25A009C, 0x25A00D8, 0x25C7C74,
    0x2284800, 0x2282810, 0x22888A0, 0x254AA00,
}


def text_blob(pe: PE):
    text = next(s for s in pe.sections if s.name == ".text")
    return text, pe.data[text.raw_ptr : text.raw_ptr + text.raw_size]


def characterize_fn(pe: PE, fn_rva: int, nbytes: int = 160) -> dict:
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
            tgt = (fn_rva + i + 5 + rel) & 0xFFFFFFFF
            # only keep plausible .text targets (filter bad disasm)
            info["calls"].append(hex(tgt))
            i += 5
            continue
        if raw[i : i + 2] in (b"\x48\x8b", b"\x4c\x8b") and (raw[i + 2] & 0xC7) == 0x05:
            rel = struct.unpack_from("<i", raw, i + 3)[0]
            info["rip_globals"].append(hex((fn_rva + i + 7 + rel) & 0xFFFFFFFF))
            i += 7
            continue
        if raw[i] == 0x48 and raw[i + 1] == 0x8B and (raw[i + 2] & 0xC0) == 0x80:
            disp = struct.unpack_from("<i", raw, i + 3)[0]
            info["field_loads"].append(hex(disp if disp >= 0 else (disp & 0xFFFFFFFF)))
            i += 7
            continue
        if raw[i] == 0x48 and raw[i + 1] == 0x89 and (raw[i + 2] & 0xC0) == 0x80:
            disp = struct.unpack_from("<i", raw, i + 3)[0]
            info["field_stores"].append(hex(disp if disp >= 0 else (disp & 0xFFFFFFFF)))
            i += 7
            continue
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
            calls.append({"at": hex(base + i), "tgt": hex(tgt)})
    return calls


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
    hits = [h for h in scan_type_names(pe, plain, limit=60) if h.get("name") == want]
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
            for v in col.get("vtables", [])[:3]
        ],
    }


def dump_vtable(pe: PE, rva: int, n: int = 32) -> list:
    out = []
    for i in range(n):
        off = pe.rva_to_off(rva + i * 8)
        if off is None:
            break
        ptr = struct.unpack_from("<Q", pe.data, off)[0]
        mrva = ptr - pe.image_base if pe.image_base <= ptr < pe.image_base + 0x40000000 else None
        out.append({"slot": hex(i * 8), "method_rva": hex(mrva) if mrva is not None else None})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    exe = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
    if not os.path.isfile(exe):
        import config
        exe = config.binary_path(required=True)
    pe = PE(exe)
    text, blob = text_blob(pe)
    text_lo, text_hi = text.virtual_address, text.virtual_address + text.virtual_size

    out = {
        "phase": "2l",
        "read_only": True,
        "FN_CMD_QUEUE_POST": None,
        "prior_dead_ends": [
            "idler+0x530 App setter",
            "CDummyServer session",
            "no CCommandQueue RTTI",
            "type-id registry 0x2284800/0x34ffbf0",
            "2k store+context softs unproven",
        ],
    }

    # --- Re-characterize priority 2k candidates with text-filtered calls ---
    priority = [0x1F7640, 0xE21CF0, 0x6B8880, 0xC917C0, 0xDDCFF0, 0x11F6F0, 0x11F770]
    cand = []
    for r in priority:
        ch = characterize_fn(pe, r, 192)
        good_calls = [c for c in (ch.get("calls") or []) if text_lo <= int(c, 16) < text_hi]
        bad_calls = [c for c in (ch.get("calls") or []) if not (text_lo <= int(c, 16) < text_hi)]
        child = []
        for c in good_calls[:8]:
            cr = int(c, 16)
            if cr in KNOWN:
                child.append({"fn": c, "known": True})
                continue
            cc = characterize_fn(pe, cr, 96)
            child.append({
                "fn": c,
                "known": False,
                "stores": (cc.get("field_stores") or [])[:4],
                "rip": (cc.get("rip_globals") or [])[:4],
                "calls_in_text": [x for x in (cc.get("calls") or []) if text_lo <= int(x, 16) < text_hi][:4],
                "head": cc.get("head"),
            })
        cand.append({
            "fn_rva": hex(r),
            "stores": (ch.get("field_stores") or [])[:8],
            "loads": (ch.get("field_loads") or [])[:8],
            "rip": (ch.get("rip_globals") or [])[:6],
            "vt_calls": (ch.get("vt_calls") or [])[:4],
            "calls_in_text": good_calls[:10],
            "calls_out_of_text": bad_calls[:6],
            "children": child,
            "head": ch.get("head"),
        })
    out["priority_candidates"] = cand

    # --- Chat / Ping command LEAs ---
    cmd_subclasses = {}
    for plain in ("CClientPingCommand", "CChatCommand", "COrderExecuteCommand"):
        info = recover_plain(pe, plain)
        cmd_subclasses[plain] = info
        if info.get("found") and info.get("vtables"):
            vt = int(info["vtables"][0]["vtable_rva"], 16)
            leas = rip_lea_xrefs(pe, vt, max_hits=40)
            soft = Counter()
            for x in leas[:30]:
                for c in nearby_calls(pe, x["insn_rva"], before=0x20, after=0xC0):
                    soft[c["tgt"]] += 1
            top = [{"tgt": t, "hits": n} for t, n in soft.most_common(12)]
            shapes = []
            for t, n in soft.most_common(6):
                r = int(t, 16)
                ch = characterize_fn(pe, r, 128)
                shapes.append({
                    "tgt": t, "hits": n, "known": r in KNOWN,
                    "stores": (ch.get("field_stores") or [])[:4],
                    "rip": (ch.get("rip_globals") or [])[:4],
                    "calls_in_text": [c for c in (ch.get("calls") or []) if text_lo <= int(c, 16) < text_hi][:5],
                    "head": ch.get("head"),
                })
            cmd_subclasses[plain]["lea_count"] = len(leas)
            cmd_subclasses[plain]["soft_top"] = top
            cmd_subclasses[plain]["soft_shapes"] = shapes
    out["subclass_lea_soft"] = {
        k: {kk: vv for kk, vv in v.items() if kk != "vtables" or True}
        for k, v in cmd_subclasses.items()
    }

    # --- CTheatre / CAirWing / CCharacter static recover ---
    for plain in ("CTheatre", "CAirWing", "CCharacter", "CUnitLeader", "CState"):
        out.setdefault("rtti", {})[plain] = recover_plain(pe, plain)

    # Live
    if args.live:
        live = {"ok": False}
        try:
            import config
            from mem import Proc, find_pid
            from gamestate import detect_session, _pdx_array, _rtti_name_from_vtable

            pid = find_pid(config.EXE_NAME)
            p = Proc(pid)
            sess = detect_session(p, pe)
            live = {"ok": True, "pid": pid, "session": sess.get("session"), "FN_CMD_QUEUE_POST": None}

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

            # Type priority RIP globals from candidates
            rip_targets = set()
            for c in cand:
                for g in c.get("rip") or []:
                    rip_targets.add(int(g, 16))
            # also known interesting
            rip_targets.update([0x33DEA38, 0x34FFBF0, 0x33DD090, 0x33DD6B0, 0x33DDB08, 0x33DDB10])
            typed_globals = []
            for rva in sorted(rip_targets):
                if rva < 0x1000 or rva > 0x4000000:
                    continue
                val = ru64(p.base + rva)
                entry = {"rva": hex(rva), "value": hex(val) if val else None}
                if val and val > 0x10000:
                    if p.base <= val < p.base + p.image_size:
                        entry["points_into_image"] = True
                    else:
                        entry["as_obj_rtti"] = rtti(val)
                        # if ptr-to-ptr
                        v2 = ru64(val)
                        if v2:
                            entry["deref_rtti"] = rtti(v2)
                            if not entry.get("as_obj_rtti") and p.base <= v2 < p.base + p.image_size:
                                entry["maybe_vt_rva"] = hex(v2 - p.base)
                typed_globals.append(entry)
            live["candidate_rip_globals"] = typed_globals

            # Player country + theatre nest sweep
            gs = sess.get("signals", {}).get("gs_ptr")
            if gs:
                gs_i = int(gs, 16) if isinstance(gs, str) else gs
                blob = p.try_read(gs_i, 0x530)
                tag = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT["GS_PLAYER_TAG"])[0]
                carr = _pdx_array(p, gs_i + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
                pc = ru64(carr["data"] + tag * 8) if carr else None
                live["player_tag"] = tag
                live["country"] = hex(pc) if pc else None
                if pc:
                    th_arr = _pdx_array(p, pc + O.HYPOTHESIS_STRUCT.get("CO_THEATRES", 0x168))
                    theatre_nest = []
                    if th_arr and th_arr["size"] > 0:
                        for ti in range(min(th_arr["size"], 2)):
                            th = ru64(th_arr["data"] + ti * 8)
                            if not th:
                                continue
                            nest = {"theatre": hex(th), "rtti": rtti(th), "typed": []}
                            # sweep theatre object 0x20..0x400
                            for off in range(0x20, 0x400, 8):
                                arr = _pdx_array(p, th + off)
                                if not arr or not (0 < arr["size"] <= 2000 and arr["size"] <= arr["capacity"] <= 4000):
                                    continue
                                names = []
                                for i in range(min(arr["size"], 2)):
                                    e = ru64(arr["data"] + i * 8)
                                    nm = rtti(e) if e else None
                                    if nm:
                                        names.append(nm)
                                if names:
                                    nest["typed"].append({"off": hex(off), "size": arr["size"], "rtti": names})
                            theatre_nest.append(nest)
                    live["theatre_nest"] = theatre_nest

                    # Also sweep country 0x400..0x600 for air/character (extend beyond 2k)
                    extra = []
                    for off in range(0x400, 0x600, 8):
                        if off in (0x460, 0x478):
                            continue  # known states
                        arr = _pdx_array(p, pc + off)
                        if not arr or not (0 < arr["size"] <= 2000 and arr["size"] <= arr["capacity"] <= 4000):
                            continue
                        names = []
                        for i in range(min(arr["size"], 2)):
                            e = ru64(arr["data"] + i * 8)
                            nm = rtti(e) if e else None
                            if nm:
                                names.append(nm)
                        if names:
                            extra.append({"off": hex(off), "size": arr["size"], "rtti": names})
                    live["country_extra_0x400_0x600"] = extra

                    # One major: same theatre nest + country extra for air
                    marr = _pdx_array(p, gs_i + O.HYPOTHESIS_STRUCT["GS_MAJORS"])
                    if marr and marr["size"] > 0:
                        # majors store CCountry*
                        mp = ru64(marr["data"])
                        if mp and rtti(mp) and "Country" in (rtti(mp) or ""):
                            maj_extra = []
                            for off in list(range(0x100, 0x200, 8)) + list(range(0x400, 0x600, 8)):
                                arr = _pdx_array(p, mp + off)
                                if not arr or not (0 < arr["size"] <= 5000 and arr["size"] <= arr["capacity"] <= 8000):
                                    continue
                                names = []
                                for i in range(min(arr["size"], 2)):
                                    e = ru64(arr["data"] + i * 8)
                                    nm = rtti(e) if e else None
                                    if nm:
                                        names.append(nm)
                                if names and any(k in names[0] for k in ("Air", "Character", "Leader", "Wing", "Equipment")):
                                    maj_extra.append({"off": hex(off), "size": arr["size"], "rtti": names})
                            # also dump all typed on major theatre
                            th_arr2 = _pdx_array(p, mp + 0x168)
                            maj_th = []
                            if th_arr2 and th_arr2["size"] > 0:
                                th = ru64(th_arr2["data"])
                                if th:
                                    for off in range(0x20, 0x500, 8):
                                        arr = _pdx_array(p, th + off)
                                        if not arr or not (0 < arr["size"] <= 5000 and arr["size"] <= arr["capacity"] <= 8000):
                                            continue
                                        names = []
                                        for i in range(min(arr["size"], 2)):
                                            e = ru64(arr["data"] + i * 8)
                                            nm = rtti(e) if e else None
                                            if nm:
                                                names.append(nm)
                                        if names:
                                            maj_th.append({"off": hex(off), "size": arr["size"], "rtti": names})
                            live["major0"] = {
                                "ptr": hex(mp),
                                "rtti": rtti(mp),
                                "interesting_arrays": maj_extra,
                                "theatre_typed": maj_th,
                            }

            p.close()
        except Exception as e:
            live = {"ok": False, "error": str(e)}
        out["live"] = live

    out["verdict"] = {
        "FN_CMD_QUEUE_POST": None,
        "posting": "DISABLED",
        "reason": (
            "Phase 2l: priority candidates re-filtered; Chat/Ping LEA softs checked; "
            "theatre nest + country extra swept. No independently proven enqueue Post."
        ),
    }

    text_out = json.dumps(out, indent=2)
    path = args.out or os.path.join(ROOT, "research", "re-dumps", "phase2l_post_leads.json")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "w", encoding="utf-8").write(text_out)
    live = out.get("live") or {}
    summary = {
        "FN": None,
        "cands": [{k: c.get(k) for k in ("fn_rva", "rip", "stores", "calls_in_text")} for c in cand],
        "ping_soft": (cmd_subclasses.get("CClientPingCommand") or {}).get("soft_top", [])[:5],
        "chat_soft": (cmd_subclasses.get("CChatCommand") or {}).get("soft_top", [])[:5],
        "live_ok": live.get("ok"),
        "theatre_nest": live.get("theatre_nest"),
        "country_extra": live.get("country_extra_0x400_0x600"),
        "major0_interesting": (live.get("major0") or {}).get("interesting_arrays"),
        "major0_theatre": (live.get("major0") or {}).get("theatre_typed"),
        "rip_globals": live.get("candidate_rip_globals"),
        "out": path,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
