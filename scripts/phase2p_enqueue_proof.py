"""Phase 2p: prove CDummyServer vt+0x28 enqueue (READ-ONLY). Never post/write."""
from __future__ import annotations
import json, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "calling"))
import config
from pe import PE
from msvc_rtti import exact_type
from mem import Proc, find_pid
from gamestate import _rtti_name_from_vtable
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

GATE = 0x22C41E0
SINK = 0x23F5CD0
G_LISTENERS = 0x3667BE8
G_COUNT = 0x3667BF4

def main():
    pe = PE(config.binary_path(required=True))
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    dummy = exact_type(pe, "CDummyServer")
    vt = dummy["vtables"][0]["vtable_rva"]
    slot28 = struct.unpack_from("<Q", pe.read_rva(vt, 0x30), 0x28)[0] - pe.image_base
    assert slot28 == SINK, (hex(slot28), hex(SINK))
    # confirm store insn present
    raw = pe.read_rva(SINK, 0x250)
    store = None
    for insn in md.disasm(raw, SINK):
        if insn.mnemonic == "mov" and "r13" in insn.op_str and "*8" in insn.op_str.replace(" ",""):
            store = insn.address
        if insn.mnemonic == "ret" and insn.address > SINK + 0x20:
            break
    p = Proc(find_pid(config.EXE_NAME))
    base = p.base
    cnt = struct.unpack("<I", p.read(base + G_COUNT, 4))[0]
    arr = struct.unpack("<Q", p.read(base + G_LISTENERS, 8))[0]
    listeners = []
    for i in range(min(cnt, 8)):
        lp = struct.unpack("<Q", p.read(arr + i * 8, 8))[0]
        vt_rva = struct.unpack("<Q", p.read(lp, 8))[0] - base
        listeners.append({"ptr": hex(lp), "rtti": _rtti_name_from_vtable(pe, vt_rva)})
    p.close()
    out = {
        "FN_CMD_QUEUE_POST": hex(GATE),
        "sink_dummy": hex(SINK),
        "store_insn": hex(store) if store else None,
        "live_listener_count": cnt,
        "listeners": listeners,
        "command_queue": "DISABLED",
        "policy": "FN RVA recorded; tooling must not call Post",
    }
    Path("research/re-dumps/phase2p_enqueue_proof.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
