import json,struct,sys,collections
from pathlib import Path
sys.path.insert(0,'calling')
from process import find_pid
from mem import Proc
from pe import PE
from gamestate import _pdx_array, probe_player_armies, _rtti_name_from_vtable
import offsets as O, ctypes
pid=find_pid('hoi4.exe'); p=Proc(pid); base=p.base
k32=ctypes.WinDLL('kernel32'); psapi=ctypes.WinDLL('psapi')
h=k32.OpenProcess(0x0410,False,pid); buf=ctypes.create_unicode_buffer(512)
psapi.GetModuleFileNameExW(h,None,buf,512); k32.CloseHandle(h)
pe=PE(buf.value)
ggs=O.WINDOWS_GLOBALS['G_GAMESTATE']; gs=struct.unpack('<Q',p.try_read(base+ggs,8))[0]
probe=probe_player_armies(p,pe,gs)
c=int(probe['country_ptr'],16)

def u64(a):
    d=p.try_read(a,8); return struct.unpack('<Q',d)[0] if d and len(d)==8 else None
def u32(a):
    d=p.try_read(a,4); return struct.unpack('<I',d)[0] if d and len(d)==4 else None
def i32(a):
    d=p.try_read(a,4); return struct.unpack('<i',d)[0] if d and len(d)==4 else None
def rtti(a):
    vt=u64(a)
    if not vt or vt<base: return None
    return _rtti_name_from_vtable(pe, vt-base)
def ptrs(addr, lim=512):
    a=_pdx_array(p,addr)
    if not a or a['size']<=0: return a,[]
    if not (0 < a['size'] <= a['capacity'] <= 100000): return None,[]
    blob=p.try_read(a['data'], min(a['size'], lim)*8) or b''
    return a,[struct.unpack_from('<Q',blob,i)[0] for i in range(0,len(blob)-7,8)]

_,armies=ptrs(c+0x290)
_,theatres=ptrs(c+0x168); th=theatres[0]
_,fronts=ptrs(th+0x50)
_,cas=ptrs(c+0x548)
_,oas=ptrs(c+0x560)
_,th_cas=ptrs(th+0x18)
hai_ctrls=[u64(fp+0x70) for fp in fronts]
army_provs={u64(a+0x1f0):a for a in armies if u64(a+0x1f0)}
front_ids={fp:u32(fp+0xc) for fp in fronts}

# --- army -> which CO_CA / CO_OA / TH_CA index ---
def area_indices(aprov, areas, off=0x30):
    hits=[]
    for i,area in enumerate(areas):
        _,ps=ptrs(area+off, lim=512)
        if aprov in set(ps): hits.append(i)
    return hits

army_geo=[]
for a in armies:
    aprov=u64(a+0x1f0)
    row={
        'army':hex(a),'prov_id':u32(a+0x28),
        'ca30':area_indices(aprov,cas,0x30),
        'oa30':area_indices(aprov,oas,0x30),
        'th_ca30':area_indices(aprov,th_cas,0x30),
        'front_ca30':[],
    }
    for i,ctrl in enumerate(hai_ctrls):
        _,ps=ptrs(ctrl+0x30, lim=512)
        if aprov in set(ps): row['front_ca30'].append(i)
    army_geo.append(row)
ca_cov=sum(1 for r in army_geo if r['ca30'])
oa_cov=sum(1 for r in army_geo if r['oa30'])
th_cov=sum(1 for r in army_geo if r['th_ca30'])
fc_cov=sum(1 for r in army_geo if r['front_ca30'])
print('ARMY_GEO ca',ca_cov,'oa',oa_cov,'th_ca',th_cov,'front_ca',fc_cov,'/',len(armies))
print('ca_idx_hist',collections.Counter(tuple(r['ca30']) for r in army_geo))
print('sample',json.dumps(army_geo[:4],indent=2))

# --- FS heap reverse again + SPer structure across all HAI FS ---
# reuse known FS from 2dg mine + find any missing
mine=json.loads(Path('reports/_2dg_mine_raw.json').read_text(encoding='utf-8'))
fs_sample=[int(x['fs'],16) for x in (mine.get('fs_heap_reverse') or {}).get('sample') or []]
# also scan from live_re field if present
fs_addrs=list(dict.fromkeys(fs_sample))

