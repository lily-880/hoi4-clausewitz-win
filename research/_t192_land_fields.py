import json
from pathlib import Path

# extract COrderGroupCommand / CSetArmyLeaderCommand / CArmyGroupCommand objects from land_post_2dg
p = Path("calling/_land_post_2dg.json")
data = json.loads(p.read_text(encoding="utf-8"))

def walk(obj, want, path=""):
    out = []
    if isinstance(obj, dict):
        # if this dict is keyed by command name
        for k,v in obj.items():
            if k in want and isinstance(v, dict):
                out.append((path + "/" + k if path else k, v))
            out += walk(v, want, path + "/" + k if path else k)
    elif isinstance(obj, list):
        for i,v in enumerate(obj):
            out += walk(v, want, f"{path}[{i}]")
    return out

want = {"COrderGroupCommand", "CSetArmyLeaderCommand", "CArmyGroupCommand"}
hits = walk(data, want)
print("hits", len(hits))
# print unique compact forms focusing on fields / size / factory
for path, v in hits:
    keys = list(v.keys())[:30]
    interesting = {k: v[k] for k in v if any(s in k.lower() for s in ("field", "size", "factory", "vt", "type", "isvalid", "execute", "layout", "handle", "theatre", "unit", "leader", "offset", "packing", "usability"))}
    print("=" * 60, path)
    print("keys", keys)
    print(json.dumps(interesting, ensure_ascii=False, indent=2)[:2500])
    print()
