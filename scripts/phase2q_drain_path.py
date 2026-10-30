"""Phase 2q: RO document CDummyServer drain/clear vs Post sink. Never post."""
from __future__ import annotations
import json, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "calling"))
import config
from pe import PE
from msvc_rtti import exact_type

def main():
    pe = PE(config.binary_path(required=True))
    vt = exact_type(pe, "CDummyServer")["vtables"][0]["vtable_rva"]
    raw = pe.read_rva(vt, 0x50)
    slots = {off: hex(struct.unpack_from("<Q", raw, off)[0] - pe.image_base)
             for off in (0x28, 0x30, 0x48)}
    out = {"CDummyServer_vtable": hex(vt), "slots": slots,
           "expected": {"0x28": "0x23f5cd0", "0x30": "0x23f64e0", "0x48": "0x23f5ad0"},
           "command_queue": "DISABLED"}
    Path("research/re-dumps/phase2q_drain_path.json").write_text(json.dumps(out, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
