# Machine-dependent strictly read-only: exact named battleplan alert entrance.
# No native calls or game mutations. No opacity/tier/confidence substitutions.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t239_final_seal.json').read_text(encoding='utf-8'))
rt=Runtime()
try:
 g=rt.guard();assert g==json.loads((Q/'t240_fresh_guard.json').read_text(encoding='utf-8'))['before'];assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
 pv,ps=rt.sections['.pdata'];pd=rt.code(pv,ps);ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)]
 def bounds(va):
  lo,hi=0,len(ranges)
  while lo<hi:
   m=(lo+hi)//2;s,e,u=ranges[m]
   if va<s:hi=m
   elif va>=e:lo=m+1
   else:return s,e,u
 cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
 def capture(va):
  pr=bounds(va);s,e,u=pr if pr else (va,va+512,0);assert e-s<0x20000
  raw=rt.code(s,e-s);f=walk_flow(cs,raw,s)
  f.update(raw_hex=raw.hex(),sha256=H(raw),pdata=[hex(x) for x in pr] if pr else None,window_start=hex(s),window_size=e-s)
  reach={int(x.split()[0],16) for x in f['asm']};l=[];rv,rs=rt.sections['.rdata']
  for ins in cs.disasm(raw,s):
   if ins.address not in reach or ins.mnemonic!='lea' or len(ins.operands)<2:continue
   o=ins.operands[1]
   if o.type!=X86_OP_MEM or o.mem.base!=X86_REG_RIP:continue
   t=ins.address+ins.size+o.mem.disp
   if not rv<=t<rv+rs:continue
   b=rt.code(t,256).split(b'\0')[0]
   if 2<=len(b)<256 and all(32<=x<127 for x in b):l.append(dict(site=hex(ins.address),rva=hex(t),text=b.decode()))
  f['literals']=l;return f
 rv,rs=rt.sections['.rdata'];rd=rt.code(rv,rs);tv,ts=rt.sections['.text'];tables=[];functions={};refs=[]
 for tooltip in (0x441970,0x442b60):
  needle=struct.pack('<Q',rt.base+tooltip);p=0
  while True:
   p=rd.find(needle,p)
   if p<0:break
   ref=rv+p;p+=1
   if ref%8:continue
   refs.append(dict(tooltip=hex(tooltip),reference_rva=hex(ref)))
   for index in range(25):
    vt=ref-index*8
    if vt-8<rv:continue
    col=struct.unpack_from('<Q',rd,vt-8-rv)[0]-rt.base
    if not rv<=col<=rv+rs-24:continue
    sig,off,cd,td,chd,selfrva=struct.unpack('<6I',rt.code(col,24))
    if sig!=1 or selfrva!=col or not rv<=td+0x10<=rv+rs-160:continue
    name=rt.code(td+0x10,160).split(b'\0')[0].decode('ascii',errors='replace')
    if 'Trigger@@' not in name:continue
    slots=[]
    for j,ptr in enumerate(struct.unpack('<24Q',rt.code(vt,192))):
     va=ptr-rt.base;intext=tv<=va<tv+ts;slots.append(dict(index=j,rva=hex(va),in_text=intext))
     if not intext:break
    assert index<len(slots) and int(slots[index]['rva'],16)==tooltip
    tables.append(dict(tooltip=hex(tooltip),tooltip_slot=index,vtable_rva=hex(vt),col_rva=hex(col),col_offset=off,class_name=name,slots=slots))
    # Generic trigger dispatcher594370 independently calls +B0 (slot22), not a classname guess.
    if len(slots)>22 and slots[22]['in_text']:
     va=int(slots[22]['rva'],16);functions[hex(va)]=capture(va)
 assert len(tables)<=8
 after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,tooltip_pointer_references=refs,tables=tables,functions=functions,promotions=[],scope='Actual loaded-image tooltip-pointer -> validated COL/self/RTTI trigger table binding; generic+B0 evaluator candidate, not unary subject as relation-to-player. No native invocation/current country or visible-unit census.')
 (Q/'t240_subject_trigger_table_bind.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
finally:rt.close()