# Full-heap quick: for each front find FS (reuse VirtualQuery)
MEM_COMMIT=0x1000
class MBI(ctypes.Structure):
    _fields_=[('BaseAddress',ctypes.c_uint64),('AllocationBase',ctypes.c_uint64),
              ('AllocationProtect',ctypes.c_uint32),('pad1',ctypes.c_uint32),
              ('RegionSize',ctypes.c_uint64),('State',ctypes.c_uint32),('Protect',ctypes.c_uint32),
              ('Type',ctypes.c_uint32),('pad2',ctypes.c_uint32)]
OpenProcess=k32.OpenProcess; OpenProcess.restype=ctypes.c_void_p
hproc=OpenProcess(0x0410,False,pid)
VirtualQueryEx=k32.VirtualQueryEx
VirtualQueryEx.argtypes=[ctypes.c_void_p,ctypes.c_uint64,ctypes.POINTER(MBI),ctypes.c_size_t]
VirtualQueryEx.restype=ctypes.c_size_t
addr=0; regions=[]
while addr < 0x7FFFFFFFFFFF:
    mbi=MBI(); got=VirtualQueryEx(hproc,addr,ctypes.byref(mbi),ctypes.sizeof(mbi))
    if not got: break
    if mbi.State==MEM_COMMIT and 0x1000 <= mbi.RegionSize <= 0x2000000:
        prot=mbi.Protect & 0xFF
        if prot in (0x04,0x08,0x40,0x80,0x02):
            regions.append((mbi.BaseAddress, mbi.RegionSize))
    nxt=mbi.BaseAddress+mbi.RegionSize
    if nxt<=addr: break
    addr=nxt

fs_found=[]
front_set=set(fronts)
for base_a,size in regions:
    off=0
    while off+0x40 <= size and len(fs_found)<100:
        chunk_sz=min(0x100000, size-off)
        data=p.try_read(base_a+off, chunk_sz)
        if not data:
            off+=chunk_sz; continue
        for fp in fronts:
            needle=struct.pack('<Q', fp)
            start=0
            while True:
                idx=data.find(needle, start)
                if idx<0: break
                if idx>=0x10 and (idx-0x10)%8==0:
                    obj=base_a+off+(idx-0x10)
                    nm=rtti(obj)
                    if nm and 'CFrontSection' in nm:
                        fs_found.append(obj)
                start=idx+8
        off+=chunk_sz
        if len(fs_found)>=80: break
    if len(fs_found)>=80: break
fs_addrs=list(dict.fromkeys(fs_found + fs_addrs))
print('FS_FOUND',len(fs_found),'unique',len(fs_addrs))

# SPer structure across FS
sper_rows=[]
sper_vt=None
prov_inline_offs=collections.Counter()
for fs in fs_addrs:
    sper=u64(fs+0x18)
    if not sper: continue
    if sper_vt is None:
        sper_vt=u64(sper)
    blob=p.try_read(sper,0xA0) or b''
    emb_prov=[]; emb_army=[]; emb_front=[]; emb_fs=[]
    for off in range(8,len(blob)-7,8):
        q=struct.unpack_from('<Q',blob,off)[0]
        nm=rtti(q) if q and q>0x10000 else None
        if nm and 'CProvince' in nm:
            emb_prov.append(off); prov_inline_offs[off]+=1
        if q in set(armies): emb_army.append(off)
        if q in front_set: emb_front.append(off)
        if q==fs: emb_fs.append(off)
    # tag at +0x8?
    tag=u32(sper+0x8)
    # parent FS backref?
    parent_candidates=[]
    for off in (0x10,0x18,0x28,0x38,0x70):
        q=u64(sper+off)
        if q==fs: parent_candidates.append(hex(off))
    sper_rows.append({
        'fs':hex(fs),'fid':u32(u64(fs+0x10)+0xc) if u64(fs+0x10) else None,
        'sper':hex(sper),'tag8':tag,'emb_prov_offs':[hex(x) for x in emb_prov],
        'emb_army':emb_army,'emb_front':[hex(x) for x in emb_front],'emb_fs':emb_fs,
        'parent_back':parent_candidates,
        'n_prov_inline':len(emb_prov),
    })

print('SPER_VT',hex(sper_vt) if sper_vt else None, 'rva',hex(sper_vt-base) if sper_vt else None)
print('prov_inline_off_freq',dict(prov_inline_offs))
print('tag8_hist',collections.Counter(r['tag8'] for r in sper_rows))
print('parent_back_hist',collections.Counter(tuple(r['parent_back']) for r in sper_rows))
print('army_in_sper',sum(1 for r in sper_rows if r['emb_army']))
print('sper_sample',json.dumps(sper_rows[:4],indent=2))

