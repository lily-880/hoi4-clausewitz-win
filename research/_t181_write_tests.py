from pathlib import Path
test = r'''import sys, json, hashlib, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from input_loaded_fields import province_adjacencies, province_land_neighbors
from input_observation import ObservationError

# reuse t180 fake builder via import of its helper if needed — inline a minimal one
import struct
from input_loaded_fields import LoadedReader

def _build_mem(pid, records):
    province = 0x10000
    definition = 0x20000
    data = 0x30000
    store = {}
    def w(addr, blob):
        store[addr] = bytes(blob)
    w(province, b"\x00" * 8)
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
            self.samples = {}
        exact = LoadedReader.exact
        q = LoadedReader.q
        require = lambda self, a, name: None
    return R()

class Tests(unittest.TestCase):
    def test_12971a0_type_2_and_3_range_check(self):
        text = (ROOT / "research/_t181_clip_river_type_range_0x12971a0.txt").read_text(encoding="utf-8")
        self.assertIn("movzx eax, byte ptr [rdx + 0x10]", text)
        self.assertIn("sub al, 2", text)
        self.assertIn("cmp al, 1", text)
        self.assertIn("ja 0x1297bd1", text)
        ev = json.loads((ROOT / "research/t181_has_river_crossing_contract.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["shape"].split(";")[0].strip()[:6], "object")
        self.assertTrue(ev["not_a_province_bool"])
        self.assertEqual(len(ev["engine_predicate"]["family"]), 5)

    def test_token_registrar_is_not_reader(self):
        ev = json.loads((ROOT / "research/t181_has_river_crossing_contract.json").read_text(encoding="utf-8"))
        self.assertTrue(ev["token_clip_0x83760"]["not_a_reader"])
        x = json.loads((ROOT / "research/t181_token_slot_xrefs.json").read_text(encoding="utf-8"))
        funcs = {h["func"] for h in x["xrefs"]}
        self.assertIn("0x83760", funcs)

    def test_no_stored_cprovince_bool(self):
        ev = json.loads((ROOT / "research/t181_no_stored_province_bool.json").read_text(encoding="utf-8"))
        self.assertEqual(len(ev["has_river_province_ids"]), 8)
        self.assertEqual(len(ev["no_river_province_ids"]), 4)
        self.assertEqual(ev["cprovince_byte_or_scalar_discriminators"], [])

    def test_collector_object_marks_type_2_and_3_only(self):
        r = _build_mem(100, [(101, 0), (102, 1), (103, 2), (104, 3), (105, 4)])
        adj = province_adjacencies(r, 0x10000)
        self.assertEqual(adj["neighbors"], [101, 103, 104])
        self.assertEqual(adj["has_river_crossing"], {"101": False, "103": True, "104": True})
        self.assertNotIn("102", adj["has_river_crossing"])
        self.assertNotIn("105", adj["has_river_crossing"])
        ids, ev = province_land_neighbors(r, 0x10000)
        self.assertEqual(ids, [101, 103, 104])
        self.assertEqual(ev["river_crossings"], 2)

    def test_live_capture_emits_object_not_province_bool(self):
        path = ROOT / "research/t181_live_capture.json"
        self.assertTrue(path.exists(), "t181 live capture missing")
        cap = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(cap["complete_input"])
        self.assertTrue(cap["read_only"])
        provs = cap["observation"]["world"]["provinces"]
        self.assertEqual(len(provs), 12)
        true_total = 0
        for p in provs:
            self.assertIsInstance(p["has_river_crossing"], dict)
            self.assertNotIsInstance(p["has_river_crossing"], bool)
            keys = set(p["has_river_crossing"])
            self.assertEqual(keys, {str(n) for n in p["neighbors"]})
            for n in p["neighbors"]:
                self.assertIsInstance(p["has_river_crossing"][str(n)], bool)
            true_total += sum(1 for v in p["has_river_crossing"].values() if v is True)
        self.assertEqual(true_total, 16)
        live = json.loads((ROOT / "research/t180_landindex_and_edges.json").read_text(encoding="utf-8"))
        expect = {}
        for row in live["provinces"]:
            expect[row["province_id"]] = {str(e["nid"]): e["b10"] in (2, 3) for e in row["edges"] if e["b10"] in (0, 2, 3)}
        for p in provs:
            self.assertEqual(p["has_river_crossing"], expect[p["province_id"]])
        eq = cap["observation"]["world"]["shortages"]["equipment"]
        self.assertEqual(eq, [{"equipment_type": "train_equipment", "stockpile": 5}])
        self.assertNotIn("demanded", eq[0])
        self.assertNotIn("affected_unit_ids", eq[0])

    def test_inventory_promotes_has_river_crossing(self):
        inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
        raw = inv.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        recorded = json.loads((ROOT / "research/t181_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertEqual(digest, recorded["sha256"])
        text = raw.decode("utf-8")
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
        self.assertEqual(verified, 43)
        self.assertEqual(len(fields) - verified, 73)
        row = next(c for c in fields if c[0] == "world.provinces.has_river_crossing")
        self.assertEqual(row[1], "已验证")
        self.assertIn("邻接边", row[2])
        self.assertNotIn("省份是否", row[2])
        neigh = next(c for c in fields if c[0] == "world.provinces.neighbors")
        self.assertEqual(neigh[1], "已验证")

if __name__ == "__main__":
    unittest.main()
'''
Path("research/test_t181_input_has_river_crossing.py").write_text(test, encoding="utf-8")
import py_compile
for f in ["calling/input_loaded_fields.py","calling/input_capture_live.py","research/test_t181_input_has_river_crossing.py","research/test_t180_input_neighbors.py"]:
    py_compile.compile(f, doraise=True)
    print("compiled", f)
