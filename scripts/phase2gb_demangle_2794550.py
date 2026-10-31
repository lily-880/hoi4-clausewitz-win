#!/usr/bin/env python3
"""Phase 2gb: demangle soft VT RVA 0x2794550 (Instance+0x100 packed twin) RO.
No Post. Never 5x. allow_post False.
"""
from __future__ import annotations

import json
import os
import struct
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "calling"))

from pe import PE  # noqa: E402
from msvc_rtti import demangle_simple, scan_type_names  # noqa: E402

TARGET_VT = 0x2794550
def try_read(b, addr, n):
    try:
        return b.read(addr, n)
    except Exception:
        return None


def u64(b, a):
    raw = try_read(b, a, 8)
    if not raw or len(raw) < 8:
        return None
    return struct.unpack("<Q", raw)[0]


def i32(b, a):
    raw = try_read(b, a, 4)
    if not raw or len(raw) < 4:
        return None
    return struct.unpack("<i", raw)[0]


def rtti_name_at_vtable(pe: PE, vt_rva: int) -> dict:
    """MSVC SI: *(vtable-8) -> COL VA; COL+0x0C -> TypeDescriptor RVA; TD+0x10 name."""
    out = {"vtable_rva": hex(vt_rva)}
    off = pe.rva_to_off(vt_rva - 8)
    if off is None:
        out["error"] = "vt-8 not in PE image"
        return out
    col_va = struct.unpack_from("<Q", pe.data, off)[0]
    out["col_va"] = hex(col_va)
    col_rva = col_va - pe.image_base
    out["col_rva"] = hex(col_rva & 0xFFFFFFFFFFFFFFFF)
    if col_rva < 0 or col_rva > 0x10000000:
        out["error"] = "col_rva out of range (not a real vtable COL ptr)"
        return out
    coff = pe.rva_to_off(col_rva)
    if coff is None:
        out["error"] = "COL RVA not mapped"
        return out
    sig, off_field, cd, td_rva = struct.unpack_from("<IIII", pe.data, coff)
    out["col_sig"] = sig
    out["col_offset"] = off_field
    out["col_cd"] = cd
    out["td_rva"] = hex(td_rva)
    if sig not in (0, 1):
        out["error"] = f"COL signature {sig} not MSVC RTTI"
        return out
    td_off = pe.rva_to_off(td_rva)
    if td_off is None:
        out["error"] = "TD RVA not mapped"
        return out
    # Prefer +0x10 (x64 TypeDescriptor.name); also report +0x14 for legacy scripts
    name10 = pe.data[td_off + 0x10 : td_off + 0x10 + 96].split(b"\x00", 1)[0].decode("latin1", "replace")
    name14 = pe.data[td_off + 0x14 : td_off + 0x14 + 96].split(b"\x00", 1)[0].decode("latin1", "replace")
    out["name_raw_at_0x10"] = name10
    out["name_raw_at_0x14"] = name14
    pick = name10 if name10.startswith(".?A") else (name14 if name14.startswith(".?A") else name10)
    out["name_raw"] = pick
    out["demangled"] = demangle_simple(pick) if pick else None
    out["ok"] = bool(pick and pick.startswith(".?A"))
    return out


def probe_vt_slots(pe: PE, vt_rva: int, nslots: int = 8) -> list:
    """First few vtable method RVAs (sanity: should land in .text)."""
    out = []
    off = pe.rva_to_off(vt_rva)
    if off is None:
        return out
    text = next((s for s in pe.sections if s.name == ".text"), None)
    for i in range(nslots):
        va = struct.unpack_from("<Q", pe.data, off + i * 8)[0]
        rva = va - pe.image_base
        in_text = bool(text and text.virtual_address <= rva < text.virtual_address + text.virtual_size)
        out.append({"slot": i, "method_rva": hex(rva & 0xFFFFFFFFFFFFFFFF), "in_text": in_text})
    return out


def nearby_type_names(pe: PE, needle_sub: str = "", limit: int = 30) -> list:
    """Optional: scan all .?AV near catalog if demangle fails — not inventing."""
    hits = []
    for prefix in (b".?AV", b".?AU"):
        from stringscan import find_ascii_all

        for rva in find_ascii_all(pe, prefix):
            raw = pe.read_rva(rva, 128) or b""
            end = raw.find(b"\0")
            name = raw[: end if end >= 0 else len(raw)].decode("ascii", "replace")
            if needle_sub and needle_sub not in name:
                continue
            hits.append({"name": name, "demangled": demangle_simple(name), "name_rva": hex(rva)})
            if len(hits) >= limit:
                return hits
    return hits


