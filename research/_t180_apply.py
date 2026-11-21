from pathlib import Path
import json

root = Path(".")

# ---- proof: neighbor reader ----
reader = {
  "build": "HOI4 1.19.5.0.7c6c",
  "pid": 26976,
  "read_only": True,
  "promoted": "world.provinces.neighbors",
  "not_promoted": ["world.provinces.has_river_crossing", "world.shortages.equipment.demanded", "deficit", "affected_unit_ids"],
  "array": {
    "object": "[CProvince+0xb8]",
    "data": "+0x70",
    "capacity": "+0x78",
    "size": "+0x7c",
    "stride": 48,
    "target_offset": 8,
    "type_offset": 16
  },
  "reader": {
    "func": "0xe90560",
    "clip": "research/_t180_clip_NeighborAdjs_size_0xe90560.txt",
    "data_load": "0xe90a44 mov rax, qword ptr [rdi + 0x70]",
    "target_load": "0xe90a48 mov edx, dword ptr [r12 + rax + 8]",
    "loop_stride": "0xe90e3c add r12, 0x30",
    "size_cmp": "0xe90e40 cmp eax, dword ptr [rdi + 0x7c]",
    "index_scale": "lea rbx, [rax+rax*2]; shl rbx, 4  (*48)",
    "note": "rdi is the CProvince+0xb8 object; only recorded E8 caller 0x1f6610"
  },
  "writer": {
    "func": "0x14a6540",
    "clip": "research/_t180_clip_0x14a6540.txt",
    "index_scale": "lea r10, [rax+rax*2]; add r10, r10; then [base + r10*8 + off] = index*48",
    "type_store": "0x14a6557 mov byte ptr [rax + r10*8 + 0x10], r8b",
    "other_stores": ["dword [..+0xc] = r9d", "qword [..+0x28] from [rsp+0x28]", "qword [..+0] from [rsp+0x30]"],
    "rcx": "the +0xb8 adjacency object (call site mov rcx, rdi / r15)",
    "r8b": "type byte from parser r12b"
  },
  "emission": {
    "field": "world.provinces.neighbors",
    "value": "neighbor province ids with type in {0, 2, 3} in engine array order",
    "excluded_types": {"1": "sea", "4": "impassable"},
    "scope": "currently observed own-unit provinces only; no world sweep",
    "not_emitted": "has_river_crossing: schema is bool or object; type 2/3 is per-edge and does not by itself fix the contract"
  }
}
(root/"research/t180_neighbor_reader.json").write_text(json.dumps(reader, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

# ---- proof: type enum ----
enum = {
  "parser": "0xab3660",
  "source": "adjacencies.csv type strings",
  "clip": "research/_t180_clip_0xab3660.txt",
  "writer_call": "0xab3e39 / 0xab3e9f call 0x14a6540 with movzx r8d, r12b",
  "types": {
    "0": {"name": "land", "how": "default xor r12b, r12b at 0xab3868, also bitmap fall-through"},
    "1": {"name": "sea", "how": "0xab38ea mov r12b, 1 after len-3 'sea' match"},
    "2": {"name": "river", "how": "0xab3888 sete r12b; 0xab388c add r12b, r12b"},
    "3": {"name": "river_large", "how": "0xab38ba mov r12b, 3 after len 0xb match"},
    "4": {"name": "impassable", "how": "0xab391a mov r12b, 4 after len 0xa match"}
  },
  "pathfinding_sea_index": {
    "func": "0xd55250",
    "clip": "research/_t180_clip_sea_province_pathfinding_0xd55250.txt",
    "table": "CMap+0x238 i32 per province id; -1 means sea",
    "assert": "Neighbour is a sea province..."
  },
  "live_own_12_provinces": {
    "proof": "research/t180_landindex_and_edges.json",
    "edges": 73,
    "type_hist": {"0": 57, "2": 16},
    "sea_or_impassable": 0,
    "land_index_minus1": 0,
    "internal_reciprocal": "22/22",
    "self_edges": 0,
    "note": "ETH sample is landlocked so types 1 and 4 are parser/writer proven, not live-sampled this scene"
  }
}
(root/"research/t180_adjacency_type_enum.json").write_text(json.dumps(enum, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print("wrote proofs")

# ---- patch input_loaded_fields.py ----
p = root/"calling/input_loaded_fields.py"
text = p.read_text(encoding="utf-8")
old_doc = "Named serializer/parser evidence: t165 proofs; further1.19.5 getter/dataflow\nproofs and corrections: research/t167,t168,t169_*semantic_proofs.json."
new_doc = "Named serializer/parser evidence: t165 proofs; further1.19.5 getter/dataflow\nproofs and corrections: research/t167,t168,t169_*semantic_proofs.json; adjacency reader t180."
if old_doc not in text:
    raise SystemExit("docstring anchor missing")
text = text.replace(old_doc, new_doc, 1)

fn = '''
# Adjacency types from adjacencies.csv parser 0xab3660, stored by 0x14a6540 at record+0x10.
# 0 land, 1 sea, 2 river, 3 river_large, 4 impassable.
# Reader 0xe90560 walks stride 0x30 and loads the neighbor id at record+8.
LAND_ADJACENCY_TYPES = frozenset({0, 2, 3})
KNOWN_ADJACENCY_TYPES = frozenset({0, 1, 2, 3, 4})
ADJACENCY_STRIDE = 0x30
MAX_ADJACENCIES = 255  # engine assert: NeighbourAdjs size > UCHAR_MAX


def province_land_neighbors(r, province):
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
anchor = "def victory_points(r,province):\n"
if anchor not in text:
    raise SystemExit("victory_points anchor missing")
if "def province_land_neighbors(" in text:
    raise SystemExit("function already present")
text = text.replace(anchor, fn + anchor, 1)
p.write_text(text, encoding="utf-8")
print("patched input_loaded_fields.py")

# ---- patch input_capture_live.py ----
cpath = root/"calling/input_capture_live.py"
ct = cpath.read_text(encoding="utf-8")
old_imp = "from input_loaded_fields import LoadedReader,battalion_width,own_leaders,infrastructure,country_tag,victory_points,unit_current_manpower,country_available_manpower,unit_hp,own_equipment_stockpile,resolve_building_templates,province_fort_level,own_reinforcement_requests,official_country_equipment_need_components"
new_imp = old_imp[:-len("own_reinforcement_requests,official_country_equipment_need_components")] + "province_land_neighbors,own_reinforcement_requests,official_country_equipment_need_components"
if old_imp not in ct:
    raise SystemExit("import anchor missing")
ct = ct.replace(old_imp, new_imp, 1)
old_ev = "        loaded=LoadedReader(p.read,cls);infrastructure_evidence=[]"
new_ev = "        loaded=LoadedReader(p.read,cls);infrastructure_evidence=[];neighbor_evidence=[]"
if old_ev not in ct:
    raise SystemExit("evidence init missing")
ct = ct.replace(old_ev, new_ev, 1)
old_block = """                province_cache[pp]={'province_id':pid,'terrain':terrain_name,'victory_points':victory_points(loaded,pp)}
                for field,type_name in [('fort_level','bunker'),('coastal_fort_level','coastal_bunker')]:"""
new_block = """                province_cache[pp]={'province_id':pid,'terrain':terrain_name,'victory_points':victory_points(loaded,pp)}
                neighbors,ne=province_land_neighbors(loaded,pp)
                neighbor_evidence.append(ne)
                province_cache[pp]['neighbors']=neighbors
                for field,type_name in [('fort_level','bunker'),('coastal_fort_level','coastal_bunker')]:"""
if old_block not in ct:
    raise SystemExit("province cache block missing")
ct = ct.replace(old_block, new_block, 1)
old_src = "                            'victory_points_source':'live CProvince+0x38 named victory_points; optional rename+0x40',"
new_src = old_src + "\n                            'neighbors_source':'live [CProvince+0xb8]+0x70 stride 48 target +8; types 0/2/3 only; 14a6540/ab3660',"
if old_src not in ct:
    raise SystemExit("victory_points_source missing")
ct = ct.replace(old_src, new_src, 1)
old_coll = "'infrastructure_collection':infrastructure_evidence,"
new_coll = "'infrastructure_collection':infrastructure_evidence,'neighbor_collection':neighbor_evidence,"
if old_coll not in ct:
    raise SystemExit("infrastructure_collection missing")
ct = ct.replace(old_coll, new_coll, 1)
cpath.write_text(ct, encoding="utf-8")
print("patched input_capture_live.py")

# ---- offsets ----
offp = root/"calling/tables/offsets_input_windows_1.19.5.json"
off = json.loads(offp.read_text(encoding="utf-8-sig"))
off["province_adjacency_reader_t180"] = {
    "location": "[CProvince+0xb8]+0x70 data, +0x78 cap, +0x7c size",
    "stride": 48,
    "target_offset": 8,
    "type_offset": 16,
    "types": {"0": "land", "1": "sea", "2": "river", "3": "river_large", "4": "impassable"},
    "reader": "0xe90560",
    "writer": "0x14a6540",
    "parser": "0xab3660 adjacencies.csv",
    "pathfinding_sea": "0xd55250 CMap+0x238 i32, -1=sea",
    "emitted": "world.provinces.neighbors = ids with type in {0,2,3} for currently observed own-unit provinces",
    "not_emitted": "has_river_crossing (bool vs per-edge contract unconfirmed); sea=1 and impassable=4 excluded",
    "promoted": True,
    "proofs": [
        "research/t180_neighbor_reader.json",
        "research/t180_adjacency_type_enum.json",
        "research/t180_landindex_and_edges.json"
    ]
}
offp.write_text(json.dumps(off, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("updated offsets")

# ---- tests (capture/inventory assertions filled after those exist; structure now, capture tests skip if missing then we rerun) ----
test = r'''import sys, json, struct, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from input_loaded_fields import LoadedReader, province_land_neighbors, LAND_ADJACENCY_TYPES
from input_observation import ObservationError

class FakeRead:
    def __init__(self, mem):
        self.mem = mem
    def __call__(self, address, size):
        return self.mem[address:address + size]

def _build_mem(pid, records):
    # records: list of (nid, typ)
    province = 0x10000
    definition = 0x20000
    data = 0x30000
    mem = {}
    def put(addr, b):
        mem[addr] = mem.get(addr, bytearray())
        # store sparsely by exact ranges later; use a flat dict of slices is hard.
        return addr
    # Use a sparse bytearray map via a dict of addr->bytes assembled on read
    store = {}
    def w(addr, blob):
        store[addr] = bytes(blob)
    w(province, b"\x00" * 8)  # vtable placeholder
    w(province + 0xa4, struct.pack("<I", pid))
    w(province + 0xb8, struct.pack("<Q", definition))
    n = len(records)
    w(definition + 0x70, struct.pack("<QII", data if n else 0, n, n))
    raw = bytearray(n * 48)
    for j, (nid, typ) in enumerate(records):
        struct.pack_into("<I", raw, j * 48 + 8, nid)
        raw[j * 48 + 0x10] = typ
    if n:
        w(data, bytes(raw))
    def read(addr, size):
        for base, blob in store.items():
            if base <= addr < base + len(blob) and addr + size <= base + len(blob):
                return blob[addr - base:addr - base + size]
        return b"\x00" * size
    class R:
        def __init__(self):
            self.read = read
            self.class_name = lambda a: ".?AVCProvince@@"
        exact = LoadedReader.exact
        q = LoadedReader.q
        i = LoadedReader.i
        require = lambda self, a, name: None
        samples = {}
    r = R()
    r.samples = {}
    return r

class Tests(unittest.TestCase):
    def test_e90560_stride_48_and_target_plus8(self):
        text = (ROOT / "research/_t180_clip_NeighborAdjs_size_0xe90560.txt").read_text(encoding="utf-8")
        self.assertIn("mov rax, qword ptr [rdi + 0x70]", text)
        self.assertIn("mov edx, dword ptr [r12 + rax + 8]", text)
        self.assertIn("add r12, 0x30", text)
        self.assertIn("cmp eax, dword ptr [rdi + 0x7c]", text)

    def test_14a6540_index_times_48_writes_type_at_plus10(self):
        text = (ROOT / "research/_t180_clip_0x14a6540.txt").read_text(encoding="utf-8")
        self.assertIn("lea r10, [rax + rax*2]", text)
        self.assertIn("add r10, r10", text)
        self.assertIn("mov byte ptr [rax + r10*8 + 0x10], r8b", text)

    def test_ab3660_csv_type_enum(self):
        text = (ROOT / "research/_t180_clip_0xab3660.txt").read_text(encoding="utf-8")
        self.assertIn("xor r12b, r12b", text)
        self.assertIn("sete r12b", text)
        self.assertIn("add r12b, r12b", text)
        self.assertIn("mov r12b, 3", text)
        self.assertIn("mov r12b, 1", text)
        self.assertIn("mov r12b, 4", text)
        self.assertIn("movzx r8d, r12b", text)
        self.assertIn("call 0x14a6540", text)
        ev = json.loads((ROOT / "research/t180_adjacency_type_enum.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["types"]["0"]["name"], "land")
        self.assertEqual(ev["types"]["1"]["name"], "sea")
        self.assertEqual(ev["types"]["2"]["name"], "river")
        self.assertEqual(ev["types"]["3"]["name"], "river_large")
        self.assertEqual(ev["types"]["4"]["name"], "impassable")

    def test_live_own_edges_types_and_reciprocity(self):
        ev = json.loads((ROOT / "research/t180_landindex_and_edges.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["edge_counts"]["total"], 73)
        self.assertEqual(ev["edge_counts"]["sea"], 0)
        hist = ev["hist_b10"]
        self.assertEqual({int(k): v for k, v in hist.items()}, {0: 57, 2: 16})
        rec = ev["own_land_reciprocal"]
        self.assertEqual(rec["internal"], rec["reciprocal"])
        self.assertEqual(rec["internal"], 22)
        for p in ev["provinces"]:
            for e in p["edges"]:
                self.assertIn(e["b10"], (0, 2))
                self.assertFalse(e["is_sea_by_landindex"])
                self.assertNotEqual(e["nid"], p["province_id"])

    def test_collector_keeps_land_river_excludes_sea_impassable(self):
        r = _build_mem(100, [(101, 0), (102, 1), (103, 2), (104, 3), (105, 4)])
        ids, ev = province_land_neighbors(r, 0x10000)
        self.assertEqual(ids, [101, 103, 104])
        self.assertEqual(ev["adjacency_count"], 5)
        self.assertEqual(ev["land_neighbors"], 3)
        self.assertEqual(LAND_ADJACENCY_TYPES, frozenset({0, 2, 3}))

    def test_collector_rejects_self_and_unknown_type(self):
        r = _build_mem(100, [(100, 0)])
        with self.assertRaises(ObservationError):
            province_land_neighbors(r, 0x10000)
        r2 = _build_mem(100, [(101, 9)])
        with self.assertRaises(ObservationError):
            province_land_neighbors(r2, 0x10000)

    def test_live_capture_emits_neighbors_not_river_or_demanded(self):
        path = ROOT / "research/t180_live_capture.json"
        self.assertTrue(path.exists(), "t180 live capture missing")
        cap = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(cap["complete_input"])
        self.assertTrue(cap["read_only"])
        provs = cap["observation"]["world"]["provinces"]
        self.assertEqual(len(provs), 12)
        total = 0
        for p in provs:
            self.assertIsInstance(p["neighbors"], list)
            self.assertTrue(all(type(x) is int for x in p["neighbors"]))
            self.assertNotIn(p["province_id"], p["neighbors"])
            self.assertEqual(len(p["neighbors"]), len(set(p["neighbors"])))
            self.assertNotIn("has_river_crossing", p)
            total += len(p["neighbors"])
        self.assertEqual(total, 73)
        live = json.loads((ROOT / "research/t180_landindex_and_edges.json").read_text(encoding="utf-8"))
        expect = {p["province_id"]: p["land_neighbors"] for p in live["provinces"]}
        for p in provs:
            self.assertEqual(p["neighbors"], expect[p["province_id"]])
        eq = cap["observation"]["world"]["shortages"]["equipment"]
        self.assertEqual(eq, [{"equipment_type": "train_equipment", "stockpile": 5}])
        self.assertNotIn("demanded", eq[0])
        self.assertNotIn("affected_unit_ids", eq[0])

    def test_inventory_promotes_only_neighbors(self):
        inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
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

if __name__ == "__main__":
    unittest.main()
'''
(root/"research/test_t180_input_neighbors.py").write_text(test, encoding="utf-8")
print("wrote tests")
print("ok")
