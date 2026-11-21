from pathlib import Path
# find one historical script that opens the gate and posts Move
hits = []
for p in Path("scripts").glob("*.py"):
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if "safe_land_tool_gate.OPEN" in t and "move(" in t.lower():
        hits.append(p)
print("scripts", [str(h) for h in hits[:20]], "n", len(hits))
if hits:
    t = hits[-1].read_text(encoding="utf-8", errors="replace")
    print("====", hits[-1], "lines", len(t.splitlines()))
    for i, l in enumerate(t.splitlines(), 1):
        if any(s in l for s in ("safe_land_tool_gate", "ALLOW_POST", "allow_post", "unlink", "OPEN", "move_order", "dry_run")):
            print(f"{i:4d}|{l[:200]}")
