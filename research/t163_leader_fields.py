import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P,u64,cls,inspect
from gamestate import _pdx_array

def text(a):
 b=P.try_read(a,32)
 if not b or len(b)!=32:return None
 n,c=struct.unpack_from('<QQ',b,16)
 if n>512 or c<n:return None
 raw=b[:n] if c<=15 else P.try_read(struct.unpack_from('<Q',b)[0],n)
 if raw is None or len(raw)!=n:return None
 try:
  s=raw.decode('utf-8');return s if all(x.isprintable() for x in s) else None
 except Exception:return None
out={'leaders':[]}
try:
 old=json.loads(Path('research/t163_army_leaders.json').read_text(encoding='utf-8'))
 for r in old['leaders']:
  lp=int(r['ptr'],16);blob=P.read(lp,0x1100);ty,idx=struct.unpack_from('<II',blob,8)
  sp=u64(lp+0xe60)
  row={'ptr':r['ptr'],'handle8':{'type':ty,'id':idx},'name20':text(lp+0x20),'skill_ptr':hex(sp),'skill_class':cls(sp),'skill':P.u32(sp+0x1b8),'attack':P.u32(lp+0xf58),'defense':P.u32(lp+0xf68),'planning':P.u32(lp+0xf78),'logistics':P.u32(lp+0xf88),'traits':[],'extra_pointers':[]}
  ar=_pdx_array(P,lp+0xdc8)
  if not ar or not 0<=ar['size']<=64:raise RuntimeError('trait array bound')
  for j in range(ar['size']):
   tp=u64(ar['data']+j*8);row['traits'].append({'ptr':hex(tp),'class':cls(tp),'token':P.u32(tp+8),'name18':text(tp+0x18),'object':inspect(tp,0x60)})
  for off in range(0xe30,0x1100,8):
   v=struct.unpack_from('<Q',blob,off)[0]
   cn=cls(v) if 0x10000<v<0x7fffffffffff else None
   if cn and any(w in cn for w in ('Character','Leader','Army','Country')):row['extra_pointers'].append({'off':hex(off),'ptr':hex(v),'class':cn})
  out['leaders'].append(row)
 Path('research/t163_leader_fields.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 for r in out['leaders']:print(r['handle8'],r['name20'],r['skill_class'],[r[k] for k in ('skill','attack','defense','planning','logistics')],[(t['class'],t['token'],t['name18'],t['object']['strings']) for t in r['traits']],r['extra_pointers'])
finally:P.close()
