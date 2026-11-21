from pathlib import Path
import json

# find neighbor evidence for border provinces
for p in [Path("research/t191_live_units.json"), Path("research/t191_session_recheck.json"),
          Path("research/t180_inventory_sha256.json")]:
    pass
hits=[]
for p in Path("research").glob("t19*") :
    if p.suffix not in {".json"}: continue
    if p.stat().st_size>5_000_000: continue
    try:
        t=p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if "13237" in t or "ITA-adj" in t or "ita_adjacent" in t or "1984" in t and "neighbor" in t:
        hits.append(p.name)
print("candidate files", hits)

# inspect resolve_province signature and province_adjacencies errors
import inspect, sys
sys.path.insert(0,"calling")
from province import resolve_province
from input_loaded_fields import province_adjacencies, province_land_neighbors
print("resolve_province", inspect.signature(resolve_province))
print("adjacencies", inspect.signature(province_adjacencies))
print(province_land_neighbors.__doc__, inspect.signature(province_land_neighbors))
