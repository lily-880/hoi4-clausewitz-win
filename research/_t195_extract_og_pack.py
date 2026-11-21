from pathlib import Path
ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
t = (ROOT / "research" / "_t192_post.py").read_text(encoding="utf-8")
lines = t.splitlines()
print("lines", len(lines))
# print consts at top 80
for i, ln in enumerate(lines[:80], 1):
    print(f"{i:4d} {ln}")
print("\n----- writes / malloc / pack -----")
for i, ln in enumerate(lines, 1):
    if any(s in ln for s in ("_write", "_game_malloc", "OG[", "OG =", "packed", "theatre", "unit", "+0x", "isvalid", "FN_CMD", "factory")):
        print(f"{i:4d} {ln[:220]}")
