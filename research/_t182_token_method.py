from pathlib import Path
# how token 4ced / supply_ratio was bound
for p in Path("research").glob("t165*"):
    if p.suffix in (".py",".md",".json") and p.stat().st_size<500000:
        t=p.read_text(encoding="utf-8", errors="replace")
        if "4ced" in t or "supply_ratio" in t or "0x610" in t:
            print("=======", p.name)
            for i,l in enumerate(t.splitlines(),1):
                if any(k in l for k in ("4ced","610","supply_ratio","token","serialize","named")):
                    print(f"  {i}:{l[:220]}")
