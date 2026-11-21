import sys,struct,json,re
from pathlib import Path
sys.path.insert(0,'research');from t163_disasm_windows import pe,window
out=[]
start,end=0x83760,0x119491;b=pe.read_rva(start,end-start)
for m in re.finditer(rb'\x4c\x8d\x05....',b,re.S):
 rva=start+m.start();before=pe.read_rva(rva-0x13,6)
 if before[:2]!=b'\x8b\x15':continue
 crva=rva-0x13+6+struct.unpack_from('<i',before,2)[0];c=pe.read_rva(crva,4)
 srva=rva+7+struct.unpack_from('<i',m.group(),3)[0];raw=pe.read_rva(srva,200)
 if not raw or not c:continue
 name=raw.split(b'\0')[0]
 if not re.fullmatch(rb'[a-zA-Z0-9_.]+',name):continue
 out.append({'token':struct.unpack('<I',c)[0],'name':name.decode(),'registration_rva':hex(rva)})
Path('research/t163_script_token_map.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('NAMED_TOKENS',len(out));print('RELEVANT',[(r['name'],hex(r['token'])) for r in out if r['name'] in ('combat_width','manpower','skill','attack_skill','defense_skill','planning_skill','logistics_skill','victory_points','infrastructure','land_fort','coastal_fort','experience')]);print('BASE_TYPE_PARSE',json.dumps(window(0x14c9586,100,340),indent=2))
