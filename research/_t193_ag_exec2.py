from pathlib import Path
# print Execute around call 0xc417a0 and later create/assign
lines = Path("research/_t192_clip_CArmyGroupCommand_execute_0x18d2640.txt").read_text(encoding="utf-8").splitlines()
# find line with 0x18d28e6 onward through 0x18d2b50
start=None
for i,l in enumerate(lines):
    if "0x18d28e6" in l or l.startswith("0x18d28e6"):
        start=i
        break
print("start", start)
for l in lines[start:start+120]:
    print(l)
