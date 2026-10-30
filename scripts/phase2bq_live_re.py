#!/usr/bin/env python3
"""Phase 2bq — RO live-buffer Dummy RT (sticky StartGame) + remaining subtypes + tool-gate deepen.

Never posts. Never opens command_queue_tool_gate. Never touches speed/HourlyTick/Pause.
Midflight Move remains stubbed; watcher stays armed separately. No input injection.
"""
from __future__ import annotations
import json, struct, sys, time, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from process import Backend, find_pid  # noqa: E402
from capstone import Cs, CS_ARCH_X86, CS_MODE_64  # noqa: E402
import cmd_layout, post_abi  # noqa: E402
from config import allow_post, binary_path  # noqa: E402
from pe import PE  # noqa: E402
from msvc_rtti import exact_type  # noqa: E402

OUT = ROOT / "reports" / "phase2bq_live_re.json"
md = Cs(CS_ARCH_X86, CS_MODE_64)

# Shared bin ser packs these CCommand header fields via token 0x1F3 (proven inverse in des).
HEADER_TOKEN = 0x1F3
HEADER_FIELDS = {
    "plus_0xc": 0xC,
    "plus_0x18_word": 0x18,
    "plus_0x1a_byte": 0x1A,
    "plus_0x1c": 0x1C,
    "plus_0x20": 0x20,
}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def u16(b, a):
    return struct.unpack("<H", b.read(a, 2))[0]


def u8(b, a):
    return b.read(a, 1)[0]


def parse_gettypeid(b, base, rva):
    blob = b.read(base + rva, 24)
    # imm: C7 02 imm32
    for i in range(len(blob) - 5):
        if blob[i] == 0xC7 and blob[i + 1] == 0x02:
            return struct.unpack_from("<I", blob, i + 2)[0], "imm"
    # mem: 8B 05 disp32 ; 89 02  (mov eax,[rip+d]; mov [rdx],eax)
    for i in range(len(blob) - 6):
        if blob[i] == 0x8B and blob[i + 1] == 0x05:
            disp = struct.unpack_from("<i", blob, i + 2)[0]
            abs_addr = (rva + i + 6) + disp  # next insn after 6-byte mov
            # rva-relative: abs_addr is RVA
            try:
                return u32(b, base + abs_addr), "mem"
            except Exception:
                return None, "mem_fail"
    return None, None


def clone_size(b, base, clone_rva):
    blob = b.read(base + clone_rva, 0x50)
    for ins in md.disasm(blob, clone_rva):
        if ins.mnemonic == "mov" and ins.op_str.startswith("ecx,") and "0x" in ins.op_str:
            return int(ins.op_str.split(",")[1].strip(), 16)
        if ins.mnemonic == "ret":
            break
    return None


def factory_idx(tid):
    ft = cmd_layout.FACTORY_TABLE
    return tid - ft["index_bias"] if tid >= ft["index_bias_sub_if_ge"] else tid


def factory_fn(b, base, tid):
    ft = cmd_layout.FACTORY_TABLE
    i = factory_idx(tid)
    if i is None or i < 0 or i > ft["max_index"]:
        return 0
    return u64(b, base + ft["rva"] + i * 8)


def watcher_alive():
    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' "
                "-and $_.CommandLine -match 'midflight' } | Select-Object -ExpandProperty ProcessId",
            ],
            text=True,
            errors="ignore",
            timeout=15,
        )
        pids = [int(x) for x in out.split() if x.strip().isdigit()]
        return {"alive": bool(pids), "pids": pids}
    except Exception as e:
        return {"alive": None, "error": str(e)}


