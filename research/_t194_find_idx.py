from pathlib import Path
import json, re

# docs first
for p in Path("docs").glob("*FACTORY*"):
    print("DOC", p, p.stat().st_size)

p = Path("docs/PHASE2FG_ORDERS_FACTORY_IDX.md")
if p.exists():
    t = p.read_text(encoding="utf-8")
    print("LEN", len(t))
    # print lines mentioning our commands
    keys = ("SetPath", "Assign", "Execute", "Pause", "AreaDefense", "Fallback", "NewFront", "NewRoot", "CreateUnitLeader", "SetArmyLeader")
    for ln in t.splitlines():
        if any(k in ln for k in keys):
            print(ln)

print("\n======= offsets_verified hits =======")
off = json.loads(Path("calling/offsets_verified.json").read_text(encoding="utf-8"))

def find_keys(o, want, prefix=""):
    if isinstance(o, dict):
        for k,v in o.items():
            path=f"{prefix}.{k}" if prefix else k
            if any(w.lower() in str(k).lower() for w in want):
                yield path, v
            else:
                yield from find_keys(v, want, path)
    elif isinstance(o, list):
        for i,v in enumerate(o):
            yield from find_keys(v, want, f"{prefix}[{i}]")

want=("COrderSetPath","COrderAssign","COrderExecute","CPauseGame","CCreateAreaDefense","COrderNewFallback","CCreateUnitLeader")
for path,v in find_keys(off, want):
    print("OFF", path)
    s=json.dumps(v, ensure_ascii=False)
    print(s[:1500])
    print()
