import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P,u64,cls
from gamestate import _pdx_array
out={'research_only_no_visibility_export':True,'unit_bound':512,'inspected':0,'contrasts':[],'countries':[]}
try:
 gs=u64(P.base+0x33dd6b0);countries=_pdx_array(P,gs+0x310);tags=u64(gs+0x358)
 for ci in range(countries['size']):
  b=P.read(tags+32*ci,32);n,cap=struct.unpack_from('<QQ',b,16)
  if n!=3:continue
  tag=(b[:n] if cap<=15 else P.read(struct.unpack_from('<Q',b)[0],n)).decode('ascii')
  if tag not in ('GER','SOV','CHI','ITA','FRA','ENG','USA','JAP'):continue
  co=u64(countries['data']+8*ci);ar=_pdx_array(P,co+0x290)
  if not ar or ar['size']>4096:continue
  out['countries'].append({'tag':tag,'index':ci,'divisions':ar['size']})
  for j in range(min(ar['size'],64)):
   if out['inspected']>=512 or len(out['contrasts'])>=8:break
   ap=u64(ar['data']+8*j)
   if cls(ap)!='.?AVCArmy@@':continue
   vals=[]
   for off in (0x3e0,0x400):
    a=_pdx_array(P,ap+off)
    if not a or a['size']>32:raise RuntimeError('manpower table bound')
    vals.append([{'country_index':k,'amount':v} for k,v in struct.iter_unpack('<ii',P.read(a['data'],a['size']*8))])
   out['inspected']+=1
   if sum(x['amount'] for x in vals[0])!=sum(x['amount'] for x in vals[1]):out['contrasts'].append({'tag':tag,'unit_id':P.u32(ap+0x1c),'ptr':hex(ap),'value':vals[0],'need':vals[1]})
 Path('research/t165_foreign_manpower_contrasts.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
finally:P.close()
