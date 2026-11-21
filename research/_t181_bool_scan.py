import json, os, sys, struct, collections
from pathlib import Path
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"
sys.path.insert(0, str(Path("calling").resolve()))
from mem import Proc, find_pid

live=json.loads(Path("research/t180_landindex_and_edges.json").read_text(encoding="utf-8"))
has_river=set(); no_river=set()
for p in live["provinces"]:
    types={e["b10"] for e in p["edges"]}
    if 2 in types or 3 in types:
        has_river.add(p["province_id"])
    else:
        no_river.add(p["province_id"])
print("with river", sorted(has_river))
print("without", sorted(no_river))

p=Proc(find_pid("hoi4.exe"))
try:
    # map pid -> ptr, b8
    rows=[]
    for rec in live["provinces"]:
        ptr=int(rec["ptr"],16)
        b8=int(rec["b8"],16)
        blob=p.read(ptr, 0x200)
        b8blob=p.read(b8, 0x100)
        rows.append((rec["province_id"], rec["province_id"] in has_river, blob, b8blob))
    def diffs(getblob, label, nbytes):
        # find offsets where all-has share a value, all-no share a different value
        hits=[]
        for off in range(nbytes):
            hv=[getblob(r)[off] for r in rows if r[1]]
            nv=[getblob(r)[off] for r in rows if not r[1]]
            if len(set(hv))==1 and len(set(nv))==1 and hv[0]!=nv[0]:
                hits.append({"off":hex(off), "has":hv[0], "no":nv[0]})
        # also i32/i64 aligned
        for width,fmt in ((4,"<i"),(8,"<q")):
            for off in range(0, nbytes-width+1, width):
                hv=[struct.unpack_from(fmt, getblob(r), off)[0] for r in rows if r[1]]
                nv=[struct.unpack_from(fmt, getblob(r), off)[0] for r in rows if not r[1]]
                if len(set(hv))==1 and len(set(nv))==1 and hv[0]!=nv[0]:
                    hits.append({"off":hex(off), "width":width, "has":hv[0], "no":nv[0]})
        print(label, "discriminating offsets", hits[:30], "count", len(hits))
        return hits
    cprov=diffs(lambda r:r[2], "CProvince+0..0x200", 0x200)
    defn=diffs(lambda r:r[3], "b8+0..0x100", 0x100)
    out={"has_river_province_ids":sorted(has_river),"no_river_province_ids":sorted(no_river),
         "cprovince_byte_or_scalar_discriminators":cprov,
         "definition_byte_or_scalar_discriminators":defn,
         "note":"offsets that perfectly split the 8-with-river vs 4-without among the 12 own provinces; may still be coincidental"}
    Path("research/t181_no_stored_province_bool.json").write_text(json.dumps(out, indent=2)+"\n", encoding="utf-8")
finally:
    p.close()
