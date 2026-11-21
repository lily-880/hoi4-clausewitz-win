import json
from pathlib import Path

off=json.loads(Path("calling/offsets_verified.json").read_text(encoding="utf-8"))

def find(o, keys, prefix=""):
    if isinstance(o, dict):
        for k,v in o.items():
            path=f"{prefix}.{k}" if prefix else k
            if any(x in str(k) for x in keys):
                yield path,v
            else:
                yield from find(v, keys, path)
    elif isinstance(o, list):
        for i,v in enumerate(o):
            yield from find(v, keys, f"{prefix}[{i}]")

for path,v in find(off, ("COrderNewRoot","COrderAddNew","CompletePlan")):
    print(path)
    print(json.dumps(v, ensure_ascii=False, indent=2)[:1500])
    print()

data=json.loads(Path("calling/_land_post_2dg.json").read_text(encoding="utf-8"))
# print all command keys containing Root or Complete or Plan
cmds=set()
def walk(o):
    if isinstance(o, dict):
        for k,v in o.items():
            if "Command" in str(k) and any(s in str(k) for s in ("Root","Complete","Plan","Front","Fallback","Invasion","Garrison","Defense","Offensive")):
                cmds.add(str(k))
            walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(data)
print("CMD NAMES:")
for c in sorted(cmds):
    print(" ", c)

# role_observe keys
ro=data.get("role_observe_2dg") or {}
print("role_observe roles", list(ro)[:30] if isinstance(ro, dict) else type(ro))
if isinstance(ro, dict):
    for role, body in ro.items():
        cmds2=(body or {}).get("commands") if isinstance(body, dict) else None
        if isinstance(cmds2, dict):
            print(role, ":", list(cmds2))
