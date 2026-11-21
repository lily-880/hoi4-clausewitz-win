import json
from pathlib import Path
a=json.loads(Path("research/t181_live_capture.json").read_text(encoding="utf-8"))
b=json.loads(Path("research/t181_live_capture_repeat.json").read_text(encoding="utf-8"))
print("obs equal", a["observation"]==b["observation"])
print("complete", a["complete_input"], "readonly", a["read_only"])
print("schema errors", a.get("schema_validation",{}).get("error_count"), "neighbors-related",
      [e for e in a.get("schema_validation",{}).get("errors",[]) if "river" in e.get("message","").lower() or "neighbor" in str(e).lower()])
trues=0
for p in a["observation"]["world"]["provinces"]:
    hr=p["has_river_crossing"]
    assert set(hr)=={str(n) for n in p["neighbors"]}
    t=sum(1 for v in hr.values() if v)
    trues += t
    print(p["province_id"], "n", len(p["neighbors"]), "river", t, [int(k) for k,v in hr.items() if v])
print("true total", trues)
print("equipment", a["observation"]["world"]["shortages"].get("equipment"))
