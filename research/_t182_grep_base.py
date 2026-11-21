from pathlib import Path
t=Path("research/_t182_clip_carmy_base_writer_0xc5c0a0.txt").read_text(encoding="utf-8")
for l in t.splitlines():
    if any(k in l.lower() for k in ("combat","token","0x1f0","0x200","path","retreat","in_")):
        print(l)
print("total lines", len(t.splitlines()))
