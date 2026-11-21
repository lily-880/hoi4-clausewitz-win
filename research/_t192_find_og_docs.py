from pathlib import Path

# Find any live post scripts or fuller layouts for COrderGroupCommand / CSetArmyLeaderCommand
for root in (Path("scripts"), Path("docs"), Path("calling"), Path("research")):
    for p in root.rglob("*"):
        if p.suffix.lower() not in {".py", ".md", ".json"} or p.stat().st_size > 3_000_000:
            continue
        if p.name == "cmd_layout.py":
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "COrderGroupCommand" in t or "CSetArmyLeaderCommand" in t or "CArmyGroupCommand" in t:
            print(f"{p}  size={p.stat().st_size}")

print("======= t184 checkpoint =====")
print(Path("research/t184_checkpoint.md").read_text(encoding="utf-8"))
