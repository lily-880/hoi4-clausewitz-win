from pathlib import Path
needles = [
    "world.plans.plan_id | 未验证",
    "world.plans.assigned_army_ids | 未验证",
    "world.armies.plan_id | 未验证",
    "world.army_groups.army_group_id | 未验证",
    "world.own_units.formation.army_group_id | 未验证",
    "0633ed5d",
]
for p in sorted(Path("research").glob("test_t*.py")):
    t=p.read_text(encoding="utf-8")
    hits=[n for n in needles if n in t]
    if hits:
        print(p.name, "->", hits)
