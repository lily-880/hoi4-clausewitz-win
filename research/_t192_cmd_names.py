from pathlib import Path

# extract command catalog entries for leader / group create
p = Path("calling/cmd_layout.py")
# Read first ~500 lines which seemed to have JSON-like command dicts
# Also search specific class names
want = [
    "CSetArmyLeaderCommand",
    "CCreateUnitLeaderCommand",
    "COrderAssignCommand",
    "COrderUnassignCommand",
    "CCreateTheatre",
    "CCreateTheater",
    "CCreateOrderGroup",
    "CCreateArmyGroup",
    "CNewTheatre",
    "CTheatreGroup",
    "CGroupArmies",
    "CCreateGroup",
    "CNewGroup",
    "CAddArmy",
    "CCreateHQ",
    "CDeployArmy",
    "CAssignToArmyGroup",
    "CAssignUnitsTo",
    "CUngroup",
    "COrdersGroup",
    "CSetTheatre",
    "CCreateTheaterGroup",
    "CNewArmyGroup",
    "CSplitGroup",
    "CMergeArmies",
]

# get unique command class names containing relevant words
names = []
with p.open(encoding="utf-8", errors="replace") as f:
    for i, l in enumerate(f, 1):
        if "Command'" in l or 'Command"' in l:
            if any(s in l for s in ("Leader", "Group", "Theatre", "Theater", "Army", "Assign", "Create", "New", "Ungroup", "Merge", "Split", "HQ", "Deploy")):
                s = l.strip()
                if s not in names and len(names) < 200:
                    names.append(s)

print("COMMAND NAME LINES", len(names))
for s in names:
    print(s)
