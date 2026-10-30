#!/usr/bin/env python3
"""Phase 2m: READ-ONLY — Idler/App/GS vtable slot shapes for Post-like methods;
light GS typed-ptr fields; air/character RTTI lea soft. No full-heap. Never post.
"""
from __future__ import annotations
import argparse, json, os, struct, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))
import offsets as O
from pe import PE
from msvc_rtti import scan_type_names, find_col_and_vtable
from stringscan import rip_lea_xrefs

KNOWN = {0x12AD90, 0x1DB710, 0x25A009C, 0x25A00D8, 0x25C7C74, 0x2284800, 0x2282810, 0x1B14F0, 0xE34E90}


def text_blob(pe):
    text = next(s for s in pe.sections if s.name == ".text")
    return text, pe.data[text.raw_ptr : text.raw_ptr + text.raw_size]


def dump_vtable(pe, rva, n=64):
    out = []
    for i in range(n):
        off = pe.rva_to_off(rva + i * 8)
        if off is None:
            break
        ptr = struct.unpack_from("<Q", pe.data, off)[0]
        mrva = ptr - pe.image_base if pe.image_base <= ptr < pe.image_base + 0x40000000 else None
        out.append({"slot": hex(i * 8), "method_rva": hex(mrva) if mrva is not None else None})
    return out


def characterize_fn(pe, fn_rva, nbytes=128):
    off = pe.rva_to_off(fn_rva)
    if off is None:
        return {"fn_rva": hex(fn_rva), "error": "bad"}
    raw = pe.data[off : off + nbytes]
    text, blob = text_blob(pe)
    lo, hi = text.virtual_address, text.virtual_address + text.virtual_size
    info = {
        "fn_rva": hex(fn_rva),
        "head": raw[:20].hex(),
        "calls": [],
        "rip": [],
        "loads": [],
        "stores": [],
        "vt_calls": [],
        "ret_early": False,
        "arg_uses_rdx_as_ptr": False,  # rough: mov rcx/rdx patterns
    }
    i = 0
    while i < len(raw) - 7:
        b = raw[i]
        if b == 0xC3:
            info["ret_early"] = i < 20
            break
        if b == 0xE8:
            rel = struct.unpack_from("<i", raw, i + 1)[0]
            tgt = (fn_rva + i + 5 + rel) & 0xFFFFFFFF
            if lo <= tgt < hi:
                info["calls"].append(hex(tgt))
            i += 5
            continue
        if raw[i : i + 2] in (b"\x48\x8b", b"\x4c\x8b") and (raw[i + 2] & 0xC7) == 0x05:
            rel = struct.unpack_from("<i", raw, i + 3)[0]
            info["rip"].append(hex((fn_rva + i + 7 + rel) & 0xFFFFFFFF))
            i += 7
            continue
        if raw[i] == 0x48 and raw[i + 1] == 0x8B and (raw[i + 2] & 0xC0) == 0x80:
            disp = struct.unpack_from("<i", raw, i + 3)[0]
            info["loads"].append(hex(disp if disp >= 0 else disp & 0xFFFFFFFF))
            i += 7
            continue
        if raw[i] == 0x48 and raw[i + 1] == 0x89 and (raw[i + 2] & 0xC0) in (0x40, 0x80):
            if (raw[i + 2] & 0xC0) == 0x40:
                info["stores"].append(hex(raw[i + 3]))
                i += 4
            else:
                disp = struct.unpack_from("<i", raw, i + 3)[0]
                info["stores"].append(hex(disp if disp >= 0 else disp & 0xFFFFFFFF))
                i += 7
            continue
        if b == 0xFF and ((raw[i + 1] >> 3) & 7) == 2:
            mod = (raw[i + 1] >> 6) & 3
            if mod == 1:
                info["vt_calls"].append(hex(raw[i + 2]))
                i += 3
                continue
            if mod == 2:
                disp = struct.unpack_from("<i", raw, i + 2)[0]
                info["vt_calls"].append(hex(disp))
                i += 6
                continue
        # mov rdx, r8 / mov rcx, rdx — weak signal second arg forwarded
        if raw[i : i + 3] in (b"\x48\x8b\xd2", b"\x49\x8b\xd0", b"\x48\x8b\xca"):
            info["arg_uses_rdx_as_ptr"] = True
        i += 1
    return info


