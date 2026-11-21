import json
from pathlib import Path
sch=json.loads(Path("calling/tables/generalissimo_input.schema.json").read_text(encoding="utf-8"))
defs=sch.get("$defs") or sch.get("definitions") or {}
print("def keys", list(defs))
want=("assigned_to","formation","in_combat","army_id","isolated","order","Leader","Unit","Army","Supply")
for k,v in defs.items():
    s=json.dumps(v, ensure_ascii=False)
    if any(x in s or x in k for x in want):
        print("===== DEF", k, "=====")
        print(json.dumps(v, indent=2, ensure_ascii=False)[:2500])
        print()
