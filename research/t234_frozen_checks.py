"""Offline research-only checks; never a game adapter or schema producer."""
import hashlib

def lea_scope(wrapper_targets, controller_targets):
    if any(t!='0x33eb090' for t in wrapper_targets):
        raise ValueError('wrapper not second EndBundle')
    if any(t!='0x33eb020' for t in controller_targets):
        raise ValueError('controller path not first EndBundle')
    return '33eb090'

def null_ecx_before_call(asm, site):
    # Exact two-instruction prelude required: xor ecx, ecx then call F7E1C0.
    rows=list(asm)
    for i,a in enumerate(rows):
        if a.startswith(site[2:] if site.startswith('0x') else site):
            prev=rows[i-1] if i else ''
            return ('xor ecx, ecx' in prev) and ('call 0xf7e1c0' in a)
    return False

def pending_is_schema_value(pending):
    return False

def schema_front_invalidated_from_research(_):
    # Shared flush plus empty pending list and no stored flag: omission mandatory.
    return None

def navy_intel_define_is_unit_confidence(text):
    t=text.upper()
    if 'NNavy' in text or 'NNAVY' in t: return False
    if 'STRENGTH_ESTIMATE' in t or 'HALF_RANGE' in t: return False
    if t=='TRIGGER_INTEL_LEVEL_OVER': return False
    return None

def code_integrity(artifact):
    for f in artifact['functions'].values():
        b=bytes.fromhex(f['raw_hex'])
        if len(b)!=f['window_size'] or hashlib.sha256(b).hexdigest()!=f['sha256']:
            return False
    return True

def strict_guard(actual,baseline):
    return actual==baseline and actual['pause']==1 and actual['speed_slot']==0 and not any(actual['markers'].values())
