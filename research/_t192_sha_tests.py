from pathlib import Path
for p in sorted(Path("research").glob("test_t18*.py")) + sorted(Path("research").glob("test_t19*.py")):
    t = p.read_text(encoding="utf-8")
    if "sha256" in t.lower() or "INV.read" in t or "e38f089d" in t or "98d83a60" in t:
        print(p.name)
        for i,l in enumerate(t.splitlines(),1):
            if any(s in l for s in ("sha256", "INV.read", "hexdigest", "T191", "LIVE_SHA", "assertEqual(sha")):
                print(f"  {i}:{l}")
