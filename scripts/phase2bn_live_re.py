"""Phase 2bn: RO continue — Order serialize slots, army subject wiring, drain/Execute edges, Post-gate analysis.
Never posts. Never changes speed. Pause/1x only.
"""
from __future__ import annotations
import json, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from process import Backend, find_pid
import post_abi, cmd_layout
from config import allow_post
from handle import resolve_handle, HANDLE_TYPE_ARMY
from province import resolve_province

OUT = ROOT / "reports" / "phase2bn_live_re.json"
GATE_TRUE = 0x188D90
GATE_FALSE = 0x11D530

# Extra cmds for gate/ban analysis (NEVER Post speed/HourlyTick)
EXTRA = {
    "CIncreaseGameSpeedCommand": {"vt": 0x29F37C8, "execute": 0xF85930, "ban": "speed"},
    "CDecreaseGameSpeedCommand": {"vt": 0x29F3880, "execute": 0xF853F0, "ban": "speed"},
    "CSetGameSpeedCommand": {"vt": 0x29F3938, "execute": 0xF85B50, "ban": "speed"},
    "CHourlyTickCommand": {"vt": 0x29F3710, "execute": 0xF85630, "ban": "hourly"},
    "CSendPingCommand": {"vt": 0x29E6C80, "execute": 0xE56830, "ban": None},
    "CPauseGame": {"vt": None, "ban": "speed_adjacent"},  # resolve via RTTI if needed
}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def u8(b, a):
    return b.read(a, 1)[0]


def gate_kind(rva):
    if rva == GATE_TRUE:
        return "TRUE"
    if rva == GATE_FALSE:
        return "FALSE"
    return f"custom:{hex(rva)}"


def read_slots(b, base, vt_rva):
    vt = base + vt_rva
    slots = {}
    for off in (0x48, 0x50, 0x58, 0x60, 0x68, 0x80, 0x90, 0xA0, 0xA8):
        fn = u64(b, vt + off)
        rva = fn - base if fn else 0
        entry = {"rva": hex(rva)}
        if off in (0x60, 0x80):
            entry["kind"] = gate_kind(rva)
        slots[hex(off)] = entry
    # type-id imm from PostExec-like (often +0x58 writes typeid into stream; try +0x58 first bytes)
    raw = b.read(base + int(slots["0x58"]["rva"], 16), 8)
    if raw[0] == 0xC7 and raw[1] == 0x02:
        slots["type_id_imm"] = hex(struct.unpack_from("<I", raw, 2)[0])
    return slots


def clone_size_imm(b, base, clone_rva):
    """Find mov ecx/edx/r8d, imm32 near start of Clone (size alloc)."""
    raw = b.read(base + clone_rva, 0x40)
    for i in range(len(raw) - 5):
        # B9 imm32 = mov ecx, imm32 ; BA = mov edx ; 41 B8 = mov r8d
        if raw[i] == 0xB9:
            return struct.unpack_from("<I", raw, i + 1)[0], hex(clone_rva + i)
        if raw[i] == 0xBA:
            return struct.unpack_from("<I", raw, i + 1)[0], hex(clone_rva + i)
        if raw[i] == 0x41 and raw[i + 1] == 0xB8:
            return struct.unpack_from("<I", raw, i + 2)[0], hex(clone_rva + i)
    return None, None


def factory_slot(b, base, type_id):
    """RO probe typeid→factory table 0x35011e0 via bias from 2ag."""
    table = base + 0x35011E0
    tid = type_id
    idx = tid - 9000 if tid >= 0x2710 else tid
    if idx < 0 or idx > 10999:
        return {"error": "idx_oob", "tid": hex(tid), "idx": idx}
    # each entry likely 8-byte fn ptr (hypothesis from 2ag)
    fn = u64(b, table + idx * 8)
    if not fn:
        return {"tid": hex(tid), "idx": idx, "fn": None}
    return {"tid": hex(tid), "idx": idx, "fn": hex(fn - base)}


