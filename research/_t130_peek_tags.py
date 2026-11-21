from pathlib import Path
import re
p = Path(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\common\country_tags\00_countries.txt")
t = p.read_text(encoding="utf-8", errors="replace")
print("==== HEAD ====")
print("\n".join(t.splitlines()[:40]))
print("==== TAIL ====")
print("\n".join(t.splitlines()[-20:]))
print("==== DYN HEAD ====")
d = Path(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\common\country_tags\zz_dynamic_countries.txt")
print(d.read_text(encoding="utf-8", errors="replace")[:1500])
