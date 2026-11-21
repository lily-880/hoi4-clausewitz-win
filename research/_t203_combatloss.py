from _t203_common import *
x=Runtime()
try:
 before=x.guard();r=x.reader();army=r.array(x.country+0x290,256)[0];assert x.cls(army)=='.?AVCArmy@@';vt=x.q(army)
 out={'guard_before':before,'army':hex(army),'slots':{hex(o):hex(x.q(vt+o)-x.base)for o in range(0,0x150,8)}}
 out['loss']=x.clip(0xcec270);f=x.clip(0x1343100);out['combat_function']=f['start'];out['candidate_calls']=[]
 slots=[int(o,16)for o,t in out['slots'].items()if t=='0xcec270']
 for k,ls in enumerate(f['asm']):
  if 'call' in ls and any(f' + {hex(s)}]' in ls for s in slots):out['candidate_calls'].append(f['asm'][max(0,k-24):k+26])
 out['guard_after']=x.guard();assert before==out['guard_after'];r.stable();(R/'research/t203_combat_manpower_chain.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
finally:x.close()
