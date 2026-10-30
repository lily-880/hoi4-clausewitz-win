"""Phase 2aa — durable early-gate catalog for known CCommand subclasses. RO."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))

KNOWN = {
    "CMoveCommand": 0x2A2C790,
    "CCancelMovementCommand": 0x2A2C9B8,
    "CChatCommand": 0x2A27F28,
    "COrderExecuteCommand": 0x2A85468,
    "CStartGameCommand": 0x2A5F448,
}
STUB_TRUE = 0x188D90
STUB_FALSE = 0x11D530


def stub_label(rva: int) -> str:
    if rva == STUB_TRUE:
        return "TRUE"
    if rva == STUB_FALSE:
        return "FALSE"
    return hex(rva)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2aa_early_gates.json"))
    args = ap.parse_args()
    out = {
        "phase": "2aa",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x — do not Post speed cmds",
        "stub_true": hex(STUB_TRUE),
        "stub_false": hex(STUB_FALSE),
        "known": {},
        "notes": [
            "vt+0x60 FALSE + session+0x725==0 => Post drops ('Dropped command:') unless r8b",
            "live session+0x725==1 bypasses vt+0x60 FALSE for army cmds",
            "vt+0x60 TRUE also gates session post-exec clone (StartGame sticky)",
            "Chat: vt+0x60 FALSE / vt+0x80 TRUE",
            "Speed cmds (Increase/Decrease/SetGameSpeed) exist — NEVER Post them",
        ],
        "posting": "DISABLED",
    }
    if args.live:
        from process import Backend, find_pid

        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base

        def u64(a):
            return struct.unpack("<Q", b.read(a, 8))[0]

        def rd(a, n):
            return b.read(a, n)

        for name, vt in KNOWN.items():
            g60 = u64(base + vt + 0x60) - base
            g80 = u64(base + vt + 0x80) - base
            out["known"][name] = {
                "vt": hex(vt),
                "IsValid": hex(u64(base + vt + 0x48) - base),
                "Execute": hex(u64(base + vt + 0x50) - base),
                "vt60": stub_label(g60),
                "vt80": stub_label(g80),
                "vt90": hex(u64(base + vt + 0x90) - base),
            }
        # also scan a fixed set of interesting extras by RTTI name search (narrow)
        extras = {
            "CIncreaseGameSpeedCommand": None,
            "CDecreaseGameSpeedCommand": None,
            "CSetGameSpeedCommand": None,
            "CHourlyTickCommand": None,
            "CSendPingCommand": None,
            "CReadyAfterHotJoinCommand": None,
        }
        # locate via known extras from prior scan if present in report; else skip
        # hardcode vts found in 2aa scratch scan
        extras_vt = {
            "CIncreaseGameSpeedCommand": 0x29F37C8,
            "CDecreaseGameSpeedCommand": 0x29F3880,
            "CSetGameSpeedCommand": 0x29F3938,
            "CHourlyTickCommand": 0x29F3710,
            "CSendPingCommand": 0x29E6C80,
            "CReadyAfterHotJoinCommand": 0x29E6EA8,
        }
        out["extras"] = {}
        for name, vt in extras_vt.items():
            g60 = u64(base + vt + 0x60) - base
            g80 = u64(base + vt + 0x80) - base
            col = u64(base + vt - 8) - base
            td = struct.unpack("<I", rd(base + col + 0x0C, 4))[0]
            rtti = rd(base + td + 0x10, 80).split(b"\x00")[0].decode("ascii", "replace")
            out["extras"][name] = {
                "vt": hex(vt),
                "rtti": rtti,
                "Execute": hex(u64(base + vt + 0x50) - base),
                "vt60": stub_label(g60),
                "vt80": stub_label(g80),
            }
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("2aa early-gate catalog; posting DISABLED; never 5x")


if __name__ == "__main__":
    main()