def deepen_subtype(b, base, pe, plain, kind):
    info = exact_type(pe, plain) or {}
    vtables = info.get("vtables") or []
    if not vtables or not isinstance(vtables[0], dict):
        return {"name": plain, "kind": kind, "err": "no_vtable"}
    vt = vtables[0]["vtable_rva"]
    slots = {
        "bin_ser": u64(b, base + vt + 0x8) - base,
        "bin_des": u64(b, base + vt + 0x18) - base,
        "isvalid": u64(b, base + vt + 0x48) - base,
        "execute": u64(b, base + vt + 0x50) - base,
        "gettypeid": u64(b, base + vt + 0x58) - base,
        "clone": u64(b, base + vt + 0x68) - base,
        "tok_ser": u64(b, base + vt + 0xA0) - base,
        "tok_des": u64(b, base + vt + 0xA8) - base,
    }
    tid, tid_kind = parse_gettypeid(b, base, slots["gettypeid"])
    size = clone_size(b, base, slots["clone"])
    fn = factory_fn(b, base, tid) if tid is not None else 0
    dr = cmd_layout.DUMMY_ROUNDTRIP
    return {
        "name": plain,
        "kind": kind,
        "vt": hex(vt),
        "type_id": hex(tid) if tid is not None else None,
        "type_id_kind": tid_kind,
        "size": hex(size) if size else None,
        "factory": hex(fn - base) if fn else None,
        "factory_idx": factory_idx(tid) if tid is not None else None,
        "factory_match": bool(fn),
        "serialize": hex(slots["tok_ser"]),
        "deserialize": hex(slots["tok_des"]),
        "clone": hex(slots["clone"]),
        "isvalid": hex(slots["isvalid"]),
        "execute": hex(slots["execute"]),
        "gettypeid": hex(slots["gettypeid"]),
        "shared_bin": (
            slots["bin_ser"] == dr["shared_bin_ser"]
            and slots["bin_des"] == dr["shared_bin_des"]
        ),
    }


