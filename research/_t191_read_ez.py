from pathlib import Path
# PHASE2EZ factory table layout notes
p = Path("docs/PHASE2EZ_FACTORY_EXECLIST.md")
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
for i, l in enumerate(lines[:120], 1):
    print(f"{i:4d}|{l[:200]}")