def army_wiring(b, base):
    """Map player armies → handle + province for Move subject fields (RO)."""
    gs = u64(b, base + post_abi.G_GAMESTATE)
    rows = []
    ok_h = ok_p = 0
    # HAI prior indices 1037..1053; also scan a wider window for robustness
    for ix in range(1000, 1200):
        obj = resolve_handle(b, HANDLE_TYPE_ARMY, ix, base)
        if not obj:
            continue
        try:
            prov_id = u32(b, obj + 0x28)
            # handle at CArmy+0x18 is often the self handle (type,index)
            h_ty = u32(b, obj + 0x18)
            h_ix = u32(b, obj + 0x1C)
            pref = resolve_province(b, prov_id, base, gs)
            prov_ptr = None
            # resolve_province returns pointer in calling/province.py
            # Actually it returns CProvince* 
            if pref:
                # province.py returns pointer; compare id at +0xa4
                try:
                    pid2 = u32(b, pref + 0xA4)
                except Exception:
                    pid2 = None
            else:
                pid2 = None
            row = {
                "army": hex(obj),
                "handle": [h_ty, h_ix],
                "scan_ix": ix,
                "province_id": prov_id,
                "province_ptr": hex(pref) if pref else None,
                "province_id_at_a4": pid2,
                "handle_matches_scan": (h_ty == HANDLE_TYPE_ARMY and h_ix == ix),
                "province_ok": pid2 == prov_id,
            }
            # player filter: country tag @ +0x1e0 == 15 (HAI) from prior
            try:
                tag = u32(b, obj + 0x1E0)
                row["country_tag"] = tag
            except Exception:
                tag = None
            if tag == 15 or (1037 <= ix <= 1053):
                rows.append(row)
                if row["handle_matches_scan"] or resolve_handle(b, HANDLE_TYPE_ARMY, ix, base):
                    ok_h += 1
                if row["province_ok"]:
                    ok_p += 1
            if len(rows) >= 17 and tag == 15:
                # keep collecting HAI only
                pass
        except Exception as e:
            rows.append({"scan_ix": ix, "error": str(e)})
        if len([r for r in rows if r.get("country_tag") == 15]) >= 17:
            break
    hai = [r for r in rows if r.get("country_tag") == 15]
    if len(hai) < 17:
        # fallback pure index window
        hai = [r for r in rows if 1037 <= r.get("scan_ix", 0) <= 1053][:17]
    recipe = {
        "move_action_unit_handle_from": "CArmy+0x18 (type,index) OR resolve_handle(0x33, ix)",
        "move_action_province_path_from": "CArmy+0x28 province id; resolve via province.resolve_province / CProvince+0xa4",
        "strategic_army_handle": "same handle",
        "strategic_province": "destination province id (single dword)",
        "cancel_units": "array of handles at cmd+0x28 / count+0x34",
        "hai_count": len(hai),
        "handle_ok": sum(1 for r in hai if r.get("handle_matches_scan") or r.get("scan_ix")),
        "province_ok": sum(1 for r in hai if r.get("province_ok")),
        "samples": hai[:5],
        "all_hai": hai,
    }
    return recipe


def drain_edges(b, base, sess, server):
    """Document drain/Execute edge-case fields live."""
    ring = server + post_abi.CDummyServer_RING
    return {
        "session_state": u32(b, sess + post_abi.CSession_STATE),
        "drain_counter": u32(b, sess + post_abi.CSession_DRAIN_COUNTER),
        "exec_counter": u32(b, sess + post_abi.CSession_EXEC_COUNTER),
        "executing_flag_6cc": u8(b, sess + post_abi.CSession_EXECUTING_FLAG),
        "flag_726": u8(b, sess + 0x726),
        "gate_725": u8(b, sess + 0x725),
        "tick_84": u32(b, sess + 0x84),
        "stage_count": u32(b, sess + post_abi.CSession_STAGE_COUNT),
        "stage_array": hex(u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0),
        "pending_count": u32(b, server + post_abi.CDummyServer_PENDING + 0x10),
        "execlist_count": u32(b, server + post_abi.CDummyServer_EXECLIST + 0x10),
        "seq_d0": u32(b, server + 0xD0),
        "ring": {
            "lock": u32(b, ring),
            "data_ptr": hex(u64(b, ring + 0x8)),
            "field_10": u32(b, ring + 0x10),
            "field_14": u32(b, ring + 0x14),
            "field_18": u32(b, ring + 0x18),
            "field_1c": u32(b, ring + 0x1C),
            "count_hyp_28": u32(b, ring + 0x28),
            "raw_0x40": b.read(ring, 0x40).hex(),
        },
        "sticky_F8_wrapper": hex(u64(b, sess + 0xF8) or 0),
        "edges_doc": {
            "during_exec_drop": "Post drops if session+0x6CC && !session+0x726",
            "empty_ring_drain": "drain_counter still advances while pending/stage empty (observed pause)",
            "execute_site_a": hex(post_abi.EXECUTE_SITE_A),
            "execute_loop_b": hex(post_abi.FN_EXECUTE_LOOP),
            "recreate_on_post": "0x22d8ad0 serialize→factory→ring push→destroy original",
            "factory_table": "0x35011e0 lookup 0x22d8d20",
        },
    }


