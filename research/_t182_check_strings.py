from pathlib import Path
p=Path("research/_t182_clip_carmy_secondary_writer_0xced2e0.txt")
t=p.read_text(encoding="utf-8")
for s in ("qword ptr [rbx + 0x5f0]","qword ptr [rbx + 0x600]","qword ptr [rbx + 0x5f8]","TOKEN army_current_supply_ratio","TOKEN max_supply","TOKEN supply_gain"):
    print(repr(s), s in t)
# show around those lines
for i,line in enumerate(t.splitlines(),1):
    if "0x5f0" in line or "0x600" in line or "0x5f8" in line or "0x4ced" in line or "0x3a43" in line or "0x4cec" in line:
        print(f"{i}:{line!r}")
