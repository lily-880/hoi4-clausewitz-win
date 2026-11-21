from pathlib import Path
import re, json

# Find ORDER_* strings already mined, and any type table
for f in [
    "research/_t188_ordertype_strings.py",
    "research/_t188_type_table.py",
    "research/_t188_type_asserts.py",
    "research/_t182_getordertype.py",
    "research/_t193_find_asserts.py",
    "research/_t193_pick_front.py",
]:
    p = Path(f)
    if p.exists():
        t = p.read_text(encoding="utf-8")
        print("=" * 80, f, "LEN", len(t))
        print(t[:4000])
        print()
