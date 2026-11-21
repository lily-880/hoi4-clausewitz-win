# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os, struct, sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
os.environ.pop("CLAUSEWITZ_ALLOW_WRITE", None)

from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable
from process import Backend
import move_order as mo

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
EXPECTED_PID = 12948
SP_ISVALID = 0x18DFF70
SP_FACTORY = 0x18D0950
SP_VT = 0x2A84FE0
SP_SIZE = 0x58
SENTINEL_A, SENTINEL_B = 380896, 380934
OUT = ROOT / "research" / "t197_setpath_diag.json"


def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF


def pdx(p, a):
    return struct.unpack("<QII", p.read(a, 16))


def ptr_array(p, a, bound=4096):
    data, cap, size = pdx(p, a)
    if not 0 <= size <= cap <= max(bound, 100) or (size and not is_ptr(data)):
        return []
    return [struct.unpack("<Q", p.read(data + 8 * j, 8))[0] for j in range(size)]


def handle_at(p, a):
    return list(struct.unpack("<II", p.read(a, 8)))


def cls(p, pe, a):
    if not is_ptr(a):
        return None
    try:
        vt = struct.unpack("<Q", p.read(a, 8))[0]
    except OSError:
        return None
    if not p.base <= vt < p.base + p.image_size:
        return None
    return _rtti_name_from_vtable(pe, vt - p.base)


