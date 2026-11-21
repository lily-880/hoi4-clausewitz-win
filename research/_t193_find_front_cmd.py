from pathlib import Path
# find NewFront / ArmyGroupCommand in smaller catalogs
needles = ("COrderNewFrontCommand", "CArmyGroupCommand", "COrderAddNewCompletePlan", "CNewFront", "NewFrontCommand")
for p in list(Path("calling").glob("*.json")) + list(Path("calling").glob("cmd_*.py")) + list(Path("research").glob("*catalog*")) + list(Path("docs").glob("*FACTORY*")):
    if p.stat().st_size > 5_000_000:
        continue
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if not any(n in text for n in needles):
        continue
    print("="*20, p, p.stat().st_size)
    for i,l in enumerate(text.splitlines(),1):
        if any(n in l for n in needles):
            print(f"{i}:{l[:300]}")
            if i>0:
                # print a bit of context if json-ish one-liners skip
                pass
