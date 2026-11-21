from pathlib import Path
# print relevant sections of input_loaded_fields, offsets, t191 test, inventory helpers
p = Path("calling/input_loaded_fields.py")
lines = p.read_text(encoding="utf-8").splitlines()
for i,l in enumerate(lines,1):
    if any(s in l.lower() for s in ("def ", "assigned", "formation", "orders_group", "army_id", "leader", "carmy+0x", "0xc0", "theatre")):
        if i < 200 or "assigned" in l.lower() or "formation" in l.lower() or "orders" in l.lower() or l.strip().startswith("def "):
            print(f"{p}:{i}:{l}")
print("---offsets.py hits---")
p = Path("calling/offsets.py")
for i,l in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
    if any(s in l for s in ("PATH", "t191", "t183", "t184", "LEADER", "ORDERS", "ARMY_ID", "1048", "assigned", "formation")):
        print(f"{p}:{i}:{l[:220]}")
