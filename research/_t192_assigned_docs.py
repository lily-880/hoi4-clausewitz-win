from pathlib import Path
import json

# t183 assigned_to official slots
# also leader handle type
for name in [
    "research/t183_checkpoint.md",
    "calling/tables/offsets_input_windows_1.19.5.json",
]:
    p = Path(name)
    t = p.read_text(encoding="utf-8", errors="replace")
    if name.endswith(".json"):
        d = json.loads(t)
        key = d.get("assigned_combat_command_t183") or d.get("assigned_to") 
        print("offsets assigned key", json.dumps(d.get("assigned_combat_command_t183"), indent=2, ensure_ascii=False)[:2500] if "assigned_combat_command_t183" in d else "no key")
        continue
    print("=" * 70, name)
    lines = t.splitlines()
    # print first 120 lines and any assigned_to sections
    print("\n".join(lines[:80]))
