import json
from pathlib import Path
sch = json.loads(Path("calling/tables/generalissimo_input.schema.json").read_text(encoding="utf-8"))
defs = sch.get("$defs") or sch.get("definitions") or {}
for name in ("Plan","Crisis","VisibleUnit","Visibility","Army"):
    if name in defs:
        print("====", name, "====")
        print(json.dumps(defs[name], ensure_ascii=False, indent=2)[:2500])
        print()
# world properties for plans/crises
world = sch.get("properties",{}).get("world",{}).get("properties",{})
for k in ("plans","crises","visible_units","armies"):
    if k in world:
        print("==== world."+k, "====")
        print(json.dumps(world[k], ensure_ascii=False, indent=2)[:800])
