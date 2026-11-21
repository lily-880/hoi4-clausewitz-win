from pathlib import Path
# army_subjects recipes around assign/create army group and frontline
lines = Path("calling/army_subjects.py").read_text(encoding="utf-8-sig").splitlines()
# print function defs with army group / order / frontline / plan
for i,l in enumerate(lines,1):
    if l.startswith("def ") and any(s in l.lower() for s in ("army_group","order","front","plan","marshal","instance")):
        print(f"{i}|{l}")
print("--- assign_to_army_group and nearby ---")
for start_name in ("def assign_to_army_group_recipe", "def create_army_group", "def army_group", "def set_army_group", "def order_assign_recipe"):
    pass
# dump 320-450 and search CArmyGroupCommand
for i,l in enumerate(lines,1):
    if "CArmyGroupCommand" in l or "CAssignToArmyGroup" in l or "CCreateArmy" in l or "OrderInstance" in l or "CFrontline" in l or "CCreateFront" in l:
        lo=max(1,i-2); hi=min(len(lines),i+25)
        print(f"\n***** {i} *****")
        for j in range(lo,hi+1):
            print(f"{j}|{lines[j-1][:200]}")
