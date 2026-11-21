from __future__ import annotations
import json, os, struct, sys, time, traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
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

EXE=r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
MARKER=ROOT/"research"/"safe_land_tool_gate.OPEN"
LEGACY=ROOT/"research"/"strategic_only_tool_gate.OPEN"
OUT=ROOT/"research"/"t193_plan_post.json"

EXPECTED_PID=26976
EXPECTED_GS=0x26C259D0FF0
EXPECTED_CO=0x26C4B672530
KEEP_PATH=[8036]
ARMY=(53,1)
PROV_A, PROV_B = 13237, 13238

NR={"factory":0x18D0440,"vt":0x2A856A0,"isvalid":0x18DF5E0,"execute":0x18D9A30,"size":0x70}

def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF

def open_gates():
    os.environ["CLAUSEWITZ_ALLOW_POST"]="1"
    MARKER.write_text("t193 one-shot COrderNewRootCommand authorized by pt180u.\nPause/1x only. Close after.\n", encoding="utf-8")
    if LEGACY.exists(): LEGACY.unlink()

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
    if not h: return {"alive":False}
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
    return data,cap,size

def ptr_array(p,a,bound=4096):
    data,cap,size=pdx(p,a)
    if not 0<=size<=cap<=max(bound,100) or (size and not is_ptr(data)):
        return []
    return [struct.unpack("<Q", p.read(data+8*j,8))[0] for j in range(size)]

def cls(p,pe,a):
    if not is_ptr(a): return None
    try:
        vt=struct.unpack("<Q", p.read(a,8))[0]
    except OSError:
        return None
    if not p.base<=vt<p.base+p.image_size: return None
    return _rtti_name_from_vtable(pe, vt-p.base)

def unit_path(p,ap):
    data,cap,size=pdx(p,ap+0x200)
    if size<=0 or not is_ptr(data) or size>64: return []
    return list(struct.unpack("<"+"I"*size, p.read(data,size*4)))

def find_unit(p,co,uid):
    for ap in ptr_array(p,co+0x290,4096):
        if struct.unpack("<I", p.read(ap+0x1C,4))[0]==uid:
            return ap
    return 0

def u32_array(p,a,bound=256):
    data,cap,size=pdx(p,a)
    if size<=0 or not is_ptr(data) or not 0<=size<=cap<=bound:
        return [], {"data":hex(data) if is_ptr(data) else data, "cap":cap, "size":size}
    raw=p.read(data, size*4)
    return list(struct.unpack("<"+"I"*size, raw)), {"data":hex(data),"cap":cap,"size":size}

def snap_instance(p,pe,ip):
    rec={"ptr":hex(ip),"class":cls(p,pe,ip)}
    if not is_ptr(ip): return rec
    rec["type_30"]=struct.unpack("<I", p.read(ip+0x30,4))[0]
    rec["instance_id_244"]=struct.unpack("<I", p.read(ip+0x244,4))[0]
    path,ph=u32_array(p, ip+0x70)
    rec["path_70"]=path; rec["path_hdr"]=ph
    states,sh=u32_array(p, ip+0xe0)
    rec["states_e0"]=states; rec["states_hdr"]=sh
    rec["range_268"]=struct.unpack("<Q", p.read(ip+0x268,8))[0]
    rec["range_270"]=struct.unpack("<Q", p.read(ip+0x270,8))[0]
    rec["field_258"]=hex(struct.unpack("<Q", p.read(ip+0x258,8))[0])
    rec["field_260"]=struct.unpack("<I", p.read(ip+0x260,4))[0]
    # common bool/status candidates
    rec["bytes_interesting"]={}
    for off in (0x118,0x119,0x39,0x200,0x210,0x220,0x230,0x240,0x248,0x24c,0x250):
        rec["bytes_interesting"][hex(off)]=list(p.read(ip+off, 8))
    return rec

def snap_group_plans(p,pe,gp):
    rec={"ptr":hex(gp),"class":cls(p,pe,gp),"handle":list(struct.unpack("<II", p.read(gp+8,8))),
         "name":msvc_string(p, gp+0x160)}
    insts=ptr_array(p, gp+0x98, 256)
    rec["order_instances"]=[snap_instance(p,pe,ip) for ip in insts]
    rec["parent_1b8"]=None
    parent=struct.unpack("<Q", p.read(gp+0x1B8,8))[0]
    rec["parent_1b8"]={"ptr":hex(parent),"class":cls(p,pe,parent),
                       "handle":list(struct.unpack("<II", p.read(parent+8,8))) if is_ptr(parent) else None}
    return rec

