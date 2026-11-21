from pathlib import Path

keys = (
    "controller_index",
    "CControllerArea",
    "province_by_id",
    "PROVINCE_ARRAY",
    "G_MAP",
    "controller country",
    "owner_tag",
    "province_owner",
    "CProvince*",
)
for p in list(Path("calling").glob("*.py")) + list(Path("research").glob("t18*.md")) + list(Path("research").glob("t18*.json")):
    if p.name == "cmd_layout.py" or p.stat().st_size > 2_000_000:
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    hits = [s for s in keys if s in t]
    if hits:
        print(p.name, hits)

print("======= offsets province/map =======")
t = Path("calling/offsets.py").read_text(encoding="utf-8")
for i, l in enumerate(t.splitlines(), 1):
    if any(s in l.upper() for s in ("PROVINCE", "MAP", "CONTROLLER", "ADJAC")):
        print(f"off {i}|{l[:200]}")
