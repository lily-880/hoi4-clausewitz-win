from pathlib import Path
root = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
hits = []
for p in list((root / "calling").rglob("*.py")) + list((root / "research").glob("_t193_nbs.py")) + list((root / "research").glob("_t191*.py")):
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if "def resolve_province" in t or "def province_land_neighbors" in t:
        hits.append(str(p))
        # print signature lines
        for i, ln in enumerate(t.splitlines(), 1):
            if "def resolve_province" in ln or "def province_land_neighbors" in ln:
                print(p.name, i, ln)
print("FILES", hits)
