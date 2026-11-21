import sys,os,re,json,struct,bisect,collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, tag_for_index, read_campaign_summary
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
IMAGE=pe.image_base
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
text=next(s for s in pe.sections if s.name==".text")
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
text_rva=text.virtual_address
pd=next(s for s in pe.sections if s.name==".pdata")
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

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
        if i.mnemonic=="ret" and i.address>start+8:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

for rva,tag in ((0x16c440,"gamedate_16c440"),(0x16c450,"gamedate_16c450"),(0x16c460,"gamedate_16c460"),(0x16c590,"gamedate_16c590"),(0x57ad40,"gamedate_57ad40"),(0x57a7b0,"gamedate_57a7b0"),(0x167b30,"gamedate_167b30")):
    lines=clip(rva, 0x80, f"research/_t186_clip_{tag}.txt")
    print(f"\n======= {hex(rva)} {tag} =====")
    print("\n".join(lines[:25]))

# 0x2e8 in diplomacy range d00000-e00000
print("\n===== +0x2e8 in 0xd00000-0xe00000 =====")
pat=re.compile(rb"[\x48\x4c][\x89\x8b\x8d][\x80-\xbf]\xe8\x02\x00\x00")
for m in pat.finditer(text_raw):
    rva=text_rva+m.start()
    if 0xd00000<=rva<0xe00000:
        fo=func_of(rva)
        ins=list(cs.disasm(text_raw[m.start():m.start()+16], rva))
        print(hex(rva), "func", hex(fo[0]) if fo else None, f"{ins[0].mnemonic} {ins[0].op_str}" if ins else "")

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
    def ptr(a):
        try: return p.ptr(a)
        except Exception: return None
    def i32(a):
        try: return p.i32(a)
        except Exception: return None

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    summary=read_campaign_summary(p, gs)
    cdata=summary["fields"]["countries"]["data"]
    csize=summary["fields"]["countries"]["size"]
    seen={}
    for ci in range(csize):
        co=ptr(cdata+ci*8)
        if not co: continue
        dip=ptr(co+0xf88)
        if not dip or cls(dip)!=".?AVCDiplomacyStatus@@":
            continue
        data=ptr(dip+8)
        size=i32(dip+0x14) or 0
        if not data or size<=0: continue
        # read all +0x2e8 pointers
        # optimize: read relation ptr array then each +0x2e8
        raw=p.try_read(data, size*8) or b""
        for i in range(size):
            rs=struct.unpack_from("<Q", raw, i*8)[0]
            if not (0x10000<rs<0x7fffffffffff):
                continue
            wp=ptr(rs+0x2e8)
            if not wp: continue
            if wp in seen: 
                seen[wp]["pairs"].append((ci, tag_for_index(ci), i, tag_for_index(i)))
                continue
            name=cls(wp)
            if name and "WarRelation" in name:
                seen[wp]={"ptr":hex(wp),"first":i32(wp+0x10),"first_tag":tag_for_index(i32(wp+0x10)),"second":i32(wp+0x14),"second_tag":tag_for_index(i32(wp+0x14)),"cancel": (p.try_read(wp+0x48,1) or b"\xff")[0],"pairs":[(ci, tag_for_index(ci), i, tag_for_index(i))]}
    print("\n===== unique world CWarRelation n=%d ====="%len(seen))
    for v in seen.values():
        print(json.dumps({k:v[k] for k in v if k!="pairs"}, default=str), "pairs", v["pairs"][:4], "npairs", len(v["pairs"]))
    Path("research/t186_world_warrelations.json").write_text(json.dumps({"n":len(seen),"wars":list(seen.values())}, indent=2)+"\n", encoding="utf-8")
finally:
    p.close()