def rtti_for_vt(pe, vt_rva):
    off = pe.rva_to_off(vt_rva - 8)
    if off is None:
        return ""
    col_va = struct.unpack_from("<Q", pe.data, off)[0]
    coff = pe.rva_to_off(col_va - pe.image_base)
    if coff is None:
        return ""
    _, _, _, td_rva = struct.unpack_from("<IIII", pe.data, coff)
    td_off = pe.rva_to_off(td_rva)
    if td_off is None:
        return ""
    return pe.data[td_off + 0x14 : td_off + 0x14 + 80].split(b"\x00", 1)[0].decode("latin1", "replace")


def recover_plain(pe, plain):
    want = ".?AV%s@@" % plain
    hits = [h for h in scan_type_names(pe, plain, limit=40) if h.get("name") == want]
    if not hits:
        return {"name": plain, "found": False}
    col = find_col_and_vtable(pe, hits[0]["td_rva"])
    return {
        "name": plain,
        "found": True,
        "vtables": [{"vtable_rva": hex(v["vtable_rva"]), "rtti": rtti_for_vt(pe, v["vtable_rva"])} for v in col.get("vtables", [])[:2]],
    }


def nearby_calls(pe, insn_rva, before=0x20, after=0x80):
    text, blob = text_blob(pe)
    base = text.virtual_address
    off = insn_rva - base
    out = []
    for i in range(max(0, off - before), min(len(blob) - 5, off + after)):
        if blob[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", blob, i + 1)[0]
        tgt = (base + i + 5 + rel) & 0xFFFFFFFF
        if base <= tgt < base + text.virtual_size:
            out.append(hex(tgt))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    exe = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
    if not os.path.isfile(exe):
        import config
        exe = config.binary_path(required=True)
    pe = PE(exe)
    out = {"phase": "2m", "FN_CMD_QUEUE_POST": None, "read_only": True}

    # Characterize Idler / App / GS vtables — look for methods that load a field then vt-call or store
    targets = {
        "CInGameIdler": O.PROVEN_STATIC["CInGameIdler_vtable"],
        "CGameApplication": O.PROVEN_STATIC["CGameApplication_vtable"],
        "CGameState": O.PROVEN_STATIC["CGameState_vtable"],
        "CCurrentGameState": O.PROVEN_STATIC["CCurrentGameState_vtable"],
    }
    vt_report = {}
    for name, vt in targets.items():
        slots = dump_vtable(pe, vt, 56)
        interesting = []
        for s in slots:
            if not s["method_rva"]:
                continue
            r = int(s["method_rva"], 16)
            if r in KNOWN:
                interesting.append({"slot": s["slot"], "fn": hex(r), "known_dead": True})
                continue
            ch = characterize_fn(pe, r, 112)
            # Post-like hyp: non-trivial, has field load(s), maybe store or forward call, not ret-early
            score = 0
            if ch.get("loads"):
                score += 2
            if ch.get("stores"):
                score += 1
            if ch.get("calls"):
                score += 1
            if ch.get("vt_calls"):
                score += 2
            if ch.get("rip"):
                score += 1
            if ch.get("ret_early"):
                score = 0
            if score >= 3:
                interesting.append({
                    "slot": s["slot"],
                    "fn": hex(r),
                    "score": score,
                    "loads": (ch.get("loads") or [])[:6],
                    "stores": (ch.get("stores") or [])[:4],
                    "calls": (ch.get("calls") or [])[:5],
                    "vt_calls": (ch.get("vt_calls") or [])[:4],
                    "rip": (ch.get("rip") or [])[:4],
                    "head": ch.get("head"),
                })
        vt_report[name] = {"vtable": hex(vt), "interesting_slots": interesting[:20], "slot_count": len(slots)}
    out["vtable_post_hyps"] = vt_report

    # Already-known idler vt+0x90 wrapper
    out["known_idler_vt90"] = characterize_fn(pe, O.PROVEN_STATIC["CInGameIdler_vt_post_wrapper"], 96)

    # AirWing / Character vtable LEA soft tops (construction sites)
    for plain in ("CAirWing", "CCharacter", "CUnitLeader", "CEquipmentVariant"):
        info = recover_plain(pe, plain)
        entry = {"found": info.get("found")}
        if info.get("found") and info.get("vtables"):
            vt = int(info["vtables"][0]["vtable_rva"], 16)
            leas = rip_lea_xrefs(pe, vt, max_hits=30)
            soft = Counter()
            for x in leas[:20]:
                for t in nearby_calls(pe, x["insn_rva"]):
                    soft[t] += 1
            entry["lea_count"] = len(leas)
            entry["soft_top"] = [{"tgt": t, "hits": n} for t, n in soft.most_common(8)]
            entry["vtable"] = hex(vt)
        out.setdefault("entity_lea", {})[plain] = entry

    if args.live:
        live = {"ok": False}
        try:
            import config
            from mem import Proc, find_pid
            from gamestate import detect_session, _pdx_array, _rtti_name_from_vtable

            pid = find_pid(config.EXE_NAME)
            p = Proc(pid)
            sess = detect_session(p, pe)
            live = {"ok": True, "pid": pid, "session": sess.get("session")}

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

            # Light: typed single-ptr fields on GS / Idler (not arrays) looking for queue-ish or air DB
            gs = sess.get("signals", {}).get("gs_ptr")
            idler = sess.get("signals", {}).get("idler_ptr")
            for label, base_ptr, span in (
                ("gs", gs, 0x700),
                ("idler", idler, 0x600),
            ):
                if not base_ptr:
                    continue
                bi = int(base_ptr, 16) if isinstance(base_ptr, str) else base_ptr
                typed = []
                for off in range(8, span, 8):
                    val = ru64(bi + off)
                    if not val or val < 0x10000:
                        continue
                    if p.base <= val < p.base + p.image_size:
                        continue
                    nm = rtti(val)
                    if not nm:
                        continue
                    # skip ubiquitous
                    if any(x in nm for x in ("CString", "CPdx", "std::", "type_info")):
                        continue
                    typed.append({"off": hex(off), "rtti": nm})
                live["%s_typed_ptrs" % label] = typed[:40]
                # interesting keywords
                live["%s_interesting" % label] = [
                    t for t in typed
                    if any(k in t["rtti"] for k in (
                        "Command", "Queue", "Air", "Character", "Leader", "Equipment",
                        "Naval", "Fleet", "Theatre", "Front", "Modifier", "Session",
                    ))
                ]

            # GS arrays (already know countries etc) — look for Air/Character keyword arrays only
            if gs:
                gi = int(gs, 16) if isinstance(gs, str) else gs
                arr_hits = []
                for off in range(0x200, 0x700, 8):
                    arr = _pdx_array(p, gi + off)
                    if not arr or not (0 < arr["size"] <= 5000 and arr["size"] <= arr["capacity"] <= 8000):
                        continue
                    names = []
                    for i in range(min(arr["size"], 2)):
                        e = ru64(arr["data"] + i * 8)
                        nm = rtti(e) if e else None
                        if nm:
                            names.append(nm)
                    if names and any(k in names[0] for k in ("Air", "Character", "Leader", "Command", "Wing", "Equipment")):
                        arr_hits.append({"off": hex(off), "size": arr["size"], "rtti": names})
                live["gs_keyword_arrays"] = arr_hits

            p.close()
        except Exception as e:
            live = {"ok": False, "error": str(e)}
        out["live"] = live

    out["verdict"] = {
        "FN_CMD_QUEUE_POST": None,
        "posting": "DISABLED",
        "reason": "2m vtable slot hyps + GS/idler typed ptrs — no independently proven Post.",
    }
    path = args.out or os.path.join(ROOT, "research", "re-dumps", "phase2m_vt_post_slots.json")
    open(path, "w", encoding="utf-8").write(json.dumps(out, indent=2))
    live = out.get("live") or {}
    summary = {
        "FN": None,
        "idler_interesting_n": len((vt_report.get("CInGameIdler") or {}).get("interesting_slots") or []),
        "app_interesting_n": len((vt_report.get("CGameApplication") or {}).get("interesting_slots") or []),
        "idler_top": ((vt_report.get("CInGameIdler") or {}).get("interesting_slots") or [])[:6],
        "app_top": ((vt_report.get("CGameApplication") or {}).get("interesting_slots") or [])[:6],
        "gs_interesting_ptrs": live.get("gs_interesting"),
        "idler_interesting_ptrs": live.get("idler_interesting"),
        "gs_keyword_arrays": live.get("gs_keyword_arrays"),
        "entity_lea": out.get("entity_lea"),
        "out": path,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
