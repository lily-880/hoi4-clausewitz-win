"""Phase 2ba: RO pipeline status snapshot + cmd_layout summary. Posting DISABLED."""
from __future__ import annotations
import json, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from process import Backend, find_pid  # noqa: E402
from cmd_layout import summarize  # noqa: E402
from post_abi import describe  # noqa: E402

OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
OUT = ROOT / "reports" / "phase2ba_pipeline_status.json"


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def main():
    b = Backend(find_pid("hoi4.exe"))
    base = int(b.image_base)
    idler = u64(b, base + OV["G_IDLER"])
    app = u64(b, idler + 0x530)
    session = u64(b, app + 0x380)
    server = u64(b, session + 0x40)
    g_session = u64(b, base + OV.get("G_SESSION", 0x34FFBE8))
    report = {
        "phase": "2ba",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "pid": b.pid,
        "base": hex(base),
        "g_session_matches": g_session == session,
        "session": hex(session),
        "server": hex(server),
        "server_vt_rva": hex(u64(b, server) - base),
        "session_state": u32(b, session + 0x30),
        "drain_counter": u32(b, session + 0x60),
        "exec_counter": u32(b, session + 0x6C8),
        "executing_flag": u32(b, session + 0x6CC),
        "stage_count": u32(b, session + 0x54),
        "pending_count": u32(b, server + 0x68),
        "execlist_count": u32(b, server + 0x50),
        "ring_count": u64(b, server + 0xC8),
        "post_ids": u32(b, server + 0xD0),
        "post_abi": describe(),
        "cmd_layout": summarize(),
    }
    # player armies quick
    gs = u64(b, base + OV["G_GAMESTATE"])
    tag = u32(b, gs + OV["GS_PLAYER_TAG"])
    countries = u64(b, gs + OV["GS_COUNTRIES_BEGIN"])
    country = u64(b, countries + tag * 8)
    armies_begin = u64(b, country + OV["CO_ARMIES"])
    armies_n = u32(b, country + OV["CO_ARMIES"] + 0xC)
    report["player_tag"] = tag
    report["armies_count"] = armies_n
    sample = []
    for i in range(min(armies_n, 3)):
        army = u64(b, armies_begin + i * 8)
        h_ty = u32(b, army + OV["CA_HANDLE"])
        h_ix = u32(b, army + OV["CA_HANDLE"] + 4)
        prov = u32(b, army + OV["CA_PROVINCE_ID"])
        sample.append({"army": hex(army), "handle": [h_ty, h_ix], "province_id": prov})
    report["army_sample"] = sample
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k not in ("cmd_layout", "post_abi")}, indent=2))
    print("wrote", OUT)
    b.close()


if __name__ == "__main__":
    main()
