from pathlib import Path
lines=Path("research/_t182_clip_carmy_base_writer_0xc5c0a0.txt").read_text(encoding="utf-8").splitlines()
# print from 0xc5c400 to end, and also path/location block already have
for l in lines:
    a=int(l.split()[0],16)
    if a>=0xc5c400 or (0xc5c180<=a<=0xc5c1c0):
        print(l)
