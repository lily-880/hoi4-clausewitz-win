import sys, json, struct, unittest
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

if __name__ == "__main__":
    unittest.main()
