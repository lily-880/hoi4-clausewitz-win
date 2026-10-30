"""Minimal PE64 reader for static inspection of hoi4.exe (no pefile dependency)."""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Section:
    name: str
    virtual_address: int
    virtual_size: int
    raw_ptr: int
    raw_size: int
    characteristics: int


class PE:
    def __init__(self, path: str):
        self.path = path
        with open(path, "rb") as f:
            self.data = f.read()
        if self.data[:2] != b"MZ":
            raise ValueError("not a PE (missing MZ)")
        e_lfanew = struct.unpack_from("<I", self.data, 0x3C)[0]
        if self.data[e_lfanew : e_lfanew + 4] != b"PE\0\0":
            raise ValueError("not a PE (missing PE signature)")
        coff = e_lfanew + 4
        machine, nsec, _, _, _, opt_size, chars = struct.unpack_from("<HHIIIHH", self.data, coff)
        self.machine = machine
        self.characteristics = chars
        opt = coff + 20
        magic = struct.unpack_from("<H", self.data, opt)[0]
        if magic != 0x20B:
            raise ValueError("expected PE32+ (0x20B), got %#x" % magic)
        self.image_base = struct.unpack_from("<Q", self.data, opt + 24)[0]
        self.size_of_image = struct.unpack_from("<I", self.data, opt + 56)[0]
        self.size_of_headers = struct.unpack_from("<I", self.data, opt + 60)[0]
        self.entry_rva = struct.unpack_from("<I", self.data, opt + 16)[0]
        sec_off = opt + opt_size
        self.sections: List[Section] = []
        for i in range(nsec):
            o = sec_off + i * 40
            name = self.data[o : o + 8].split(b"\0", 1)[0].decode("ascii", "replace")
            vsize, va, rsize, rptr, _, _, _, chars = struct.unpack_from("<IIIIIIHH", self.data, o + 8)
            # actually layout: Name[8], VirtualSize, VirtualAddress, SizeOfRawData, PointerToRawData,
            # PointerToRelocations, PointerToLinenumbers, NumberOfRelocations, NumberOfLinenumbers, Characteristics
            vsize, va, rsize, rptr = struct.unpack_from("<IIII", self.data, o + 8)
            chars = struct.unpack_from("<I", self.data, o + 36)[0]
            self.sections.append(
                Section(name, va, vsize, rptr, rsize, chars)
            )

    def rva_to_off(self, rva: int) -> Optional[int]:
        for s in self.sections:
            if s.virtual_address <= rva < s.virtual_address + max(s.virtual_size, s.raw_size):
                return s.raw_ptr + (rva - s.virtual_address)
        if rva < self.size_of_headers:
            return rva
        return None

    def read_rva(self, rva: int, n: int) -> Optional[bytes]:
        off = self.rva_to_off(rva)
        if off is None:
            return None
        return self.data[off : off + n]

    def summary(self) -> dict:
        return {
            "path": self.path,
            "size": len(self.data),
            "image_base": self.image_base,
            "size_of_image": self.size_of_image,
            "entry_rva": self.entry_rva,
            "sections": [
                {
                    "name": s.name,
                    "va": s.virtual_address,
                    "vsize": s.virtual_size,
                    "raw_ptr": s.raw_ptr,
                    "raw_size": s.raw_size,
                }
                for s in self.sections
            ],
        }
