# Distinct bounded remaining-field pivot: named war/front invalidation causes only; readonly.
import sys,json,struct,hashlib,datetime,re
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
H=lambda b:hashlib.sha256(b).hexdigest();session=json.loads((Q/'t232_initial_session_rebind.json').read_text());rt=Runtime()
try:
 g=rt.guard();assert g==session['before'];assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==session['native_controls'][hex(va)]
 for name,h in session['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
 # Semantically limited whole C-string match; no own plans/zero faction samples.
 rv,rs=rt.sections['.rdata'];rd=rt.code(rv,rs)
 pattern=re.compile(r'(front.{0,90}(invalid|rebuild|war.relation|fraction|obsolete))|((invalid|rebuild|war.relation|fraction|obsolete).{0,90}front)',re.I)
 found=[]
 for m in re.finditer(rb'[\x20-\x7e]{6,}\x00',rd):
  s=m.group()[:-1].decode()
  if pattern.search(s):found.append({'rva':hex(rv+m.start()),'text':s})
  if len(found)>=48:break
 dv,ds=rt.sections['.data'];data=rt.code(dv,ds);rtti=[]
 for m in re.finditer(rb'\.\?AV[^\x00]+\x00',data):
  s=m.group()[:-1].decode('ascii','replace')
  if 'Front' in s and any(k in s for k in ('WarRelation','Diplom','Invalid','Obsolete','Rebuild','BuildSections')):
   rtti.append({'rva':hex(dv+m.start()),'name':s})
  if len(rtti)>=32:break
 # Bounded LEA xrefs to these named invalidation/rebuild strings, no renderer/native invocation.
 tv,ts=rt.sections['.text'];text=rt.code(tv,ts);targets={int(x['rva'],16):[] for x in found}
 for rex in (0x48,0x4c):
  for modrm in (5,13,21,29,53,61):
   pre=bytes((rex,0x8d,modrm));at=0
   while True:
    i=text.find(pre,at)
    if i<0:break
    at=i+1
    if i+7<=len(text):
     dst=tv+i+7+struct.unpack_from('<i',text,i+3)[0]
     if dst in targets and len(targets[dst])<12:targets[dst].append(hex(tv+i))
 for x in found:x['xrefs']=targets[int(x['rva'],16)]
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';stable=r.stable();after=rt.guard();assert after==g
 out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'target':'world.wars.front_invalidated','named_strings':found,'rtti_names':rtti,'stable_dependencies':stable,'current_front_invalidated_sample_count':0,'promotions':[],'scope':'Named entrance search only. A rebuild log, loader error or RTTI BuildSections name is not an actual war-change invalidation flag/causal witness. No world heap walk, plan scan, null-faction query, date conversion or scope expansion.'}
 (Q/'t232_front_invalidation_pivot.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('before','after')},ensure_ascii=False,indent=2))
finally:rt.close()
