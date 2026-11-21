from pathlib import Path
needles = [
    "world.leaders.assigned_to | 未验证",
    "world.own_units.formation.army_id | 未验证",
    "world.armies.army_id | 未验证",
    "world.armies.name | 未验证",
    "world.armies.leader_id | 未验证",
    "world.armies.unit_ids | 未验证",
    "set_army_leader_recipe(",
]
for p in list(Path(".").rglob("test_*.py")) + list(Path("calling").glob("*.py")):
    if "cmd_layout" in str(p) or "site-packages" in str(p):
        continue
    try:
        t = p.read_text(encoding="utf-8")
    except Exception:
        continue
    hits = [n for n in needles if n in t]
    if hits:
        print(p, "->", hits)
