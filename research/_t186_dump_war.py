import sys,os,re,json,struct,collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, tag_for_index
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

def clip(start, nbytes, path=None):
    raw=pe.read_rva(start, nbytes) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
        if m:
            tok=int(m.group(2),16)
            if tok in id2name:
                a += "  ; TOKEN "+id2name[tok]
        lines.append(a)
        if i.mnemonic=="ret" and i.address>start+16:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

# finish CRelationStatus writer
lines=clip(0xd8f5c0, 0x800, "research/_t186_clip_relationstatus_writer_0xd8f5c0.txt")
print("CRelationStatus writer n", len(lines), "last", lines[-1])
for ln in lines:
    if "TOKEN" in ln or "0x2e8" in ln or "war" in ln.lower():
        print(ln)

p=Proc(find_pid("hoi4.exe"))
try:
    def cls(a):
        if not a or a<0x10000 or a>0x7fffffffffff: return None
        try:
            vt=p.ptr(a)
        except Exception:
            return None
        if not vt or not (p.base<=vt<p.base+p.image_size): return None
        try:
            return _rtti_name_from_vtable(pe, vt-p.base)
        except Exception:
            return None

    def i32(a):
        try: return p.i32(a)
        except Exception: return None
    def u32(a):
        try: return p.u32(a)
        except Exception: return None
    def u64(a):
        try: return p.u64(a)
        except Exception: return None
    def ptr(a):
        try: return p.ptr(a)
        except Exception: return None
    def u8(a):
        b=p.try_read(a,1)
        return b[0] if b else None

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)
    dip=p.ptr(co+0xf88)
    data=p.ptr(dip+8)
    size=p.i32(dip+0x14)

    # scan ALL relation statuses for relation-subclass pointers
    # check offsets 0x200-0x3f8 for pointers with Relation in name
    slot_hits=collections.Counter()
    wars=[]
    other_special=[]
    for i in range(size):
        rs=ptr(data+i*8)
        if not rs: continue
        blob=p.try_read(rs, 0x400) or b""
        for off in range(0x1c0, len(blob)-7, 8):
            v=struct.unpack_from("<Q", blob, off)[0]
            if 0x10000<v<0x7fffffffffff:
                name=cls(v)
                if name and "Relation" in name:
                    slot_hits[(hex(off), name)] += 1
                    rec={"other_index":i,"other_tag":tag_for_index(i),"rs":hex(rs),"off":hex(off),"ptr":hex(v),"cls":name}
                    if "WarRelation" in name:
                        wars.append(rec)
                    else:
                        other_special.append(rec)

    print("slot hits", dict(slot_hits))
    print("n war pointers from ETH status rows", len(wars))
    print("wars", json.dumps(wars, indent=2))
    print("other relation ptrs n", len(other_special), "sample", other_special[:8])

    def dump_war(wp, label):
        d={
            "label":label,
            "ptr":hex(wp),
            "cls":cls(wp),
            "vt_rva":hex(p.ptr(wp)-p.base) if p.ptr(wp) and p.base<=p.ptr(wp)<p.base+p.image_size else None,
            "first_10": i32(wp+0x10),
            "first_tag": tag_for_index(i32(wp+0x10)) if i32(wp+0x10) is not None else None,
            "second_14": i32(wp+0x14),
            "second_tag": tag_for_index(i32(wp+0x14)) if i32(wp+0x14) is not None else None,
            "cancel_48": u8(wp+0x48),
            "d20": i32(wp+0x20), "d24": i32(wp+0x24),
            "start_date_obj_28": {
                "q": hex(u64(wp+0x28) or 0),
                "d0": i32(wp+0x28), "d4": i32(wp+0x2c),
                "d8": i32(wp+0x30), "d12": i32(wp+0x34),
                "cls": cls(wp+0x28),
                "ptr_cls": cls(u64(wp+0x28) or 0),
            },
            "d38": i32(wp+0x38),
            "end_date_gate_38_vs_20": (i32(wp+0x38), i32(wp+0x20), (i32(wp+0x38) or 0) > (i32(wp+0x20) or 0)),
            "end_date_obj_40": {"q":hex(u64(wp+0x40) or 0),"d0":i32(wp+0x40),"d4":i32(wp+0x44),"cls":cls(wp+0x40),"ptr_cls":cls(u64(wp+0x40) or 0)},
            "first_was_instigator_158": u8(wp+0x158),
            "hostility_defender_15c": i32(wp+0x15c),
            "hostility_instigator_160": i32(wp+0x160),
            "threat_150": u64(wp+0x150),
        }
        print(json.dumps(d, indent=2))
        return d

    war_dumps=[]
    for w in wars:
        war_dumps.append(dump_war(int(w["ptr"],16), f"ETH rel[{w['other_index']} {w['other_tag']}] {w['off']}"))

    # ITA country diplomacy -> ETH war pointer symmetry
    # get countries array
    from gamestate import read_campaign_summary
    summary=read_campaign_summary(p, gs)
    # countries data from summary
    cdata=summary["fields"]["countries"]["data"]
    ita_co=p.ptr(cdata+16*8)
    print("ITA country", hex(ita_co), cls(ita_co))
    ita_dip=ptr(ita_co+0xf88)
    print("ITA dip", hex(ita_dip) if ita_dip else None, cls(ita_dip) if ita_dip else None)
    if ita_dip:
        idata=ptr(ita_dip+8)
        isize=i32(ita_dip+0x14)
        print("ITA rel size", isize)
        if idata and 44<isize:
            irs=ptr(idata+44*8)
            print("ITA->ETH RS", hex(irs) if irs else None, cls(irs) if irs else None)
            if irs:
                wptr=ptr(irs+0x2e8)
                print("ITA->ETH +0x2e8", hex(wptr) if wptr else None, cls(wptr) if wptr else None)
                if wptr and cls(wptr) and "WarRelation" in cls(wptr):
                    war_dumps.append(dump_war(wptr, "ITA->ETH +0x2e8"))

    Path("research/t186_live_warrelation.json").write_text(json.dumps({
        "eth_dip":hex(dip),
        "slot_hits":{str(k):v for k,v in slot_hits.items()},
        "wars_from_eth":wars,
        "other_special_n":len(other_special),
        "war_dumps":war_dumps,
    }, indent=2)+"\n", encoding="utf-8")
finally:
    p.close()
