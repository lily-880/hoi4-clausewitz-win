import sys,json,re,struct
from pathlib import Path
sys.path.insert(0,'research');from t163_disasm_windows import pe,window
keys=['LEDGER_STOCKPILE_AMOUNT_TOOLTIP','LEDGER_TOTAL_STOCKPILE_AMOUNT_TOOLTIP','EFFECT_REMOVE_EQUIPMENT_FROM_STOCKPILE'];wanted={}
for key in keys:
 pos=0
 while True:
  pos=pe.data.find(key.encode()+b'\0',pos)
  if pos<0:break
  for s in pe.sections:
   if s.raw_ptr<=pos<s.raw_ptr+s.raw_size:wanted[s.virtual_address+pos-s.raw_ptr]=key
  pos+=1
sec=next(s for s in pe.sections if s.name=='.text');blob=pe.data[sec.raw_ptr:sec.raw_ptr+sec.raw_size];out=[]
for m in re.finditer(rb'[\x48\x4c][\x8d\x8b][\x05\x0d\x15\x1d\x25\x2d\x35\x3d].{4}',blob,re.S):
 rva=sec.virtual_address+m.start();target=rva+7+struct.unpack_from('<i',m.group(),3)[0]
 if target not in wanted:continue
 w=window(rva,180,220);out.append({'key':wanted[target],'xref':hex(rva),'context':w})
Path('research/t167_stockpile_ui_xrefs.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('COUNTS',{k:sum(r['key']==k for r in out) for k in keys})
for r in out:print(r['key'],r['xref'],'; '.join(x['rva']+' '+x['asm'] for x in r['context'].get('code',[])))
