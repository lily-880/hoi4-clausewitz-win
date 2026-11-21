import json
from pathlib import Path
d=json.loads(Path("research/t184_rtti_vtables.json").read_text(encoding="utf-8"))
want=("CTheatre@@","CArmyGroup@@","CTheaterGroup@@","COrdersGroup@@","COrderGroup@@","COrdersGroupMember","CFront@@","CLandCombat@@","CCombat@@","CCommand@@","COrderInstance@@","CMoveCommand@@","CLandCombatant@@","CCancelMovementCommand","CMassMoveCommand","CDeleteUnitCommand")
for n,v in d["vtables"].items():
    if any(s in n for s in want) and "Dialog" not in n and "View" not in n and "Item" not in n and "Command@@" not in n or n.endswith(("COrdersGroup@@","CArmyGroup@@","CTheaterGroup@@","CTheatre@@","CFront@@","CLandCombat@@","CCombat@@","CCommand@@","COrderInstance@@","CMoveCommand@@","CLandCombatant@@","COrdersGroupMember@@")):
        print(n, v)
print("--- all vt keys matching core ---")
for n,v in d["vtables"].items():
    short=n.replace(".?AV","").replace("@@","")
    if short in ("CTheatre","CArmyGroup","CTheaterGroup","COrdersGroup","COrderGroup","CFront","CLandCombat","CCombat","CCommand","COrderInstance","CMoveCommand","CLandCombatant","COrdersGroupMember","CArmyGroupCommand"):
        print(n, json.dumps(v))
