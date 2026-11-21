from pathlib import Path
import json

# t183 assigned_to + t184 live theatre + formation json
for name in [
    "research/t184_live_theatre.json",
    "research/t184_formation_writers.json",
    "research/t183_checkpoint.md",
]:
    p = Path(name)
    print("=" * 70, name)
    if name.endswith(".md"):
        t = p.read_text(encoding="utf-8")
        # print assigned_to / leader sections
        lines = t.splitlines()
        for i,l in enumerate(lines):
            if any(s in l.lower() for s in ("assigned", "leader", "deployed", "formation")):
                lo=max(0,i-1); hi=min(len(lines), i+3)
                print("\n".join(lines[lo:hi])); print("---")
    else:
        d = json.loads(p.read_text(encoding="utf-8"))
        print(json.dumps(d, ensure_ascii=False, indent=2)[:3500])
        print()
