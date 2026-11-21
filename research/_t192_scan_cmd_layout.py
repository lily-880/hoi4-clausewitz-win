from pathlib import Path

# search cmd_layout for factory names without loading 155k lines fully - use chunk scan
p = Path("calling/cmd_layout.py")
needles = (
    "CCreate",
    "CNewArmy",
    "COrdersGroup",
    "CAssignLeader",
    "CAssignGeneral",
    "CChangeUnitLeader",
    "CSetLeader",
    "CAssignArmy",
    "CCreateArmy",
    "CCreateOrder",
    "CNewOrderGroup",
    "COrderNew",
    "CAssignUnits",
    "CUnitAssign",
    "CTheatre",
    "ArmyLeader",
    "CAssignCommander",
    "CPromote",
)
# stream
found = {n: [] for n in needles}
# also collect nearby "C" command names with leader/army/group
extra = []
with p.open(encoding="utf-8", errors="replace") as f:
    for i, l in enumerate(f, 1):
        for n in needles:
            if n in l:
                if len(found[n]) < 8:
                    found[n].append((i, l.strip()[:180]))
        if i < 5:
            continue
        if ("FACTORY" in l or "factory_idx" in l or "type_id" in l) and any(s in l for s in ("Leader", "ArmyGroup", "OrdersGroup", "CreateArmy", "AssignUnit", "AssignLeader", "NewArmy", "NewGroup", "Commander")):
            extra.append((i, l.strip()[:200]))
            if len(extra) > 80:
                break

print("NEEDLE HITS")
for n, rows in found.items():
    print(n, "count_shown", len(rows))
    for i, l in rows:
        print(f"  {i}:{l}")
print("EXTRA", len(extra))
for i, l in extra[:40]:
    print(f"  {i}:{l}")
