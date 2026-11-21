exec(open(__file__.replace('_t198_bind.py','_t198_research.py'),encoding='utf-8').read().split('out={}')[0])
vt=0x2a852e0
valid=struct.unpack('<Q',p.read_rva(vt+0x48,8))[0]-0x140000000
print('VALID',hex(valid));print('\n'.join(das(valid,0x200)))
# lea references constructor/factory
from capstone.x86 import X86_OP_MEM,X86_REG_RIP
cs.detail=True
text=next(s for s in p.sections if s.name=='.text')
# byte search rip lea prefixes, resolve to vt
refs=[]
for pref in (b'\x48\x8d\x05',b'\x48\x8d\x0d',b'\x48\x8d\x15'):
 start=0
 while 1:
  i=p.data.find(pref,start)
  if i<0:break
  start=i+1;a=rv(i)
  if a and a+7+struct.unpack_from('<i',p.data,i+3)[0]==vt:refs.append(a)
pdata=next(s for s in p.sections if s.name=='.pdata')
funcs=list(struct.iter_unpack('<III',p.data[pdata.raw_ptr:pdata.raw_ptr+pdata.raw_size][:pdata.raw_size//12*12]))
out={'vt':hex(vt),'valid':hex(valid),'valid_disasm':das(valid,0x200),'references':[]}
for a in refs:
 fn=next(((s,e) for s,e,u in funcs if s<=a<e),None)
 if fn:
  out['references'].append({'at':hex(a),'fn':hex(fn[0]),'asm':das(fn[0],min(fn[1]-fn[0],0x180))})
for rec in out['references']:print(json.dumps(rec))
(R/'research/t198_insertfront_bind.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
