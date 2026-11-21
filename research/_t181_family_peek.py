from pathlib import Path
lines=Path("research/_t181_clip_family_0x12971a0.txt").read_text(encoding="utf-8").splitlines()
# print start 80, around type 0x1297bbd +/- 40, and any lea rip strings / calls / rets
print("===== START 90 =====")
print("\n".join(lines[:90]))
print("===== AROUND TYPE =====")
for i,l in enumerate(lines):
    a=int(l.split()[0],16)
    if 0x1297b00 <= a <= 0x1297d80:
        print(l)
print("===== interesting keywords =====")
for l in lines:
    s=l.lower()
    if any(k in s for k in ("lea r", "rip +", "cmp eax, 2", "cmp eax, 3", "cmp eax, 1", "cmp eax, 4",
                              "0x10", "call 0x", "ret", "sete", "setne", "movzx eax, byte")):
        if any(k in s for k in ("rip +", "cmp eax,", "movzx eax, byte", "ret", "sete", "setne", "setb", "setae")):
            print(l)
