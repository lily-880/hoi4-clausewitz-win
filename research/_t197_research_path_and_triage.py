# -*- coding: utf-8 -*-
from __future__ import annotations
import json, re, struct
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys_path_note = str(ROOT / "calling")
import sys
sys.path.insert(0, sys_path_note)

from pe import PE

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
OUT = ROOT / "research" / "t197_path_gate_and_triage.json"

# prefer existing disasm helper if present
try:
    from research_disasm import disasm_rva, clip_function  # type: ignore
except Exception:
    disasm_rva = None


def try_capstone(pe, rva, nbytes=0x400):
    try:
        import capstone
    except ImportError:
        return None, "no capstone"
    data = pe.read(rva, nbytes)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = False
    lines = []
    for i in md.disasm(data, 0x140000000 + rva):
        lines.append(f"0x{i.address - 0x140000000:x}  {i.mnemonic} {i.op_str}")
        if i.mnemonic in {"ret", "int3"} and len(lines) > 8:
            # don't stop early; function may have many rets in exception paths
            pass
    return lines, None


def find_clip_helper():
    hits = []
    for p in (ROOT / "research").glob("_t194*.py"):
        t = p.read_text(encoding="utf-8", errors="ignore")
        if "capstone" in t or "Cs(" in t or "disasm" in t:
            hits.append(str(p))
    for p in (ROOT / "calling").glob("*.py"):
        if "disasm" in p.name.lower() or p.name.lower() in {"asm.py", "clip.py"}:
            hits.append(str(p))
    return hits


def main():
    out = {"clip_helpers": find_clip_helper()}
    pe = PE(EXE)
    # 0x10b8620 is the NewFront gate
    for rva, name, n in (
        (0x10B8620, "path_gate_0x10b8620", 0x500),
        (0x10B0D90, "copy_path_0x10b0d90", 0x300),
        (0xC41BB0, "maybe_new_instance_0xc41bb0", 0x200),
        (0xC41620, "maybe_prep_0xc41620", 0x200),
        (0x10AF100, "newfront_10af100", 0x300),
    ):
        lines, err = try_capstone(pe, rva, n)
        rec = {"rva": hex(rva), "err": err, "n_lines": len(lines or [])}
        if lines:
            rec["head"] = lines[:80]
            # interesting stores / calls
            rec["calls"] = [ln for ln in lines if "call " in ln][:40]
            rec["stores_70"] = [ln for ln in lines if "+ 0x70" in ln or "+0x70" in ln or "0x70]" in ln]
        out[name] = rec

    # t190 blocked / boundary
    triage = json.loads((ROOT / "research/t190_unverified_triage.json").read_text(encoding="utf-8"))
    blocked = triage.get("blocked_or_boundary") or {}
    out["t190_blocked_or_boundary_type"] = type(blocked).__name__
    if isinstance(blocked, dict):
        out["t190_blocked"] = blocked.get("blocked")
        out["t190_boundary"] = blocked.get("boundary")
    else:
        out["t190_blocked_raw"] = blocked

    # unverified structure
    uv = triage.get("unverified")
    out["t190_unverified_type"] = type(uv).__name__
    if isinstance(uv, dict):
        out["t190_unverified_keys"] = list(uv.keys())[:40]
    elif isinstance(uv, list):
        out["t190_unverified_len"] = len(uv)
        if uv:
            out["t190_unverified_item0_keys"] = list(uv[0].keys()) if isinstance(uv[0], dict) else type(uv[0]).__name__
            out["t190_unverified_item0"] = uv[0] if isinstance(uv[0], dict) else str(uv[0])[:500]

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

    compact = {
        "helpers": out["clip_helpers"],
        "capstone_ok": out["path_gate_0x10b8620"].get("err"),
        "gate_head": out["path_gate_0x10b8620"].get("head"),
        "gate_calls": out["path_gate_0x10b8620"].get("calls"),
        "copy_path_stores_70": out["copy_path_0x10b0d90"].get("stores_70"),
        "copy_path_head": (out["copy_path_0x10b0d90"].get("head") or [])[:40],
        "c41bb0_head": out["maybe_new_instance_0xc41bb0"].get("head"),
        "t190_unverified_type": out["t190_unverified_type"],
        "t190_blocked_type": out["t190_blocked_or_boundary_type"],
    }
    # shrink blocked for stdout
    b = out.get("t190_blocked")
    if isinstance(b, dict):
        compact["blocked_fields"] = list(b.keys()) if all(isinstance(k, str) for k in b) else type(b).__name__
    elif isinstance(b, list):
        compact["blocked_n"] = len(b)
        compact["blocked_sample"] = [
            {k: (str(v)[:200] if not isinstance(v, (list, dict)) else k) for k, v in (item.items() if isinstance(item, dict) else [])}
            if isinstance(item, dict) else str(item)[:200]
            for item in b[:15]
        ]
    bnd = out.get("t190_boundary")
    if isinstance(bnd, list):
        compact["boundary_n"] = len(bnd)
        compact["boundary_sample"] = [str(x)[:240] if not isinstance(x, dict) else {k: str(v)[:160] for k, v in list(x.items())[:8]} for x in bnd[:15]]
    elif isinstance(bnd, dict):
        compact["boundary_keys"] = list(bnd.keys())[:30]
    print(json.dumps(compact, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
