import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t163_disasm_windows import pe,window
wanted={0xcc64c0:'current_manpower_leaf',0xd5dae0:'available_country_manpower'};out={n:[] for n in wanted.values()};sec=next(s for s in pe.sections if s.name=='.text');data=pe.data[sec.raw_ptr:sec.raw_ptr+sec.raw_size];pos=0
while True:
 pos=data.find(b'\xe8',pos)
 if pos<0 or pos+5>len(data):break
 target=sec.virtual_address+pos+5+struct.unpack_from('<i',data,pos+1)[0]
 if target in wanted and len(out[wanted[target]])<128:
  a=sec.virtual_address+pos;w=window(a,55,100)
  if any(int(x['rva'],16)==a and x['asm']=='call '+hex(target) for x in w.get('code',[])):out[wanted[target]].append({'call_rva':hex(a),'context':w})
 pos+=1
Path('research/t167_current_available_callers.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('COUNTS',{k:len(v) for k,v in out.items()})
for key,rows in out.items():
 for r in rows:
  a=int(r['call_rva'],16)
  if 0xcc8000<=a<0xcf0000:print('ARMY_CURRENT_USE',r['call_rva'],'; '.join(x['rva']+' '+x['asm'] for x in r['context'].get('code',[])))
