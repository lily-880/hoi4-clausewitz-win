
"""Read-only disassembly of 14075c0 / 15b1da0 family. No process attach."""
import sys, struct, json, bisect
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, 'calling')
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_OP_IMM

EXE = r'D:\STEAM\steamapps\common\Hearts of Iron IV\hoi4.exe'
# actual path from session: D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe
EXE = r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe'

pe = PE(EXE)
pd = next(s for s in pe.sections if s.name == '.pdata')
raw_pd = pe.data[pd.raw_ptr:pd.raw_ptr + pd.raw_size]
functions = [struct.unpack_from('<III', raw_pd, o)[:2] for o in range(0, len(raw_pd) - 11, 12)]
starts = [x[0] for x in functions]
cs = Cs(CS_ARCH_X86, CS_MODE_64)
cs.detail = True

def pdata_window(rva):
    i = bisect.bisect_right(starts, rva) - 1
    if i < 0:
        return None
    start, end = functions[i]
    if not start <= rva < end:
        return None
    return start, end

def disasm_exact(entry, max_bytes=0x2000):
    """Disassemble from entry, prefer pdata end, clip at first ret of this function.
    If pdata is short, continue until ret or max_bytes, but stop if we enter the next pdata start."""
    win = pdata_window(entry)
    if win:
        start, pend = win
        # if entry is not the pdata start, still disassemble from entry
        end = min(entry + max_bytes, pend)
    else:
        start, end = entry, entry + max_bytes
        pend = end
    # also find next function start after entry
    j = bisect.bisect_right(starts, entry)
    next_start = starts[j] if j < len(starts) else entry + max_bytes
    hard_end = min(entry + max_bytes, max(pend, next_start))
    # if pdata end is very close to entry (thunk), still include it
    length = max(1, hard_end - entry)
    # if pdata ended too early (fragment), extend to next_start but we'll clip at ret
    if win and pend - entry < 16 and next_start > pend:
        length = min(max_bytes, next_start - entry)
        hard_end = entry + length
    raw = pe.read_rva(entry, length) or b''
    ins = list(cs.disasm(raw, entry))
    # clip at first ret/jmp-out that ends the function if we started at entry and it's a complete function
    clipped = []
    first_ret = None
    for i in ins:
        if i.address >= hard_end:
            break
        clipped.append(i)
        if i.mnemonic == 'ret':
            first_ret = i.address
            break
        # tail jmp to a different function can end too, but only if it's an unconditional jmp and not a mid-function jump
        if i.mnemonic == 'jmp' and i.operands and i.operands[0].type == CS_OP_IMM:
            target = i.operands[0].imm
            # if jumping outside this pdata window (and not a tiny thunk at start), treat as end if we already had calls
            if win and not (win[0] <= target < win[1]) and i.address != entry:
                # could be tail call - include it, then stop
                first_ret = i.address
                break
    return {
        'entry': hex(entry),
        'pdata': {'start': hex(win[0]), 'end': hex(win[1])} if win else None,
        'first_end': hex(first_ret) if first_ret is not None else None,
        'ins_count': len(clipped),
        'code': [{'rva': hex(i.address), 'asm': i.mnemonic + ' ' + i.op_str} for i in clipped],
        'calls': sorted({i.op_str.split()[-1] for i in clipped if i.mnemonic == 'call'}),
        'text': '\n'.join(f'{hex(i.address)}  {i.mnemonic} {i.op_str}' for i in clipped),
    }

def find_callers(target, scan_rvas=None):
    """Scan .text for E8 rel32 to target. Bounded: use whole .text but it's a file read, fine."""
    text = next(s for s in pe.sections if s.name == '.text')
    data = pe.data[text.raw_ptr:text.raw_ptr + text.raw_size]
    va = text.virtual_address  # this is RVA
    hits = []
    # E8 rel32
    pos = 0
    tgt = target
    while True:
        i = data.find(b'\xE8', pos)
        if i < 0:
            break
        if i + 5 <= len(data):
            rel = struct.unpack_from('<i', data, i + 1)[0]
            at = va + i
            dest = (at + 5 + rel) & 0xffffffff
            # RVAs in this pe are 32-bit; destinations are RVAs
            if dest == tgt:
                hits.append(at)
        pos = i + 1
        if len(hits) > 200:
            break
    # also E9 tail jmps
    jmps = []
    pos = 0
    while True:
        i = data.find(b'\xE9', pos)
        if i < 0:
            break
        if i + 5 <= len(data):
            rel = struct.unpack_from('<i', data, i + 1)[0]
            at = va + i
            dest = (at + 5 + rel) & 0xffffffff
            if dest == tgt:
                jmps.append(at)
        pos = i + 1
        if len(jmps) > 50:
            break
    callers = []
    for at in hits:
        w = pdata_window(at)
        callers.append({'at': hex(at), 'kind': 'call', 'func': hex(w[0]) if w else None})
    for at in jmps:
        w = pdata_window(at)
        callers.append({'at': hex(at), 'kind': 'jmp', 'func': hex(w[0]) if w else None})
    return callers

targets = [0x14075c0, 0x15b1da0, 0x15b1d90, 0x15b3220, 0x15b1de0, 0x15b2ab0]
out = {}
for t in targets:
    d = disasm_exact(t)
    Path(f'research/_t174_func_{hex(t)}.txt').write_text(d['text'] + '\n', encoding='utf-8')
    # also write a compact record
    rec = {k: d[k] for k in ('entry','pdata','first_end','ins_count','calls')}
    rec['text_path'] = f'research/_t174_func_{hex(t)}.txt'
    rec['callers'] = find_callers(t)
    # unique caller functions
    rec['caller_funcs'] = sorted({c['func'] for c in rec['callers'] if c['func']})
    rec['caller_count'] = len(rec['callers'])
    out[hex(t)] = rec
    print(hex(t), 'pdata', rec['pdata'], 'ins', rec['ins_count'], 'end', rec['first_end'],
          'calls', rec['calls'], 'callers', rec['caller_count'], 'funcs', rec['caller_funcs'][:20])

Path('research/t174_alloc_disasm_index.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print('wrote index')
