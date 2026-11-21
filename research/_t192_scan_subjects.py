from pathlib import Path

# army_subjects recipes related to army/leader
p = Path("calling/army_subjects.py")
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
print("army_subjects lines", len(lines))
for i, l in enumerate(lines, 1):
    if l.startswith("def ") or l.startswith("class "):
        low = l.lower()
        if any(s in low for s in ("assign", "leader", "army", "group", "theatre", "order", "create", "new_", "unassign")):
            print(f"{i:5d}|{l}")

print("======= offsets army group / leader =====")
t = Path("calling/offsets.py").read_text(encoding="utf-8")
for i, l in enumerate(t.splitlines(), 1):
    if any(s in l for s in ("COrdersGroup", "CArmyGroup", "Assign", "Leader", "FACTORY", "orders_group", "THEATRE")):
        print(f"{i:5d}|{l[:200]}")
