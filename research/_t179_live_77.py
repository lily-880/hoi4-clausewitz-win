"""t179 live: session, bounded 77 scan. Read-only, no method execution."""
from __future__ import annotations
import os, sys, json, struct
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'calling'))
from mem import Proc, find_pid
from pe import PE
from gamestate import detect_session, resolve_player_country, read_campaign_summary, _rtti_name_from_vtable

HERE = Path(__file__).resolve().parent
FIXED = 100000
NEED77 = 77
NEED77_FIXED = 77 * FIXED  # 7700000

def demangle(n):
    if not n: return None
    if n.startswith('.?A') and n.endswith('@@'):
        return n[4:-2].split('@')[0]
    return n

def cls(pe, P, addr):
    if not addr or not (0x10000 < addr < 0x7fffffffffff):
        return None
    try:
        vt = P.u64(addr)
    except Exception:
        return None
    if not (P.base <= vt < P.base + P.image_size):
        return None
    try:
        n = _rtti_name_from_vtable(pe, vt - P.base)
        return demangle(n)
    except Exception:
        return None

def scan_obj(P, base, size, label, clsname=None):
    b = P.try_read(base, size) if hasattr(P, 'try_read') else None
    if not b:
        try:
            b = P.read(base, size)
        except Exception:
            return {'label':label,'ptr':hex(base),'class':clsname,'error':'unread','hits':[]}
    hits = []
    # qwords
    for off in range(0, len(b)-7, 8):
        v = struct.unpack_from('<q', b, off)[0]
        if v in (NEED77, NEED77_FIXED, -NEED77, -NEED77_FIXED):
            hits.append({'off':hex(off),'kind':'i64','value':v})
    # dwords (only distinctive FIXED; skip raw 77 due to false positives, but record 77 if aligned and neighboring looks numeric)
    for off in range(0, len(b)-3, 4):
        v = struct.unpack_from('<i', b, off)[0]
        if v in (NEED77_FIXED, -NEED77_FIXED):
            hits.append({'off':hex(off),'kind':'i32','value':v})
    return {'label':label,'ptr':hex(base),'class':clsname,'size':len(b),'hits':hits}

