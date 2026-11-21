import json
from pathlib import Path

# find AddNewCompletePlan factory idx and NewRoot recipes
needles=("COrderNewRootCommand","COrderAddNewCompletePlanCommand","NewRootCommand","AddNewCompletePlan")
# docs
for p in list(Path("docs").glob("*FACTORY*"))+list(Path("docs").glob("*PHASE2F*"))+list(Path("calling").glob("offsets_verified.json")):
    try:
        t=p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if any(n in t for n in needles):
        print("====", p)
        for i,l in enumerate(t.splitlines(),1):
            if any(n in l for n in needles):
                print(f"{i}:{l[:250]}")

# land post field maps
data=json.loads(Path("calling/_land_post_2dg.json").read_text(encoding="utf-8"))

def find(o, prefix=""):
    if isinstance(o, dict):
        for k,v in o.items():
            path=f"{prefix}.{k}" if prefix else str(k)
            if k in ("COrderNewRootCommand","COrderAddNewCompletePlanCommand"):
                yield path,v
            else:
                yield from find(v, path)
    elif isinstance(o, list):
        for i,v in enumerate(o):
            yield from find(v, f"{prefix}[{i}]")

n=0
for path,v in find(data):
    if "role_observe" in path and path.endswith("Command"):
        print("\n====", path)
        print(json.dumps({k:v[k] for k in v if k in ("command","role","execute_rva","isvalid_rva","vt_rva","field_map","required_gates","post_path_confidence")}, ensure_ascii=False, indent=2))
        n+=1
        if n>=6: break
