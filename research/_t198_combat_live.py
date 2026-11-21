import sys,json,struct
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'));sys.path.insert(0,str(R/'research'))
import _t197_setpath_zero_post as h
p=h.Proc(12948);pe=h.PE(h.EXE);s=h.detect_session(p,pe);gs=int(s['signals']['gs_ptr'],16);idler=int(s['signals']['idler_ptr'],16);co=int(h.resolve_player_country(p,gs)['country_ptr'],16);assert p.read(idler+0x6c1,1)==b'\1'
own={h.handle_at(p,u+0x18)[1]:u for u in h.ptr_array(p,co+0x290,4096)}
out={'pid':12948,'pause':1,'combats':[]}
for cp in h.ptr_array(p,gs+0x268,1024):
 # serializer is secondary at +0x10; its offsets are relative to that pointer
 sp=cp+0x10;vp=struct.unpack('<Q',p.read(sp+0x28,8))[0]
 rec={'ptr':hex(cp),'class':h.cls(p,pe,cp),'handle':h.handle_at(p,sp+8),'province_class':h.cls(p,pe,vp),'province_id':struct.unpack('<I',p.read(vp+0xa4,4))[0],'day_raw':struct.unpack('<I',p.read(sp+0x30,4))[0],'duration_raw':struct.unpack('<I',p.read(sp+0x34,4))[0],'sides':{}}
 for side,off in (('attacker',0x18),('defender',0x20)):
  bp=struct.unpack('<Q',p.read(sp+off,8))[0];x={'ptr':hex(bp),'class':h.cls(p,pe,bp),'arrays':{}}
  for aoff in (0x20,0xe8,0x100,0x118):
   vals=[]
   try:
    for up in h.ptr_array(p,bp+aoff,1000):
     hh=h.handle_at(p,up+0x18)
     vals.append({'handle':hh,'class':h.cls(p,pe,up),'own':hh[0]==51 and hh[1] in own,'ptr_matches_own':own.get(hh[1])==up})
   except Exception as e:vals=[{'error':str(e)}]
   x['arrays'][hex(aoff)]=vals
  rec['sides'][side]=x
 # keep only own-involved combats; no foreign-only situations exported
 involved=any(v.get('own') for x in rec['sides'].values() for v in x['arrays']['0x20'])
 if involved:out['combats'].append(rec)
 else:out.setdefault('foreign_only_omitted',0);out['foreign_only_omitted']+=1
p.close();(R/'research/t198_own_combat_live.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
