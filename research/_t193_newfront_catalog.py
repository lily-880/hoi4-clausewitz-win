import json
from pathlib import Path

# extract NewFront and ArmyGroup entries from offsets_verified and a land_post json via python (not loading whole as text spam)
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

want=("COrderNewFront","CArmyGroupCommand","COrderAddNewComplete")
for path,v in find_keys(off, want):
    print("OFF", path)
    print(json.dumps(v, ensure_ascii=False, indent=2)[:2000])
    print()

# land post 2dg or latest field map - pick 2dg if smaller structured
# Use ijson-like: just json load 2cz section by scanning with raw decoder at known lines
# Read PHASE2FG for factory idx
print("===== PHASE2FG =====")
print(Path("docs/PHASE2FG_ORDERS_FACTORY_IDX.md").read_text(encoding="utf-8"))
