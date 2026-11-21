import json,re
from pathlib import Path
names=json.loads(Path("research/t188_rtti_plan_names.json").read_text(encoding="utf-8"))
# keep short core classes, drop Command/Effect/Trigger/View/Item/Tooltip/Define/Tut/Window/Popup
drop=("Command","Effect","Trigger","View","Item","Tooltip","Define","Tut","Window","Popup","Nudger","Listener","Handler","Database","Registry","Medal","Skill","Config","Confirmation","Roster")
core=[]
for n in names:
    short=n.replace(".?AV","").replace("@@","")
    # namespaced leftovers
    if any(x in short for x in drop):
        continue
    if any(k in short for k in ("Order","Front","Plan","AreaDef","Garrison","Fallback","Spear","Offense","Theatre","Theater","Crisis","Alert","Encirc","Spot","Visibility","BuildingStatus","Building@@","Intel")):
        core.append(n)
print("core", len(core))
for n in core:
    print(n)
