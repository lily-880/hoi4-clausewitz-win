
"""Find call [reg+0x10] sites whose parent also touches request/stock primitives."""
import sys,struct,json,bisect
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,'calling')
from pe import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_64,CS_OP_IMM,CS_OP_MEM

EXE=r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe'
pe=PE(EXE)
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=True
pd=next(s for s in pe.sections if s.name=='.pdata')
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',raw_pd,o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]
IMAGE=0x140000000

def pdata(rva):
    if rva>=IMAGE: rva-=IMAGE
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

text=next(s for s in pe.sections if s.name=='.text')
blob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
va=text.virtual_address

# Disassemble in chunks of 1MB to find call qword ptr [reg+0x10]
# Pattern for call [rax+0x10]: FF 50 10
# call [rcx+0x10]: FF 51 10
# call [rdx+0x10]: FF 52 10
# call [rbx+0x10]: FF 53 10
# call [rsi+0x10]: FF 56 10
# call [rdi+0x10]: FF 57 10
# call [r8+0x10]: 41 FF 50 10  -- wait 41 FF 50 10 is [r8+0x10]? 
# REX.B (0x41) + FF /2 + modrm
# call [r12+0x10]: 41 FF 54 24 10 (SIB)
# We'll just search FF 5x 10 and FF 50-57 10, plus 41 FF 5x 10

sites=[]
# simple 3-byte: FF 50/51/52/53/55/56/57 10  (not 54 which needs SIB)
for modrm in (0x50,0x51,0x52,0x53,0x55,0x56,0x57):
    pat=bytes([0xFF, modrm, 0x10])
    pos=0
    while True:
        i=blob.find(pat,pos)
        if i<0: break
        sites.append(va+i)
        pos=i+1
# rex.b 41 FF 50-57 10 except 54
for modrm in (0x50,0x51,0x52,0x53,0x55,0x56,0x57):
    pat=bytes([0x41,0xFF, modrm, 0x10])
    pos=0
    while True:
        i=blob.find(pat,pos)
        if i<0: break
        sites.append(va+i)
        pos=i+1
# also 4C? no that's rex.w+b for 64-bit? call is implicit. 41 is enough for r8-r15 without SIB.

print('simple call [reg+0x10] sites', len(sites))

# Interesting immediate call targets or displacement constants to look for in parent function
MARKERS={
    0x1095b00,0x1092b70,0x1098700,0x1098540,0x1094900,0x10948a0,0x15a92f0,0x15a8c20,
    0xee1250,0x10961f0,0x15a16a0,0xcdb4b0,0xc07690,0x717350,0x140b9c0,
    0x15aa9c0,0x15a5c80,0xbd8e40,0x15a55e0,
}

# For each site, get parent (pdata start). Group by parent. For each parent, disasm a window
# and see if it has E8 to interesting targets, or +0x78 / +0x38 / +0x200 in mem ops.

# Limit: too many sites. First group by parent, then only inspect parents that also
# contain an E8 to one of MARKERS, or are in 0x15a0000-0x15b0000 / 0xed0000 / 0x13f0000 / production.

def rel_calls_in(entry, end):
    raw=pe.read_rva(entry, min(end-entry, 0x4000)) or b''
    found=set()
    # scan E8
    for i in range(len(raw)-4):
        if raw[i]==0xE8:
            rel=struct.unpack_from('<i',raw,i+1)[0]
            dest=(entry+i+5+rel)&0xffffffff
            if dest in MARKERS:
                found.add(dest)
    return found

parents=defaultdict(list)
for at in sites:
    w=pdata(at)
    if w:
        parents[w[0]].append(at)
    else:
        parents[-1].append(at)
print('unique parents', len(parents))

interesting=[]
for ent, ats in parents.items():
    if ent<0: continue
    w=pdata(ent)
    end=w[1] if w else ent+0x800
    # extend a bit for fragmented pdata (cap 0x2000)
    span=min(0x2000, max(end, max(ats)+0x40)-ent)
    marks=rel_calls_in(ent, ent+span)
    # also check if parent is in reinforcement-ish ranges
    in_range = (0x15a0000<=ent<0x15c0000) or (0xed0000<=ent<0xee8000) or (0x13f8000<=ent<0x1400000) or (0xce0000<=ent<0xcf0000) or (0xcd0000<=ent<0xce0000)
    if marks or (in_range and len(ats)<=12):
        interesting.append({'func':hex(ent),'n_slot2_calls':len(ats),'sites':[hex(x) for x in ats[:12]],
                            'markers':[hex(m) for m in sorted(marks)],'in_range':in_range})

# sort by number of markers then range
interesting.sort(key=lambda r: (-len(r['markers']), -int(r['in_range']), r['func']))
print('interesting parents', len(interesting))
for r in interesting[:40]:
    print(r)

Path('research/t175_virt_slot2_parents.json').write_text(json.dumps({
    'site_count':len(sites),'parent_count':len(parents),'interesting':interesting
},indent=2),encoding='utf-8')
print('done')
