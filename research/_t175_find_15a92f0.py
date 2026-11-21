
"""Find 15a92f0 references: 32-bit RVA, RIP-relative lea, relocs, live vtable. Read-only."""
from __future__ import annotations
import os,sys,struct,json,bisect
from pathlib import Path
from collections import defaultdict
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'calling'))
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_OP_IMM, CS_OP_MEM
from mem import Proc,find_pid
from gamestate import _rtti_name_from_vtable,detect_session,resolve_player_country

EXE=r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe'
pe=PE(EXE)
cs=Cs(CS_ARCH_X86,CS_MODE_64); cs.detail=True

TARGETS={
    '15a92f0':0x15a92f0,
    '15a8cf0':0x15a8cf0,
    '15a8f00':0x15a8f00,
    '15a85da':0x15a85da,
}

# pdata
pd=next(s for s in pe.sections if s.name=='.pdata')
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from('<III',raw_pd,o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]
def pdata(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def scan_imm32(target):
    needle=struct.pack('<I', target)
    hits=[]
    for s in pe.sections:
        blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
        pos=0
        while True:
            i=blob.find(needle,pos)
            if i<0: break
            # skip if this is part of a 64-bit 0x00000000_015a92f0 we already want
            hits.append({'section':s.name,'rva':hex(s.virtual_address+i),'file_off':s.raw_ptr+i})
            pos=i+1
            if len(hits)>80: break
    return hits

def scan_rip_lea(target):
    """Disassemble .text looking for lea/mov that compute target via rip+disp32."""
    text=next(s for s in pe.sections if s.name=='.text')
    # chunked disasm would be huge; instead scan for possible disp32 encodings.
    # lea r64, [rip+disp32] is 48 8D 05/0D/15/1D/25/2D/35/3D disp32  (REX.W lea)
    # also 4C 8D ... for r8-r15
    blob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
    va=text.virtual_address
    hits=[]
    # general: for each occurrence of the 4-byte displacement that would make rip+disp = target
    # Instruction length for lea/mov rip-rel is typically 7 (rex + opcode + modrm + disp32)
    # We can iterate all positions with 7-byte lea patterns, or compute required disp for each insn start.
    # Faster: for each possible insn_end, disp = target - insn_end, search for that disp preceded by lea/mov rip-rel opcodes.
    prefixes=[
        bytes([0x48,0x8D]), bytes([0x4C,0x8D]),  # lea
        bytes([0x48,0x8B]), bytes([0x4C,0x8B]),  # mov r64, [rip]
        bytes([0x48,0x89]), bytes([0x4C,0x89]),  # mov [rip], r64 (unlikely for code addr)
    ]
    # RIP-relative modrm: mod=00, r/m=101 (0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D)
    rip_modrms=bytes([0x05,0x0D,0x15,0x1D,0x25,0x2D,0x35,0x3D])
    # Also without REX: 8D / 8B
    for op in (b'\x8D', b'\x8B'):
        pos=0
        while True:
            i=blob.find(op,pos)
            if i<0: break
            # possible with or without rex immediately before
            for start in (i-1, i):  # rex+op or just op
                if start<0: continue
                # need start, op, modrm, disp32
                if start==i:
                    # no rex: [op][modrm][disp]
                    if i+1>=len(blob): continue
                    modrm=blob[i+1]
                    disp_at=i+2
                    insn_len=6
                    insn_rva=va+i
                else:
                    if blob[start] not in (0x48,0x4C,0x4A,0x49):
                        continue
                    if i+1>=len(blob): continue
                    modrm=blob[i+1]
                    disp_at=i+2
                    insn_len=7
                    insn_rva=va+start
                if (modrm & 0xC7) != 0x05:  # mod=00 rm=101
                    continue
                if disp_at+4>len(blob): continue
                disp=struct.unpack_from('<i',blob,disp_at)[0]
                dest=(insn_rva+insn_len+disp)&0xffffffff
                if dest==target:
                    w=pdata(insn_rva)
                    hits.append({'at':hex(insn_rva),'func':hex(w[0]) if w else None,'len':insn_len,
                                 'bytes':blob[insn_rva-va:insn_rva-va+insn_len].hex()})
            pos=i+1
            if len(hits)>40: break
    return hits

# Also scan for FF 15 [rip] etc is not needed if we find vtable slots.

out={'imm32':{}, 'rip_lea':{}}
for name,t in TARGETS.items():
    imm=scan_imm32(t)
    lea=scan_rip_lea(t)
    out['imm32'][name]={'count':len(imm),'hits':imm[:20]}
    out['rip_lea'][name]={'count':len(lea),'hits':lea}
    print(name, 'imm32', len(imm), 'rip_lea', len(lea), lea[:8])

# Relocs: IMAGE_DIRECTORY_ENTRY_BASERELOC = 5
# PE helper may have data directories. We'll try to parse relocs if possible.
reloc_hits=[]
try:
    # pe.py may expose optional header dirs
    dirs=getattr(pe,'data_directories',None) or getattr(pe,'directories',None)
    print('pe attrs sample', [a for a in dir(pe) if 'rel' in a.lower() or 'dir' in a.lower() or 'opt' in a.lower()][:30])
except Exception as e:
    print('reloc inspect', e)

Path('research/t175_15a92f0_refs_static.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('static done')
