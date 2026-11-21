"""t179: session recheck, 1409810 caller store analysis, bounded 77 scan.

Read-only. No Post, no memory write, no game-method execution, no campaign change.
"""
from __future__ import annotations
import os, sys, json, struct, bisect
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'calling'))
from mem import Proc, find_pid
from pe import PE
from gamestate import _rtti_name_from_vtable, detect_session, resolve_player_country, read_campaign_summary
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

HERE = Path(__file__).resolve().parent
IMAGE = 0x140000000

def cls_name(pe, P, addr):
    if not addr or not (0x10000 < addr < 0x7fffffffffff):
        return None
    b = P.try_read(addr, 8)
    if not b or len(b) < 8:
        return None
    vt = struct.unpack_from('<Q', b)[0]
    if not (P.base <= vt < P.base + P.image_size):
        return None
    try:
        n = _rtti_name_from_vtable(pe, vt - P.base)
        if n and n.startswith(('.?AV', '.?AU')) and n.endswith('@@'):
            # demangle lightly
            return n
    except Exception:
        return None
    return None

def demangle(n):
    if not n:
        return None
    # .?AVCFoo@@ or .?AVCFoo@ns@@
    core = n[4:-2] if n.startswith('.?A') and n.endswith('@@') else n
    return core.split('@')[0]

def u64(P, a):
    b = P.try_read(a, 8)
    return struct.unpack('<Q', b)[0] if b and len(b)==8 else None

def i64(P, a):
    b = P.try_read(a, 8)
    return struct.unpack('<q', b)[0] if b and len(b)==8 else None

def i32(P, a):
    b = P.try_read(a, 4)
    return struct.unpack('<i', b)[0] if b and len(b)==4 else None

def build_pdata(pe):
    pd = next(s for s in pe.sections if s.name=='.pdata')
    raw = pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
    functions = [struct.unpack_from('<III', raw, o)[:2] for o in range(0, len(raw)-11, 12)]
    starts = [x[0] for x in functions]
    return functions, starts

def fn_of(functions, starts, rva):
    i = bisect.bisect_right(starts, rva) - 1
    if i < 0:
        return None
    s, e = functions[i]
    return (s, e) if s <= rva < e else None

def e8_callers(blob, va, functions, starts, target):
    hits = []
    start = 0
    while True:
        j = blob.find(b'\xe8', start)
        if j < 0 or j+5 > len(blob):
            break
        rel = struct.unpack_from('<i', blob, j+1)[0]
        if va + j + 5 + rel == target:
            site = va + j
            f = fn_of(functions, starts, site)
            hits.append({'site': hex(site), 'func': hex(f[0]) if f else None, 'end': hex(f[1]) if f else None})
        start = j + 1
    return hits

def disasm_window(pe, cs, start, end, max_bytes=0x400):
    size = min(max(end-start, 0), max_bytes)
    raw = pe.read_rva(start, size) or b''
    out = []
    for i in cs.disasm(raw, start):
        out.append({'rva': hex(i.address), 'asm': (i.mnemonic+' '+i.op_str).strip()})
        if i.address + i.size >= start + size:
            break
    return out

def rip_leas(pe, cs, func_start, func_end, max_bytes=0x8000):
    size = min(func_end-func_start, max_bytes)
    raw = pe.read_rva(func_start, size) or b''
    hits = []
    for i in cs.disasm(raw, func_start):
        if i.mnemonic == 'lea' and 'rip' in i.op_str:
            # dest is last number in disp
            try:
                # capstone already resolves lea rX, [rip + disp] as absolute? usually "lea rdx, [rip + 0x..]"
                # compute dest = i.address + i.size + disp
                if i.operands and len(i.operands)>=2:
                    op = i.operands[1]
                    dest = i.address + i.size + op.mem.disp if op.type == 3 else None
                    if dest:
                        # read cstring
                        b = pe.read_rva(dest, 80) or b''
                        z = b.find(b'\x00')
                        s = b[:z].decode('ascii', 'replace') if z>0 and all(32<=c<127 or c in (9,) for c in b[:z]) else None
                        hits.append({'at': hex(i.address), 'dest': hex(dest), 's': s})
            except Exception:
                pass
    return hits

