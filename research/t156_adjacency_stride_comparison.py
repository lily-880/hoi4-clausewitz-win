import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research')
from t156_objects import P,u64
from gamestate import _pdx_array
out={'status':'stride_differential_only_not_verified_neighbors','scores':[]}
try:
 a=json.loads(Path('research/t156_country_areas.json').read_text(encoding='utf-8'));area=int(a['own_province_membership'][0]['area'],16)
 ar=_pdx_array(P,area+0x30);buffers={}
 for i in range(ar['size']):
  pp=u64(ar['data']+i*8);pid=P.u32(pp+0xa4);dp=u64(pp+0xb8);ad=_pdx_array(P,dp+0x70)
  if not ad or not 0<=ad['size']<=32:raise RuntimeError('bound')
  buffers[pid]=(ad['size'],P.read(ad['data'],ad['size']*128) if ad['size'] else b'')
 for stride in range(24,129,8):
  graph={pid:[struct.unpack_from('<I',b,i*stride+8)[0] for i in range(n)] for pid,(n,b) in buffers.items()}
  vals=[v for ns in graph.values() for v in ns];pairs=[(p,n) for p,ns in graph.items() for n in ns if n in graph]
  out['scores'].append({'stride':stride,'edge_count':len(vals),'plausible_ids':sum(1<=v<=20000 for v in vals),'internal':len(pairs),'reciprocal':sum(p in graph[n] for p,n in pairs),'self':sum(p in ns for p,ns in graph.items()),'sample_5010':graph[5010]})
 Path('research/t156_adjacency_stride_comparison.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(out,indent=2))
finally:P.close()
