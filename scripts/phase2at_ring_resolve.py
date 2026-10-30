"""Phase 2at — DummyServer ring embed confirmation + handle-resolve candidates (RO).

Posting DISABLED. Game speed: pause/1x only.
"""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))

G_POST_LISTENERS = 0x3667BE8
G_POST_LISTENERS_COUNT = 0x3667BF4
FN_POST_SINK_DUMMY = 0x23F5CD0
FN_POST_DRAIN_DUMMY = 0x23F64E0
FN_SESSION_POST_GATE = 0x22C41E0
RING_EMBED = 0xA0  # add rbx, 0xa0 in sink before lock
# Ring fields relative to DummyServer+0xa0 (from sink disasm)
RING_LOCK = 0x0
RING_GROW_OBJ = 0x8  # lea rcx, [rbx+8]; call grow
RING_BUCKETS = 0x10
RING_CAPACITY = 0x18
RING_CURSOR = 0x20
RING_SEQ = 0x28  # inc after enqueue store

HYP_ORDER_CHECK = 0x748390  # not resolve — permission/check using handle index
HYP_GS_UNIT_THUNK = 0xC5A9E0  # GS virtual lookup by id; resolve candidate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2at_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2at",
        "posting": "DISABLED",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "ring": {
            "proof": "sink 0x23f5cd0 does add rbx,0xa0 then lock cmpxchg dword [rbx]",
            "DummyServer_RING_EMBED": hex(RING_EMBED),
            "fields_rel_embed": {
                "lock_dword": hex(RING_LOCK),
                "grow_obj": hex(RING_GROW_OBJ),
                "buckets": hex(RING_BUCKETS),
                "capacity": hex(RING_CAPACITY),
                "cursor": hex(RING_CURSOR),
                "seq_count": hex(RING_SEQ),
            },
            "note": "capacity/seq may use packed/tagged qwords; interpret via disasm not raw dumps alone",
        },
        "FN_CMD_QUEUE_POST": hex(FN_SESSION_POST_GATE),
        "FN_CMD_QUEUE_POST_SINK_DUMMY": hex(FN_POST_SINK_DUMMY),
        "FN_CMD_QUEUE_POST_DRAIN_DUMMY": hex(FN_POST_DRAIN_DUMMY),
        "handle_resolve": {
            "FN_HANDLE_RESOLVE": None,
            "rejected": {"0x6e4800": "epilogue/tail — not an entry"},
            "HYP_ORDER_CHECK": {
                "rva": hex(HYP_ORDER_CHECK),
                "role": "permission/check using handle type@0 + index@+4; indexes side table — NOT object resolve",
            },
            "HYP_GS_UNIT_THUNK": {
                "rva": hex(HYP_GS_UNIT_THUNK),
                "role": "loads G_GAMESTATE, virtual-call lookup by edx id; string gamestate uninitialized",
                "status": "candidate_unproven",
            },
        },
        "CLAUSEWITZ_ALLOW_POST": "stubbed default False (even if env=1 until checklist closed)",
        "safe_enable": "NOT proven — posting DISABLED",
    }
    if args.live:
        from process import Backend, find_pid
        from config import allow_post, allow_write
        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base
        def u64(a): return struct.unpack("<Q", b.read(a, 8))[0]
        def u32(a): return struct.unpack("<I", b.read(a, 4))[0]
        cnt = u32(base + G_POST_LISTENERS_COUNT)
        ds = u64(base + G_POST_LISTENERS)
        ring = ds + RING_EMBED
        # Prove sink bytes contain add rbx,0xa0
        sink = b.read(base + FN_POST_SINK_DUMMY, 0x150)
        embed_ok = b"\x48\x81\xC3\xA0\x00\x00\x00" in sink  # add rbx, 0xa0
        out["live"] = {
            "listeners": cnt,
            "DummyServer": hex(ds),
            "ring_abs": hex(ring),
            "lock_dword": u32(ring + RING_LOCK),
            "buckets": hex(u64(ring + RING_BUCKETS)),
            "cursor": hex(u64(ring + RING_CURSOR)),
            "seq_raw": hex(u64(ring + RING_SEQ)),
            "sink_has_add_rbx_0xa0": embed_ok,
            "allow_write": allow_write(),
            "allow_post": allow_post(),
            "checks": {
                "listeners_1": cnt == 1,
                "ds_heap": ds > 0x10000,
                "embed_insn": embed_ok,
                "post_denied": allow_post() is False,
            },
        }
        out["all_checks_ok"] = all(out["live"]["checks"].values())
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    if args.live:
        print("checks", out["all_checks_ok"], out["live"]["checks"])


if __name__ == "__main__":
    main()
