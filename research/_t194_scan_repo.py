from pathlib import Path
keys = [
    "GetOrderType", "ORDER_MOVE", "ORDER_INVASION", "COrderExecute",
    "axis_province", "assigned_unit_ids", "set_unit_leader", "CSetUnitLeader",
    "vertex_province", "ORDER_FRONT", "offensive_line", "area_defense",
    "COrderNewFront", "scheduled_member", "can_execute",
]
paths = []
for p in Path("calling").rglob("*"):
    if p.suffix.lower() in {".py", ".md", ".json", ".txt"} and "__pycache__" not in str(p):
        paths.append(p)
for p in Path("research").glob("*"):
    if p.is_file() and p.suffix.lower() in {".py", ".md", ".json", ".txt"}:
        paths.append(p)
print("files", len(paths))
for p in paths:
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    found = [k for k in keys if k in t]
    if found:
        print(str(p).replace("\\", "/"), "=>", ",".join(found))
