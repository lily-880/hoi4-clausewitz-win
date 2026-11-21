from pathlib import Path
lines = Path("calling/army_subjects.py").read_text(encoding="utf-8-sig").splitlines()
# dump new_front, insert_front, add_complete_plan, set_path
for name in ("def new_front_recipe", "def insert_front_recipe", "def add_complete_plan_recipe",
             "def set_path_recipe", "def reshape_front_recipe", "def connect_front_recipe"):
    for i,l in enumerate(lines,1):
        if l.startswith(name):
            for j in range(i, min(i+40, len(lines)+1)):
                print(f"{j}|{lines[j-1]}")
                if j>i and lines[j-1].startswith("def "):
                    break
            print()
            break

print("===== t184 CArmyGroup writer excerpt =====")
text = Path("research/t184_checkpoint.md").read_text(encoding="utf-8")
for i,l in enumerate(text.splitlines(),1):
    if any(s in l for s in ("CArmyGroup", "field_marshal", "0xc4cfa0", "+0x230")):
        print(f"{i}|{l}")

print("===== t192 CArmyGroup clips exist? =====")
for p in sorted(Path("research").glob("*ArmyGroup*")) + sorted(Path("research").glob("*t192_clip*")):
    print(p.name, p.stat().st_size)
