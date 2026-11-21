from pathlib import Path
for n in ["research/_t180_clip_0xef2c80.txt","research/_t180_clip_0xef2fc0.txt"]:
    t=Path(n).read_text(encoding="utf-8")
    print("=======", n, "lines", len(t.splitlines()), "=======")
    print(t)
