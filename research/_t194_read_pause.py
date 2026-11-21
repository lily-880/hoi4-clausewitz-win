from pathlib import Path
# t187 checkpoint pause section + setpause script + gamestate symbols
for f in ["research/t187_checkpoint.md", "research/_t187_setpause_store.py"]:
    t=Path(f).read_text(encoding="utf-8")
    print("="*80, f, "LEN", len(t))
    print(t[:5000])
    print()