def resolve_handle(b, type_id, idx, base):
    # Same pattern as phase2ga
    from process import WINDOWS_OFFSETS  # may fail; fall back

    raise NotImplementedError


def live_sample_soft_vt(b, base, target_vt=TARGET_VT):
    """Re-walk Instance+0x100 opaque qwords; count soft VT hits matching target."""
    from process import find_pid
    import importlib.util

    ga_path = ROOT / "scripts" / "phase2ga_e100_elem_type.py"
    spec = importlib.util.spec_from_file_location("phase2ga_e100_elem_type", ga_path)
    ga = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ga)

    live = ga.live_meta(b, base)
    live["scenario"] = "ITA@1x demangle VT 0x2794550 (no Post)"
    live["pid"] = find_pid()

    soft_hits = []
    vt_counter = Counter()
    ois = set(range(0, 80))
    for oi in (4, 5, 6, 7, 8, 9, 13, 17, 20, 22, 25, 27, 38, 40, 44, 52, 68, 70, 124):
        ois.add(oi)

    nonempty = 0
    for oi in sorted(ois):
        rec = ga.read_inst(b, base, oi)
        if not rec or not rec.get("vt_ok"):
            continue
        e = rec.get("e100") or {}
        if e.get("empty"):
            continue
        nonempty += 1
        for pelem in e.get("ptr_elems_sample") or []:
            vr = pelem.get("vt_rva")
            if vr:
                try:
                    vt_counter[int(vr, 16)] += 1
                except Exception:
                    pass
            if vr and int(vr, 16) == target_vt:
                soft_hits.append({
                    "oi": oi,
                    "inst": rec.get("inst"),
                    "ptr": pelem.get("ptr"),
                    "vt_rva": vr,
                    "kind": pelem.get("kind"),
                })
        for s16 in e.get("stride16_sample") or []:
            for key in ("q0_class", "q1_class"):
                cls = s16.get(key) or {}
                vr = cls.get("vt_rva")
                if not vr:
                    continue
                try:
                    vt_counter[int(vr, 16)] += 1
                except Exception:
                    continue
                if int(vr, 16) == target_vt:
                    soft_hits.append({
                        "oi": oi,
                        "inst": rec.get("inst"),
                        "ptr": cls.get("ptr"),
                        "vt_rva": vr,
                        "kind": cls.get("kind"),
                        "via": key,
                    })

    return {
        "live": live,
        "nonempty_ois_scanned": nonempty,
        "soft_hit_count_target": len(soft_hits),
        "soft_hits_sample": soft_hits[:12],
        "vt_counter_top": [{"vt_rva": hex(k), "n": v} for k, v in vt_counter.most_common(10)],
    }



