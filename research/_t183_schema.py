import sys,re,json
from pathlib import Path
sys.path.insert(0,"calling")
# observation leader
text=Path("calling/input_observation.py").read_text(encoding="utf-8")
for i,line in enumerate(text.splitlines(),1):
    if re.search(r"leader|formation|army_group|theatre|assigned|in_combat|commandlist", line, re.I):
        if "TODO" in line or "leader" in line.lower() or "formation" in line.lower() or "combat" in line.lower() or "assigned" in line.lower():
            print(f"{i}:{line[:200]}")

print("\n======= schema snippets =======")
sch=json.loads(Path("calling/tables/generalissimo_input.schema.json").read_text(encoding="utf-8"))
# find assigned_to, formation, in_combat, order
s=json.dumps(sch, indent=2, ensure_ascii=False)
# too big; walk
def find_props(obj, path=""):
    if isinstance(obj, dict):
        if "properties" in obj and isinstance(obj["properties"], dict):
            for k,v in obj["properties"].items():
                if k in ("assigned_to","formation","in_combat","order","combat_id","army_id","army_group_id","supply","ratio","isolated","in_supply"):
                    print("PROP", path+"."+k, json.dumps(v, ensure_ascii=False)[:500])
                find_props(v, path+"."+k)
        else:
            for k,v in obj.items():
                find_props(v, path+"."+k)
    elif isinstance(obj, list):
        for i,v in enumerate(obj[:5]):
            find_props(v, path+f"[{i}]")
find_props(sch)
