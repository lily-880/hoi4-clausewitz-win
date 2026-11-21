import json
from pathlib import Path
d=json.loads(Path("research/t193_ag_post.json").read_text(encoding="utf-8"))
# leader of AG immediately after create, before set leader
after=d["theatre_after_ag"][0]["field_marshal"]["items"]
print("=== after AG create, before/with leader attempt ===")
print(json.dumps(after, ensure_ascii=False, indent=2))
print("=== sl packed ===")
print(json.dumps({k:d.get(k) for k in ("chosen_ag_leader","sl_packed","sl_dry_isvalid","sl_post","ag_packed")}, ensure_ascii=False, indent=2))
print("=== army1 after create fm_flag ===")
print(json.dumps(d["theatre_after_ag"][0]["orders_group"]["items"], ensure_ascii=False, indent=2)[:2000])
