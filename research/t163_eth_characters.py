import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P,PEFILE,u64,cls,inspect
from gamestate import _pdx_array

def text(a):
 b=P.try_read(a,32)
 if not b or len(b)!=32:return None
 n,c=struct.unpack_from('<QQ',b,16)
 if n>256 or c<n:return None
 raw=b[:n] if c<=15 else P.try_read(struct.unpack_from('<Q',b)[0],n)
 if raw is None or len(raw)!=n:return None
 try:return raw.decode('utf-8')
 except Exception:return None
out={'characters':[],'building_functions':[]}
try:
 gs=u64(P.base+0x33dd6b0);cm=u64(gs+0x6a8);ar=_pdx_array(P,cm+0x10)
 if not ar or not 0<ar['size']<=15000:raise RuntimeError('character array bound')
 for j in range(ar['size']):
  cp=u64(ar['data']+8*j);name=text(cp+0x28)
  if not name or not (name.startswith('ETH_') or any(t in name.lower() for t in ('selassie','kassa','kebbede','demissie'))):continue
  r={'ptr':hex(cp),'key':name,'class':cls(cp),'object':inspect(cp,0x140),'roles':[]}
  roles=_pdx_array(P,cp+0x80)
  if roles and 0<roles['size']<=16:
   for k in range(roles['size']):
    rp=u64(roles['data']+8*k);r['roles'].append(inspect(rp,0x200))
  out['characters'].append(r)
 old=json.loads(Path('research/t156_buildings.json').read_text(encoding='utf-8'))
 bp=int(old['buildings'][0]['object']['ptr'],16);vt=u64(bp)
 out['building_functions']=[hex(u64(vt+8*i)-P.base) for i in range(9)]
 Path('research/t163_eth_characters_all.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('CHARACTERS',[(r['key'],[(rr['class'],rr['ptr'],rr['strings'][:3],[(x['off'],x['class']) for x in rr['pointers']]) for rr in r['roles']]) for r in out['characters']]);print('BUILDING_FUNCTIONS',out['building_functions'])
finally:P.close()
