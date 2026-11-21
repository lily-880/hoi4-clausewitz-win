# -*- coding: utf-8 -*-
import json
from pathlib import Path
p = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win\research\t197_path_gate_disasm.json")
d = json.loads(p.read_text(encoding="utf-8"))
print("===== T190 META =====")
print(json.dumps(d.get("t190_meta"), indent=2, ensure_ascii=False))
print("===== T190 BLOCKED/BOUNDARY (truncated) =====")
b = d.get("t190_blocked_or_boundary")
s = json.dumps(b, indent=2, ensure_ascii=False)
print(s[:9000])
print("===== T190 UNVERIFIED HEAD =====")
items = d.get("t190_unverified_items") or d.get("t190_unverified_keys") or []
print("n=", len(items))
print(json.dumps(items[:8], indent=2, ensure_ascii=False)[:4000])
print("===== GATE 0x10b8620 HEAD =====")
print("\n".join(d["path_gate_0x10b8620"]["head"][:90]))
print("===== GATE CALLS =====")
print("\n".join(d["path_gate_0x10b8620"]["calls"]))
print("===== COPY 0x10b0d90 HEAD =====")
print("\n".join(d["copy_path_0x10b0d90"]["head"][:50]))
print("===== C41BB0 HEAD =====")
print("\n".join(d["maybe_new_instance_0xc41bb0"]["head"][:40]))
