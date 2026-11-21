# Complete F6F9B0/D56B10 bodies and decide whether a null F7E1C0 list enqueues countries.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t233_final_seal.json').read_text(encoding='utf-8'))
rt=Runtime()
try:
 g=rt.guard();assert g==prev['before'];assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
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
 def capture_window(s,e,note):
  assert 0<e-s<0x8000;raw=rt.code(s,e-s);f=walk_flow(cs,raw,s)
  f.update(raw_hex=raw.hex(),sha256=H(raw),window_start=hex(s),window_size=e-s,note=note,pdata=None)
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
 def capture(va):
  pr=bounds(va);s,e,u=pr if pr else (va,va+512,0);assert e-s<0x10000
  f=capture_window(s,e,'pdata' if pr else 'bounded512');f['pdata']=[hex(x) for x in pr] if pr else None;return f
 # F6F9B0 pdata ends 0xf6fad7; continuation until F6FC70 entry. D56B10 pdata 25 bytes, continue until next unwind.
 functions={
  '0xf6f9b0':capture(0xf6f9b0),
  '0xf6f9b0_tail':capture_window(0xf6fad7,0xf6fc70,'explicit tail after truncated pdata to next function F6FC70'),
  '0xd56b10':capture(0xd56b10),
  '0xd56b10_tail':capture_window(0xd56b29,(bounds(0xd56bde) or (0xd56b29,0xd56b29+0x200,0))[1],'explicit tail after 25-byte pdata'),
  '0xd580d0':capture(0xd580d0),
  '0xd570d0':capture(0xd570d0),
 }
 # Narrow named intel/confidence literals in .rdata only; no opacity/tier rescan and no tokenizer walk.
 rv,rs=rt.sections['.rdata'];rd=rt.code(rv,rs)
 needles=(b'INTEL_CONFIDENCE',b'VISIBILITY_CONFIDENCE',b'INTEL_LEVEL',b'RECON_LEVEL',b'INTEL_NETWORK',b'SPOTTED_CONFIDENCE',b'UNIT_INTEL',b'NAVAL_INTEL',b'ARMY_INTEL',b'AIR_INTEL',b'CONFIDENCE_LEVEL',b'INTELLED',b'INTELLIGENCE_LEVEL',b'DECRYPTION_LEVEL',b'RADAR_INTEL')
 hits=[]
 for n in needles:
  off=0
  while len(hits)<40:
   i=rd.find(n,off)
   if i<0:break
   s=i
   while s>0 and 32<=rd[s-1]<127:s-=1
   t=i
   while t<len(rd) and 32<=rd[t]<127:t+=1
   hits.append(dict(needle=n.decode(),rva=hex(rv+s),text=rd[s:t].decode('ascii','replace')))
   off=i+1
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
 stable=r.stable();after=rt.guard();assert after==g
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=g,after=after,functions=functions,intel_literal_hits=hits,promotions=[],stable_dependencies=stable,
  scope='Completes truncated enqueue helpers only. Named intel needles are presence tests, not schema mapping. No empty-scope counters, F6A071, or opacity/tier reuse. Bytes only, never invoked.')
 (Q/'t234_enqueue_completion.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 meta={k:{kk:f.get(kk) for kk in ('window_start','window_size','sha256','literals','calls','external_tails','unresolved_edges','note','pdata')} for k,f in functions.items()}
 print(json.dumps(dict(at_est=out['at_est'],intel_literal_hits=hits,function_meta=meta,stable_dependencies=stable),ensure_ascii=False,indent=2))
finally:rt.close()
