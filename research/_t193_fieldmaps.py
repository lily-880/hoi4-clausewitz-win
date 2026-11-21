import json
from pathlib import Path

# Prefer latest land_post json
p = Path("calling/_land_post_2dg.json")
if not p.exists():
    p = Path("calling/_land_post_2df.json")
data = json.loads(p.read_text(encoding="utf-8"))
print("top keys", list(data)[:20] if isinstance(data, dict) else type(data))

def find(o, pred, prefix=""):
    if isinstance(o, dict):
        if pred(o) or (prefix and pred({"_key": prefix, **{}})):
            # if this dict looks like the command entry
            pass
        for k,v in o.items():
            path=f"{prefix}.{k}" if prefix else str(k)
            if any(s in str(k) for s in ("COrderNewFrontCommand","CArmyGroupCommand","COrderAddNewCompletePlanCommand")):
                yield path, v
            else:
                yield from find(v, pred, path)
    elif isinstance(o, list):
        for i,v in enumerate(o):
            yield from find(v, pred, f"{prefix}[{i}]")

# search command keys
count=0
for path,v in find(data, lambda o: False):
    if path.endswith("COrderNewFrontCommand") or path.endswith("CArmyGroupCommand"):
        print("\n====", path, "====")
        s=json.dumps(v, ensure_ascii=False, indent=2)
        print(s[:3500])
        if len(s)>3500:
            print("...[truncated", len(s), "]")
        count += 1
        if count>=8:
            break
