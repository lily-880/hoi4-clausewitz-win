
"""Read-only t171: recheck live session, finish 1409890 disassembly, inspect F70.

No Post, no memory write, no speed/pause/campaign change, no save I/O, no heap sweep.
"""
from __future__ import annotations
import os, sys, json, struct, hashlib, bisect
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'calling'))
from mem import Proc, find_pid
from pe import PE
from gamestate import _rtti_name_from_vtable, detect_session, resolve_player_country, read_campaign_summary
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

HERE = Path(__file__).resolve().parent
OUT = HERE/'t171_session_recheck.json'
profile=json.loads((HERE.parent/'calling/tables/offsets_input_windows_1.19.5.json').read_text(encoding='utf-8-sig'))

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest().upper()

def build_pdata(pe):
    pd=next(s for s in pe.sections if s.name=='.pdata')
    raw=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
    functions=[struct.unpack_from('<III',raw,o)[:2] for o in range(0,len(raw)-11,12)]
    starts=[x[0] for x in functions]
    return functions, starts

def bounds(functions, starts, target):
    i=bisect.bisect_right(starts, target)-1
    if i<0:
        return None
    start,end=functions[i]
    if not start<=target<end:
        # fragment: still return this window and note
        return {'start':start,'end':end,'covers':False,'index':i}
    return {'start':start,'end':end,'covers':True,'index':i}

def disasm_range(pe, cs, start, end, max_bytes=0x2000):
    size=min(end-start, max_bytes)
    raw=pe.read_rva(start, size) or b''
    ins=[]
    for i in cs.disasm(raw, start):
        ins.append({'rva':hex(i.address),'asm':(i.mnemonic+' '+i.op_str).strip(),'addr':i.address})
        if i.address+i.size>=start+size:
            break
    return ins, start+size

def continue_until_ret(pe, cs, functions, starts, entry, max_extend=8):
    """Disassemble a function, continuing past truncated .pdata fragments until a ret
    at depth 0 or a later pdata function that is clearly a new prologue. Bounded."""
    b=bounds(functions, starts, entry)
    if not b:
        return {'error':'no pdata','entry':hex(entry)}
    chunks=[]
    cur=b['start']
    expected_end=b['end']
    used=[b]
    for _ in range(max_extend):
        ins, consumed = disasm_range(pe, cs, cur, expected_end, 0x4000)
        chunks.extend(ins)
        # if last is ret or the window ended on ret, stop if we reached expected_end reasonably
        if ins and ins[-1]['asm'].startswith('ret') and consumed>=expected_end:
            break
        # if pdata ended mid-function, continue from end to next pdata start or +0x800
        nxt_i=bisect.bisect_left(starts, expected_end)
        next_start = functions[nxt_i][0] if nxt_i < len(functions) else expected_end+0x800
        # If next pdata start is immediately after, might be a split of same function
        # Continue at expected_end if we didn't see ret.
        if ins and ins[-1]['asm'].startswith('ret'):
            break
        if expected_end>=next_start and nxt_i < len(functions):
            # adjacent fragment
            frag=functions[nxt_i]
            cur=expected_end
            expected_end=frag[1]
            used.append({'start':frag[0],'end':frag[1],'covers':True,'index':nxt_i,'continued':True})
            continue
        # gap or need more bytes: extend a bounded tail
        cur=expected_end
        expected_end=min(next_start, expected_end+0x800)
        used.append({'start':cur,'end':expected_end,'covers':False,'continued':True,'reason':'tail-extend'})
    return {
        'entry':hex(entry),
        'windows':[{k: (hex(v) if k in ('start','end') and isinstance(v,int) else v) for k,v in w.items()} for w in used],
        'code':[{'rva':x['rva'],'asm':x['asm']} for x in chunks],
        'last': chunks[-1] if chunks else None,
        'count':len(chunks),
    }

def calls_of(fn):
    out=[]
    for x in fn['code']:
        if x['asm'].startswith('call '):
            out.append(x)
    return out

def memref_of(fn, needle):
    return [x for x in fn['code'] if needle in x['asm']]

