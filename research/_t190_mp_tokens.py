import json
from pathlib import Path
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
keys=("manpower","needed","deficit","shortage","reinforce","reinforcement","casualty","casualties","available")
for i in mp:
    n=i["name"].lower()
    if "manpower" in n or n in ("needed","need","deficit","demanded","demand") or "reinforce" in n and "manpower" in n:
        print(f"0x{i['token']:x} {i['name']}")
print("--- shortage-like ---")
for i in mp:
    n=i["name"].lower()
    if any(k in n for k in ("manpower_need","needed_manpower","manpower_deficit","missing_manpower","free_manpower","deployable")):
        print(f"0x{i['token']:x} {i['name']}")
