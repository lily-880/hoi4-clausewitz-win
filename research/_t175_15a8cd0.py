
import sys,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64,CS_OP_IMM
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=True
pd=next(s for s in pe.sections if s.name==".pdata")
raw=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III",raw,o)[:2] for o in range(0,len(raw)-11,12)]
starts=[x[0] for x in functions]
IMAGE=0x140000000

def pdata(rva):
    if rva>=IMAGE: rva-=IMAGE
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def nearby(rva,n=8):
    i=bisect.bisect_right(starts,rva)
    lo=max(0,i-3); hi=min(len(functions),i+n)
    return [(hex(s),hex(e),e-s) for s,e in functions[lo:hi]]

print("NEAR 15a8cd0", nearby(0x15a8cd0))
print("NEAR 15a8790", nearby(0x15a8790))

def stitch(entry, stop):
    rawb=pe.read_rva(entry, stop-entry) or b""
    ins=list(cs.disasm(rawb, entry))
    targets=set()
    for i in ins:
        if i.mnemonic.startswith("j") and i.operands and i.operands[0].type==CS_OP_IMM:
            t=i.operands[0].imm
            if entry<=t<stop: targets.add(t)
    last=max([entry]+list(targets))
    out=[]
    for i in ins:
        if i.address>=stop: break
        if i.mnemonic=="int3" and out and out[-1].mnemonic in ("ret","jmp") and i.address>last:
            break
        out.append(i)
        if i.mnemonic=="ret" and i.address>=last:
            break
    text="\n".join("%s  %s %s"%(hex(i.address),i.mnemonic,i.op_str) for i in out)
    return text,out

for entry,stop,name in [(0x15a8cd0,0x15a8f00,"15a8cd0"),(0x15a8790,0x15a8940,"15a8790")]:
    text,out=stitch(entry,stop)
    Path("research/_t175_clip_%s.txt"%name).write_text(text+"\n",encoding="utf-8")
    print("="*60, name, "ins", len(out), "end", hex(out[-1].address) if out else None)
    print("calls", sorted({i.op_str.split()[-1] for i in out if i.mnemonic=="call"}))
    print(text)
