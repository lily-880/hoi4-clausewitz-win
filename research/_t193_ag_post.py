# Inspect theatre arrays, then dry-run + optional Post CArmyGroupCommand, then optional SetArmyLeader.
from __future__ import annotations
import json, os, struct, sys, time, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"calling"))
os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
os.environ.pop("CLAUSEWITZ_ALLOW_WRITE", None)

from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary
from config import allow_post
from process import Backend
import move_order as mo
import post_abi

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
MARKER = ROOT/"research"/"safe_land_tool_gate.OPEN"
LEGACY = ROOT/"research"/"strategic_only_tool_gate.OPEN"
OUT = ROOT/"research"/"t193_ag_post.json"

EXPECTED_PID=26976
EXPECTED_GS=0x26C259D0FF0
EXPECTED_CO=0x26C4B672530
KEEP_PATH=[8036]
THEATRE=(67,43)
ARMY=(53,1)

AG={"factory":0x18CF780,"vt":0x2A846E0,"isvalid":0x18DDFE0,"execute":0x18D2640,"size":0x80}
SL={"factory":0x18D0C10,"vt":0x2A85E20,"isvalid":0x18E0540,"execute":0x18DB330,"size":0x40}

def is_ptr(x):
    return type(x) is int and 0x100000000 < x < 0x7FFFFFFFFFFF

def open_gates():
    os.environ["CLAUSEWITZ_ALLOW_POST"]="1"
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text("t193 one-shot CArmyGroupCommand (+ optional SetArmyLeader) authorized by pt180u.\nPause/1x only. Close after block.\n", encoding="utf-8")
    if LEGACY.exists():
        LEGACY.unlink()

def close_gates():
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    os.environ.pop("CLAUSEWITZ_ALLOW_WRITE", None)
    if MARKER.exists(): MARKER.unlink()
    if LEGACY.exists(): LEGACY.unlink()

