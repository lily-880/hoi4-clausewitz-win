"""Typed live process memory access (platform-independent above Backend)."""
from __future__ import annotations

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from process import Backend, find_pid  # noqa: E402,F401


class Proc:
    """Typed memory access to a HOI4 process."""

    def __init__(self, pid=None, exe_name=None):
        import config

        self.be = Backend(pid, exe_name or config.EXE_NAME)
        self.pid = self.be.pid
        self.base = self.be.image_base
        self.image_size = getattr(self.be, "image_size", 0)
        self.image_path = getattr(self.be, "image_path", "")
        self.maps = self.be.regions()

    def va(self, file_rva: int) -> int:
        """RVA / ELF file vaddr-style offset -> runtime address (image_base + rva)."""
        return self.base + file_rva

    def read(self, addr, size):
        return self.be.read(addr, size)

    def write(self, addr, data):
        return self.be.write(addr, data)

    def try_read(self, addr, size):
        try:
            return self.read(addr, size)
        except OSError:
            return None

    def u8(self, a):
        return self.read(a, 1)[0]

    def u16(self, a):
        return struct.unpack("<H", self.read(a, 2))[0]

    def u32(self, a):
        return struct.unpack("<I", self.read(a, 4))[0]

    def i32(self, a):
        return struct.unpack("<i", self.read(a, 4))[0]

    def u64(self, a):
        return struct.unpack("<Q", self.read(a, 8))[0]

    def i64(self, a):
        return struct.unpack("<q", self.read(a, 8))[0]

    def f32(self, a):
        return struct.unpack("<f", self.read(a, 4))[0]

    def f64(self, a):
        return struct.unpack("<d", self.read(a, 8))[0]

    def ptr(self, a):
        v = self.try_read(a, 8)
        return struct.unpack("<Q", v)[0] if v and len(v) == 8 else None

    def cstr(self, addr, maxlen=256):
        b = self.try_read(addr, maxlen)
        if not b:
            return None
        i = b.find(b"\0")
        return b[: i if i >= 0 else len(b)].decode("utf-8", "replace")

    def msvc_string(self, addr):
        """MSVC std::string (x64): { union { char* ptr; char buf[16]; }; size_t size; size_t capacity; }
        If capacity <= 15, SSO uses buf; else ptr is heap.
        Layout commonly: 16-byte buffer/pointer union, size @+16, capacity @+24.
        """
        d = self.try_read(addr, 32)
        if not d or len(d) < 32:
            return None
        size = struct.unpack_from("<Q", d, 16)[0]
        cap = struct.unpack_from("<Q", d, 24)[0]
        if size > 0x10000:
            return None
        if cap <= 15:
            return d[0:size].decode("utf-8", "replace")
        ptr = struct.unpack_from("<Q", d, 0)[0]
        b = self.try_read(ptr, size)
        return b.decode("utf-8", "replace") if b else None

    # Alias: upstream uses libstdc++ SSO; Windows uses MSVC. Prefer msvc_string.
    def stdstring(self, addr):
        return self.msvc_string(addr)

    def regions(self, writable=True, anon_only=False, min_size=0):
        out = []
        for m in self.maps:
            if "r" not in m["perms"]:
                continue
            if writable and "w" not in m["perms"]:
                continue
            if anon_only and m.get("path"):
                continue
            if m["end"] - m["start"] < min_size:
                continue
            out.append(m)
        return out

    def scan_value(self, needle: bytes, regions=None, limit=None, align=8):
        hits = []
        regions = regions if regions is not None else self.regions()
        CH = 8 << 20
        for m in regions:
            a = m["start"]
            while a < m["end"]:
                n = min(CH, m["end"] - a)
                d = self.try_read(a, n)
                if d:
                    i = 0
                    while True:
                        i = d.find(needle, i)
                        if i < 0:
                            break
                        addr = a + i
                        if align == 1 or addr % align == 0:
                            hits.append(addr)
                            if limit and len(hits) >= limit:
                                return hits
                        i += 1
                a += n
        return hits

    def scan_ptr(self, value, **kw):
        return self.scan_value(struct.pack("<Q", value), **kw)

    def close(self):
        self.be.close()


if __name__ == "__main__":
    p = Proc()
    print("pid  =", p.pid)
    print("base =", hex(p.base))
    print("size =", hex(p.image_size))
    print("path =", p.image_path)
    print("regions =", len(p.maps))
