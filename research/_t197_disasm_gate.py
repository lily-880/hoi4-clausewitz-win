# -*- coding: utf-8 -*-
from __future__ import annotations
import json, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
from pe import PE

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
OUT = ROOT / "research" / "t197_path_gate_disasm.json"
pe = PE(EXE)
cs = Cs(CS_ARCH_X86, CS_MODE_64)


def dump(rva, n):
    off = pe.rva_to_off(rva)
    blob = pe.data[off:off + n]
    lines = []
    for i in cs.disasm(blob, rva):
        lines.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
    return lines


def main():
    out = {}
    for rva, name, n in (
        (0x10B8620, "path_gate_0x10b8620", 0x600),
        (0x10B0D90, "copy_path_0x10b0d90", 0x280),
        (0xC41BB0, "maybe_new_instance_0xc41bb0", 0x180),
        (0xC41620, "maybe_prep_0xc41620", 0x180),
        (0x10AF100, "newfront_10af100", 0x280),
    ):
        lines = dump(rva, n)
        rec = {
            "n": len(lines),
            "head": lines[:100],
            "calls": [ln for ln in lines if "  call " in ln][:50],
            "mentions_70": [ln for ln in lines if "0x70" in ln],
            "mentions_258": [ln for ln in lines if "0x258" in ln or "0x25c" in ln or "0x25C" in ln],
        }
        out[name] = rec
        # also write clip
        (ROOT / "research" / f"_t197_clip_{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # t190 blocked/boundary compact
    triage = json.loads((ROOT / "research/t190_unverified_triage.json").read_text(encoding="utf-8"))
    blocked = triage.get("blocked_or_boundary") or {}
    out["t190_meta"] = {
        "blocked_type": type(blocked).__name__,
        "unverified_type": type(triage.get("unverified")).__name__,
        "top_keys": list(triage.keys()),
    }
    if isinstance(blocked, dict):
        def slim(obj, depth=0):
            if isinstance(obj, dict):
                if depth >= 2:
                    return {k: (str(v)[:240] if not isinstance(v, (dict, list)) else type(v).__name__ + ":" + str(len(v))) for k, v in list(obj.items())[:20]}
                return {k: slim(v, depth + 1) for k, v in list(obj.items())[:40]}
            if isinstance(obj, list):
                return [slim(x, depth + 1) for x in obj[:25]]
            return obj
        out["t190_blocked_or_boundary"] = slim(blocked)

    uv = triage.get("unverified")
    if isinstance(uv, dict):
        out["t190_unverified_keys"] = list(uv.keys())
    elif isinstance(uv, list) and uv:
        # maybe list of {field, ...}
        fields = []
        for item in uv:
            if isinstance(item, dict) and "field" in item:
                fields.append({k: (str(item[k])[:300] if k != "field" else item[k]) for k in item})
            elif isinstance(item, str):
                fields.append(item)
            elif isinstance(item, dict):
                fields.append({k: str(v)[:200] for k, v in list(item.items())[:8]})
        out["t190_unverified_items"] = fields

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

    compact = {
        "gate_head": out["path_gate_0x10b8620"]["head"][:70],
        "gate_calls": out["path_gate_0x10b8620"]["calls"],
        "gate_70": out["path_gate_0x10b8620"]["mentions_70"],
        "copy_head": out["copy_path_0x10b0d90"]["head"][:50],
        "copy_70": out["copy_path_0x10b0d90"]["mentions_70"],
        "c41bb0_head": out["maybe_new_instance_0xc41bb0"]["head"][:40],
        "t190_meta": out["t190_meta"],
        "t190_blocked_or_boundary": out.get("t190_blocked_or_boundary"),
        "t190_unverified_n": len(out.get("t190_unverified_items") or out.get("t190_unverified_keys") or []),
    }
    print(json.dumps(compact, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
