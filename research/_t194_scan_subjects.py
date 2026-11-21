import re
from pathlib import Path

# extract relevant sections from army_subjects, offsets, schema, t182 xrefs
files_patterns = {
    "calling/army_subjects.py": [
        r"COrderExecute", r"offensive_line", r"area_defense", r"COrderNew",
        r"set_unit", r"unit_leader", r"assigned", r"ExecuteCommand", r"def "
    ],
}
text = Path("calling/army_subjects.py").read_text(encoding="utf-8", errors="ignore")
print("army_subjects len", len(text), "lines", text.count("\n"))
# function names
for m in re.finditer(r"^def |^class |^[A-Z_]+ ?=|^[A-Za-z_]+COMMAND", text, re.M):
    start = text.rfind("\n", 0, m.start()) + 1
    print("SYM", text[start:text.find("\n", m.start())][:200])

# search windows around keywords
keys = ["COrderExecute", "COrderNewFront", "offensive", "area_defense", "set_army_leader", "unit_leader", "CSet", "garrison", "frontline", "NewRoot", "vertex", "axis"]
for k in keys:
    idxs = [m.start() for m in re.finditer(re.escape(k), text)]
    if not idxs:
        continue
    print("\n****", k, "hits", len(idxs))
    for i in idxs[:3]:
        print(text[max(0, i-200):i+400])
        print("---")
