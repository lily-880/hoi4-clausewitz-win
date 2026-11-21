from pathlib import Path
import json

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")

# t192 bind
p = ROOT / "research" / "t192_bind_cmds.json"
if p.exists():
    data = json.loads(p.read_text(encoding="utf-8"))
    print("==== t192_bind_cmds keys", list(data)[:20] if isinstance(data, dict) else type(data))
    s = json.dumps(data, indent=2, ensure_ascii=False)
    print(s[:8000])
else:
    print("NO t192_bind")

# tighter post script: only from CONST through first post, skip huge dumps
for rel in ["research/_t192_post.py", "research/_t193_ag_post.py"]:
    t = (ROOT / rel).read_text(encoding="utf-8")
    print("\n====", rel, "TOTAL LINES", t.count("\n"))
    lines = t.splitlines()
    # print until main packing writes, cap 220 lines if file starts with consts
    for i, ln in enumerate(lines[:250], 1):
        print(f"{i:4d} {ln}")
