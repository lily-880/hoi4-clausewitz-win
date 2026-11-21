from pathlib import Path
files = [
    "research/t188_checkpoint.md",
    "research/t185_checkpoint.md",
    "research/t191_checkpoint.md",
    "research/t190_unverified_triage.json",
    "research/t185_orderinstance_type.json",
    "research/t182_combat_order_strings.json",
    "research/t188_plan_writers.json",
]
for f in files:
    p = Path(f)
    t = p.read_text(encoding="utf-8")
    print("=" * 80)
    print(f, "LEN", len(t))
    print(t[:8000] if len(t) > 8000 else t)
    print()
