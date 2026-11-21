import json
from pathlib import Path

# formation inventory summary
p=Path("research/t165_world_formation_inventory.json")
d=json.loads(p.read_text(encoding="utf-8"))
def brief(x, depth=0):
    if isinstance(x, dict):
        print("  "*depth + "{")
        for k,v in x.items():
            if k in ("units","theatres","rows","samples","raw") and isinstance(v, (list,dict)) and len(str(v))>400:
                print("  "*(depth+1)+f"{k}: <{type(v).__name__} len={len(v)}>")
            elif isinstance(v, (dict,list)) and len(str(v))>500:
                print("  "*(depth+1)+f"{k}:")
                brief(v, depth+2)
            else:
                print("  "*(depth+1)+f"{k}: {v if not isinstance(v,(dict,list)) else json.dumps(v, ensure_ascii=False)[:200]}")
        print("  "*depth + "}")
    elif isinstance(x, list):
        print("  "*depth + f"list[{len(x)}]")
        if x:
            brief(x[0], depth+1)
brief({k:d[k] for k in list(d)[:30] if k not in ("units",)})
print("TOP KEYS", list(d.keys())[:40])
