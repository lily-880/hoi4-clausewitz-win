from pathlib import Path
c=Path("calling/input_capture_live.py").read_text(encoding="utf-8")
for i,l in enumerate(c.splitlines(),1):
    if i>=186:
        print(f"{i}:{l}")
# tests that mention input_capture or sha of inventory
print("======= test files mentioning inventory or capture hash =======")
for p in sorted(Path("research").glob("test_t1*.py")):
    t=p.read_text(encoding="utf-8")
    if "4d9f3b10" in t or "态势" in t or "input_capture" in t or "complete_input" in t:
        print(p.name)
        for i,l in enumerate(t.splitlines(),1):
            if any(k in l for k in ("4d9f3b10","态势","input_capture","sha256","42/","41/")):
                print(f"  {i}:{l[:160]}")
