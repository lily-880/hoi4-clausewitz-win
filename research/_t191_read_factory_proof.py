import json
from pathlib import Path
p = Path("reports/phase2ez_factory_lookup_proof.json")
if p.exists():
    d = json.loads(p.read_text(encoding="utf-8"))
    print("keys", list(d.keys())[:40])
    print(json.dumps(d, indent=2, ensure_ascii=False)[:4000])
else:
    print("missing", p)
    # search others
    for q in Path("reports").glob("*factory*") if Path("reports").exists() else []:
        print(" ", q, q.stat().st_size)
