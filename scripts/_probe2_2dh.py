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
hai_ctrls=list({u64(fp+0x70) for fp in fronts})
front_by_id={u32(fp+0xc):fp for fp in fronts}

mine=json.loads(Path('reports/_2dh_mine_raw.json').read_text(encoding='utf-8'))
# re-get FS via heap from mine sper sample + scan
fs_addrs=[]
for row in (mine.get('sper') or {}).get('sample') or []:
    fs_addrs.append(int(row['fs'],16))
# also from 2dg
m2=json.loads(Path('reports/_2dg_mine_raw.json').read_text(encoding='utf-8'))
for x in (m2.get('fs_heap_reverse') or {}).get('sample') or []:
    fs_addrs.append(int(x['fs'],16))
fs_addrs=list(dict.fromkeys(fs_addrs))
print('fs',len(fs_addrs),[hex(x) for x in fs_addrs])

# Sort FS by address; check neighbor packing
fs_sorted=sorted(fs_addrs)
print('fs_deltas',[hex(fs_sorted[i+1]-fs_sorted[i]) for i in range(len(fs_sorted)-1)])

# For each FS: validate +0x30/+0x48 always; +0xa0/+0xb8 only when?
rows=[]
for fs in fs_addrs:
    fid=u32(u64(fs+0x10)+0xc) if u64(fs+0x10) else None
    row={'fs':hex(fs),'fid':fid,'arrays':{}}
    for off in (0x30,0x48,0xa0,0xb8,0x68,0x88):
        arr,ps=ptrs(fs+off, lim=256)
        if not arr: 
            row['arrays'][hex(off)]=None; continue
        ty=collections.Counter()
        ok=0
        for q in ps:
            nm=rtti(q)
            if nm and 'CProvince' in nm: ok+=1; ty['CProvince']+=1
            elif nm: ty[nm]+=1
            else: ty['?']+=1
        # neighbor FS at +0x90?
        neigh=rtti(fs+0x90)
        row['arrays'][hex(off)]={
            'size':arr['size'],'cap':arr['capacity'],
            'prov_ok':ok,'n':len(ps),'ty':dict(ty),
            'prov_frac': (ok/len(ps) if ps else 0),
        }
    row['rtti_at_plus90']=rtti(fs+0x90)
    row['obj_at_plus90_is_fs']= (rtti(fs+0x90) or '').find('CFrontSection')>=0
    rows.append(row)
print(json.dumps(rows,indent=2)[:5000])

# Front ctrl province sets vs FS province sets overlap
print('--- front_ca vs FS prov ---')
for i,ctrl in enumerate(hai_ctrls):
    # which front?
    fids=[]
    for fp in fronts:
        if u64(fp+0x70)==ctrl: fids.append(u32(fp+0xc))
    _,cps=ptrs(ctrl+0x30, lim=512)
    cset=set(cps)
    for fs in fs_addrs:
        fid=u32(u64(fs+0x10)+0xc) if u64(fs+0x10) else None
        if fid not in fids: continue
        for off in (0x30,0x48):
            _,fps=ptrs(fs+off, lim=256)
            inter=len(cset & set(fps))
            print(f'ctrl_fronts={fids} fs_id={fid} fs{hex(off)} inter={inter}/{len(fps)} ctrl_size={len(cps)}')

# CO_CA[i] sizes + strategic regions; classify which are "main"
print('--- CO_CA sizes ---')
for i,ca in enumerate(cas):
    a30,_=ptrs(ca+0x30,lim=512)
    a60,_=ptrs(ca+0x60,lim=512)
    ab0,_=ptrs(ca+0xb0,lim=512)
    af8,_=ptrs(ca+0xf8,lim=64)
    print(i, '30',a30['size'] if a30 else None, '60',a60['size'] if a60 else None,
          'b0',ab0['size'] if ab0 else None, 'f8',af8['size'] if af8 else None)

# SPer: dump all 8 as hex qword map + classify
print('--- SPer raw ---')
sper_meta=[]
for fs in fs_addrs:
    sper=u64(fs+0x18)
    blob=p.try_read(sper,0x80) or b''
    fields={}
    for off in range(0,0x80,8):
        q=struct.unpack_from('<Q',blob,off)[0]
        nm=rtti(q) if q>0x10000 else None
        fields[hex(off)]={'q':hex(q),'rtti':nm, 'u32_lo':q & 0xffffffff, 'u32_hi':(q>>32)&0xffffffff}
    # check if +0x20.. looks like province id range (prior hyp)
    tag=u32(sper+0x8)
    # inline count of consecutive CProvince*
    run=0; maxrun=0; start=None
    for off in range(0x20,0x80,8):
        nm=(fields[hex(off)].get('rtti') or '')
        if 'CProvince' in nm:
            if start is None: start=off
            run+=1; maxrun=max(maxrun,run)
        else:
            run=0; start=None
    sper_meta.append({'fs':hex(fs),'fid':u32(u64(fs+0x10)+0xc),'tag':tag,'max_prov_run':maxrun,
                      'fields_rtti':{k:v['rtti'] for k,v in fields.items() if v['rtti']},
                      'u32_8':tag,'u32_c':u32(sper+0xc),'u32_10':u32(sper+0x10),'u32_14':u32(sper+0x14),
                      'u32_20':u32(sper+0x20),'u32_24':u32(sper+0x24),'u32_28':u32(sper+0x28),'u32_2c':u32(sper+0x2c)})
print(json.dumps(sper_meta,indent=2)[:4000])

# Army CA membership: does peer share same CA index? already 6. Document index hist as proven locality.
# TH+0x198: dump types carefully - reject if mixed
arr,ps=ptrs(th+0x198, lim=16)
print('TH+0x198',arr)
for q in ps:
    print(' ',hex(q),rtti(q))

# Midflight counters RO
import offsets as Off
# session from prior midflight pattern if available
print('DONE probe2')
Path('reports/_2dh_probe2.json').write_text(json.dumps({
 'phase':'2dh','allow_post':False,
 'army_in_CO_CA': '17/17', 'army_in_front_CA': '0/17',
 'ca_idx_hist': mine['army_geo']['ca_idx_hist'],
 'fs_array_stable': ['0x30','0x48'],
 'fs_array_partial': rows,
 'front_ca_vs_fs': 'see stdout',
 'sper_tag8_hai_all': all(s['tag']==15 for s in sper_meta),
 'sper_inline_prov_stable': False,
 'th_198_mixed': True,
},indent=2),encoding='utf-8')
