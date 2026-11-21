from pathlib import Path
p = Path("research/_t180_clip_river_crossing_token_0x83760.txt")
print("exists", p.exists(), "size", p.stat().st_size if p.exists() else 0)
if p.exists():
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    print("lines", len(lines))
    print("===== HEAD 80 =====")
    print("\n".join(lines[:80]))
    print("===== TAIL 40 =====")
    print("\n".join(lines[-40:]))
# inventory line + schema already known; list other river clips / proofs
print("===== river-related files =====")
for q in sorted(Path("research").glob("*river*")):
    print(q.name, q.stat().st_size)
for q in sorted(Path("research").glob("*adjac*")):
    print(q.name, q.stat().st_size)
