from pathlib import Path
# how t180 built the river clip; any notes
for p in sorted(Path("research").glob("_t180*.py")) + sorted(Path("research").glob("t180*.md")):
    t=p.read_text(encoding="utf-8", errors="replace")
    if "river" in t.lower() or "83760" in t:
        print("====", p.name)
        for i,l in enumerate(t.splitlines(),1):
            if any(k in l.lower() for k in ("river","83760","crossing","has_river")):
                print(f"{i}:{l[:200]}")
print("===== t163 helper head =====")
h=Path("research/t163_disasm_windows.py")
print("exists", h.exists(), "size", h.stat().st_size if h.exists() else 0)
if h.exists():
    print("\n".join(h.read_text(encoding="utf-8").splitlines()[:80]))
