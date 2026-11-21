from pathlib import Path
needles = (
    "CArmyGroupCommand", "COrderInstance", "0x10d1450", "frontline", "ORDER_",
    "assign_to_army_group", "ArmyGroup", "CreateFront", "CFront", "plan_id",
    "GetOrderType", "0xc4cfa0", "field_marshal",
)
paths = []
for base in [Path("calling"), Path("research"), Path("docs")]:
    if not base.exists():
        continue
    for p in base.rglob("*"):
        if p.suffix.lower() not in {".py", ".md", ".json"}:
            continue
        if p.name in {"cmd_layout.py"} or p.stat().st_size > 2_000_000:
            continue
        paths.append(p)
for p in paths:
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    hits = []
    for i,l in enumerate(text.splitlines(),1):
        if any(n in l for n in needles):
            hits.append(f"{i}:{l[:220]}")
            if len(hits) >= 12:
                break
    if hits:
        print("="*20, p)
        print("\n".join(hits))
