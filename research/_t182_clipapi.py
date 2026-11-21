import sys
from pathlib import Path
sys.path.insert(0, "research")
sys.path.insert(0, "calling")
from t163_disasm_windows import disasm_window

# dump start of path serializer and supply tokens from secondary writer
for rva, name, n in (
    (0x1d2bf0, "research/_t182_clip_path_serializer_0x1d2bf0.txt", 40),
    (0xced2e0, "research/_t182_clip_carmy_secondary_writer_0xced2e0.txt", 80),
    (0x209190, "research/_t182_clip_land_combat_id_0x208f90.txt", 20),
):
    lines = disasm_window(rva, max_ins=n) if False else None
# use whatever API exists
print("API", [x for x in dir(__import__("t163_disasm_windows")) if not x.startswith("_")])
