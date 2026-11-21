from pathlib import Path
# own_leaders function
p = Path("calling/input_loaded_fields.py")
lines = p.read_text(encoding="utf-8").splitlines()
print("\n".join(f"{i+58:4d}|{lines[i]}" for i in range(57, 104)))
print("\n===== offsets_input t183/t184/t191 keys =====")
import json
off = json.loads(Path("calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8"))
for k,v in off.items():
    if any(s in k.lower() for s in ("t183","t184","t191","leader","army","formation","orders","assigned","theatre")):
        print(k, ":", json.dumps(v, ensure_ascii=False)[:400])
print("\n===== offsets.py CA_* nearby =====")
ol = Path("calling/offsets.py").read_text(encoding="utf-8").splitlines()
print("\n".join(f"{i+90:4d}|{ol[i]}" for i in range(90, 120)))
