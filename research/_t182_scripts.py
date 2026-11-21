from pathlib import Path
# scripts and mentions
for p in [Path("research/t165_army_manpower_supply.py"), Path("research/t165_world_formation_inventory.py")]:
    print("=======", p)
    print(p.read_text(encoding="utf-8")[:3000])

print("======= grep research mentions =====")
needles=("CA_PATH_200","in_combat","0x200","army_current_supply","IsInCombat","assigned_to","CUnitOrder","COrder")
# only search smaller text files
count=0
for p in Path("research").glob("*.md"):
    t=p.read_text(encoding="utf-8", errors="replace")
    hits=[]
    for i,l in enumerate(t.splitlines(),1):
        if any(n.lower() in l.lower() for n in ("in_combat","CA_PATH","order.type","supply.ratio","assigned_to","formation")):
            hits.append(f"  {i}:{l[:200]}")
    if hits:
        print(p.name)
        print("\n".join(hits[:20]))
