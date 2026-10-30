"""Phase 2am — token id→name table + corrected APPLY; posting DISABLED."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))

# CUnitMoveAction serialize tags (vt+0xc0 @ 0x12c3920) — names from G_TOKEN_ARRAY
MOVE_SERIALIZE_TAGS = {
    0x28A3: "unit",
    0x2840: "province",
    0x174: "path",
    0x29F1: "clear",
    0x2C84: "safe",
    0x3A98: "safe_until_very_end",
    0x38F1: "safe_with_nonsafe_fallback",
    0x2C85: "avoid",
    0x37BC: "move_priority",
    0x368F: "sticky",
}

# Proven this phase (corrected APPLY was misaligned mid-image at 0x12af450)
PHASE2AM = {
    "CUnitMoveAction_APPLY": 0xC4F450,  # wrapper; Execute@0x12c26e7 calls here
    "CUnitMoveAction_APPLY_INNER": 0xC4D700,
    "FN_TOKEN_WRITE": 0x2546BA0,
    "FN_TOKEN_NAME_GET": 0x1F8360,  # (writer, token) -> std::string*
    "FN_TOKEN_TO_STRING": 0x253EB90,  # (token) -> SSO string* in G_TOKEN_ARRAY
    "G_TOKEN_ARRAY": 0x368F5A0,  # ptr to SSO[32] entries
    "G_TOKEN_MAX": 0x368F574,  # i32 max token id
    "TOKEN_ENTRY_SIZE": 32,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument(
        "--out",
        default=os.path.join(ROOT, "research", "re-dumps", "phase2am_report.json"),
    )
    args = ap.parse_args()
    out = {
        "phase": "2am",
        "command_queue": "DISABLED",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "move_serialize_tags": {hex(k): v for k, v in MOVE_SERIALIZE_TAGS.items()},
        "offsets": {k: hex(v) if isinstance(v, int) else v for k, v in PHASE2AM.items()},
        "apply_note": (
            "2ak listed APPLY 0x12af450 — wrong (Capstone abs without base). "
            "Real wrapper RVA 0xc4f450; inner 0xc4d700. Args from Execute: "
            "rcx=unit*, rdx=&action+0x30 (path/provinces), r8=byte[action+0x50], "
            "r9=dword[action+0x58] (move_priority)."
        ),
        "safe_enable": "NOT proven — posting remains DISABLED",
    }
    if not args.live:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
        print("wrote", args.out, "(offline)")
        return

    from process import Backend, find_pid
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64

    ov = json.load(
        open(os.path.join(ROOT, "calling", "offsets_verified.json"), encoding="utf-8")
    )
    b = Backend(find_pid("hoi4.exe"))
    base = b.image_base
    md = Cs(CS_ARCH_X86, CS_MODE_64)

    def u64(a):
        return struct.unpack("<Q", b.read(a, 8))[0]

    def u32(a):
        return struct.unpack("<I", b.read(a, 4))[0]

    def disasm(rva, n=0x100, max_lines=40):
        lines = []
        for insn in md.disasm(b.read(base + rva, n), base + rva):
            lines.append(f"{hex(insn.address - base)}: {insn.mnemonic} {insn.op_str}")
            if insn.mnemonic == "ret":
                break
            if len(lines) >= max_lines:
                break
        return lines

    def token_name(tok, arr):
        e = arr + tok * 32
        size = u64(e + 16)
        cap = u64(e + 24)
        if size > 10_000_000:
            return None
        if cap > 15 or size > 15:
            ptr = u64(e)
            if ptr < 0x10000:
                return None
            raw = b.read(ptr, min(int(size), 120))
        else:
            raw = b.read(e, int(size) if size <= 15 else 15)
        return raw.split(b"\x00")[0].decode("latin1", "replace")

    # Verify APPLY call target from Execute
    raw = b.read(base + 0x12C26E7, 5)
    assert raw[0] == 0xE8
    rel = struct.unpack("<i", raw[1:5])[0]
    apply_rva = (0x12C26E7 + 5 + rel)
    out["execute_call_apply_rva"] = hex(apply_rva)
    out["apply_match"] = apply_rva == PHASE2AM["CUnitMoveAction_APPLY"]
    out["apply_disasm"] = disasm(PHASE2AM["CUnitMoveAction_APPLY"], 0x40, 20)
    out["apply_inner_disasm"] = disasm(PHASE2AM["CUnitMoveAction_APPLY_INNER"], 0x80, 35)

    arr = u64(base + PHASE2AM["G_TOKEN_ARRAY"])
    tmax = u32(base + PHASE2AM["G_TOKEN_MAX"])
    out["token_table"] = {
        "array_ptr": hex(arr),
        "max": tmax,
        "entry_size": 32,
    }
    resolved = {}
    for tid, expect in MOVE_SERIALIZE_TAGS.items():
        try:
            name = token_name(tid, arr)
        except Exception as e:
            name = f"ERR:{e}"
        resolved[hex(tid)] = {"expect": expect, "live": name, "ok": name == expect}
    out["tags_resolved_live"] = resolved
    out["all_tags_ok"] = all(v["ok"] for v in resolved.values())

    # token_write site from serialize
    raw = b.read(base + 0x12C3938, 5)
    if raw[0] == 0xE8:
        tw = 0x12C3938 + 5 + struct.unpack("<i", raw[1:5])[0]
        out["token_write_from_serialize"] = hex(tw)
        out["token_write_match"] = tw == PHASE2AM["FN_TOKEN_WRITE"]

    listeners = u64(base + 0x3667BE8)
    count = u32(base + 0x3667BF4)
    out["G_POST_LISTENERS"] = {
        "ptr": hex(listeners),
        "count": count,
        "slot0_vt": hex(u64(u64(listeners)) - base) if listeners and count else None,
    }

    idler = u64(base + ov["G_IDLER"])
    session = u64(u64(idler + 0x530) + 0x380)
    out["live"] = {
        "pid": b.pid,
        "base": hex(base),
        "tick": u32(session + 0x84),
        "drain": u32(session + 0x60),
        "exec": u32(session + 0x6C8),
        "state": u32(session + 0x8) if False else "see session+0x? state2 elsewhere",
        "flag_725": b.read(session + 0x725, 1)[0],
        "flag_3c": u32(session + 0x3C),
    }
    # session state at known offset — keep RO snapshot of counters only
    out["live"]["seq"] = u32(u64(session + 0x40) + 0xD0) if u64(session + 0x40) else None

    b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("apply", out["execute_call_apply_rva"], "match", out["apply_match"])
    print("tags_ok", out["all_tags_ok"])
    for k, v in resolved.items():
        print(f"  {k} expect={v['expect']} live={v['live']} ok={v['ok']}")
    print("listeners", out["G_POST_LISTENERS"])
    print("live", out["live"])


if __name__ == "__main__":
    main()
