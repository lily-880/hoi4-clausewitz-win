from pathlib import Path
keys = (
    "FACTORY_IDX",
    "factory_idx",
    "factory_lookup",
    "FN_CMD_QUEUE_POST",
    "0x13FB000",
    "0x13fb000",
    "1402",
    "ACTION_ISVALID",
)
files = []
for root in (Path("calling"), Path("research"), Path("docs")):
    if not root.exists():
        continue
    for p in root.rglob("*"):
        if p.suffix.lower() not in {".py", ".json", ".md"}:
            continue
        if p.name == "cmd_layout.py" or p.stat().st_size > 2_000_000:
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "factory_lookup" in t or "FACTORY_TABLE" in t or "factory_table" in t or "G_FACTORY" in t:
            files.append(str(p))
print("factory table files:")
for f in files:
    print(" ", f)

print("======= offsets / post rva mentions in 1.19.5 tables =======")
p = Path("calling/tables/offsets_input_windows_1.19.5.json")
t = p.read_text(encoding="utf-8-sig")
for s in ("13fb000", "22c41e0", "factory", "post", "12c2ca0", "2a2c790", "29d6d98"):
    if s.lower() in t.lower():
        print(" profile contains", s)

# search calling python for factory table rva
for p in Path("calling").glob("*.py"):
    if p.name == "cmd_layout.py":
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    for i, l in enumerate(t.splitlines(), 1):
        if any(s in l for s in ("factory_table", "FACTORY_TABLE", "factory_lookup", "G_CMD_FACTORY", "CMD_FACTORY", "0x13FB000", "factory_idx 1402")):
            print(f"{p}:{i}:{l[:200]}")
