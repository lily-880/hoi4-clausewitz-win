from pathlib import Path
# Execute clip - print first 120 lines and any interesting displacements
p = Path("research/_t192_clip_CArmyGroupCommand_execute_0x18d2640.txt")
lines = p.read_text(encoding="utf-8").splitlines()
print("N", len(lines))
for i,l in enumerate(lines[:160]):
    print(l)
print("===== interesting =====")
for l in lines:
    if any(s in l.lower() for s in ("0x28", "0x30", "0x38", "0x40", "0x48", "0x50", "0x58", "0x60", "0x68", "0x70", "call 0xc4", "call 0xc3", "call 0x18", "cmp dword", "test")):
        if any(s in l for s in ("[r", "[c", "[b", "call ", "jmp ")):
            print(l)
