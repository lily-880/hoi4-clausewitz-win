# -*- coding: utf-8 -*-
import json
from pathlib import Path
p = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win\research\t197_path_gate_disasm.json")
d = json.loads(p.read_text(encoding="utf-8"))
out = {
    "t190_meta": d.get("t190_meta"),
    "t190_unverified_n": d.get("t190_unverified_n") or (len(d.get("t190_unverified_items") or d.get("t190_unverified_keys") or [])),
    "t190_blocked_or_boundary": d.get("t190_blocked_or_boundary"),
    "t190_unverified_keys_or_items_head": (d.get("t190_unverified_keys") or d.get("t190_unverified_items") or [])[:20],
}
# print all of gate head and copy head, c41bb0
for name in ("path_gate_0x10b8620", "copy_path_0x10b0d90", "maybe_new_instance_0xc41bb0", "maybe_prep_0xc41620", "newfront_10af100"):
    rec = d[name]
    out[name] = {
        "n": rec["n"],
        "head": rec["head"],
        "calls": rec["calls"],
        "mentions_70": rec["mentions_70"],
        "mentions_258": rec["mentions_258"],
    }
Path(r"C:\Users\Lenovo\agent-tools\t197_disasm_summary.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
print("wrote summary", len(json.dumps(out)))
# print t190 + first 80 lines of gate only to stdout
print("===== T190 =====")
print(json.dumps({k: out[k] for k in out if k.startswith("t190")}, indent=2, ensure_ascii=False)[:8000])
print("===== GATE HEAD =====")
print("\n".join(out["path_gate_0x10b8620"]["head"][:80]))
print("===== GATE CALLS =====")
print("\n".join(out["path_gate_0x10b8620"]["calls"]))
print("===== COPY PATH HEAD =====")
print("\n".join(out["copy_path_0x10b0d90"]["head"][:60]))
print("===== C41BB0 =====")
print("\n".join(out["maybe_new_instance_0xc41bb0"]["head"][:40]))
print("===== 10AF100 CALLS =====")
print("\n".join(out["newfront_10af100"]["calls"]))