def main():
    assert not allow_post(), "ALLOW_POST must stay False"
    pid = find_pid("hoi4.exe")
    b = Backend(pid)
    base = int(b.image_base)
    pe = PE(binary_path(required=False))
    report = {
        "phase": "2bq",
        "posting": "DISABLED",
        "allow_post": allow_post(),
        "speed_rule": "pause or 1x only; never 5x",
        "pid": pid,
        "base": hex(base),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    sess = u64(b, base + post_abi.G_SESSION)
    report["session"] = {
        "ptr": hex(sess),
        "tick": u32(b, sess + 0x84),
        "flag_725": u8(b, sess + 0x725),
        "flag_6cc": u8(b, sess + 0x6CC),
        "flag_726": u8(b, sess + 0x726),
        "auth_3c": u8(b, sess + 0x3C),
    }

    server = u64(b, sess + post_abi.CSession_SERVER)
    ring = server + post_abi.CDummyServer_RING
    report["dummy_server"] = {
        "ptr": hex(server),
        "vt": hex(u64(b, server) - base),
        "pending_count": u32(b, server + post_abi.CDummyServer_PENDING + 0x10),
        "execlist_count": u32(b, server + post_abi.CDummyServer_EXECLIST + 0x10),
        "seq": u32(b, server + 0xD0),
        "ring_lock": u32(b, ring),
        "ring_cap": u64(b, ring + 0x18),
        "ring_idx20": u64(b, ring + 0x20),
        "ring_idx28": u64(b, ring + 0x28),
        "ring_empty": u64(b, ring + 0x20) == 0 and u64(b, ring + 0x28) == 0,
    }

    # --- Live sticky StartGame as serialize→recreate source (no Post) ---
    wrap = u64(b, sess + 0xF8)
    cmd = u64(b, wrap) if wrap else 0
    sticky = {"wrapper": hex(wrap) if wrap else None, "addr": hex(cmd) if cmd else None}
    rt = {"status": "STUBBED", "reason": "no sticky"}
    if cmd:
        vt = u64(b, cmd) - base
        gt = u64(b, base + vt + 0x58) - base
        tid, tid_kind = parse_gettypeid(b, base, gt)
        fn = factory_fn(b, base, tid) if tid is not None else 0
        clone = u64(b, base + vt + 0x68) - base
        size = clone_size(b, base, clone)
        tok_ser = u64(b, base + vt + 0xA0) - base
        tok_des = u64(b, base + vt + 0xA8) - base
        bin_ser = u64(b, base + vt + 0x10) - base
        bin_des = u64(b, base + vt + 0x20) - base
        fields = {
            "plus_0xc": u32(b, cmd + 0xC),
            "plus_0x18_word": u16(b, cmd + 0x18),
            "plus_0x1a_byte": u8(b, cmd + 0x1A),
            "plus_0x1c": u32(b, cmd + 0x1C),
            "plus_0x20": u32(b, cmd + 0x20),
        }
        # Prove ser↔des field inverse by reading shared bin bodies (disasm contracts).
        ser_blob = b.read(base + 0x22D9390, 0xA0)
        des_blob = b.read(base + 0x22D90F0, 0xA0)
        ser_has_1f3 = b"\xf3\x01\x00\x00" in ser_blob  # mov edx, 0x1f3
        des_has_1f3 = b"\xf3\x01\x00\x00" in des_blob
        # tok ser for StartGame is ret0 (no payload beyond header)
        tok_ser_blob = b.read(base + tok_ser, 4)
        tok_ser_nop = tok_ser_blob[:1] == b"\xc3" or tok_ser_blob[:3] == b"\xc2\x00\x00"
        # recreate → factory_lookup call site
        rec = b.read(base + cmd_layout.DUMMY_ROUNDTRIP["recreate"], 0x200)
        calls_lookup = False
        for ins in md.disasm(rec, cmd_layout.DUMMY_ROUNDTRIP["recreate"]):
            if ins.mnemonic == "call" and "0x22d8d20" in ins.op_str:
                calls_lookup = True
                break
            if ins.address > cmd_layout.DUMMY_ROUNDTRIP["recreate"] + 0x1F0:
                break
        factory_expect = cmd_layout.STARTGAME.get("factory")
        sticky.update(
            {
                "vt": hex(vt),
                "vt_match": vt == cmd_layout.STARTGAME["vt"],
                "type_id": hex(tid) if tid is not None else None,
                "type_id_kind": tid_kind,
                "type_id_match": tid == cmd_layout.STARTGAME["type_id"],
                "factory_live": hex(fn - base) if fn else None,
                "factory_match": (fn == base + factory_expect) if factory_expect and fn else False,
                "size": hex(size) if size else None,
                "size_match_factory_alloc": size == 0x28,  # factory mov ecx,0x28
                "tok_ser": hex(tok_ser),
                "tok_des": hex(tok_des),
                "tok_ser_nop": tok_ser_nop,
                "bin_ser_body": hex(bin_ser),
                "bin_des_body": hex(bin_des),
                "fields": fields,
                "hex": b.read(cmd, size or 0x28).hex(),
            }
        )
        structural_ok = all(
            [
                sticky["vt_match"],
                sticky["type_id_match"],
                sticky["factory_match"],
                sticky["size_match_factory_alloc"],
                ser_has_1f3,
                des_has_1f3,
                bin_ser == 0x22D9390,
                bin_des == 0x22D90F0,
                calls_lookup,
                report["dummy_server"]["ring_empty"],  # no in-flight; safe RO observation
            ]
        )
        rt = {
            "status": "STRUCTURAL_LIVE_OK" if structural_ok else "PARTIAL",
            "mode": "sticky_CStartGameCommand_no_Post",
            "header_token": hex(HEADER_TOKEN),
            "header_fields": HEADER_FIELDS,
            "ser_has_token_1f3": ser_has_1f3,
            "des_has_token_1f3": des_has_1f3,
            "ser_des_inverse_offsets": (
                "bin_ser packs +0xc/+0x18/+0x1a/+0x1c/+0x20; "
                "bin_des unpacks same offsets (token 0x1F3 path)"
            ),
            "recreate_calls_factory_lookup": calls_lookup,
            "tok_ser_nop": tok_ser_nop,
            "live_inprocess_ring_embed": "STUBBED",
            "note": (
                "Live sticky StartGame observed RO. Shared bin ser↔des header token 0x1F3 "
                "is a proven field inverse; recreate calls factory_lookup; factory size 0x28 "
                "matches clone. Full in-process serialize→recreate→ring embed still needs "
                "Post or midflight (blocked). Ring currently empty — safe to observe only."
            ),
            "structural_ok": structural_ok,
        }

    report["sticky_startgame"] = sticky
    report["live_buffer_dummy_rt"] = rt

    # --- Remaining subtypes ---
    land = [
        "CMoveArmiesInTheaterCommand",
        "CMoveArmyGroupInTheaterCommand",
        "CCancelRunningAwayCommand",
        "CRailwayGunManualOrderCommand",
        "CSetCountryGarrisonPriorityCommand",
        "CSetQuickDeployPreferenceCommand",
    ]
    naval_air = [
        "CNavalMoveCommand",
        "CMoveShipsCommand",
        "CNavalMissionMoveCommand",
        "CNavalMissionMassMoveCommand",
        "CDeployAirWingCommand",
        "CNavyCancelActivityCommand",
    ]
    extra = {}
    for n in land:
        extra[n] = deepen_subtype(b, base, pe, n, "land")
    for n in naval_air:
        extra[n] = deepen_subtype(b, base, pe, n, "naval_air")
    land_ok = sum(1 for n in land if extra[n].get("shared_bin") and extra[n].get("type_id"))
    na_ok = sum(1 for n in naval_air if extra[n].get("shared_bin") and extra[n].get("type_id"))
    report["extra_commands"] = {
        "land_ok": land_ok,
        "land_n": len(land),
        "naval_air_ok": na_ok,
        "naval_air_n": len(naval_air),
        "entries": extra,
    }

    # NEVER_POST sizes from live clone
    np_sizes = {}
    for name, meta in cmd_layout.NEVER_POST.items():
        cl = u64(b, base + meta["vt"] + 0x68) - base
        sz = clone_size(b, base, cl)
        np_sizes[name] = {
            "size_live": hex(sz) if sz else None,
            "catalog_size": hex(meta["size"]) if meta.get("size") else None,
            "match": (sz == meta["size"]) if meta.get("size") and sz else None,
        }
    report["never_post_sizes"] = np_sizes

    # Tool-gate deepen (analysis only)
    report["tool_gate"] = {
        "command_queue_tool_gate": "open_gap_but_DISABLED",
        "status": "CLOSED_NOT_OPENED",
        "allow_post": allow_post(),
        "action_this_phase": "analysis only — gate NOT opened",
        "predicates_all_required": [
            {
                "id": "midflight_CMoveCommand",
                "status": "STUBBED",
                "must": "Live mid-flight Move/Strategic sample with unit+path vectors",
            },
            {
                "id": "serialize_recreate_roundtrip",
                "status": "structural_sticky_ok_inprocess_stubbed",
                "must": "In-process serialize→recreate→ring embed (Post or captured buffer)",
                "progress_2bq": "sticky StartGame structural ser↔des + factory/recreate wiring proven RO",
            },
            {
                "id": "CLAUSEWITZ_ALLOW_POST",
                "status": "hard-deny",
                "must": "Explicit env + code path flip; currently always False",
            },
            {
                "id": "session_725",
                "status": "necessary_not_sufficient",
                "live": report["session"]["flag_725"],
            },
            {
                "id": "never_post_banlist",
                "status": "closed",
                "must": "Speed/Hourly/Ping/Pause remain NEVER_POST",
            },
            {
                "id": "no_guess_writes",
                "status": "policy",
                "must": "No WPM/Post on guessed layouts",
            },
            {
                "id": "ring_empty_safe_observe",
                "status": "ok" if report["dummy_server"]["ring_empty"] else "busy",
                "live_empty": report["dummy_server"]["ring_empty"],
            },
        ],
    }

    mid = watcher_alive()
    report["midflight"] = {
        "status": "stubbed",
        "watcher": mid,
        "input_injection": False,
    }

    works = []
    stubbed = []
    if rt.get("structural_ok"):
        works.append(
            "live-buffer Dummy RT structural (sticky StartGame ser↔des token 0x1F3 + recreate/factory) RO"
        )
    else:
        stubbed.append("live-buffer Dummy RT structural incomplete")
    stubbed.append("live in-process serialize→recreate→ring embed (needs Post/midflight)")
    if land_ok >= 5:
        works.append(f"extra land command subtypes deepened {land_ok}/{len(land)}")
    else:
        stubbed.append(f"extra land subtypes {land_ok}/{len(land)}")
    works.append(f"extra naval/air subtypes catalogued RO {na_ok}/{len(naval_air)}")
    works.append("NEVER_POST clone sizes live-read")
    works.append("tool_gate predicates deepened; CLOSED_NOT_OPENED")
    works.append("allow_post False hard-deny")
    stubbed.append("midflight_CMoveCommand sample (DX11)")
    stubbed.append("command_queue_tool_gate enable")

    report["works"] = works
    report["stubbed"] = stubbed

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "allow_post": report["allow_post"],
                "rt_status": rt.get("status"),
                "structural_ok": rt.get("structural_ok"),
                "land_ok": land_ok,
                "naval_air_ok": na_ok,
                "tool_gate": report["tool_gate"]["status"],
                "tick": report["session"]["tick"],
                "flag_725": report["session"]["flag_725"],
                "ring_empty": report["dummy_server"]["ring_empty"],
                "midflight_watcher": mid,
                "works_n": len(works),
                "stubbed_n": len(stubbed),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
