from pathlib import Path
import json, re

for p in [
    "docs/PHASE2FG_ORDERS_FACTORY_IDX.md",
    "docs/PHASE2GZ_ASSIGN_UNASSIGN_EXECUTE_FACTORY.md",
    "docs/PHASE2GX_ASSIGN_FACTORY_EDGE.md",
    "docs/PHASE2EZ_FACTORY_EXECLIST.md",
]:
    print("="*80, p)
    print(Path(p).read_text(encoding="utf-8"))
    print()

# search docs and research for SetPath / PauseGame factory idx
keys = ("COrderSetPath", "CPauseGame", "CCreateAreaDefense", "SetPathCommand")
for base in [Path("docs"), Path("research"), Path("calling")]:
    files = list(base.glob("*.md")) + list(base.glob("*.json")) + list(base.glob("*.py"))
    if base.name == "calling":
        files += list(Path("calling/tables").glob("*.json")) if Path("calling/tables").exists() else []
    for f in files:
        try:
            t = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not any(k in t for k in keys):
            continue
        hits = []
        for ln in t.splitlines():
            if any(k in ln for k in keys):
                hits.append(ln.strip()[:240])
        if hits:
            print("FILE", f, "n", len(hits))
            for h in hits[:8]:
                print(" ", h)
