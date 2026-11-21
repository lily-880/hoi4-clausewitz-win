from pathlib import Path
c=Path("calling/input_capture_live.py").read_text(encoding="utf-8")
for i,l in enumerate(c.splitlines(),1):
    if 75<=i<=100:
        print(f"{i}:{l}")
print("======= clips exist =======")
for n in ["research/_t180_clip_0xe90560.txt","research/_t180_clip_NeighborAdjs_size_0xe90560.txt","research/_t180_clip_0xab3660.txt","research/_t180_clip_0x14a6540.txt","research/_t180_clip_sea_province_pathfinding_0xd55250.txt"]:
    p=Path(n)
    print(n, p.exists(), p.stat().st_size if p.exists() else 0)
# e90560 filename?
for p in sorted(Path("research").glob("_t180_clip*")):
    print(p.name, p.stat().st_size)