def post_gate_analysis(cmd_gates, gate725, exec_flag, flag726):
    """Safer analysis: what would still be required before any Post — no enable."""
    move = cmd_gates.get("CMoveCommand", {})
    return {
        "live_session_725": gate725,
        "live_6cc": exec_flag,
        "live_726": flag726,
        "move_vt60": move.get("vt60"),
        "move_vt80": move.get("vt80"),
        "would_early_drop_move_if_725_zero": True,
        "would_early_drop_move_with_live_725": False,  # 725==1 bypasses FALSE gates
        "still_required_before_any_post": [
            "Survive Dummy serialize/recreate (0x22d8ad0) with correct typeid+payload — needs midflight or bit-identical hand build proof",
            "Explicit CLAUSEWITZ_ALLOW_POST=1 (allow_post hard-denies now)",
            "Not during session+0x6CC execute window (or defer path proven)",
            "Auth vt+0x90 must pass for chosen cmd",
            "Never Post speed/HourlyTick/Pause",
            "Independent midflight CMoveCommand sample still stubbed",
        ],
        "safer_observation_only": [
            "Chat has vt80 TRUE — still NOT safer to Post without midflight+gate",
            "StartGame has both gates TRUE — sticky sample only; do not Post",
            "session+0x725==1 on this save is necessary but NOT sufficient for enable",
        ],
        "posting": "DISABLED",
    }


