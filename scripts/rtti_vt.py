"""Read-only: find the vtable(s) of a class by its MSVC RTTI name in the game exe.
Usage: rtti_vt.py .?AVCOrderEditRootCommand@@ [...]
Prints vtable RVA and its first 12 slots."""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from pe import PE  # noqa: E402

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"


def main(names):
    raw = Path(EXE).read_bytes()
    pe = PE(EXE)
    secs = pe.sections

    def off2rva(off):
        for s in secs:
            if s.raw_ptr <= off < s.raw_ptr + s.raw_size:
                return s.virtual_address + off - s.raw_ptr
        return None

    def rva2off(rva):
        for s in secs:
            if s.virtual_address <= rva < s.virtual_address + max(s.virtual_size, s.raw_size):
                return s.raw_ptr + rva - s.virtual_address
        return None
    for name in names:
        i = raw.find(name.encode() + b"\x00")
        if i < 0:
            print(name, "not found")
            continue
        td_rva = off2rva(i - 0x10)  # TypeDescriptor: vftable ptr, spare, name
        # CompleteObjectLocator (x64): sig=1, offset, cdOffset, pTypeDescriptor(rva), pClassHierarchy(rva), pSelf(rva)
        pat = struct.pack("<I", td_rva)
        start = 0
        while True:
            j = raw.find(pat, start)
            if j < 0:
                break
            start = j + 1
            col = j - 12
            if col < 0:
                continue
            sig, off, cd = struct.unpack_from("<III", raw, col)
            selfrva = struct.unpack_from("<I", raw, col + 20)[0]
            col_rva = off2rva(col)
            if sig != 1 or selfrva != col_rva:
                continue
            # vtable[-1] = absolute address of COL
            col_va = pe.image_base + col_rva if hasattr(pe, "image_base") else 0x140000000 + col_rva
            k = raw.find(struct.pack("<Q", col_va))
            while k >= 0:
                vt_rva = off2rva(k + 8)
                slots = [struct.unpack_from("<Q", raw, k + 8 + 8 * n)[0] - (col_va - col_rva) for n in range(12)]
                print(name, "offset", off, "vtable", hex(vt_rva), [hex(x) for x in slots])
                k = raw.find(struct.pack("<Q", col_va), k + 1)


if __name__ == "__main__":
    main(sys.argv[1:])