def main():
    result={"authorized_by":["pt180u"],"provinces":[PROV_A,PROV_B],"stay_paused":True}
    p=None
    try:
        process_pid=mem_find_pid("hoi4.exe")
        result["health_before"]=process_health(process_pid)
        if process_pid!=EXPECTED_PID or not result["health_before"].get("alive"):
            result.update({"ok":False,"error":"PID_OR_HEALTH"})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False)); return
        p=Proc(process_pid); pe=PE(EXE)
        session=detect_session(p,pe)
        gs=int(session["signals"]["gs_ptr"],16)
        co=int(resolve_player_country(p,gs)["country_ptr"],16)
        summary=read_campaign_summary(p,gs)
        date=(summary.get("verified") or {}).get("date_full") or (summary.get("verified") or {}).get("date") or {}
        idler=int(session["signals"].get("idler_ptr") or "0",16)
        pause=p.read(idler+0x6C1,1)[0]
        speed=struct.unpack("<i", p.read(gs+0x4BC,4))[0]
        result["session"]={"pid":process_pid,"gs":hex(gs),"co":hex(co),"date":date,"pause":pause,"speed":speed}
        if not (gs==EXPECTED_GS and co==EXPECTED_CO and pause==1 and speed==0
                and isinstance(date,dict) and date.get("ui")=="1936-01-01" and date.get("ui_hour")==12):
            result.update({"ok":False,"error":"SESSION_GUARD_FAIL"})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False)); return
        u1829=find_unit(p,co,1829)
        result["keep_path_before"]=unit_path(p,u1829)
        if result["keep_path_before"]!=KEEP_PATH:
            result.update({"ok":False,"error":"KEEP_PATH_CHANGED"})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False)); return
        theatres=ptr_array(p,co+0x168,64)
        tp=theatres[0]
        ogs=ptr_array(p,tp+0x80,256)
        fms=ptr_array(p,tp+0x98,256)
        result["army_before"]=snap_group_plans(p,pe,ogs[0])
        result["ag_before"]={"n":len(fms),"handle":list(struct.unpack("<II", p.read(fms[0]+8,8))) if fms else None,
                             "name":msvc_string(p,fms[0]+0x160) if fms else None,
                             "order_n": pdx(p,fms[0]+0x98)[2] if fms else None}
        if result["army_before"]["handle"]!=[53,1] or result["army_before"]["order_instances"]:
            result.update({"ok":False,"error":"ARMY_OR_PLANS_UNEXPECTED"})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False,default=str)); return

        b=Backend()
        made=mo._remote(process_pid, b.image_base+NR["factory"], wait_ms=5000)
        cmd=made.get("rax") or 0
        if made.get("wait")!=0 or cmd<0x10000:
            result.update({"ok":False,"error":"FACTORY_FAIL","factory":made})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False)); return
        vt=mo._u64(b,cmd)-b.image_base
        if vt!=NR["vt"]:
            result.update({"ok":False,"error":"FACTORY_VT_MISMATCH","vt":hex(vt)})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False)); return
        mo._write(process_pid, cmd+0x28, struct.pack("<II", *ARMY))
        mo._write(process_pid, cmd+0x48, struct.pack("<II", PROV_A, PROV_B))
        # leave +0x50/+0x58/+0x60/+0x6c at factory zero
        raw=p.read(cmd, NR["size"])
        result["nr_packed"]={
            "cmd":hex(cmd),"vt":hex(vt),
            "group":list(struct.unpack_from("<II", raw, 0x28)),
            "p48_4c":list(struct.unpack_from("<II", raw, 0x48)),
            "d50":struct.unpack_from("<I", raw, 0x50)[0],
            "q58":struct.unpack_from("<Q", raw, 0x58)[0],
            "q60":struct.unpack_from("<Q", raw, 0x60)[0],
            "b6c": raw[0x6c],
        }
        valid=mo._remote(process_pid, b.image_base+NR["isvalid"], {"rcx":cmd}, wait_ms=5000)
        isvalid=valid["rax"]&0xFF if valid.get("wait")==0 else None
        result["nr_dry_isvalid"]={"wait":valid.get("wait"),"rax":valid.get("rax"),"isvalid":isvalid}
        print("DRY", result["nr_dry_isvalid"], result["nr_packed"])
        if valid.get("wait")!=0 or isvalid!=1:
            result.update({"ok":False,"error":"NR_ISVALID_FALSE"})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False,default=str)); return
        if p.read(idler+0x6C1,1)[0]!=1 or struct.unpack("<i", p.read(gs+0x4BC,4))[0]!=0:
            result.update({"ok":False,"error":"PAUSE_OR_SPEED_CHANGED"})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False)); return

        open_gates()
        result["allow_post_at_post"]=allow_post()
        if not allow_post():
            result.update({"ok":False,"error":"ALLOW_POST_STILL_FALSE"})
            OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
            print(json.dumps(result,indent=2,ensure_ascii=False)); return
        sess=mo._u64(b, b.image_base+post_abi.G_SESSION)
        posted=mo._remote(process_pid, b.image_base+post_abi.FN_CMD_QUEUE_POST, {"rcx":sess,"rdx":cmd,"r8":1}, wait_ms=8000)
        result["nr_post"]={"wait":posted.get("wait"),"rax":posted.get("rax"),"post_rax":(posted.get("rax") or 0)&0xFF,
                           "elapsed_ms":posted.get("elapsed_ms"),"stub_freed":posted.get("stub_freed")}
        time.sleep(0.5)
        result["health_after"]=process_health(EXPECTED_PID)
        ogs=ptr_array(p,tp+0x80,256)
        fms=ptr_array(p,tp+0x98,256)
        result["army_after"]=snap_group_plans(p,pe,ogs[0])
        result["ag_after"]=snap_group_plans(p,pe,fms[0]) if fms else None
        result["keep_path_after"]=unit_path(p, find_unit(p,co,1829) or u1829)
        result["still_paused"]=p.read(idler+0x6C1,1)[0]==1
        result["speed_after"]=struct.unpack("<i", p.read(gs+0x4BC,4))[0]
        result["plan_created"]=bool(result["army_after"]["order_instances"])
        result["ok"]=bool(result["health_after"].get("alive") and result["plan_created"]
                          and result["keep_path_after"]==KEEP_PATH and result["still_paused"] and result["speed_after"]==0)
        result["result"]="PLAN_CREATED" if result["plan_created"] else "POSTED_BUT_NO_PLAN"
        OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
        print(json.dumps({
            "ok":result["ok"],"result":result["result"],
            "nr_dry_isvalid":result["nr_dry_isvalid"],"nr_post":result["nr_post"],
            "army_after":result["army_after"],
            "ag_after_instances": (result["ag_after"] or {}).get("order_instances"),
            "keep_path_after":result["keep_path_after"],
            "still_paused":result["still_paused"],"speed_after":result["speed_after"],
            "health_after":result["health_after"],
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
