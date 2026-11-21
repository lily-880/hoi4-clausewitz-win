from pathlib import Path
for name in [
    "research/test_t186_input_war_relation.py",
    "research/test_t187_input_pause.py",
    "research/test_t188_input_plans.py",
    "research/test_t189_input_crisis_fow_buildings.py",
    "research/test_t190_input_unverified_triage.py",
    "research/_t186_inv_and_flags.py",
]:
    p = Path(name)
    if not p.exists():
        print("missing", name)
        continue
    t = p.read_text(encoding="utf-8")
    print("=" * 70, name)
    for i, l in enumerate(t.splitlines(), 1):
        if any(s in l for s in ("SHA", "sha256", "verified", "unverified", "fields", "98d83a", "INV", "已验证", "complete_input")):
            print(f"{i:4d}|{l[:200]}")
