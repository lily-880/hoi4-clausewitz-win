import json,struct,sys
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

_,theatres=ptrs(c+0x168); th=theatres[0]
_,fronts=ptrs(th+0x50)
_,armies=ptrs(c+0x290)
_,cas=ptrs(c+0x548)

m2=json.loads(Path('reports/_2dg_mine_raw.json').read_text(encoding='utf-8'))
fs_addrs=list(dict.fromkeys(int(x['fs'],16) for x in m2['fs_heap_reverse']['sample']))

rows=[]
match30=0; match48=0
front_fs48_inter=[]
hai_ctrls={u32(fp+0xc):u64(fp+0x70) for fp in fronts}
for fs in fs_addrs:
    fid=u32(u64(fs+0x10)+0xc)
    sper=u64(fs+0x18)
    a30,_=ptrs(fs+0x30); a48,_=ptrs(fs+0x48)
    s10=u32(sper+0x10); s8=u32(sper+0x8)
    m30 = (a30 and s10==a30['size']); m48=(a48 and s10==a48['size'])
    if m30: match30+=1
    if m48: match48+=1
    # FS48 vs front ctrl
    ctrl=hai_ctrls.get(fid)
    inter=0; csz=0; fsz=0
    if ctrl and a48:
        _,cps=ptrs(ctrl+0x30,lim=512); _,fps=ptrs(fs+0x48,lim=256)
        inter=len(set(cps)&set(fps)); csz=len(cps); fsz=len(fps)
        front_fs48_inter.append({'fid':fid,'inter':inter,'fs48':fsz,'ctrl30':csz,'frac':inter/fsz if fsz else 0})
    # any army in this FS's provinces?
    aprovs={u64(a+0x1f0) for a in armies}
    _,p30=ptrs(fs+0x30); _,p48=ptrs(fs+0x48)
    rows.append({
        'fid':fid,'tag8':s8,'sper10':s10,
        'fs30':a30['size'] if a30 else None,'fs48':a48['size'] if a48 else None,
        'match30':m30,'match48':m48,
        'army_in_30':len(set(p30)&aprovs) if p30 else 0,
        'army_in_48':len(set(p48)&aprovs) if p48 else 0,
    })
print(json.dumps(rows,indent=2))
print('match30',match30,'/',len(fs_addrs),'match48',match48)
print('front_fs48',json.dumps(front_fs48_inter,indent=2))
print('fs48_with_inter',sum(1 for x in front_fs48_inter if x['inter']>0),'/',len(front_fs48_inter))

# army CA membership summary for sidecar
def area_idx(aprov, areas):
    hits=[]
    for i,area in enumerate(areas):
        _,ps=ptrs(area+0x30,lim=512)
        if aprov in set(ps): hits.append(i)
    return hits
geo=[]
for a in armies:
    aprov=u64(a+0x1f0)
    geo.append({'army':hex(a),'ca':area_idx(aprov,cas),'prov_id':u32(a+0x28)})
print('geo',geo)

# Check CArmy* in SPer - are they HAI armies?
for fs in fs_addrs:
    sper=u64(fs+0x18)
    blob=p.try_read(sper,0x80) or b''
    for off in range(8,len(blob)-7,8):
        q=struct.unpack_from('<Q',blob,off)[0]
        if q in set(armies):
            print('HAI_ARMY_IN_SPER',hex(fs), 'fid',u32(u64(fs+0x10)+0xc), 'off',hex(off), hex(q))
        nm=rtti(q) if q>0x10000 else None
        if nm and 'CArmy' in nm and q not in set(armies):
            print('OTHER_ARMY_IN_SPER',hex(fs),'off',hex(off),hex(q),'tag',u32(q+0x1e0) if u32(q+0x1e0) is not None else None)