# FS extra arrays beyond 0x30/0x48
fs_array_scan=collections.Counter()
fs_array_types={}
for fs in fs_addrs[:20]:
    for off in range(0,0x120,8):
        arr,ps=ptrs(fs+off, lim=64)
        if not arr or arr['size']<=0: continue
        if not (0 < arr['size'] <= arr['capacity'] <= 100000): continue
        ty=collections.Counter()
        for q in ps[:16]:
            nm=rtti(q)
            if nm: ty[nm.split('@')[0].lstrip('.?AV').lstrip('.?AU')]+=1
        key=hex(off)
        fs_array_scan[key]+=1
        fs_array_types.setdefault(key, collections.Counter())
        for k,v in ty.items(): fs_array_types[key][k]+=v
print('FS_ARRAYS', {k: {'n':fs_array_scan[k],'ty':dict(fs_array_types[k])} for k in sorted(fs_array_scan, key=lambda x:int(x,16))})

# Theatre extra CPdxArrays not yet mapped
th_extra=[]
known={0x18,0x50,0x68}
for off in range(0,0x280,8):
    if off in known: continue
    arr,ps=ptrs(th+off, lim=32)
    if not arr or arr['size']<=0: continue
    if not (0 < arr['size'] <= arr['capacity'] <= 10000): continue
    ty=collections.Counter(rtti(q) or '?' for q in ps[:16] if q)
    if any(t and t!='?' for t in ty):
        th_extra.append({'off':hex(off),'size':arr['size'],'cap':arr['capacity'],'ty':dict(ty)})
print('TH_EXTRA',json.dumps(th_extra,indent=2)[:3000])

# Country arrays sample for any unmapped land-relevant
co_extra=[]
known_co={0x168,0x1b8,0x278,0x290,0x460,0x478,0x548,0x560,0x5d0}
for off in range(0x100,0x600,8):
    if off in known_co: continue
    arr,ps=ptrs(c+off, lim=32)
    if not arr or arr['size']<=0: continue
    if not (0 < arr['size'] <= arr['capacity'] <= 10000): continue
    ty=collections.Counter(rtti(q) or '?' for q in ps[:16] if q)
    landish=any(x and any(s in x for s in ('Army','Front','Theatre','Order','Command','Province','Controller','Owner','Division')) for x in ty)
    if landish or (arr['size']<=64 and any(t!='?' for t in ty)):
        co_extra.append({'off':hex(off),'size':arr['size'],'ty':dict(ty),'landish':landish})
print('CO_EXTRA_LAND',json.dumps([x for x in co_extra if x['landish']],indent=2)[:2500])

# Peer: shared CA index?
shared_ca=0; n_peer=0
for a in armies:
    req=u64(a+0x478)
    if not req: continue
    peer=u64(req+0x108)
    if not peer: continue
    n_peer+=1
    aprov=u64(a+0x1f0); pprov=u64(peer+0x1f0)
    a_idx=set(area_indices(aprov,cas)); p_idx=set(area_indices(pprov,cas))
    if a_idx & p_idx: shared_ca+=1
print('PEER_CA_SHARE',n_peer,shared_ca)

out={
 'phase':'2dh_mine','allow_post':False,'posting':'DISABLED','pid':pid,
 'army_geo':{'ca_cov':ca_cov,'oa_cov':oa_cov,'th_ca_cov':th_cov,'front_ca_cov':fc_cov,'n':len(armies),
             'ca_idx_hist':{str(k):v for k,v in collections.Counter(tuple(r['ca30']) for r in army_geo).items()},
             'sample':army_geo[:6]},
 'fs_found':len(fs_found),'fs_unique':len(fs_addrs),
 'sper':{'vt_rva':hex(sper_vt-base) if sper_vt else None,
         'prov_inline_off_freq':{hex(k):v for k,v in prov_inline_offs.items()},
         'tag8_hist':{str(k):v for k,v in collections.Counter(r['tag8'] for r in sper_rows).items()},
         'army_embeds':sum(1 for r in sper_rows if r['emb_army']),
         'n':len(sper_rows),'sample':sper_rows[:8]},
 'fs_arrays':{k: {'n':fs_array_scan[k],'ty':dict(fs_array_types[k])} for k in sorted(fs_array_scan, key=lambda x:int(x,16))},
 'th_extra':th_extra,'co_extra_land':[x for x in co_extra if x['landish']],
 'peer_ca_share':{'n':n_peer,'shared':shared_ca},
}
Path('reports/_2dh_mine_raw.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('WROTE mine')
