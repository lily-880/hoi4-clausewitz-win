from pathlib import Path
for name in [
    "docs/SAFE_POST_ENABLE_CHECKLIST.md",
    "docs/PHASE2IJI_SAFE_POST_GATE_CHECKLIST.md",
    "docs/LAND_ARMY_AGENT.md",
]:
    p = Path(name)
    print("=" * 70, name, "len", p.stat().st_size)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, l in enumerate(lines):
        if any(s in l for s in ("safe_land_tool_gate", "OPEN", "allow_post", "How to", "marker", "create the", "touch ")):
            lo = max(0, i - 1)
            hi = min(len(lines), i + 3)
            print("\n".join(f"{j+1}:{lines[j]}" for j in range(lo, hi)))
            print("---")
