from pathlib import Path
# last 40 lines of t188 t189 inventory tests
for name in ["research/test_t188_input_plans.py", "research/test_t189_input_crisis_fow_buildings.py"]:
    lines = Path(name).read_text(encoding="utf-8").splitlines()
    print("=" * 70, name)
    print("\n".join(f"{i+1:4d}|{l}" for i,l in enumerate(lines) if i>=55 or "inventory" in l.lower() or "SHA" in l or "LIVE" in l or "T187" in l))
