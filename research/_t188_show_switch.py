from pathlib import Path
lines=Path("research/_t188_clip_order_loc_0xfc9e00.txt").read_text(encoding="utf-8").splitlines()
# print 0xfca170 - 0xfca240 fully, and branch heads
for ln in lines:
    addr=int(ln.split()[0],16)
    if 0xfca160 <= addr <= 0xfca250 or addr in (0xfca472,0xfca5dc,0xfca819,0xfca85c,0xfcadf1,0xfcb1bd,0xfcb371):
        print(ln)

print("\n======= explicit window 0xfca170-0xfca240 =======")
for ln in lines:
    addr=int(ln.split()[0],16)
    if 0xfca170 <= addr <= 0xfca250:
        print(ln)
