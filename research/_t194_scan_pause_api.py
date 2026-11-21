import re, sys
from pathlib import Path
# gamestate pause/speed helpers
text=Path("calling/gamestate.py").read_text(encoding="utf-8")
# find function defs related
for m in re.finditer(r"^def .*$", text, re.M):
    line=m.group()
    if any(k in line.lower() for k in ("pause","speed","idler","tick","campaign","session")):
        print(line)
print("--- snippets ---")
for k in ["0x6c1", "speed_index", "pause", "idler"]:
    idxs=[m.start() for m in re.finditer(k, text)]
    print(k, "hits", len(idxs))
# print unique functions with 0x6c1 nearby
for m in re.finditer(r"0x6c1", text):
    print(text[max(0,m.start()-300):m.start()+300])
    print("====")
