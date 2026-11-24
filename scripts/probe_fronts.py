"""Read-only: list the theatre's CFront objects (border fronts) and the arrays
inside them (element class names; CProvince ids resolved to controller tags)."""
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "calling"))
import live_trial as lt  # noqa: E402
import orbat  # noqa: E402


def main(verbose_id=None):
    s = lt.Session(check_sha=False)
    r = orbat.Reader(s)
    tags = {}

    def tag_of(pid):
        if pid not in tags:
            try:
                c = s.controller_of(pid)
                tags[pid] = s.tag(c) if c is not None else None
            except Exception:
                tags[pid] = "?"
        return tags[pid]

    tp = r.arr(s.country + 0x168, 64)[0]
    for fp in r.arr(tp + 0x50, 256):
        h = r.handle(fp)
        raw = s.p.read(fp, 0x300)
        rows = []
        for o in range(0x10, 0x300 - 16, 8):
            data, cap, size = struct.unpack_from("<QII", raw, o)
            if not (orbat._ptr(data) and 0 < size <= cap <= 5000):
                continue
            try:
                first = struct.unpack("<Q", s.p.read(data, 8))[0]
                c = r.cls(first) if orbat._ptr(first) else None
            except Exception:
                c = None
            info = ""
            if c == ".?AVCProvince@@":
                ptrs = struct.unpack("<" + "Q" * size, s.p.read(data, 8 * size))
                ids = [s.u32(x + 0xA4) for x in ptrs]
                info = dict(Counter(tag_of(i) for i in ids))
                if verbose_id == h[1]:
                    info = (info, ids)
            rows.append((hex(o), size, c, info))
        print("front", h, rows)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
