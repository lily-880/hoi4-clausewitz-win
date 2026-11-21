from pathlib import Path
import inspect, sys
sys.path.insert(0, "calling")
sys.path.insert(0, "research")
p = Path("research/t163_disasm_windows.py")
t = p.read_text(encoding="utf-8")
print("lines", len(t.splitlines()))
for i, l in enumerate(t.splitlines()[:80], 1):
    print(f"{i:4d}|{l[:200]}")
