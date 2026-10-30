"""Phase 2bl: RO dump sticky CStartGameCommand as live CCommand equivalent; stage/pending empty check.
Posting DISABLED. Pause/1x only.
"""
from __future__ import annotations
import json, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from mem import Proc, find_pid
import post_abi, cmd_layout

OUT = ROOT / "reports" / "phase2bl_sticky_equivalent.json"


def u64(p, a):
    return struct.unpack("<Q", p.read(a, 8))[0]


def u32(p, a):
    return struct.unpack("<I", p.read(a, 4))[0]


def main():
    pid = find_pid("hoi4.exe")
    p = Proc(pid)
    base = p.base
    sess = u64(p, base + post_abi.G_SESSION)
    server = u64(p, sess + post_abi.CSession_SERVER)
    sticky = u64(p, sess + 0xF8)
    drain = u32(p, sess + post_abi.CSession_DRAIN_COUNTER)
    exec_c = u32(p, sess + post_abi.CSession_EXEC_COUNTER)
    seq = u32(p, server + 0xD0)
    pending_h = u64(p, server + post_abi.CDummyServer_PENDING)
    pending_t = u64(p, server + post_abi.CDummyServer_PENDING + 8)
    pending_c = u32(p, server + post_abi.CDummyServer_PENDING + 0x10)
    execl_h = u64(p, server + post_abi.CDummyServer_EXECLIST)
    execl_c = u32(p, server + post_abi.CDummyServer_EXECLIST + 0x10)
    ring_blob = p.read(server + post_abi.CDummyServer_RING, 0x40)
    vt_server = u64(p, server) - base

    sticky_info = None
    if sticky:
        blob = p.read(sticky, 0x80)
        vt = struct.unpack_from("<Q", blob, 0)[0]
        sticky_info = {
            "addr": hex(sticky),
            "vt_rva": hex(vt - base),
            "expect_CStartGameCommand": "0x2a5f448",
            "match": (vt - base) == 0x2A5F448,
            "hex_0x60": blob[:0x60].hex(),
            "fields_u64": [hex(struct.unpack_from("<Q", blob, i)[0]) for i in range(0, 0x60, 8)],
        }

    stage = u64(p, sess + post_abi.CSession_STAGE_ARRAY)
    scount = u32(p, sess + post_abi.CSession_STAGE_COUNT)
    stage_hits = []
    want = {cmd_layout.MOVE["vt"], cmd_layout.STRATEGIC["vt"], 0x2A5F448, CANCEL_VT := 0x2A2C9B8}
    if stage and 0 < scount < 64:
        for i in range(scount):
            ptr = u64(p, stage + i * 8)
            if not ptr:
                continue
            try:
                vt = u64(p, ptr) - base
            except Exception:
                continue
            if vt in want:
                stage_hits.append({"i": i, "ptr": hex(ptr), "vt": hex(vt)})

    out = {
        "phase": "2bl",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "pid": pid,
        "base": hex(base),
        "sess": hex(sess),
        "server": hex(server),
        "server_vt_rva": hex(vt_server),
        "drain": drain,
        "exec": exec_c,
        "seq": seq,
        "pending": {
            "head": hex(pending_h) if pending_h else None,
            "tail": hex(pending_t) if pending_t else None,
            "count": pending_c,
        },
        "execlist": {"head": hex(execl_h) if execl_h else None, "count": execl_c},
        "ring_hex": ring_blob.hex(),
        "sticky_startgame": sticky_info,
        "stage_count": scount,
        "stage_hits": stage_hits,
        "cmd_layout_move_vt": hex(cmd_layout.MOVE["vt"]),
        "cmd_layout_strategic_vt": hex(cmd_layout.STRATEGIC["vt"]),
        "post_abi": post_abi.describe(),
        "allow_post": False,
        "midflight_move": "STUBBED",
        "midflight_note": (
            "SP frees Move inside tick; pause heap empty (2bd). "
            "DX11 ignores SendInput/PostMessage/mouse_event/UI click for gameplay "
            "(seq stuck 15 across 2be-2bk). Sticky CStartGameCommand is live CCommand equivalent sample. "
            "Needs real user right-click or hardware input for midflight Move."
        ),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
