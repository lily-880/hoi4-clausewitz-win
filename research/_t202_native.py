from _t202_common import *
x=Runtime()
try:
 before=x.guard();out={'functions':{},'record_class':{},'record_strings':{},'combat_side_stats':[]}
 for a in(0x708270,0x707d10,0x10b9ed0,0x133abc0,0x1342a10,0x1343100,0x134aa40):out['functions'][hex(a)]=x.clip(a)
 vt=x.base+0x2a23650;col=x.q(vt-8);td=struct.unpack('<IIII',x.pr.read(col,16))[3];out['record_class']={'vtable_rva':'0x2a23650','rtti':x.pr.read(x.base+td+16,160).split(b'\0')[0].decode('ascii')}
 for a in(0x27963d0,0x27963ff,0x2796424,0x27963c4):out['record_strings'][hex(a)]=x.code(a,160).split(b'\0')[0].decode('utf-8',errors='replace')
 r=x.reader()
 for cp in r.array(x.gs+0x268,4096):
  for side,off in(('attacker',0x28),('defender',0x30)):
   bp=r.q(cp+off);sp=r.q(bp+0x130);d={'combat_id':r.i(cp+0x1c),'side':side,'side_stats_ptr130':hex(sp)}
   if sp:
    try:d['stats_rtti']=x.cls(sp)
    except(AssertionError,UnicodeError):d['stats_rtti']=None
    d['raw_fields_138_through160']={hex(o):struct.unpack('<q',r.exact(sp+o,8))[0]for o in range(0x138,0x168,8)}
   out['combat_side_stats'].append(d)
 r.stable();after=x.guard();assert before==after;out['guard_after']=after;(R/'research/t202_native_stat_axis.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
 print('FUNCTIONS',[(a,len(v['asm']))for a,v in out['functions'].items()]);print('RECORD_CLASS',out['record_class']);print('STRINGS',out['record_strings']);print('STATS',json.dumps(out['combat_side_stats'],indent=2))
finally:x.close()
