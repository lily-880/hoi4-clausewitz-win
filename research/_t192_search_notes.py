from pathlib import Path
keys = ("assigned_to", "0x1048", "0x1068", "formation.army", "orders_group", "COrdersGroup", "army_id", "deploy_army")
paths = [
    Path("calling/offsets.py"),
    Path("calling/input_loaded_fields.py"),
    Path("calling/tables/offsets_verified.json"),
    Path("calling/tables/offsets_input_windows_1.19.5.json"),
    Path("research/t184_checkpoint.md"),
    Path("research/t183_checkpoint.md"),
    Path("research/t183_assigned_to_contract.md") if Path("research/t183_assigned_to_contract.md").exists() else None,
]
# also glob related
for p in Path("research").glob("t183*"):
    paths.append(p)
for p in Path("research").glob("t184*"):
    paths.append(p)
for p in Path("calling").glob("*leader*"):
    paths.append(p)
for p in Path("calling").glob("*army*"):
    paths.append(p)
seen=set()
for p in paths:
    if p is None or not p.exists() or p.resolve() in seen:
        continue
    seen.add(p.resolve())
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    for i,l in enumerate(text.splitlines(),1):
        if any(k in l for k in keys):
            if p.suffix in {".md",".py",".json"}:
                print(f"{p}:{i}:{l[:220]}")
