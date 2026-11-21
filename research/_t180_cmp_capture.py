import json
from pathlib import Path
a=json.loads(Path("research/t180_live_capture.json").read_text(encoding="utf-8"))
b=json.loads(Path("research/t180_live_capture_repeat.json").read_text(encoding="utf-8"))
oa,ob=a["observation"],b["observation"]
print("obs equal", oa==ob)
print("complete", a["complete_input"], b["complete_input"])
print("read_only", a["read_only"], b["read_only"])
print("schema", a.get("schema_validation"), b.get("schema_validation"))
provs=oa["world"]["provinces"]
print("provinces", len(provs))
total=0
for p in provs:
    n=p.get("neighbors")
    print(p["province_id"], "n", len(n or []), n, "has_river", "has_river_crossing" in p)
    total += len(n or [])
print("total neighbors", total)
eq=oa["world"]["shortages"].get("equipment")
print("equipment", eq)
live=json.loads(Path("research/t180_landindex_and_edges.json").read_text(encoding="utf-8"))
expect={p["province_id"]: p["land_neighbors"] for p in live["provinces"]}
mismatch=[]
for p in provs:
    if p["neighbors"]!=expect.get(p["province_id"]):
        mismatch.append((p["province_id"], p["neighbors"], expect.get(p["province_id"])))
print("mismatches", mismatch)
print("pid", a["pid"], "hour", oa["meta"])
# evidence neighbor_collection
nc=a["evidence"].get("neighbor_collection")
print("neighbor_collection entries", len(nc or []))
if nc:
    print("hist sample", [(x["province_id"], x["type_hist"], x["land_neighbors"]) for x in nc])
