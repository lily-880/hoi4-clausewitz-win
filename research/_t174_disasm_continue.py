
"""Continue truncated listings; also nearby pdata and 14075c0 body after 0x14075ed."""
import sys, struct, json, bisect
from pathlib import Path
sys.path.insert(0, 'calling')
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_OP_IMM

EXE = r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe'
pe = PE(EXE)
pd = next(s for s in pe.sections if s.name == '.pdata')
raw_pd = pe.data[pd.raw_ptr:pd.raw_ptr + pd.raw_size]
functions = [struct.unpack_from('<III', raw_pd, o)[:2] for o in range(0, len(raw_pd) - 11, 12)]
starts = [x[0] for x in functions]
cs = Cs(CS_ARCH_X86, CS_MODE_64)
cs.detail = True

def nearby_pdata(rva, n=6):
    i = bisect.bisect_right(starts, rva)
    lo = max(0, i-n)
    hi = min(len(functions), i+n)
    return [{'start': hex(s), 'end': hex(e), 'size': e-s} for s,e in functions[lo:hi]]

def disasm_range(start, length):
    raw = pe.read_rva(start, length) or b''
    ins = list(cs.disasm(raw, start))
    return [{'rva': hex(i.address), 'asm': i.mnemonic+' '+i.op_str} for i in ins]

# nearby pdata around key functions
nearby = {
    hex(t): nearby_pdata(t) for t in
    [0x14075c0, 0x14075ed, 0x140762b, 0x15b1d80, 0x15b1d90, 0x15b1da0, 0x15b1dc4, 0x15b3220, 0x15b2ab0, 0x15b1de0]
}

# Continue 15b1da0 from 0x15b1dc4 (the jle target after the cap-store ret)
# Continue 14075c0 from 0x14075ed
# Also dump a generous window for both

def until_real_end(entry, hints, max_bytes=0x400):
    """Disassemble a generous window and include all ins until a ret that is not jumped over,
    or until the next pdata function that is a true new function after the last branch target."""
    raw = pe.read_rva(entry, max_bytes) or b''
    ins = list(cs.disasm(raw, entry))
    # collect branch targets
    targets = set()
    addrs = []
    for i in ins:
        addrs.append(i.address)
        if i.operands and i.operands[0].type == CS_OP_IMM and i.mnemonic in (
            'jmp','je','jne','ja','jb','jae','jbe','jg','jl','jge','jle','jo','jno','js','jns','jp','jnp','jrcxz','jecxz','call'
        ) and i.mnemonic != 'call':
            targets.add(i.operands[0].imm)
    last_needed = entry
    for t in targets:
        if entry <= t < entry + max_bytes:
            last_needed = max(last_needed, t)
    # include until a ret whose address is >= last_needed, and also include that ret
    # but stop before next obvious int3 padding run after such a ret
    out = []
    seen_covering_ret = False
    for i in ins:
        out.append(i)
        if i.mnemonic == 'ret' and i.address >= last_needed:
            seen_covering_ret = True
            break
        if i.mnemonic == 'int3' and i.address > last_needed and seen_covering_ret:
            out.pop(); break
    text = '\n'.join(f'{hex(i.address)}  {i.mnemonic} {i.op_str}' for i in out)
    return {
        'entry': hex(entry),
        'branch_targets': [hex(t) for t in sorted(targets) if entry <= t < entry+max_bytes],
        'last_needed': hex(last_needed),
        'end': hex(out[-1].address) if out else None,
        'ins_count': len(out),
        'calls': sorted({i.op_str.split()[-1] for i in out if i.mnemonic=='call'}),
        'text': text,
    }

full = {}
for entry, nbytes, name in [
    (0x14075c0, 0x200, '14075c0_full'),
    (0x15b1da0, 0x80, '15b1da0_full'),
    (0x15b1d90, 0x20, '15b1d90_full'),
    (0x15b3220, 0x30, '15b3220_full'),
    (0x15b2ab0, 0x20, '15b2ab0_full'),
    (0x15b1de0, 0x200, '15b1de0_full'),
]:
    d = until_real_end(entry, None, nbytes)
    Path(f'research/_t174_func_{name}.txt').write_text(d['text']+'\n', encoding='utf-8')
    rec = {k:d[k] for k in d if k!='text'}
    rec['path'] = f'research/_t174_func_{name}.txt'
    full[name] = rec
    print(name, 'ins', rec['ins_count'], 'end', rec['end'], 'targets', rec['branch_targets'], 'calls', rec['calls'])

# 140765f was listed as a caller of 15b1da0 / 15b1d90 — likely a sibling function
sib = until_real_end(0x140765f, None, 0x200)
Path('research/_t174_func_140765f_full.txt').write_text(sib['text']+'\n', encoding='utf-8')
full['140765f'] = {k:sib[k] for k in sib if k!='text'}
print('140765f ins', sib['ins_count'], 'end', sib['end'], 'calls', sib['calls'])

# pdata around 14075c0 family
print('NEAR 14075c0:')
for e in nearby['0x14075c0']:
    print(' ', e)

print('NEAR 15b1da0:')
for e in nearby['0x15b1da0']:
    print(' ', e)

Path('research/t174_alloc_disasm_continued.json').write_text(json.dumps({'nearby_pdata': nearby, 'funcs': full}, indent=2), encoding='utf-8')
print('done')
