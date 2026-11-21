from pathlib import Path
roots = [
    Path(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV"),
    Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV"),
]
for root in roots:
    if not root.exists():
        print("MISSING", root)
        continue
    print("ROOT", root)
    hits = []
    for folder in [root / "common", root / "common" / "country_tags", root]:
        if not folder.exists():
            continue
        if folder.name == "Hearts of Iron IV":
            for p in folder.iterdir():
                if p.is_dir() and "tag" in p.name.lower():
                    print(" DIR", p)
        else:
            for p in folder.rglob("*"):
                if not p.is_file():
                    continue
                n = p.name.lower()
                if "country_tag" in n or "00_countries" in n or n.endswith("tags.txt"):
                    hits.append(p)
    for h in hits[:50]:
        print(" FILE", h)
# also list common/country_tags directly
ct = Path(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\common\country_tags")
print("ct exists", ct.exists())
if ct.exists():
    for p in sorted(ct.iterdir()):
        print(" ", p.name, p.stat().st_size)
