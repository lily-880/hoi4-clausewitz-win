from pathlib import Path
import sys,json,struct
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'research'));sys.path.insert(0,str(R/'calling'))
import _t197_setpath_zero_post as h
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
p=PE(h.EXE);cs=Cs(CS_ARCH_X86,CS_MODE_64)
def das(a,n):return [f'{i.address:x} {i.mnemonic} {i.op_str}' for i in cs.disasm(p.read_rva(a,n),a)]
# Fallback tail
print('FALLBACK', '\n'.join(das(0x18d9030,0x40)))
# dry InsertFront; no Post in this diagnostic
pid=h.mem_find_pid('hoi4.exe');assert pid==12948
pr=h.Proc(pid);b=h.Backend();s=h.detect_session(pr,p);gs=int(s['signals']['gs_ptr'],16);idler=int(s['signals']['idler_ptr'],16);co=int(h.resolve_player_country(pr,gs)['country_ptr'],16)
assert pr.read(idler+0x6c1,1)==b'\1'
gp,ins=h.find_group(pr,p,co,(53,411));assert any(x['instance_id_244']==2 for x in ins)
cmd,fr=h.factory_make(pid,b,0x18d01c0,0x2a852e0,0x98);assert cmd
# three factory-initialized vectors retained unless required: units empty; front two provinces; axis two; affected-order IDs [2]
def vec(off, vals):
 buf=h.mo._game_malloc(pid,max(8,4*len(vals)));h.mo._write(pid,buf,struct.pack('<'+'I'*len(vals),*vals));h.mo._write(pid,cmd+off,struct.pack('<QII',buf,len(vals),len(vals)))
h.mo._write(pid,cmd+0x28,struct.pack('<II',53,411));h.mo._write(pid,cmd+0x78,struct.pack('<I',2))
vec(0x48,[2072,7944]);vec(0x60,[7944,5097]);vec(0x80,[2])
dry=h.dry_isvalid(pid,b,0x18df2a0,cmd)
rec={'pid':pid,'cmd':hex(cmd),'factory':fr,'dry':dry,'group':[53,411],'attach':2,'front':[2072,7944],'axis':[7944,5097],'affected':[2],'raw':pr.read(cmd,0x98).hex(),'execute_tail':das(0x18d6870,0x100),'fallback':das(0x18d9030,0x40)}
(R/'research/t198_insertfront_dry.json').write_text(json.dumps(rec,indent=2),encoding='utf-8');print(json.dumps(rec,indent=2));h.close_gates();pr.close()
