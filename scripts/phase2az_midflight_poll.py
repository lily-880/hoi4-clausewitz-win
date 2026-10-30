"""Phase 2az: RO mid-flight poll at pause/1x (never 5x). No Post/Write.

Optionally taps Space once to unpause if session looks paused (speed unknown).
Polls DummyServer pending/stage for command vtables for a few seconds.
"""
from __future__ import annotations
import json, struct, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from process import Backend, find_pid  # noqa: E402

OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
OUT = ROOT / "reports" / "phase2az_midflight.json"

VT = {
    0x2A2C790: "CMoveCommand",
    0x2A2C9B8: "CCancelMovement",
    0x2A2D818: "CStrategicRedeploymentCommand",
    0x29F3710: "CHourlyTickCommand",
    0x2A85468: "COrderExecuteCommand",
    0x2A27F28: "CChatCommand",
}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def rtti(b, base, obj):
    try:
        vt = u64(b, obj)
        col = u64(b, vt - 8)
        td = u64(b, col + 0x10)
        return b.read(td + 0x10, 80).split(b"\0", 1)[0].decode("latin1", "replace")
    except Exception:
        return None


def walk_list(b, base, head, limit=32):
    out = []
    seen = set()
    cur = head
    while cur and cur not in seen and len(out) < limit:
        seen.add(cur)
        try:
            vt = u64(b, cur)
            name = VT.get(vt - base)
            out.append({
                "obj": hex(cur),
                "vt_rva": hex(vt - base),
                "name": name,
                "rtti": rtti(b, base, cur),
            })
            # intrusive list: try +0x8 next (common) and +0x0 via known pending node
            nxt = u64(b, cur + 8)
            if nxt == cur:
                break
            cur = nxt
        except Exception as e:
            out.append({"obj": hex(cur), "error": str(e)})
            break
    return out


def main():
    do_space = "--space" in sys.argv
    b = Backend(find_pid("hoi4.exe"))
    base = int(b.image_base)
    idler = u64(b, base + OV["G_IDLER"])
    session = u64(b, u64(b, idler + 0x530) + 0x380)
    server = u64(b, session + 0x40)
    report = {
        "phase": "2az",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "space_tap": False,
        "samples": [],
    }
    if do_space:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # VK_SPACE = 0x20; keybd_event deprecated but fine for one tap
            user32.keybd_event(0x20, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(0x20, 0, 2, 0)
            report["space_tap"] = True
            time.sleep(0.3)
        except Exception as e:
            report["space_error"] = str(e)

    t_end = time.time() + 8.0
    while time.time() < t_end:
        pending_c = u32(b, server + 0x68)
        stage_c = u32(b, session + 0x54)
        exe_c = u32(b, server + 0x50)
        ring_c = u64(b, server + 0xC8)
        snap = {
            "t": round(time.time(), 3),
            "pending_count": pending_c,
            "execlist_count": exe_c,
            "stage_count": stage_c,
            "ring_count": ring_c,
            "drain_counter": u32(b, session + 0x60),
            "exec_counter": u32(b, session + 0x6C8),
        }
        if pending_c or stage_c or exe_c or ring_c:
            snap["pending"] = walk_list(b, base, u64(b, server + 0x58))
            # stage array at session+0x48
            try:
                arr = u64(b, session + 0x48)
                cmds = []
                for i in range(min(stage_c, 16)):
                    p = u64(b, arr + i * 8)
                    if not p:
                        continue
                    vt = u64(b, p)
                    cmds.append({
                        "obj": hex(p),
                        "vt_rva": hex(vt - base),
                        "name": VT.get(vt - base),
                        "rtti": rtti(b, base, p),
                    })
                snap["stage"] = cmds
            except Exception as e:
                snap["stage_error"] = str(e)
            report["samples"].append(snap)
        time.sleep(0.05)

    # final always-on snapshot
    report["final"] = {
        "pending_count": u32(b, server + 0x68),
        "execlist_count": u32(b, server + 0x50),
        "stage_count": u32(b, session + 0x54),
        "ring_count": u64(b, server + 0xC8),
        "drain_counter": u32(b, session + 0x60),
        "exec_counter": u32(b, session + 0x6C8),
        "session_state": u32(b, session + 0x30),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:6000])
    print("wrote", OUT)
    b.close()


if __name__ == "__main__":
    main()
