"""Read-only: find code that references an RVA (RIP-relative lea/mov) or calls it.
Usage: xref.py RVA [RVA...]"""
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from pe import PE  # noqa: E402

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"


def sections(pe):
    for s in getattr(pe, "sections", []):
        yield s


def main(args):
    targets = {int(a, 16) for a in args}
    raw = Path(EXE).read_bytes()
    pe = PE(EXE)
    text = None
    for s in pe.sections:
        name = s["name"] if isinstance(s, dict) else getattr(s, "name", "")
        if str(name).strip("\x00").startswith(".text"):
            text = s
            break
    get = (lambda k: text[k]) if isinstance(text, dict) else (lambda k: getattr(text, k))
    va, off, size = get("virtual_address"), get("raw_ptr"), get("raw_size")
    blob = raw[off:off + size]
    hits = []
    # lea/mov r64, [rip+disp32]: REX(48/4C) 8D/8B modrm(00 reg 101)
    for m in re.finditer(rb"[\x48\x4c][\x8d\x8b][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]", blob):
        i = m.start()
        disp = struct.unpack_from("<i", blob, i + 3)[0]
        tgt = va + i + 7 + disp
        if tgt in targets:
            hits.append((va + i, "lea/mov", tgt))
    for m in re.finditer(rb"\xe8", blob):
        i = m.start()
        disp = struct.unpack_from("<i", blob, i + 1)[0] if i + 5 <= len(blob) else 0
        tgt = va + i + 5 + disp
        if tgt in targets:
            hits.append((va + i, "call", tgt))
    for h in hits:
        print(f"{h[0]:#x} {h[1]} -> {h[2]:#x}")


if __name__ == "__main__":
    main(sys.argv[1:])

