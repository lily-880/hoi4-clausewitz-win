"""Offline research-only checks; never a game adapter or schema producer."""
import hashlib

def resolve_key(direct,enemy_count=None,enemy_first=None):
    # Exact selected F69F30 rejection predicate, excluding debug assertion switches.
    if direct:return direct
    if enemy_count is None or enemy_count==0:return None
    if enemy_count<0:raise ValueError('invalid fixture count')
    return enemy_first or None

def own_membership(theatre):
    fronts=theatre['fronts'];by={x['pointer']:x for x in fronts}
    if len(by)!=len(fronts):raise ValueError('duplicate current front')
    if not all(x['theatre_back']==theatre['pointer'] and x['kind']==66 for x in fronts):raise ValueError('wrong theatre or kind')
    rows=theatre['dictionary_rows']
    if len(rows)!=len(fronts) or {x['front'] for x in rows}!=set(by):raise ValueError('not exact dictionary membership')
    if not all(x['front_class']=='.?AVCFront@@' for x in rows):raise ValueError('wrong RTTI')
    return set(by)

def code_integrity(artifact):
    for f in artifact['functions'].values():
        b=bytes.fromhex(f['raw_hex'])
        if len(b)!=f['window_size'] or hashlib.sha256(b).hexdigest()!=f['sha256']:return False
    return True

def strict_guard(actual,baseline):
    return actual==baseline and actual['pause']==1 and actual['speed_slot']==0 and not any(actual['markers'].values())

def schema_invalidated_from_research(_):
    # No qualified native war-change witness or semantic bridge: omission mandatory.
    return None
