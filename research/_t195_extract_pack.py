from pathlib import Path
import json, re

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")

# Print relevant bind / pack fragments
files = [
    "research/t192_bind_cmds.json",
    "research/t193_bind_newroot.json",
    "research/t194_bind_cmds.json",
    "calling/tables/offsets_input_windows_1.19.5.json",
]
for rel in files:
    p = ROOT / rel
    if not p.exists():
        print("MISSING", rel)
        continue
    print("=" * 80, rel, p.stat().st_size)
    if p.suffix == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        # walk for command keys
        def walk(o, prefix=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    path = f"{prefix}.{k}" if prefix else k
                    if any(s in str(k) for s in ("OrderGroup", "SetArmyLeader", "ArmyGroup", "NewRoot", "NewFront", "Assign", "Execute", "Pause", "move_path", "army_leader", "army_group_plan")):
                        yield path, v
                    else:
                        yield from walk(v, path)
            elif isinstance(o, list) and prefix:
                return
        for path, v in walk(data):
            s = json.dumps(v, ensure_ascii=False)
            if len(s) > 1800:
                s = s[:1800] + "..."
            print("\nKEY", path)
            print(s)

# packing from post scripts: lines around _write and pack
for rel in ["research/_t192_post.py", "research/_t193_ag_post.py", "research/_t193_plan_post.py"]:
    p = ROOT / rel
    if not p.exists():
        print("MISSING", rel)
        continue
    t = p.read_text(encoding="utf-8")
    print("\n" + "=" * 80, rel, "len", len(t))
    # print constants and write packs
    for i, ln in enumerate(t.splitlines(), 1):
        if any(s in ln for s in ("FACTORY", "factory", "VT", "size", "0x28", "0x30", "0x40", "_write", "_game_malloc", "theatre", "OG=", "AG=", "IDX", "idx")):
            if "print" in ln and "json" in ln:
                continue
            print(f"{i:4d} {ln[:200]}")
