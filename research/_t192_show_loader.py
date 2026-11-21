from pathlib import Path
lines = Path("calling/input_loaded_fields.py").read_text(encoding="utf-8").splitlines()
for i,l in enumerate(lines,1):
    if "assigned_to" in l or (90 <= i <= 160 and "def own_leaders" in l) or (i>=130 and i<=175):
        if "assigned_to" in l or 130 <= i <= 175:
            print(f"{i:4d}|{l}")
print("--- own_armies full ---")
for i,l in enumerate(lines,1):
    if 214 <= i <= 280:
        print(f"{i:4d}|{l}")