def main():
    pe_path = r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe'
    pe = PE(pe_path)
    functions, starts = build_pdata(pe)
    cs = Cs(CS_ARCH_X86, CS_MODE_64)
    cs.detail = True
    text = next(s for s in pe.sections if s.name=='.text')
    blob = pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
    va = text.virtual_address

    targets = {
        '1409810': 0x1409810,
        '1409890': 0x1409890,
        '14080c0': 0x14080c0,
        '1409630': 0x1409630,
        '2572ef0': 0x2572ef0,
        '254d0a0': 0x254d0a0,
    }
    e8 = {}
    for n,t in targets.items():
        h = e8_callers(blob, va, functions, starts, t)
        e8[n] = {'count': len(h), 'funcs': sorted({x['func'] for x in h if x['func']}), 'sites': h}
        print('E8', n, len(h), 'funcs', e8[n]['funcs'])

    # For each 1409810 call site, disassemble 0x80 bytes after the call and 0x40 before
    caller_windows = []
    for hit in e8['1409810']['sites']:
        site = int(hit['site'], 16)
        func = int(hit['func'], 16) if hit['func'] else site
        fend = int(hit['end'], 16) if hit['end'] else site+0x100
        pre = disasm_window(pe, cs, max(func, site-0x60), site)
        post = disasm_window(pe, cs, site, min(fend, site+0xc0))
        leas = rip_leas(pe, cs, func, min(fend, func+0x4000))
        strings = [x for x in leas if x.get('s')]
        post_asms = [x['asm'] for x in post]
        storeish = [x for x in post if any(k in x['asm'] for k in ('mov qword ptr [', 'mov dword ptr [', 'lock add', 'mov [', 'xchg'))]
        caller_windows.append({
            'site': hit['site'], 'func': hit['func'], 'end': hit['end'],
            'pre': pre[-12:], 'post': post[:28],
            'post_has_lock_add': any('lock add' in a for a in post_asms),
            'post_stores': storeish[:12],
            'nearby_strings': strings[:20],
        })
        print('SITE', hit['site'], 'FUNC', hit['func'], 'lock_add', any('lock add' in a for a in post_asms),
              'strings', [s['s'] for s in strings[:8]])

    Path('research/t179_1409810_callers.json').write_text(
        json.dumps({'e8': {k:{'count':v['count'],'funcs':v['funcs'],'sites':v['sites']} for k,v in e8.items()},
                    'windows': caller_windows}, ensure_ascii=False, indent=2),
        encoding='utf-8')

    # Live session
    pid = find_pid('hoi4.exe')
    if not pid:
        Path('research/t179_session_recheck.json').write_text(
            json.dumps({'pid': None, 'in_game': False, 'stop': True, 'reason': 'no hoi4.exe'}, indent=2),
            encoding='utf-8')
        print('NO HOI4')
        return
    P = Proc(pid)
    try:
        session = detect_session(P, pe)
        country = resolve_player_country(P, pe, session)
        summary = read_campaign_summary(P, pe, session, country)
        rec = {
            'pid': P.pid,
            'expected_pid': 26976,
            'pid_matches': P.pid==26976,
            'in_game': bool(session and session.get('in_game') if isinstance(session, dict) else session),
            'session': session if not isinstance(session, (bytes,)) else str(session),
            'country': country if not isinstance(country, (bytes,)) else str(country),
            'summary': summary if not isinstance(summary, (bytes,)) else str(summary),
            'read_only': True,
            'no_game_method_execution': True,
        }
        # detect_session / summary shapes may vary; also read well-known GS fields if present
        print(json.dumps({k: rec[k] for k in rec if k not in ('session','country','summary')}, indent=2))
        print('SESSION_TYPE', type(session), 'COUNTRY_TYPE', type(country))
        # dump compact
        def slim(x, depth=0):
            if depth>3:
                return '...'
            if isinstance(x, dict):
                return {k: slim(v, depth+1) for k,v in list(x.items())[:40]}
            if isinstance(x, (list, tuple)):
                return [slim(v, depth+1) for v in x[:20]]
            if isinstance(x, int) and x>0x10000:
                return hex(x)
            return x
        rec['session_slim'] = slim(session)
        rec['country_slim'] = slim(country)
        rec['summary_slim'] = slim(summary)
        Path('research/t179_session_recheck.json').write_text(json.dumps(rec, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        print('slim session', json.dumps(rec['session_slim'], ensure_ascii=False, default=str)[:2000])
        print('slim summary', json.dumps(rec['summary_slim'], ensure_ascii=False, default=str)[:2000])
        print('slim country', json.dumps(rec['country_slim'], ensure_ascii=False, default=str)[:2000])
    finally:
        P.close()

if __name__=='__main__':
    main()
