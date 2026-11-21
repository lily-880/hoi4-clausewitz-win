from pathlib import Path
src = Path("calling/army_subjects.py").read_text(encoding="utf-8")
lines = src.splitlines()
# find set_army_leader_recipe
for i,l in enumerate(lines):
    if "def set_army_leader" in l or "set_army_leader_recipe" in l:
        start=i
        break
for j in range(start, min(start+80, len(lines))):
    print(f"{j+1:4d}|{lines[j]}")
    if j>start and lines[j].startswith("def "):
        break
print("===== input_loaded header =====")
print("\n".join(Path("calling/input_loaded_fields.py").read_text(encoding="utf-8").splitlines()[:50]))
