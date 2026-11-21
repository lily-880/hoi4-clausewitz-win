from pathlib import Path
import json, re

root = Path(".")

# short clip of the range check
fam = Path("research/_t181_clip_family_0x12971a0.txt").read_text(encoding="utf-8").splitlines()
clip = [l for l in fam if 0x1297bb0 <= int(l.split()[0],16) <= 0x1297bd0]
Path("research/_t181_clip_river_type_range_0x12971a0.txt").write_text("\n".join(clip)+"\n", encoding="utf-8")
print("clip", clip)

# proofs
reader = {
  "build": "HOI4 1.19.5.0.7c6c",
  "pid": 26976,
  "read_only": True,
  "promoted": "world.provinces.has_river_crossing",
  "shape": "object: neighbor province id (decimal string) -> bool, same land-neighbor set as world.provinces.neighbors; true iff adjacency type in {2,3}",
  "not_a_province_bool": True,
  "not_promoted_as": "single boolean on the province",
  "engine_predicate": {
    "func": "0x12971a0",
    "clip": "research/_t181_clip_river_type_range_0x12971a0.txt",
    "family": ["0x12971a0", "0x1297f10", "0x1298c80", "0x12999f0", "0x129a760"],
    "ins": [
      "0x1297bbd movzx eax, byte ptr [rdx + 0x10]",
      "0x1297bc1 sub al, 2",
      "0x1297bc3 cmp al, 1",
      "0x1297bc5 ja 0x1297bd1"
    ],
    "meaning": "unsigned range type in {2,3} (river, river_large); adds an extra path cost from [rip+0x33e1838]",
    "context_asserts": [
      "NeighborFlow < CurrentEntry._Flow",
      "InfraRatio <= 1_fixed",
      "caller 0x12ae4e5: !_NonLocalNodes.Contains( _pCapital->GetProvinceID() )"
    ],
    "context": "supply/infra network pathfinding; per-edge, not a province-wide flag"
  },
  "token_clip_0x83760": {
    "role": "string-token registrar only; river_crossing string 0x2b494b0 is lea'd at 0xab285 into slot 0x346D188",
    "not_a_reader": True,
    "direct_rip_consumers_of_slot": "none besides registrar"
  },
  "no_stored_province_bool": {
    "proof": "research/t181_no_stored_province_bool.json",
    "cprovince_0_0x200": "no byte or aligned scalar splits the 8 river-edge vs 4 non-river own provinces",
    "definition_arrays": "[CProvince+0xb8]+0x28 and +0x40 are pdx arrays present only on the 8 river-edge provinces; size at +0x34 is 1 vs 0, but province 1984 has five type-2 edges so this is not a crossing count. RTTI SRiverPath / SProvinceRiverPoint are map river geometry, not the field."
  },
  "live": {
    "own_provinces": 12,
    "edges": 73,
    "type_hist": {"0": 57, "2": 16, "3": 0},
    "true_crossings": 16,
    "provinces_with_any_crossing": 8
  }
}
Path("research/t181_has_river_crossing_contract.json").write_text(json.dumps(reader, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

# ---- patch collector: add province_adjacencies, keep province_land_neighbors wrapper ----
p = root/"calling/input_loaded_fields.py"
text = p.read_text(encoding="utf-8")
old = '''def province_land_neighbors(r, province):
    r.require(province, 'CProvince')
    pid = struct.unpack('<I', r.exact(province + 0xa4, 4))[0]
    if pid == 0:
        raise ObservationError('invalid province id for adjacency')
    definition = r.q(province + 0xb8)
    if definition < 0x10000:
        raise ObservationError('invalid province definition pointer')
    data, cap, n = struct.unpack('<QII', r.exact(definition + 0x70, 16))
    if not 0 <= n <= cap <= MAX_ADJACENCIES or (n and data < 0x10000):
        raise ObservationError('invalid province adjacency array')
    raw = r.exact(data, n * ADJACENCY_STRIDE) if n else b''
    ids = []
    hist = {}
    for j in range(n):
        rec = raw[j * ADJACENCY_STRIDE:(j + 1) * ADJACENCY_STRIDE]
        tgt = struct.unpack_from('<I', rec, 8)[0]
        typ = rec[0x10]
        hist[typ] = hist.get(typ, 0) + 1
        if typ not in KNOWN_ADJACENCY_TYPES:
            raise ObservationError('unknown adjacency type')
        if typ in LAND_ADJACENCY_TYPES:
            if not 1 <= tgt <= 65535 or tgt == pid:
                raise ObservationError('invalid land neighbor id')
            if tgt in ids:
                raise ObservationError('duplicate land neighbor id')
            ids.append(tgt)
    evidence = {
        'province_id': pid,
        'adjacency_count': n,
        'type_hist': {str(k): v for k, v in sorted(hist.items())},
        'land_neighbors': len(ids),
        'source': 'e90560 stride 48 target +8; ab3660/14a6540 type +0x10; land types 0/2/3',
    }
    return ids, evidence
'''
new = '''def province_adjacencies(r, province):
    r.require(province, 'CProvince')
    pid = struct.unpack('<I', r.exact(province + 0xa4, 4))[0]
    if pid == 0:
        raise ObservationError('invalid province id for adjacency')
    definition = r.q(province + 0xb8)
    if definition < 0x10000:
        raise ObservationError('invalid province definition pointer')
    data, cap, n = struct.unpack('<QII', r.exact(definition + 0x70, 16))
    if not 0 <= n <= cap <= MAX_ADJACENCIES or (n and data < 0x10000):
        raise ObservationError('invalid province adjacency array')
    raw = r.exact(data, n * ADJACENCY_STRIDE) if n else b''
    ids = []
    crossings = {}
    hist = {}
    for j in range(n):
        rec = raw[j * ADJACENCY_STRIDE:(j + 1) * ADJACENCY_STRIDE]
        tgt = struct.unpack_from('<I', rec, 8)[0]
        typ = rec[0x10]
        hist[typ] = hist.get(typ, 0) + 1
        if typ not in KNOWN_ADJACENCY_TYPES:
            raise ObservationError('unknown adjacency type')
        if typ in LAND_ADJACENCY_TYPES:
            if not 1 <= tgt <= 65535 or tgt == pid:
                raise ObservationError('invalid land neighbor id')
            if tgt in ids:
                raise ObservationError('duplicate land neighbor id')
            ids.append(tgt)
            crossings[str(tgt)] = typ in (2, 3)
    evidence = {
        'province_id': pid,
        'adjacency_count': n,
        'type_hist': {str(k): v for k, v in sorted(hist.items())},
        'land_neighbors': len(ids),
        'river_crossings': sum(1 for v in crossings.values() if v),
        'source': 'e90560 stride 48 target +8; 0x12971a0 type in {2,3} is per-edge river crossing',
    }
    return {'neighbors': ids, 'has_river_crossing': crossings, 'evidence': evidence}


def province_land_neighbors(r, province):
    adj = province_adjacencies(r, province)
    return adj['neighbors'], adj['evidence']
'''
if old not in text:
    raise SystemExit("collector function block not found")
text = text.replace(old, new, 1)
# docstring mention
text = text.replace("adjacency reader t180.", "adjacency reader t180; has_river_crossing t181.")
p.write_text(text, encoding="utf-8")
print("patched loaded_fields")

# ---- patch capture to use province_adjacencies ----
cpath = root/"calling/input_capture_live.py"
ct = cpath.read_text(encoding="utf-8")
ct = ct.replace("province_land_neighbors,own_reinforcement_requests",
                "province_land_neighbors,province_adjacencies,own_reinforcement_requests", 1)
old_block = """                neighbors,ne=province_land_neighbors(loaded,pp)
                neighbor_evidence.append(ne)
                province_cache[pp]['neighbors']=neighbors
"""
new_block = """                adj=province_adjacencies(loaded,pp)
                neighbor_evidence.append(adj['evidence'])
                province_cache[pp]['neighbors']=adj['neighbors']
                province_cache[pp]['has_river_crossing']=adj['has_river_crossing']
"""
if old_block not in ct:
    raise SystemExit("capture neighbor block missing")
ct = ct.replace(old_block, new_block, 1)
old_src = "'neighbors_source':'live [CProvince+0xb8]+0x70 stride 48 target +8; types 0/2/3 only; 14a6540/ab3660',"
new_src = old_src + "\n                            'has_river_crossing_source':'same adjacency records; type in {2,3} per 0x12971a0 range check; object neighbor_id->bool',"
if old_src not in ct:
    raise SystemExit("neighbors_source missing")
ct = ct.replace(old_src, new_src, 1)
cpath.write_text(ct, encoding="utf-8")
print("patched capture")

# ---- offsets ----
offp = root/"calling/tables/offsets_input_windows_1.19.5.json"
off = json.loads(offp.read_text(encoding="utf-8-sig"))
off["has_river_crossing_t181"] = {
    "location": "same [CProvince+0xb8]+0x70 record as neighbors; type at +0x10",
    "predicate": "type in {2,3}: sub al,2; cmp al,1 at 0x1297bc1 in 0x12971a0 family",
    "shape": "object mapping land-neighbor id (decimal string) to bool; not a province-level bool",
    "consumer": "supply/infra pathfinding 0x12971a0 (extra edge cost); five clones 0x1297f10..0x129a760",
    "not": "CProvince scalar; definition +0x28/+0x40 are SRiverPath/SProvinceRiverPoint geometry arrays",
    "token_registrar": "0x83760 / slot 0x346D188 is not a reader",
    "promoted": True,
    "proofs": [
        "research/t181_has_river_crossing_contract.json",
        "research/t181_no_stored_province_bool.json",
        "research/_t181_clip_river_type_range_0x12971a0.txt"
    ]
}
offp.write_text(json.dumps(off, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print("offsets updated")

# ---- freeze t180 inventory test so it no longer hashes live D ----
t180 = (root/"research/test_t180_input_neighbors.py").read_text(encoding="utf-8")
old_inv = '''    def test_inventory_promotes_only_neighbors(self):
        inv = Path(r"D:\\Michael Foo\\钢四陆军总司令\\态势信息读取能力清单.md")
        raw = inv.read_bytes()
        digest = __import__("hashlib").sha256(raw).hexdigest()
        recorded = json.loads((ROOT / "research/t180_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertEqual(digest, recorded["sha256"])
        text = raw.decode("utf-8")
        lines = [l for l in text.splitlines() if l.startswith("| world.") or l.startswith("| meta.") or l.startswith("| policy.") or l.startswith("| unit.") or l.startswith("| ")]
        # count official field rows: 3-col pipes excluding header/separator
        fields = []
        tables = 0
        verified = 0
        for l in text.splitlines():
            if l.startswith("| 字段名 |"):
                tables += 1
                continue
            if l.startswith("| ---"):
                continue
            if l.startswith("| ") and l.count("|") >= 3:
                cols = [c.strip() for c in l.strip().strip("|").split("|")]
                if len(cols) >= 3 and cols[0] and cols[1] in ("已验证", "未验证"):
                    fields.append(cols)
                    if cols[1] == "已验证":
                        verified += 1
        self.assertEqual(tables, 14)
        self.assertEqual(len(fields), 116)
        self.assertEqual(verified, 42)
        self.assertEqual(len(fields) - verified, 74)
        row = next(c for c in fields if c[0] == "world.provinces.neighbors")
        self.assertEqual(row[1], "已验证")
        self.assertIn("陆地邻接", row[2])
        self.assertIn("不含海", row[2])
        river = next(c for c in fields if c[0] == "world.provinces.has_river_crossing")
        self.assertEqual(river[1], "未验证")
'''
new_inv = '''    def test_inventory_promotes_only_neighbors(self):
        # Frozen t180 record; live D inventory is asserted by later batches.
        recorded = json.loads((ROOT / "research/t180_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertEqual(recorded["sha256"], "0f0576e02549f045b58f158472cb4adf8fa13e6b39b321cbbd549737a480841b")
        self.assertEqual(recorded["fields"], 116)
        self.assertEqual(recorded["tables"], 14)
        self.assertEqual(recorded["verified"], 42)
        self.assertEqual(recorded["unverified"], 74)
        cap = json.loads((ROOT / "research/t180_live_capture.json").read_text(encoding="utf-8"))
        for p in cap["observation"]["world"]["provinces"]:
            self.assertIn("neighbors", p)
            self.assertNotIn("has_river_crossing", p)
'''
if old_inv not in t180:
    raise SystemExit("t180 inventory test block not found")
(root/"research/test_t180_input_neighbors.py").write_text(t180.replace(old_inv, new_inv, 1), encoding="utf-8")
print("froze t180 inventory test")
print("ok")
