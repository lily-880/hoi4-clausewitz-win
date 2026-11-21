from _t202_common import *
x=Runtime()
try:
 before=x.guard();out={'functions':{},'label':None,'primary_changer_predicate':None}
 for a in(0xe64c50,0x1739900):out['functions'][hex(a)]=x.clip(a)
 out['label']=x.code(0x2a2e5e0,80).split(b'\0')[0].decode('ascii',errors='replace')
 vt=x.base+0x2a63590;a=x.q(vt+0x218)-x.base;out['primary_changer_predicate']={'slot':'0x218','target':hex(a),'function':x.clip(a)}
 out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t202_isolated_binding.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('LABEL',out['label']);print('FUNCTIONS',[(a,len(f['asm']))for a,f in out['functions'].items()]);print('PREDICATE',hex(a),out['primary_changer_predicate']['function']['asm'])
finally:x.close()