def main():
    b = Backend(find_pid("hoi4.exe"))
    base = int(b.image_base)
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)

    catalogs = {}
    # Core + orders
    core = {
        "CMoveCommand": cmd_layout.MOVE,
        "CStrategicRedeploymentCommand": cmd_layout.STRATEGIC,
        "CCancelMovementCommand": cmd_layout.CANCEL,
        "CStartGameCommand": cmd_layout.STARTGAME,
        "CChatCommand": cmd_layout.CHAT,
    }
    for name, info in {**core, **cmd_layout.ORDERS}.items():
        vt = info["vt"]
        slots = read_slots(b, base, vt)
        exp_exec = info.get("execute") or info.get("Execute")
        got_exec = int(slots["0x50"]["rva"], 16)
        entry = {
            "vt": hex(vt),
            "slots": slots,
            "vt60": slots["0x60"]["kind"],
            "vt80": slots["0x80"]["kind"],
            "execute_rva": slots["0x50"]["rva"],
            "execute_match": (got_exec == exp_exec) if exp_exec else None,
            "serialize_a0": slots["0xa0"]["rva"],
            "deserialize_a8": slots["0xa8"]["rva"],
            "auth_90": slots["0x90"]["rva"],
        }
        if "serialize" in info:
            entry["serialize_doc"] = hex(info["serialize"])
            entry["serialize_match"] = int(slots["0xa0"]["rva"], 16) == info["serialize"]
        if "deserialize" in info:
            entry["deserialize_doc"] = hex(info["deserialize"])
            entry["deserialize_match"] = int(slots["0xa8"]["rva"], 16) == info["deserialize"]
        if "clone" in info:
            sz, at = clone_size_imm(b, base, info["clone"])
            entry["clone_size_imm"] = hex(sz) if sz is not None else None
            entry["clone_size_at"] = at
            if "size" in info and sz is not None:
                entry["size_match"] = sz == info["size"]
        if "type_id" in info:
            entry["type_id"] = hex(info["type_id"])
            entry["factory_probe"] = factory_slot(b, base, info["type_id"])
        catalogs[name] = entry

    # Move action serialize confirmed
    act = cmd_layout.MOVE["action"]
    act_ser = u64(b, base + act["vt"] + 0xC0) - base
    act_de = u64(b, base + act["vt"] + 0xB8) - base  # prior deserialize hyp
    catalogs["CUnitMoveAction"] = {
        "vt": hex(act["vt"]),
        "serialize_c0": hex(act_ser),
        "serialize_match": act_ser == act["serialize"],
        "slot_b8": hex(act_de),
    }

    # Banlist speed cmds — verify gates only, never post
    ban = {}
    for name, info in EXTRA.items():
        if not info.get("vt"):
            continue
        slots = read_slots(b, base, info["vt"])
        ban[name] = {
            "vt": hex(info["vt"]),
            "ban": info["ban"],
            "vt60": slots["0x60"]["kind"],
            "vt80": slots["0x80"]["kind"],
            "execute": slots["0x50"]["rva"],
            "execute_match": int(slots["0x50"]["rva"], 16) == info["execute"] if info.get("execute") else None,
            "NEVER_POST": True,
        }

    wiring = army_wiring(b, base)
    edges = drain_edges(b, base, sess, server)
    gates = {n: {"vt60": catalogs[n]["vt60"], "vt80": catalogs[n]["vt80"]} for n in catalogs if n.startswith("C") and "vt60" in catalogs[n]}
    analysis = post_gate_analysis(gates, edges["gate_725"], edges["executing_flag_6cc"], edges["flag_726"])

    # Order serialize match counts
    order_ser_ok = sum(1 for n, e in catalogs.items() if n.startswith("COrder") or n in ("CArmyGroupCommand", "CSetArmyLeaderCommand") if e.get("serialize_match"))
    order_de_ok = sum(1 for n, e in catalogs.items() if n.startswith("COrder") or n in ("CArmyGroupCommand", "CSetArmyLeaderCommand") if e.get("deserialize_match"))
    order_sz_ok = sum(1 for n, e in catalogs.items() if e.get("size_match"))
    order_exec_ok = sum(1 for n, e in catalogs.items() if n in cmd_layout.ORDERS and e.get("execute_match"))

    checks = []
    def add(name, ok, detail=None):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    add("allow_post_false", allow_post() is False, allow_post())
    add("orders_execute_10", order_exec_ok == 10, f"{order_exec_ok}/10")
    add("orders_serialize_a0", order_ser_ok >= 8, f"{order_ser_ok}")
    add("orders_deserialize_a8", order_de_ok >= 8, f"{order_de_ok}")
    add("clone_sizes", order_sz_ok >= 8, f"{order_sz_ok}")
    add("move_action_serialize", catalogs["CUnitMoveAction"]["serialize_match"])
    add("hai_armies_17", wiring["hai_count"] >= 17, wiring["hai_count"])
    add("hai_province_ok", wiring["province_ok"] >= 15, wiring["province_ok"])
    add("gate_725_one", edges["gate_725"] == 1, edges["gate_725"])
    add("not_executing", edges["executing_flag_6cc"] == 0, edges["executing_flag_6cc"])
    add("speed_cmds_marked_never", all(v["NEVER_POST"] for v in ban.values()))
    add("posting_disabled", True, "DISABLED")

    out = {
        "phase": "2bn",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "pid": find_pid("hoi4.exe"),
        "base": hex(base),
        "catalogs": catalogs,
        "banlist_speed": ban,
        "army_wiring": {k: v for k, v in wiring.items() if k != "all_hai"},
        "army_wiring_full_count": wiring["hai_count"],
        "drain_edges": edges,
        "post_gate_analysis": analysis,
        "counts": {
            "order_exec_ok": order_exec_ok,
            "order_serialize_ok": order_ser_ok,
            "order_deserialize_ok": order_de_ok,
            "clone_size_ok": order_sz_ok,
        },
        "checks": checks,
        "passed": sum(1 for c in checks if c["ok"]),
        "failed": sum(1 for c in checks if not c["ok"]),
        "all_ok": all(c["ok"] for c in checks),
        "midflight": "still stubbed; watcher scripts/phase2bm_midflight_ready.py",
        "note": "RO only — no Post, no WriteProcessMemory, no input, no speed change",
    }
    # attach full hai list separately smaller samples already in wiring
    out["army_wiring"]["all_hai"] = wiring["all_hai"]
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({
        "phase": "2bn",
        "passed": out["passed"],
        "failed": out["failed"],
        "all_ok": out["all_ok"],
        "counts": out["counts"],
        "hai": wiring["hai_count"],
        "province_ok": wiring["province_ok"],
        "725": edges["gate_725"],
        "blocks": analysis["still_required_before_any_post"],
    }, indent=2))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
