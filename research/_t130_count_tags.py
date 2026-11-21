from pathlib import Path
import re

def parse_tag_file(path):
    tags = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # skip dynamic_tags = yes
        if re.match(r"dynamic_tags\s*=", s, re.I):
            continue
        m = re.match(r'^([A-Z0-9]{3})\s*=\s*"([^"]+)"', s)
        if m:
            tags.append((m.group(1), m.group(2)))
    return tags

base = Path(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\common\country_tags")
static = parse_tag_file(base / "00_countries.txt")
dyn = parse_tag_file(base / "zz_dynamic_countries.txt")
# 1-based: index 0 unused
all_tags = [None] + static + dyn
print("static", len(static), "dyn", len(dyn), "total_with_zero", len(all_tags), "max_index", len(all_tags)-1)
for i in (0, 1, 14, 15, 16, 37, 38, 39, 43, 44, 45, 67, 68, 69):
    if 0 <= i < len(all_tags):
        print(i, all_tags[i])
    else:
        print(i, "OOB")
# find ETH USA CHI SPR ITA HAI
want = {"ETH","USA","CHI","SPR","ITA","HAI","GER","ENG"}
for i, row in enumerate(all_tags):
    if row and row[0] in want:
        print("FOUND", i, row)
