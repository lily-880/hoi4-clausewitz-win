from pathlib import Path
p = Path("calling/army_subjects.py")
raw = p.read_bytes()
print("BOM", raw[:3], "len", len(raw))
text = raw.decode("utf-8-sig")
# show recipe
lines = text.splitlines()
for i,l in enumerate(lines):
    if "def set_army_leader" in l:
        for j in range(i, i+25):
            print(f"{j+1:4d}|{lines[j]}")
        break
# compile via utf-8-sig
compile(text, str(p), "exec")
print("recipe compiles")

# show assigned_to and own_armies in loader
lines = Path("calling/input_loaded_fields.py").read_text(encoding="utf-8").splitlines()
for i,l in enumerate(lines,1):
    if 150 <= i <= 280 and (i<=170 or any(s in l for s in ("assigned_to","def own_armies","def unit_formation","HANDLE_TYPE","ORDERS_GROUP","army + 0xc0","0x1048"))):
        print(f"{i:4d}|{l}")
