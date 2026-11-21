from pathlib import Path
lines = Path("research/_t192_clip_CArmyGroupCommand_execute_0x18d2640.txt").read_text(encoding="utf-8").splitlines()
start=None
for i,l in enumerate(lines):
    if l.startswith("0x18d2a5a") or "0x18d2a5a  " in l:
        start=i
        break
print("start", start)
for l in lines[start:]:
    print(l)
