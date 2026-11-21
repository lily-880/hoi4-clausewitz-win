from pathlib import Path
for name in ["research/test_t187_input_pause.py", "research/test_t190_input_unverified_triage.py", "research/test_t186_input_stockpile.py"]:
    p = Path(name)
    if not p.exists():
        print("MISSING", name)
        continue
    print("="*20, name)
    lines = p.read_text(encoding="utf-8").splitlines()
    for i,l in enumerate(lines,1):
        if any(s in l.lower() for s in ("sha", "inventory", "inv", "verified", "freeze", "recorded", "read_bytes", "hashlib", "t186", "t187", "t191")):
            print(f"{i:4d}|{l}")
inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
print("INV exists", inv.exists(), "size", inv.stat().st_size)
