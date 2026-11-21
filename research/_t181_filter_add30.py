import json
from pathlib import Path
d=json.loads(Path("research/t181_add30_adj_funcs.json").read_text(encoding="utf-8"))
print("add30 count", d["add30"], "interesting", len(d["interesting"]))
# score: must mention qword [reg+0x70] and dword [reg+0x7c]
good=[]
for it in d["interesting"]:
    hits=it["hits"]
    has_data=any(("0x70]" in h and "qword" in h) or h.endswith("0x70]") or "+ 0x70]" in h for h in hits)
    has_size=any("0x7c]" in h for h in hits)
    # tighter: 'qword ptr [??? + 0x70]'
    data_hits=[h for h in hits if "0x70]" in h and ("qword" in h or "mov" in h)]
    size_hits=[h for h in hits if "0x7c]" in h]
    type_hits=[h for h in hits if "0x10]" in h]
    if size_hits and data_hits:
        good.append(it)
        print("====", it["func"], "end", it["end"], "adds", it["add_sites"])
        for h in it["hits"]:
            print("  ", h)
print("good", len(good), [g["func"] for g in good])
