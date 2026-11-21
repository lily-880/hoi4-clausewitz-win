import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P,u64,cls
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

out=[]
try:
 cc=int(json.loads(Path('research/t163_country_characters.json').read_text(encoding='utf-8'))['ptr'],16);ar=_pdx_array(P,cc+0x10)
 for j in range(ar['size']):
  cp=u64(ar['data']+16*j);tp=u64(cp+0x20)
  out.append({'ptr':hex(cp),'class':cls(cp),'name28':text(cp+0x28),'name48':text(cp+0x48),'template':hex(tp),'template_class':cls(tp),'template40':text(tp+0x40),'template18':text(tp+0x18)})
 Path('research/t163_own_character_names.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out[:22],ensure_ascii=False,indent=2));print('COUNT',len(out))
finally:P.close()
