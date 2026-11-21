from pathlib import Path
# verify syntax of patched loaders
import ast
for p in ["calling/input_loaded_fields.py", "calling/offsets.py", "calling/army_subjects.py",
          "research/test_t191_input_move_path.py", "research/test_t183_input_assigned_combat_command.py",
          "research/test_t184_input_formation_combat.py"]:
    ast.parse(Path(p).read_text(encoding="utf-8"))
    print("OK", p)

# show inserted functions
lines = Path("calling/input_loaded_fields.py").read_text(encoding="utf-8").splitlines()
for i,l in enumerate(lines,1):
    if 150 <= i <= 175 or "def own_armies" in l or "def unit_formation" in l or "HANDLE_TYPE_ORDERS" in l or "assigned_to" in l:
        print(f"{i:4d}|{l}")