def process_health(pid):
    import ctypes
    from ctypes import wintypes as wt
    k=ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype=wt.HANDLE
    k.OpenProcess.argtypes=[wt.DWORD, wt.BOOL, wt.DWORD]
    k.GetExitCodeProcess.argtypes=[wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    k.GetExitCodeProcess.restype=wt.BOOL
    k.CloseHandle.argtypes=[wt.HANDLE]
    h=k.OpenProcess(0x1000|0x0400, False, pid)
    if not h: return {"alive":False,"exit_code":None,"open_err":ctypes.get_last_error()}
    try:
        code=wt.DWORD(0); k.GetExitCodeProcess(h, ctypes.byref(code))
        return {"alive": int(code.value)==259, "exit_code": int(code.value)}
    finally:
        k.CloseHandle(h)

def msvc_string(p,a):
    blob=p.read(a,32)
    n,cap=struct.unpack_from("<QQ",blob,16)
    if not 0<=n<=1024 or cap<n: return None
    raw=blob[:n] if cap<=15 else p.read(struct.unpack_from("<Q",blob)[0], n)
    return raw.decode("utf-8","replace")

def pdx(p,a):
    data,cap,size=struct.unpack("<QII", p.read(a,16))
    return {"data":data,"cap":cap,"size":size}

def ptr_array(p,a,bound=4096):
    h=pdx(p,a)
    if not 0<=h["size"]<=h["cap"]<=max(bound,100) or (h["size"] and not is_ptr(h["data"])):
        return [], h
    return [struct.unpack("<Q", p.read(h["data"]+8*j,8))[0] for j in range(h["size"])], h

def cls(p,pe,a):
    if not is_ptr(a): return None
    vt=struct.unpack("<Q", p.read(a,8))[0]
    if not p.base<=vt<p.base+p.image_size: return None
    return _rtti_name_from_vtable(pe, vt-p.base)

def unit_path(p,ap):
    h=pdx(p,ap+0x200)
    if h["size"]<=0 or not is_ptr(h["data"]) or h["size"]>64: return []
    raw=p.read(h["data"], h["size"]*4)
    return list(struct.unpack("<"+"I"*h["size"], raw))

def find_unit(p,co,uid):
    arr,_=ptr_array(p,co+0x290,4096)
    for ap in arr:
        if struct.unpack("<I", p.read(ap+0x1C,4))[0]==uid:
            return ap
    return 0

def snap_group(p,pe,gp):
    rec={"ptr":hex(gp),"class":cls(p,pe,gp)}
    if not is_ptr(gp): return rec
    rec["handle"]=list(struct.unpack("<II", p.read(gp+8,8)))
    rec["name"]=msvc_string(p, gp+0x160)
    rec["fm_flag_39"]=p.read(gp+0x39,1)[0]
    mems,mh=ptr_array(p,gp+0x50,256)
    rec["members_n"]=mh["size"]
    rec["member_ids"]=[]
    for mp in mems:
        primary=mp-0xB8
        if is_ptr(primary) and cls(p,pe,primary)==".?AVCArmy@@":
            rec["member_ids"].append(struct.unpack("<I", p.read(primary+0x1C,4))[0])
    leader=struct.unpack("<Q", p.read(gp+0x88,8))[0]
    rec["leader_ptr"]=hex(leader)
    rec["leader_class"]=cls(p,pe,leader)
    if is_ptr(leader):
        rec["leader_handle"]=list(struct.unpack("<II", p.read(leader+8,8)))
    rec["order_instance_n"]=pdx(p,gp+0x98)[ "size" ]
    # CArmyGroup extra
    children,ch=ptr_array(p,gp+0x230,256)
    rec["child_orders_hdr"]={k:(hex(v) if k=="data" else v) for k,v in ch.items()}
    rec["child_orders"]=[]
    for cp in children:
        rec["child_orders"].append({
            "ptr":hex(cp),"class":cls(p,pe,cp),
            "handle": list(struct.unpack("<II", p.read(cp+8,8))) if is_ptr(cp) else None,
            "name": msvc_string(p, cp+0x160) if is_ptr(cp) and cls(p,pe,cp) else None,
        })
    rec["collapse_248"]=p.read(gp+0x248,1)[0] if True else None
    return rec

def snap_theatre(p,pe,co):
    theatres,th=ptr_array(p,co+0x168,64)
    out=[]
    for tp in theatres:
        rec={"ptr":hex(tp),"class":cls(p,pe,tp),
             "handle":list(struct.unpack("<II", p.read(tp+8,8))) if is_ptr(tp) else None}
        if not is_ptr(tp):
            out.append(rec); continue
        # dump raw headers for 0x50,0x68,0x80,0x98,0xc8
        for name,off in (("fronts",0x50),("units",0x68),("orders_group",0x80),("field_marshal",0x98),("theater_group",0xC8)):
            arr,h=ptr_array(p,tp+off,4096 if name=="units" else 256)
            rec[name]={"hdr":{k:(hex(v) if k=="data" else v) for k,v in h.items()},
                       "n":len(arr),
                       "items":[snap_group(p,pe,x) if name!="units" and name!="fronts" else {
                           "ptr":hex(x),"class":cls(p,pe,x),
                           "handle": list(struct.unpack("<II", p.read(x+8,8))) if is_ptr(x) else None,
                           "id_1c": struct.unpack("<I", p.read(x+0x1C,4))[0] if name=="units" and is_ptr(x) else None,
                       } for x in arr]}
        out.append(rec)
    return out

def factory_make(pid,b,factory,expect_vt):
    made=mo._remote(pid, b.image_base+factory, wait_ms=5000)
    cmd=made.get("rax") or 0
    if made.get("wait")!=0 or cmd<0x10000:
        return {"ok":False,"result":"FACTORY_FAIL","call":made}
    vt=mo._u64(b,cmd)-b.image_base
    if vt!=expect_vt:
        return {"ok":False,"result":"FACTORY_VT_MISMATCH","vt":hex(vt),"expect":hex(expect_vt),"cmd":hex(cmd)}
    return {"ok":True,"cmd":cmd,"vt":hex(vt)}

def main():
    result={"authorized_by":["pt180u"],"stay_paused":True,"never_5x":True}
    p=None
    try:
        process_pid=mem_find_pid("hoi4.exe")
        result["health_before"]=process_health(process_pid)
        if process_pid!=EXPECTED_PID or not result["health_before"].get("alive"):
            result.update({"ok":False,"error":"PID_OR_HEALTH"}); 
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False,default=str)); return
        p=Proc(process_pid); pe=PE(EXE)
        session=detect_session(p,pe)
        gs=int(session["signals"]["gs_ptr"],16)
        co=int(resolve_player_country(p,gs)["country_ptr"],16)
        summary=read_campaign_summary(p,gs)
        ver=summary.get("verified") or {}
        date=ver.get("date_full") or ver.get("date") or {}
        idler=int(session["signals"].get("idler_ptr") or "0",16)
        pause=p.read(idler+0x6C1,1)[0]
        speed=struct.unpack("<i", p.read(gs+0x4BC,4))[0]
        result["session"]={"pid":process_pid,"gs":hex(gs),"co":hex(co),"date":date,"pause":pause,"speed":speed,
                           "ok": gs==EXPECTED_GS and co==EXPECTED_CO and pause==1 and speed==0
                           and isinstance(date,dict) and date.get("ui")=="1936-01-01" and date.get("ui_hour")==12}
        if not result["session"]["ok"] or not session.get("in_game"):
            result.update({"ok":False,"error":"SESSION_GUARD_FAIL"})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False,default=str)); return
        u1829=find_unit(p,co,1829)
        result["keep_path_before"]=unit_path(p,u1829)
        if result["keep_path_before"]!=KEEP_PATH:
            result.update({"ok":False,"error":"KEEP_PATH_CHANGED"})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False,default=str)); return
        result["theatre_before"]=snap_theatre(p,pe,co)
        tb=result["theatre_before"][0]
        # compact print of unexpected arrays
        result["array_summary_before"]={k:{"n":tb[k]["n"],"classes":[i.get("class") for i in tb[k]["items"][:5]],
                                           "handles":[i.get("handle") for i in tb[k]["items"][:5]]}
                                        for k in ("fronts","orders_group","field_marshal","theater_group")}
        # require army 1 still present, fm empty
        ogs=tb["orders_group"]["items"]
        if not ogs or ogs[0].get("handle")!=[53,1] or ogs[0].get("name")!="第1集团军":
            result.update({"ok":False,"error":"ARMY1_MISSING"}); 
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False,default=str)); return
        if tb["field_marshal"]["n"]!=0:
            result.update({"ok":False,"error":"FM_ALREADY_PRESENT"})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False,default=str)); return
        # record theater_group whatever it is; do not fail only because n==1 — inspect and proceed if not a CArmyGroup already
        result["theater_group_before"]=tb["theater_group"]

        b=Backend()
        made=factory_make(process_pid,b,AG["factory"],AG["vt"])
        result["ag_factory"]={k:v for k,v in made.items()}
        if not made.get("ok"):
            result.update({"ok":False,"error":"AG_FACTORY_FAIL"})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False,default=str)); return
        cmd=made["cmd"]
        buf=mo._game_malloc(process_pid, 16)
        mo._write(process_pid, buf, struct.pack("<II", ARMY[0], ARMY[1]))
        # +0x28 theatre handle; +0x30 vector of one orders_group handle; rest stay 0 from factory
        mo._write(process_pid, cmd+0x28, struct.pack("<II", THEATRE[0], THEATRE[1]))
        mo._write(process_pid, cmd+0x30, struct.pack("<QII", buf, 1, 1))
        raw=p.read(cmd, AG["size"])
        result["ag_packed"]={
            "cmd":hex(cmd),"buf":hex(buf),
            "theatre":list(struct.unpack_from("<II", raw, 0x28)),
            "vec":list(struct.unpack_from("<QII", raw, 0x30)),
            "arr48_size": struct.unpack_from("<I", raw, 0x54)[0],
            "h60": list(struct.unpack_from("<II", raw, 0x60)),
        }
        valid=mo._remote(process_pid, b.image_base+AG["isvalid"], {"rcx":cmd}, wait_ms=5000)
        isvalid=valid["rax"]&0xFF if valid.get("wait")==0 else None
        result["ag_dry_isvalid"]={"wait":valid.get("wait"),"rax":valid.get("rax"),"isvalid":isvalid}
        print("DRY", json.dumps(result["ag_dry_isvalid"]), "packed", result["ag_packed"], "arrays", result["array_summary_before"])
        if valid.get("wait")!=0 or isvalid!=1:
            result.update({"ok":False,"error":"AG_ISVALID_FALSE"})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps({k:result[k] for k in result if k!="theatre_before"}, indent=2, ensure_ascii=False, default=str))
            return
        if p.read(idler+0x6C1,1)[0]!=1 or struct.unpack("<i", p.read(gs+0x4BC,4))[0]!=0:
            result.update({"ok":False,"error":"PAUSE_OR_SPEED_CHANGED"})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False,default=str)); return

        open_gates()
        result["allow_post_at_post"]=allow_post()
        if not allow_post():
            result.update({"ok":False,"error":"ALLOW_POST_STILL_FALSE"})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False,default=str)); return
        sess=mo._u64(b, b.image_base+post_abi.G_SESSION)
        posted=mo._remote(process_pid, b.image_base+post_abi.FN_CMD_QUEUE_POST, {"rcx":sess,"rdx":cmd,"r8":1}, wait_ms=8000)
        result["ag_post"]={"wait":posted.get("wait"),"rax":posted.get("rax"),"post_rax":(posted.get("rax") or 0)&0xFF,
                           "elapsed_ms":posted.get("elapsed_ms"),"stub_freed":posted.get("stub_freed")}
        time.sleep(0.5)
        result["health_after_ag"]=process_health(EXPECTED_PID)
        result["theatre_after_ag"]=snap_theatre(p,pe,co)
        result["keep_path_after_ag"]=unit_path(p,u1829)
        ta=result["theatre_after_ag"][0]
        result["array_summary_after_ag"]={k:{"n":ta[k]["n"],"classes":[i.get("class") for i in ta[k]["items"]],
                                             "handles":[i.get("handle") for i in ta[k]["items"]],
                                             "names":[i.get("name") for i in ta[k]["items"] if "name" in i]}
                                          for k in ("orders_group","field_marshal","theater_group")}
        result["ag_created"]=ta["field_marshal"]["n"]>0 and any(i.get("class")==".?AVCArmyGroup@@" for i in ta["field_marshal"]["items"])
        result["new_army_groups"]=ta["field_marshal"]["items"]
        # also check if it landed in theater_group or orders_group
        result["maybe_elsewhere"]={
            "orders_group": ta["orders_group"]["items"],
            "theater_group": ta["theater_group"]["items"],
        }

        result["leader_attempted"]=False
        if result["ag_created"] and result["health_after_ag"].get("alive") and result["keep_path_after_ag"]==KEEP_PATH:
            ag=next(i for i in ta["field_marshal"]["items"] if i.get("class")==".?AVCArmyGroup@@")
            gtype,gid=ag["handle"]
            # pick first unassigned leader != 312. We'll read +0x1048
            cc=struct.unpack("<Q", p.read(co+0xFF0,8))[0]
            leaders,_=ptr_array(p, cc+0x70, 512)
            chosen=None
            for lp in leaders:
                hid=struct.unpack("<I", p.read(lp+0xC,4))[0]
                typ,aid=struct.unpack("<II", p.read(lp+0x1048,8))
                htype=struct.unpack("<I", p.read(lp+8,4))[0]
                if hid!=312 and typ==0 and aid==0:
                    chosen={"ptr":hex(lp),"handle":[htype,hid],"name_key":msvc_string(p, lp+0x20)}
                    break
            result["chosen_ag_leader"]=chosen
            if chosen and gtype and gid:
                result["leader_attempted"]=True
                made2=factory_make(process_pid,b,SL["factory"],SL["vt"])
                result["sl_factory"]={k:v for k,v in made2.items()}
                if made2.get("ok"):
                    cmd2=made2["cmd"]
                    mo._write(process_pid, cmd2+0x28, struct.pack("<II", *chosen["handle"]))
                    mo._write(process_pid, cmd2+0x30, struct.pack("<II", int(gtype), int(gid)))
                    mo._write(process_pid, cmd2+0x38, struct.pack("<I", 0))
                    raw2=p.read(cmd2, SL["size"])
                    result["sl_packed"]={"cmd":hex(cmd2),
                                         "leader":list(struct.unpack_from("<II", raw2, 0x28)),
                                         "group":list(struct.unpack_from("<II", raw2, 0x30)),
                                         "deploy_hq":struct.unpack_from("<I", raw2, 0x38)[0]}
                    valid2=mo._remote(process_pid, b.image_base+SL["isvalid"], {"rcx":cmd2}, wait_ms=5000)
                    isvalid2=valid2["rax"]&0xFF if valid2.get("wait")==0 else None
                    result["sl_dry_isvalid"]={"wait":valid2.get("wait"),"rax":valid2.get("rax"),"isvalid":isvalid2}
                    if isvalid2==1 and p.read(idler+0x6C1,1)[0]==1:
                        posted2=mo._remote(process_pid, b.image_base+post_abi.FN_CMD_QUEUE_POST,
                                           {"rcx":sess,"rdx":cmd2,"r8":1}, wait_ms=8000)
                        result["sl_post"]={"wait":posted2.get("wait"),"rax":posted2.get("rax"),
                                           "post_rax":(posted2.get("rax") or 0)&0xFF}
                        time.sleep(0.5)
                    else:
                        result["sl_post"]={"skipped":True,"reason":"ISVALID_FALSE_OR_UNPAUSED"}

        result["health_after"]=process_health(EXPECTED_PID)
        result["theatre_final"]=snap_theatre(p,pe,co)
        result["keep_path_final"]=unit_path(p, find_unit(p,co,1829) or u1829)
        result["still_paused"]=p.read(idler+0x6C1,1)[0]==1
        result["speed_after"]=struct.unpack("<i", p.read(gs+0x4BC,4))[0]
        tf=result["theatre_final"][0]
        result["array_summary_final"]={k:{"n":tf[k]["n"],"items":tf[k]["items"]} for k in ("orders_group","field_marshal","theater_group")}
        result["ok"]=bool(result["health_after"].get("alive") and result.get("ag_created")
                          and result["keep_path_final"]==KEEP_PATH and result["still_paused"] and result["speed_after"]==0)
        result["result"]="ARMY_GROUP_CREATED" if result.get("ag_created") else "POSTED_BUT_NO_ARMY_GROUP"
        OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
        print(json.dumps({
            "ok":result["ok"],"result":result.get("result"),
            "ag_dry_isvalid":result.get("ag_dry_isvalid"),"ag_post":result.get("ag_post"),
            "array_summary_before":result.get("array_summary_before"),
            "array_summary_after_ag":result.get("array_summary_after_ag"),
            "new_army_groups":result.get("array_summary_final",{}).get("field_marshal"),
            "orders_final":result.get("array_summary_final",{}).get("orders_group"),
            "theater_group_final":result.get("array_summary_final",{}).get("theater_group"),
            "leader_attempted":result.get("leader_attempted"),
            "chosen_ag_leader":result.get("chosen_ag_leader"),
            "sl_dry_isvalid":result.get("sl_dry_isvalid"),"sl_post":result.get("sl_post"),
            "keep_path_final":result.get("keep_path_final"),
            "still_paused":result.get("still_paused"),"speed_after":result.get("speed_after"),
            "health_after":result.get("health_after"),
        }, indent=2, ensure_ascii=False, default=str))
    except Exception as e:
        result["ok"]=False; result["error"]="EXCEPTION"; result["exception"]=f"{type(e).__name__}: {e}"
        result["traceback"]=traceback.format_exc()
        OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
        print(json.dumps({k:result[k] for k in result if k!="traceback"}, indent=2, ensure_ascii=False, default=str))
        print(result["traceback"])
    finally:
        close_gates()
        try:
            data=json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else result
            data["gate_closed"]={"allow_post_after_close":allow_post(),"marker_exists":MARKER.exists()}
            OUT.write_text(json.dumps(data,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print("GATE_CLOSED", json.dumps(data["gate_closed"]))
        except Exception as e:
            print("GATE_CLOSE_STATUS_WRITE_FAIL", e)
        if p is not None:
            try: p.close()
            except Exception: pass

if __name__=="__main__":
    main()
