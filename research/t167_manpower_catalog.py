import sys,json,re
from pathlib import Path
sys.path.insert(0,'research');from t163_disasm_windows import pe,cs,functions
out=[]
for start,end in functions:
 if not 0xcc4000<=start<0xcc7c00:continue
 ins=[{'rva':hex(i.address),'asm':i.mnemonic+' '+i.op_str} for i in cs.disasm(pe.read_rva(start,end-start),start)]
 out.append({'start':hex(start),'end':hex(end),'code':ins})
 hits=[i['asm'] for i in ins if any(s in i['asm'] for s in ('[rcx + 0x28]','[rbx + 0x28]','[rcx + 0x14]','[rbx + 0x14]'))]
 if hits:print(hex(start),hex(end),'count',len(ins),' ; '.join(hits[:10]))
Path('research/t167_manpower_function_catalog.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('bounded functions',len(out))