def main():
    out = {"authorized_by": ["pt183u", "pt180u"]}
    pid = mem_find_pid("hoi4.exe")
    out["pid"] = pid
    out["pid_ok"] = pid == EXPECTED_PID
    if pid != EXPECTED_PID:
        OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(out, indent=2))
        return
    p = Proc(pid)
    pe = PE(EXE)
    b = Backend()
    try:
        session = detect_session(p, pe)
        gs = int(session["signals"]["gs_ptr"], 16)
        idler = int(session["signals"]["idler_ptr"], 16)
        co = int(resolve_player_country(p, gs)["country_ptr"], 16)
        pause = p.read(idler + 0x6C1, 1)[0]
        speed = struct.unpack("<i", p.read(gs + 0x4BC, 4))[0]
        out["pause"] = pause
        out["speed"] = speed
        # find army 411
        tp = ptr_array(p, co + 0x168, 64)[0]
        groups = []
        target = None
        inst = None
        for gp in ptr_array(p, tp + 0x80, 256):
            h = handle_at(p, gp + 8)
            insts = []
            for ip in ptr_array(p, gp + 0x98, 256):
                rec = {
                    "ptr": hex(ip),
                    "class": cls(p, pe, ip),
                    "id": struct.unpack("<I", p.read(ip + 0x244, 4))[0],
                    "type": struct.unpack("<I", p.read(ip + 0x30, 4))[0],
                    "path70_n": pdx(p, ip + 0x70)[2],
                    "f258": struct.unpack("<I", p.read(ip + 0x258, 4))[0],
                    "f25c": struct.unpack("<I", p.read(ip + 0x25C, 4))[0],
                    "exec": p.read(ip + 0x248, 1)[0],
                }
                insts.append(rec)
            recg = {"ptr": hex(gp), "class": cls(p, pe, gp), "handle": h, "instances": insts}
            groups.append(recg)
            if h == [53, 411]:
                target = recg
                inst = insts[0] if insts else None
        out["groups"] = groups
        out["target"] = target
        out["inst"] = inst
        if not target or not inst:
            OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
            return

        inst_ptr = int(inst["ptr"], 16)
        group_ptr = int(target["ptr"], 16)

        # helpers
        def remote(rva, regs, note):
            rec = mo._remote(pid, b.image_base + rva, regs, wait_ms=5000)
            rec["note"] = note
            rec["rax_hex"] = hex(rec["rax"]) if rec.get("rax") else rec.get("rax")
            rec["al"] = (rec["rax"] & 0xFF) if rec.get("wait") == 0 and rec.get("rax") is not None else None
            return rec

        # 0xbbb250 on a temp 8-byte handle buffer
        hbuf = mo._game_malloc(pid, 16)
        mo._write(pid, hbuf, struct.pack("<II", 53, 411))
        out["bbb250_handle"] = remote(0xBBB250, {"rcx": hbuf}, "bbb250 on {53,411}")
        out["resolve_group"] = remote(0x2284870, {"rcx": hbuf}, "resolve {53,411}")
        resolved = out["resolve_group"].get("rax") or 0
        out["resolved_cls"] = cls(p, pe, resolved)
        out["resolved_ptr"] = hex(resolved)
        out["expected_group_ptr"] = hex(group_ptr)

        # c402a0 with ids 0,1,2,3
        c402 = {}
        for iid in (0, 1, 2, 3, 411):
            rec = remote(0xC402A0, {"rcx": resolved or group_ptr, "rdx": iid}, f"c402a0 id={iid}")
            rax = rec.get("rax") or 0
            rec["cls"] = cls(p, pe, rax)
            rec["matches_inst"] = (rax == inst_ptr)
            if is_ptr(rax) and rec["cls"] and "COrderInstance" in rec["cls"]:
                rec["id_244"] = struct.unpack("<I", p.read(rax + 0x244, 4))[0]
                rec["f258"] = struct.unpack("<I", p.read(rax + 0x258, 4))[0]
                rec["f25c"] = struct.unpack("<I", p.read(rax + 0x25C, 4))[0]
            c402[str(iid)] = rec
        out["c402a0"] = c402

        # rebuild SetPath cmd and IsValid, also dump +0x28/+0x30
        made = mo._remote(pid, b.image_base + SP_FACTORY, wait_ms=5000)
        cmd = made.get("rax") or 0
        out["factory"] = {"wait": made.get("wait"), "cmd": hex(cmd), "vt": hex(mo._u64(b, cmd) - b.image_base) if cmd else None}
        if cmd and mo._u64(b, cmd) - b.image_base == SP_VT:
            mo._write(pid, cmd + 0x28, struct.pack("<II", 53, 411))
            mo._write(pid, cmd + 0x30, struct.pack("<I", 2))
            raw = p.read(cmd, SP_SIZE)
            out["repack"] = {
                "plus28": list(struct.unpack_from("<II", raw, 0x28)),
                "plus30_8": list(struct.unpack_from("<II", raw, 0x30)),
            }
            # IsValid on this cmd
            out["isvalid_id2"] = remote(SP_ISVALID, {"rcx": cmd}, "IsValid id=2")
            # try id 0 and 1 on same cmd without posting
            mo._write(pid, cmd + 0x30, struct.pack("<I", 0))
            out["isvalid_id0"] = remote(SP_ISVALID, {"rcx": cmd}, "IsValid id=0")
            mo._write(pid, cmd + 0x30, struct.pack("<I", 1))
            out["isvalid_id1"] = remote(SP_ISVALID, {"rcx": cmd}, "IsValid id=1")
            # also try writing full 8 bytes at +0x30 as {2,0}
            mo._write(pid, cmd + 0x30, struct.pack("<II", 2, 0))
            out["isvalid_id2_hi0"] = remote(SP_ISVALID, {"rcx": cmd}, "IsValid id=2 hi=0")
            # bbb250 on the command's +0x28
            out["bbb250_cmd"] = remote(0xBBB250, {"rcx": cmd + 0x28}, "bbb250 on cmd+0x28")
    finally:
        p.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    # compact
    compact = {k: out[k] for k in (
        "pid_ok", "pause", "speed", "target", "inst",
        "bbb250_handle", "resolve_group", "resolved_cls", "resolved_ptr",
        "expected_group_ptr", "c402a0", "factory", "repack",
        "isvalid_id2", "isvalid_id0", "isvalid_id1", "isvalid_id2_hi0", "bbb250_cmd",
    ) if k in out}
    print(json.dumps(compact, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