def main():
    allow_post = False
    assert allow_post is False

    # --- Static PE demangle ---
    exe_candidates = [
        ROOT / "research" / "re-dumps" / "hoi4_1.19.4.exe",
        Path(os.environ.get("HOI4_EXE", "")),
    ]
    exe = next((p for p in exe_candidates if p and p.is_file()), None)
    if exe is None:
        try:
            import config

            exe = Path(config.binary_path(required=True))
        except Exception as e:
            exe = None
            pe_err = str(e)
    pe_report = {"exe": str(exe) if exe else None, "target_vt_rva": hex(TARGET_VT)}
    if exe:
        pe = PE(str(exe))
        pe_report["image_base"] = hex(pe.image_base)
        pe_report["rtti"] = rtti_name_at_vtable(pe, TARGET_VT)
        pe_report["vtable_slots"] = probe_vt_slots(pe, TARGET_VT, 8)
        pe_report["slots_in_text"] = sum(1 for s in pe_report["vtable_slots"] if s.get("in_text"))
        # Neighbor check: try ±0x0..±0x40 aligned in case soft VT was mid-table
        neighbors = []
        for delta in range(-0x40, 0x48, 8):
            if delta == 0:
                continue
            cand = TARGET_VT + delta
            if cand <= 0:
                continue
            info = rtti_name_at_vtable(pe, cand)
            if info.get("ok"):
                neighbors.append({"delta": delta, **{k: info[k] for k in ("vtable_rva", "demangled", "name_raw", "col_rva")}})
            if len(neighbors) >= 6:
                break
        pe_report["nearby_ok_vtables"] = neighbors
        # Does any known catalog type use this VT?
        catalog_hit = None
        for plain in ("CProvince", "CArmy", "COrderInstance", "COrdersGroup", "CFront", "CUnit", "CNavy", "CAirWing"):
            hits = [h for h in scan_type_names(pe, plain, limit=8) if demangle_simple(h["name"]) == plain]
            if hits:
                # cheap: only record if name exists; full COL match not required here
                pass
        pe_report["catalog_plain_probe_note"] = "name existence only; binding via rtti_name_at_vtable above"
    else:
        pe_report["error"] = "no hoi4 exe found"

    # --- Live soft-VT reconfirm (RO) ---
    live_report = {"skipped": True}
    try:
        from process import Backend, find_pid

        b = Backend()
        base = b.image_base
        live_report = live_sample_soft_vt(b, base)
        live_report["skipped"] = False
        live_report["image_base"] = hex(base)
        live_report["allow_post"] = False
    except Exception as e:
        live_report = {"skipped": True, "error": repr(e)}

    rtti = pe_report.get("rtti") or {}
    demangled = rtti.get("demangled") if rtti.get("ok") else None
    slots_ok = pe_report.get("slots_in_text", 0)
    if demangled and slots_ok >= 4:
        result = f"vt_2794550_named__{demangled}"
        note = f"VT 0x2794550 demangles to {demangled}; COL/TD ok; {slots_ok}/8 slots in .text"
    elif demangled:
        result = f"vt_2794550_weak_named__{demangled}"
        note = f"TD name {demangled} but only {slots_ok}/8 method slots in .text — weak"
    elif pe_report.get("nearby_ok_vtables"):
        near = pe_report["nearby_ok_vtables"][0]
        result = "vt_2794550_not_vtable__nearby_named"
        note = (
            f"0x2794550 itself not a real MSVC vtable ({rtti.get('error')}); "
            f"nearby delta {near['delta']} → {near.get('demangled')}"
        )
    else:
        result = "vt_2794550_not_real_msvc_vtable__catalog_miss"
        note = (
            f"0x2794550 fails COL/RTTI demangle ({rtti.get('error')}); "
            f"slots_in_text={slots_ok}; soft hits were wrong-stride/packed-data artifact — no invent"
        )

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
        f"result={result}",
        "static PE COL→TD demangle attempted for 0x2794550",
        "live soft-VT recount (if Backend attached)",
    ]
    stubbed = [
        "in-process ring embed",
        "2fb recipe execution",
        "ordinary CMove live leaf",
        "SAFE_POST / ALLOW_POST",
        "self-MOVE",
        "tool-gate open",
        "Post inject",
        "war-dense relaunch (B preferred this slice)",
        "named CArmy path-field offsets",
        "HourlyTick abuse",
        "Capstone/121 re-churn",
        "NewFallback subject type-id table",
        "live midflight NewFallback hex",
        "demangled RTTI string dump for VT 0x29d6fb8 beyond catalog",
        "named +0xe0 role beyond u32 province stream",
    ]
    if not demangled:
        stubbed.append("named +0x100 Clausewitz elem class (0x2794550 not a real VT)")

    next_blocker = (
        "NON-Post: bounded NF/RF midflight OR war-dense named CArmy path; still NO ALLOW_POST"
    )

    summary = {
        "phase": "2gb",
        "allow_post": False,
        "result": result,
        "result_note": note,
        "live": (live_report.get("live") if isinstance(live_report, dict) else None),
        "pe": pe_report,
        "live_soft": {k: live_report.get(k) for k in (
            "skipped", "error", "nonempty_ois_scanned", "soft_hit_count_target",
            "soft_hits_sample", "vt_counter_top", "image_base", "allow_post",
        ) if isinstance(live_report, dict)},
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
    }

    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "phase2gb_demangle_2794550.json").write_text(json.dumps({
        "pe": pe_report,
        "live_soft": live_report,
    }, indent=2), encoding="utf-8")
    (out_dir / "phase2gb_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({
        "result": result,
        "note": note,
        "demangled": demangled,
        "slots_in_text": slots_ok,
        "rtti_error": rtti.get("error"),
        "live_soft_hits": (live_report or {}).get("soft_hit_count_target"),
        "ui_date": (summary.get("live") or {}).get("ui_date"),
        "allow_post": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
