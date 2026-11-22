"""Three bounded offline checks of t255 selected header and pointer matcher.
Synthetic matcher vectors are NOT live positive/negative ownership controls.
No process, game, production-module imports, or external services.
"""
import base64
import json
from pathlib import Path
import struct
import unittest


def decode_header(raw):
    if len(raw) != 24:
        raise ValueError("header24 required")
    data, capacity, size, alloc = struct.unpack("<QiiQ", raw)
    if not 0 <= size <= capacity <= 4096:
        raise ValueError("array bounds")
    if size and not 65536 <= data < 0x800000000000:
        raise ValueError("data bounds")
    udata, ucapacity, usize = struct.unpack("<QII", raw[:16])
    if (data, capacity, size) != (udata, ucapacity, usize):
        raise ValueError("signed/unsigned mismatch")
    return data, capacity, size, alloc


def exact_indices(raw, target):
    if len(raw) % 8:
        raise ValueError("pointer stride")
    return [i for i, (p,) in enumerate(struct.iter_unpack("<Q", raw)) if p == target]


class SelectedEvidenceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = json.loads(Path(__file__).with_name("t255_candidate_army_membership.json").read_text())

    def test_actual_header_both_interpretations(self):
        a = self.e["candidate_array"]
        data, capacity, size, alloc = decode_header(base64.b64decode(a["header24_base64"]))
        self.assertEqual((data, capacity, size, alloc),
                         (int(a["data"], 16), 63, 49, int(a["alloc_opaque"], 16)))
        self.assertEqual(size * 8, a["pointer_bytes_read"])
        self.assertFalse(a["exact_pointer_present"])
        self.assertFalse(a["independent_1_19_5_native_meaning_certificate"])

    def test_synthetic_size_capacity_rejected(self):
        a = self.e["candidate_array"]
        bad = struct.pack("<QiiQ", int(a["data"], 16), 63, 64, 0)
        with self.assertRaises(ValueError):
            decode_header(bad)

    def test_synthetic_exact_pointer_not_nearby(self):
        target = int(self.e["witness"]["pointer"], 16)
        fake = struct.pack("<QQQ", target + 8, target, target + 16)
        self.assertEqual(exact_indices(fake, target), [1])
        self.assertEqual(exact_indices(fake, target + 1), [])


if __name__ == "__main__":
    unittest.main()
