"""Read-only: disassemble a function of the game exe (file on disk, no process).
Usage: disas.py RVA [LEN]"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
import capstone  # noqa: E402
from pe import PE  # noqa: E402

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"


def main(a):
    rva = int(a[0], 16)
    n = int(a[1], 16) if len(a) > 1 else 0x100
    pe = PE(EXE)
    data = pe.read_rva(rva, n) if hasattr(pe, "read_rva") else None
    if data is None:
        off = pe.rva_to_offset(rva)
        data = Path(EXE).read_bytes()[off:off + n]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    for ins in md.disasm(data, rva):
        print(f"{ins.address:#x}: {ins.mnemonic} {ins.op_str}")


if __name__ == "__main__":
    main(sys.argv[1:])
