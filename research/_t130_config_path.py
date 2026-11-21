from pathlib import Path
import re
# show config game path helpers and list all country_tags files
import sys
sys.path.insert(0, "calling")
import config
print("config attrs", [a for a in dir(config) if not a.startswith("_")])
for name in ("GAME_DIR","game_dir","HOI4_DIR","binary_path","EXE_DIR","STEAM","ROOT"):
    if hasattr(config, name):
        v = getattr(config, name)
        print(name, v() if callable(v) else v)
# country_tags dir files in order
ct = Path(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\common\country_tags")
print("files", [p.name for p in sorted(ct.iterdir()) if p.is_file()])
