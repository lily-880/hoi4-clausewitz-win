import sys,struct,json,bisect
from pathlib import Path
sys.path.insert(0,'calling');from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
pe=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe');pd=next(s for s in pe.sections if s.name=='.pdata');raw=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size];functions=[struct.unpack_from('<III',raw,o)[:2] for o in range(0,len(raw)-11,12)];starts=[x[0] for x in functions];cs=Cs(CS_ARCH_X86,CS_MODE_64)
def window(target,before=48,after=96):
 start,end=functions[bisect.bisect_right(starts,target)-1]
 if not start<=target<end:return {'error':'no function'}
 raw=pe.read_rva(start,min(end-start,target-start+after+16)) or b''
 return {'function':hex(start),'end':hex(end),'code':[{'rva':hex(i.address),'asm':i.mnemonic+' '+i.op_str} for i in cs.disasm(raw,start) if target-before<=i.address<=target+after]}
if __name__=='__main__':
 targets=[0x685d0f,0x685d62,0x148bddd,0x14c93b0,0x14dbb4e,0x14ef2f8]
 out={hex(t):window(t,64,150) for t in targets}
 Path('research/t163_stat_parse_code.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
 for t,r in out.items():print(t,r['function'],'\n'+'\n'.join(i['rva']+' '+i['asm'] for i in r['code']))
