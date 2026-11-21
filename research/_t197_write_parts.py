# -*- coding: utf-8 -*-
import json, runpy, io, sys
from pathlib import Path
# just do the print_parts logic and write the file
ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
p = ROOT / "research" / "t197_path_gate_disasm.json"
d = json.loads(p.read_text(encoding="utf-8"))
chunks = []
def add(title, text):
    chunks.append(f"===== {title} =====\n{text}\n")
add("T190 META", json.dumps(d.get("t190_meta"), indent=2, ensure_ascii=False))
add("T190 BLOCKED/BOUNDARY", json.dumps(d.get("t190_blocked_or_boundary"), indent=2, ensure_ascii=False)[:12000])
items = d.get("t190_unverified_items") or d.get("t190_unverified_keys") or []
add("T190 UNVERIFIED HEAD n="+str(len(items)), json.dumps(items[:12], indent=2, ensure_ascii=False)[:6000])
add("GATE 0x10b8620 HEAD", "\n".join(d["path_gate_0x10b8620"]["head"][:100]))
add("GATE CALLS", "\n".join(d["path_gate_0x10b8620"]["calls"]))
add("COPY 0x10b0d90 HEAD", "\n".join(d["copy_path_0x10b0d90"]["head"][:60]))
add("C41BB0 HEAD", "\n".join(d["maybe_new_instance_0xc41bb0"]["head"][:40]))
add("10AF100 HEAD", "\n".join(d["newfront_10af100"]["head"][:40]))
text = "\n".join(chunks)
outp = Path(r"C:\Users\Lenovo\agent-tools\t197_parts_py.txt")
outp.write_text(text, encoding="utf-8")
print("WROTE", outp, len(text), "chars")
