import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research')
from t156_objects import P,u64,cls
from gamestate import _pdx_array
out={'status':'candidate_not_emitted_as_neighbors','stride_hypothesis':40,'target_offset_hypothesis':8,'provinces':[]}
try:
 a=json.loads(Path('research/t156_country_areas.json').read_text(encoding='utf-8'));area=int(a['own_province_membership'][0]['area'],16)
 ar=_pdx_array(P,area+0x30);own={}
 for i in range(ar['size']):
  pp=u64(ar['data']+8*i);own[P.u32(pp+0xa4)]=pp
 for pid,pp in own.items():
  dp=u64(pp+0xb8);ad=_pdx_array(P,dp+0x70)
  if not ad or not 0<=ad['size']<=32:raise RuntimeError('unbounded edge candidate')
  b=P.read(ad['data'],ad['size']*40) if ad['size'] else b''
  out['provinces'].append({'province_id':pid,'count':ad['size'],'edges':[{'target_candidate':struct.unpack_from('<I',b,i*40+8)[0],'first_u64':hex(struct.unpack_from('<Q',b,i*40)[0]),'raw':b[i*40:(i+1)*40].hex()} for i in range(ad['size'])]})
 graph={r['province_id']:{e['target_candidate'] for e in r['edges']} for r in out['provinces']}
 pairs=[(p,n) for p,ns in graph.items() for n in ns if n in graph]
 out['internal_directed_edges']=len(pairs);out['reciprocal_directed_edges']=sum(p in graph[n] for p,n in pairs)
 out['self_edges']=[p for p,ns in graph.items() if p in ns]
 out['caveat']='Reciprocity/stride evidence only; land/strait/river/passability semantics not independently proven. Not written into world.provinces.neighbors.'
 Path('research/t156_adjacency_candidate.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in out.items() if k!='provinces'},indent=2));print('SAMPLE',[(r['province_id'],[e['target_candidate'] for e in r['edges']]) for r in out['provinces'][:5]])
finally:P.close()
