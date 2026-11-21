from pathlib import Path
import json

# type research files
for f in [
    "research/t185_orderinstance_type.json",
    "research/t182_combat_order_strings.json",
    "research/t182_order_combat_xrefs.json",
]:
    t = Path(f).read_text(encoding="utf-8")
    print("=" * 80, f, "LEN", len(t))
    print(t[:6000])
    print()
