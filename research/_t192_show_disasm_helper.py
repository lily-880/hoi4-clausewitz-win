from pathlib import Path
# reuse the exec window / bind script style
for name in ["research/_t192_exec_window.py", "research/_t192_bind_cmds.py"]:
    p = Path(name)
    if p.exists():
        t = p.read_text(encoding="utf-8")
        print("="*20, name, "len", len(t))
        print("\n".join(t.splitlines()[:80]))
