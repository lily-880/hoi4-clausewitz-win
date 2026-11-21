from pathlib import Path
import re, json

# Extract structured blocks for key commands from cmd_layout.py
# The file starts with a large dict ORDERS / catalogs. Let's find FACTORY entries.

p = Path("calling/cmd_layout.py")
text = p.read_text(encoding="utf-8", errors="replace")

# Find "COrderGroupCommand" blocks - print around first 3 occurrences with context
keys = ["COrderGroupCommand", "CArmyGroupCommand", "CSetArmyLeaderCommand", "CDeleteOrderGroupCommand", "CAssignToArmyGroupCommand"]
for key in keys:
    print("=" * 70, key)
    idx = 0
    pos = 0
    shown = 0
    while shown < 3:
        i = text.find(key, pos)
        if i < 0:
            break
        # find line number
        lineno = text[:i].count("\n") + 1
        # window of 30 lines
        start = text.rfind("\n", 0, i)
        chunk = "\n".join(text[max(0, i-200):i+1200].splitlines()[:40])
        print(f"--- at line {lineno} ---")
        print(chunk)
        print()
        pos = i + len(key)
        shown += 1
