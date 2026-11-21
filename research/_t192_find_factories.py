from pathlib import Path

keys = (
    "COrdersGroup",
    "CArmyGroup",
    "AssignLeader",
    "assign_leader",
    "CAssign",
    "CreateArmy",
    "new_army",
    "orders_group",
    "COrderAssign",
    "assigned_to",
    "factory_idx",
)
# search calling py (not huge cmd_layout first pass by name)
hits = []
for p in Path("calling").glob("*.py"):
    if p.name == "cmd_layout.py":
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    found = [s for s in ("COrdersGroup", "CArmyGroup", "assign_leader", "AssignGeneral", "CAssignLeader", "create_army", "new_army_group", "CCreateArmy", "CNewArmy", "orders_group", "COrderAssignCommand", "CAssignUnit", "CAssignTheatre", "leader_assign", "CChangeLeader", "CSetLeader") if s in t]
    if found:
        hits.append((str(p), found))
print("calling hits:")
for h in hits:
    print(h)

print("======= research checkpoints / docs =====")
for root in (Path("research"), Path("docs"), Path("scripts")):
    for p in root.glob("*"):
        if p.suffix.lower() not in {".py", ".md", ".json"} or p.stat().st_size > 2_000_000:
            continue
        name = p.name.lower()
        if any(s in name for s in ("assign", "ordersgroup", "army_group", "leader", "formation", "t183", "t184")):
            if p.suffix in {".md", ".py"} or "t183" in name or "t184" in name:
                pass
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "COrdersGroup" in t and ("FACTORY" in t or "factory" in t or "Post" in t or "ASSIGN" in t):
            if p.name.startswith("test_"):
                continue
            if "PHASE" in p.name or p.suffix==".md" or "order" in p.name.lower() or "assign" in p.name.lower() or p.parent.name=="calling":
                print(p, "size", p.stat().st_size)
