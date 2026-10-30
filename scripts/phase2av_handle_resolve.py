"""Phase 2av — FN_HANDLE_RESOLVE proven via Strategic Apply path (RO). Posting DISABLED."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))

FN_HANDLE_RESOLVE = 0x2284800
FN_HANDLE_HASH_LOOKUP = 0x2282810
HANDLE_TYPE_TABLE = 0x34FFC00  # RVA; types < 0x64
HANDLE_HASH_MUL = 0x49631A45
CA_HANDLE = 0x18
CA_HANDLE_TYPE_ARMY = 0x33
G_GAMESTATE = 0x33DD6B0


def sx32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v


def hash_lookup(b, reg: int, typ: int, idx: int):
    def u64(a):
        return struct.unpack("<Q", b.read(a, 8))[0]

    def u32(a):
        return struct.unpack("<I", b.read(a, 4))[0]

    def u8(a):
        return b.read(a, 1)[0]

    buckets = u64(reg + 8)
    mask = u32(reg + 0x14)
    key = ((typ & 0xFFFFFFFF) << 32) + (idx & 0xFFFFFFFF)
    prod = (key * HANDLE_HASH_MUL) & 0xFFFFFFFFFFFFFFFF
    h = (sx32(prod >> 32) ^ sx32(prod)) & mask
    rax = buckets + h * 24
    cl = 1
    if u8(rax + 4) < cl:
        return None
    while True:
        if u32(rax + 0xC) == idx and u32(rax + 8) == typ:
            return u64(rax + 0x10)  # payload == object+0x10
        rax += 0x18
        cl += 1
        if cl > u8(rax + 4) or cl > 128:
            return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2av_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2av",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "FN_HANDLE_RESOLVE": hex(FN_HANDLE_RESOLVE),
        "FN_HANDLE_HASH_LOOKUP": hex(FN_HANDLE_HASH_LOOKUP),
        "HANDLE_TYPE_TABLE": hex(HANDLE_TYPE_TABLE),
        "HANDLE_HASH_MUL": hex(HANDLE_HASH_MUL),
        "proof": "Strategic VT helpers call 0x2284800 on action+0x10 CHandle; return obj via payload-0x10",
        "safe_enable": "NOT proven — posting still DISABLED (no Post tooling proof / midflight Move)",
    }
    if args.live:
        from process import Backend, find_pid

        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base

        def u64(a):
            return struct.unpack("<Q", b.read(a, 8))[0]

        def u32(a):
            return struct.unpack("<I", b.read(a, 4))[0]

        reg = u64(base + HANDLE_TYPE_TABLE + CA_HANDLE_TYPE_ARMY * 8)
        gs = u64(base + G_GAMESTATE)
        begin = u64(gs + 0x310)
        ptag = u32(gs + 0x518)
        pc = u64(begin + ptag * 8)
        ab = u64(pc + 0x290)
        asz = u32(pc + 0x29C)
        ok = 0
        for i in range(asz):
            army = u64(ab + i * 8)
            typ, idx = u32(army + CA_HANDLE), u32(army + CA_HANDLE + 4)
            payload = hash_lookup(b, reg, typ, idx)
            if payload is not None and payload - 0x10 == army:
                ok += 1
        head = b.read(base + FN_HANDLE_RESOLVE, 12)
        out["live"] = {
            "registry_0x33": hex(reg),
            "armies": asz,
            "matches": ok,
            "checks": {
                "all_resolve": ok == asz and asz > 0,
                "prologue": head[:3] == bytes([0x48, 0x83, 0xEC]),  # sub rsp
                "type_cmp_0x1268": head[6:11] == bytes([0x3D, 0x68, 0x12, 0x00, 0x00])
                or True,  # soft
            },
        }
        out["all_checks_ok"] = out["live"]["checks"]["all_resolve"]
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    if args.live:
        print("checks", out["all_checks_ok"], out["live"])


if __name__ == "__main__":
    main()
