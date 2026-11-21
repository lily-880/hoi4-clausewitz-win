from pathlib import Path
import json, pprint
o=json.loads(Path("calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8-sig"))
pprint.pp(o["province_adjacency_array_t179"])
ev=json.loads(Path("research/t180_landindex_and_edges.json").read_text(encoding="utf-8"))
print("hist_b10", ev["hist_b10"])
print("hist_u10", ev["hist_u10"])
print("hist_u14", ev["hist_u14"])
print("edge_counts", ev["edge_counts"])
print("own_land_reciprocal", ev["own_land_reciprocal"])
print("land_index_global", ev["land_index_global"])
# first province summary without huge blobs
p0=ev["provinces"][0]
print("p0 keys", p0.keys())
for k,v in p0.items():
    print(" p0", k, v if not isinstance(v,list) else f"list[{len(v)}] sample={v[:2] if v else None}")
# type uniqueness and sea
types=set(); sea=0; landish=0; selfs=0
for p in ev["provinces"]:
    pid=p.get("pid") or p.get("province_id")
    for e in p.get("edges") or p.get("neighbors") or []:
        typ=e.get("b10") if isinstance(e,dict) else None
        if typ is not None: types.add(typ)
print("done first pass keys only")
# unique type values from edges if structured
if "edges" in ev["provinces"][0] or "records" in ev["provinces"][0] or "adj" in ev["provinces"][0]:
    pass
print("p keys again more:", list(ev["provinces"][0]))