p=None
try:
    p=Proc(find_pid('hoi4.exe'))
    digest=sha256_file(p.image_path)
    pe=PE(p.image_path)
    session=detect_session(p, pe)
    in_game=bool(session.get('in_game')) and session.get('session')=='in_game'
    result={
        'pid':p.pid,
        'path':p.image_path,
        'base':hex(p.base),
        'exe_sha256':digest,
        'fingerprint_matches':digest==profile['exe_sha256'],
        'session':session,
        'read_only':True,
        'expected_pid':26976,
        'pid_matches_t170':p.pid==26976,
    }
    if not result['fingerprint_matches']:
        result['stop']='unknown executable fingerprint; no layout reads'
        OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'stop':result['stop'],'pid':p.pid,'sha':digest},indent=2))
        sys.exit(0)
    if not in_game:
        result['stop']='HOI4 is running but not in a campaign (not CInGameIdler). No new scan started; no campaign started or changed.'
        OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'stop':result['stop'],'pid':p.pid,'session':session.get('session'),'idler':(session.get('signals') or {}).get('idler_class')},indent=2))
        sys.exit(0)
    gs=int(session['signals']['gs_ptr'],16) if isinstance(session['signals']['gs_ptr'],str) else session['signals']['gs_ptr']
    campaign=read_campaign_summary(p, gs)
    fields=campaign['fields']
    player=resolve_player_country(p, gs)
    speed=fields.get('game_speed_index')
    result.update({
        'gs':hex(gs),
        'player':player,
        'speed_index_4bc':speed,
        'speed_notch':fields.get('game_speed_notch'),
        'hour_progress':fields.get('game_hour_progress'),
        'date':fields.get('date_full'),
        'in_game':True,
    })
    if speed not in (0,None) and fields.get('game_speed_notch') not in (1,None):
        result['speed_warning']='game is not at 1x; not changing speed'
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')

    # --- disassembly of official need path (static exe bytes only) ---
    functions, starts = build_pdata(pe)
    cs=Cs(CS_ARCH_X86, CS_MODE_64)
    targets=['1409810','1409890','14080c0','140a400','1409e50','140a600','b2cb40','d498a0','d49890','31f8b0','cf4fe0']
    # also include whatever 1409890 calls once we have it
    disasm={}
    for t in targets:
        disasm[t]=continue_until_ret(pe, cs, functions, starts, int(t,16))
    # If 1409890 still incomplete, note
    Path(HERE/'t171_1409890_family_disasm.json').write_text(json.dumps(disasm,ensure_ascii=False,indent=2),encoding='utf-8')
    # compact listings
    listings={}
    for t,fn in disasm.items():
        if 'code' in fn:
            listings[t]='\n'.join(x['rva']+'  '+x['asm'] for x in fn['code'])
            listings[t+'_meta']={'windows':fn.get('windows'),'count':fn.get('count'),'last':fn.get('last')}
    Path(HERE/'t171_1409890_family_listings.json').write_text(json.dumps(listings,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({
        'pid':p.pid,'in_game':True,'tag':player.get('tag'),'index':player.get('player_index'),
        'speed_notch':fields.get('game_speed_notch'),'date':fields.get('date_full'),
        'disasm_counts':{t:disasm[t].get('count') for t in disasm},
        'disasm_last':{t:disasm[t].get('last') for t in disasm},
        '1409890_windows':disasm['1409890'].get('windows'),
        '1409890_calls':calls_of(disasm['1409890']),
        '14080c0_calls':calls_of(disasm['14080c0']) if 'code' in disasm['14080c0'] else disasm['14080c0'],
        '1409890_f70':memref_of(disasm['1409890'],'0xf70'),
        '1409890_f78':memref_of(disasm['1409890'],'0xf78'),
        '1409890_f98':memref_of(disasm['1409890'],'0xf98'),
        '1409890_fd0':memref_of(disasm['1409890'],'0xfd0'),
        '1409890_15a8':memref_of(disasm['1409890'],'0x15a8'),
    },indent=2))
finally:
    if p is not None:
        p.close()
