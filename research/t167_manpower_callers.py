import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research');from t163_disasm_windows import pe,window
wanted={0xcc6bf0:'extract_current_manpower',0xcc6480:'missing_manpower',0xcc6570:'sum_country_amounts'};out={n:[] for n in wanted.values()};sec=next(s for s in pe.sections if s.name=='.text');data=pe.data[sec.raw_ptr:sec.raw_ptr+sec.raw_size];pos=0
while True:
 pos=data.find(b'\xe8',pos)
 if pos<0 or pos+5>len(data):break
 target=sec.virtual_address+pos+5+struct.unpack_from('<i',data,pos+1)[0]
 if target in wanted:
  a=sec.virtual_address+pos;w=window(a,64,100)
  if any(int(x['rva'],16)==a and x['asm']=='call '+hex(target) for x in w.get('code',[])):
   if len(out[wanted[target]])<128:out[wanted[target]].append({'call_rva':hex(a),'context':w})
 pos+=1
Path('research/t167_manpower_callers.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('COUNTS',{k:len(v) for k,v in out.items()})
for r in out['extract_current_manpower']:print('CALLER',r['call_rva'],r['context']['function'],'; '.join(x['rva']+' '+x['asm'] for x in r['context']['code']))
