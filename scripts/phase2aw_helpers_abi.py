"""Phase 2aw — wire RO helpers + Post ABI notes; posting DISABLED."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))

G_GAMESTATE = 0x33DD6B0
FN_CMD_QUEUE_POST = 0x22C41E0
FN_CMD_QUEUE_POST_SINK_DUMMY = 0x23F5CD0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2aw_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2aw",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "helpers": ["calling/handle.py", "calling/province.py"],
        "post_abi_notes": {
            "entry": hex(FN_CMD_QUEUE_POST),
            "convention": "rcx=CSession*, rdx=CCommand*",
            "sink_sp": hex(FN_CMD_QUEUE_POST_SINK_DUMMY),
            "enable_requires": [
                "CLAUSEWITZ_ALLOW_POST=1 AND checklist closed (config.allow_post still hard-denies)",
                "midflight or constructed CCommand with valid vtable/type_id",
                "non-destructive proof (e.g. Chat) observing ring seq inc then drain",
            ],
            "status": "NOT calling Post — documentation only",
        },
        "safe_enable": "NOT proven",
    }
    if args.live:
        from process import Backend, find_pid
        from handle import resolve_handle, HANDLE_TYPE_ARMY
        from province import resolve_province
        from config import allow_post

        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base

        def u64(a):
            return struct.unpack("<Q", b.read(a, 8))[0]

        def u32(a):
            return struct.unpack("<I", b.read(a, 4))[0]

        gs = u64(base + G_GAMESTATE)
        begin = u64(gs + 0x310)
        ptag = u32(gs + 0x518)
        pc = u64(begin + ptag * 8)
        ab = u64(pc + 0x290)
        asz = u32(pc + 0x29C)
        roster = []
        ok_h = ok_p = 0
        for i in range(asz):
            army = u64(ab + i * 8)
            typ, idx = u32(army + 0x18), u32(army + 0x1C)
            pid = u32(army + 0x28)
            got_a = resolve_handle(b, typ, idx, base)
            got_p = resolve_province(b, pid, base, gs)
            prov_ptr = u64(army + 0x1F0)
            if got_a == army:
                ok_h += 1
            if got_p == prov_ptr:
                ok_p += 1
            if i < 5:
                roster.append(
                    {
                        "i": i,
                        "army": hex(army),
                        "handle": [typ, idx],
                        "province_id": pid,
                        "resolve_handle_ok": got_a == army,
                        "resolve_province_ok": got_p == prov_ptr,
                    }
                )
        out["live"] = {
            "armies": asz,
            "handle_ok": ok_h,
            "province_ok": ok_p,
            "allow_post": allow_post(),
            "roster_sample": roster,
            "checks": {
                "handles": ok_h == asz,
                "provinces": ok_p == asz,
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
