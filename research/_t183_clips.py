import sys,re,json,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={item["token"]:item["name"] for item in mp}
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
pd=next(s for s in pe.sections if s.name==".pdata")
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]
text=next(s for s in pe.sections if s.name==".text")
text_rva=text.virtual_address
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def clip(start, end, path=None):
    raw=pe.read_rva(start, end-start) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
        if m:
            tok=int(m.group(2),16)
            if tok in id2name:
                a += "  ; TOKEN "+id2name[tok]
        lines.append(a)
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

def dump_func(rva, path, pad=0x20):
    fo=func_of(rva)
    if not fo:
        # try disasm 0x200 from rva
        lines=clip(rva, rva+0x200, path)
        print(path, "NO PDATA, dumped 0x200, lines", len(lines))
        return lines
    s,e=fo
    # .pdata can truncate; if requested rva is mid-func it's fine
    end=max(e, rva+pad)
    # if window tiny, extend
    if end-s < 0x80:
        end=s+0x200
    lines=clip(s, min(s+0x400, end+0x40), path)
    print(path, hex(s), "size", hex(end-s), "lines", len(lines))
    return lines

# is_assigned family
dump_func(0x26940, "research/_t183_clip_is_assigned_0x26940.txt")
dump_func(0x14a8ec0, "research/_t183_clip_is_assigned_0x14a8ec0.txt")
dump_func(0x26c40, "research/_t183_clip_is_field_marshal_0x26c40.txt")
dump_func(0x26e80, "research/_t183_clip_is_leading_army_group_0x26e80.txt")
dump_func(0xf00797, "research/_t183_clip_supply_ratio_0xf00797.txt")

# commandlist section of base writer
clip(0xc5c430, 0xc5c4d0, "research/_t183_clip_commandlist_loop_0xc5c43f.txt")

# lea/rip xrefs to InCombat string at 0x29f9547 and "is in combat" 0x283234b
# preferred image base 0x140000000 so VA = 0x140000000+rva
IMAGE=0x140000000
def lea_xrefs(target_rva, limit=30):
    # search rip-relative lea/cmp that point to target
    # E8 is call; 48 8D 0D / 15 / 05 / 1D / 2D / 35 / 3D  disp32
    hits=[]
    # also 4C 8D ... for r8-r15
    for m in re.finditer(rb"(?:\x48|\x4c)\x8d.[\x00-\xff]{4}", text_raw):
        # too broad; parse with capstone a few bytes
        pass
    # scan all lea/mov with rip rel via walking... expensive.
    # narrower: find disp32 such that instr_end+disp = target_rva
    # for each occurrence of the little-endian rva-ish we compute
    # Actually search for the displacement bytes: for a 7-byte lea (48 8d XX disp32)
    # at file offset o, rva=text_rva+o, instr_end=rva+7, disp=target_rva-instr_end
    # We'll search the disp32 for possible instr lengths 6 and 7 (and 8?).
    hits=[]
    for instlen in (6,7,8,9):
        # we'd need exact opcode lengths; instead search all occurrences of candidate disp
        # for each potential instruction start we can't. Simpler:
        # scan text for the 4-byte encoding of (target_rva - (site+instlen))
        pass
    # Brute: for each match of 4-byte sequences that could be disp to target
    # We'll iterate possible sites by finding bytes that decode as disp.
    # Practical approach used before: regex over text_raw for RIP-relative by capstone windows around string xrefs from .rdata
    # Find 32-bit rel32 values in text that jump to target.
    sites=[]
    for instlen in range(2, 12):
        # For each position, disp = target - (rva+instlen); we search for pack(disp)
        # Can't do for all positions. Instead: we can compute: if a disp32 at offset o (meaning inst ends at o+4)
        # then if text_rva+o+4+disp == target, it's a hit. Scan every 1 byte is 40MB*... acceptable-ish in python? text is maybe 30MB, 30e6*1 is ok if we only unpack every aligned? 
        pass
    # Walk every 1 byte looking at 4-byte LE ints as disp assuming inst-end at that+4
    # 30MB is fine.
    n=len(text_raw)
    for o in range(0, n-4):
        disp=struct.unpack_from("<i", text_raw, o)[0]
        inst_end=text_rva+o+4
        if inst_end+disp==target_rva:
            sites.append(text_rva+o)  # disp location
            if len(sites)>=limit:
                break
    return sites

for name,rva in [("InCombat(", 0x29f9547), ("is in combat", 0x283234b)]:
    sites=lea_xrefs(rva, 20)
    print(name, "disp sites", [hex(s) for s in sites], "n", len(sites))
    # decode 16 bytes before each disp
    for s in sites[:10]:
        start=max(text_rva, s-12)
        raw=pe.read_rva(start, 24) or b""
        insts=[]
        for i in cs.disasm(raw, start):
            insts.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
        print(" -- site", hex(s))
        print("\n".join(insts))

# print is_assigned clips heads
for fn in ["research/_t183_clip_is_assigned_0x26940.txt","research/_t183_clip_is_assigned_0x14a8ec0.txt","research/_t183_clip_is_field_marshal_0x26c40.txt","research/_t183_clip_is_leading_army_group_0x26e80.txt"]:
    t=Path(fn).read_text(encoding="utf-8")
    print("\n========", fn, "len", len(t.splitlines()))
    print("\n".join(t.splitlines()[:60]))