def main():
    pid = find_pid('hoi4.exe')
    out = {'expected_pid':26976,'pid':pid,'read_only':True,'no_game_method_execution':True}
    if not pid:
        out.update({'in_game':False,'stop':True,'reason':'no hoi4.exe'})
        Path('research/t179_session_recheck.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
        print('NO HOI4')
        return
    pe = PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')
    P = Proc(pid)
    try:
        session = detect_session(P, pe)
        gs_hex = (session.get('signals') or {}).get('gs_ptr')
        gs_ptr = int(gs_hex, 16) if isinstance(gs_hex, str) else None
        country = resolve_player_country(P, gs_ptr) if gs_ptr else {'ok':False,'reason':'no gs'}
        summary = read_campaign_summary(P, gs_ptr) if gs_ptr else {}
        country_ptr = country.get('country_ptr')
        if isinstance(country_ptr, str):
            country_ptr = int(country_ptr, 16)
        out.update({
            'pid_matches': pid==26976,
            'in_game': bool(session.get('in_game')),
            'session': session.get('session'),
            'idler': session.get('idler'),
            'player_index': country.get('player_index'),
            'tag': country.get('tag'),
            'country_ptr': hex(country_ptr) if country_ptr else None,
            'summary': summary,
        })
        # extra clock/speed from summary or GS
        print(json.dumps({k:out[k] for k in ('pid','pid_matches','in_game','session','player_index','tag')},indent=2,default=str))
        print('summary', json.dumps(summary, default=str, ensure_ascii=False)[:2000])
        if not session.get('in_game') or not country_ptr:
            out['stop'] = True
            Path('research/t179_session_recheck.json').write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')
            print('NOT IN GAME, STOP')
            return

        # known status map
        offs = {
            'CTechnologyStatus': 0xf60,
            'CProductionStatus': 0xf68,
            'CDeploymentStatus': 0xf70,
            'CReinforcementStatus': 0xf78,
            'CArmyUpgradesStatus': 0xf80,
            'CDiplomacyStatus': 0xf88,
            'CPoliticalStatus': 0xf90,
            'CLogisticsStatus': 0xf98,
            'CDecisionStatus': 0xfa0,
            'CCountryOccupationStatus': 0xfd0,
            'CCountryResources': 0x11f8,
        }
        objects = []
        objects.append(scan_obj(P, country_ptr, 0x1400, 'CCountry', cls(pe,P,country_ptr)))
        status_ptrs = {}
        for name, off in offs.items():
            p = P.u64(country_ptr + off)
            status_ptrs[name] = hex(p) if p else None
            c = cls(pe,P,p)
            objects.append(scan_obj(P, p, 0x800, name, c))
            # also scan a couple of known sub-arrays if they look like pdx arrays
        # production pool at +0x200
        prod = P.u64(country_ptr + 0xf68)
        if prod:
            objects.append(scan_obj(P, prod + 0x200, 0x100, 'production_plus_200', cls(pe,P,prod+0x200) or 'pool?'))
            # walk present rows via typical header +0x20 {begin, cap, size} or similar; bounded 64 rows
            # t177: 1095760 copies present rows at pool+0x20 stride 16 {type, qty FIXED}
            pool = prod + 0x200
            # try both pool itself and pool+0x20 as array header
            for hdr_off, label in ((0, 'pool_hdr0'), (0x20, 'pool_hdr20')):
                begin = P.u64(pool + hdr_off)
                cap = P.u32(pool + hdr_off + 8) if hasattr(P,'u32') else None
                # fallback
                raw = P.try_read(pool + hdr_off, 16) or b''
                if len(raw)>=16:
                    begin2 = struct.unpack_from('<Q', raw, 0)[0]
                    cap2, size2 = struct.unpack_from('<II', raw, 8)
                    rows=[]
                    if begin2 and 0 < size2 <= cap2 <= 4096:
                        blob = P.try_read(begin2, min(size2*16, 16*64)) or b''
                        for i in range(0, len(blob)//16):
                            typ, qty = struct.unpack_from('<Qq', blob, i*16)
                            tname = cls(pe,P,typ)
                            rows.append({'i':i,'type':hex(typ),'class':tname,'qty':qty,'qty_int': qty/FIXED if qty else 0})
                    objects.append({'label':label,'begin':hex(begin2),'cap':cap2,'size':size2,'rows':rows,
                                    'has_77': any(r['qty'] in (NEED77, NEED77_FIXED) for r in rows)})

        # reinforcement status +0x20 request list
        rs = P.u64(country_ptr + 0xf78)
        req_hits=[]
        if rs:
            raw = P.try_read(rs+0x20, 16) or b''
            if len(raw)>=16:
                begin, capsz = struct.unpack_from('<Q', raw, 0)[0], struct.unpack_from('<II', raw, 8)
                cap, size = capsz
                reqs=[]
                if begin and 0 < size <= cap <= 4096:
                    blob = P.try_read(begin, min(size*8, 8*64)) or b''
                    for i in range(len(blob)//8):
                        rp = struct.unpack_from('<Q', blob, i*8)[0]
                        c = cls(pe,P,rp)
                        sc = scan_obj(P, rp, 0x200, f'request_{i}', c)
                        reqs.append(sc)
                        # named need/produced
                        if rp:
                            produced = None
                            need = None
                            # request+0x38 produced pool, +0x78 need pool — values may be in those pools not the request itself
                            reqs[-1]['produced_pool'] = hex(P.u64(rp+0x38)) if P.u64(rp+0x38) else None
                            reqs[-1]['need_pool'] = hex(P.u64(rp+0x78)) if P.u64(rp+0x78) else None
                objects.append({'label':'reinforcement_plus20','begin':hex(begin),'cap':cap,'size':size,'requests':reqs})

        # logistics status larger window
        logi = P.u64(country_ptr + 0xf98)
        if logi:
            objects.append(scan_obj(P, logi, 0x1000, 'CLogisticsStatus_1k', cls(pe,P,logi)))

        hits = []
        def walk(o, path):
            if isinstance(o, dict):
                if o.get('hits'):
                    hits.append({**{k:o[k] for k in ('label','ptr','class') if k in o}, 'hits':o['hits']})
                for k,v in o.items():
                    walk(v, path+[k])
            elif isinstance(o, list):
                for i,v in enumerate(o):
                    walk(v, path+[i])
        walk(objects, [])
        out['status_ptrs'] = status_ptrs
        out['scan_hit_objects'] = [h for h in hits if h.get('hits')]
        out['scan_hit_count'] = sum(len(h['hits']) for h in out['scan_hit_objects'])
        Path('research/t179_session_recheck.json').write_text(json.dumps(out, indent=2, default=str, ensure_ascii=False), encoding='utf-8')
        Path('research/t179_bounded_77_scan.json').write_text(json.dumps({
            'need77': NEED77, 'need77_fixed': NEED77_FIXED,
            'objects': objects, 'hits_distinctive': out['scan_hit_objects'],
            'note': 'i32 77 itself was not scanned (too many false positives). Hits are 77 as i64 or 77*100000 as i32/i64.'
        }, indent=2, default=str, ensure_ascii=False), encoding='utf-8')
        print('HIT_OBJECTS', json.dumps(out['scan_hit_objects'], default=str)[:4000])
        print('hit_count', out['scan_hit_count'])
        print('prod rows', json.dumps([o for o in objects if 'rows' in o], default=str)[:2000])
    finally:
        P.close()

if __name__=='__main__':
    main()
