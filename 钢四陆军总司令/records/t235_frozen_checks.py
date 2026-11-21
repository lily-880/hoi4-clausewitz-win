"""Offline domain checks only, not a game adapter or confidence estimator."""
import hashlib

def code_integrity(j):
 for f in j['functions'].values():
  raw=bytes.fromhex(f['raw_hex'])
  if len(raw)!=f['window_size'] or hashlib.sha256(raw).hexdigest()!=f['sha256']:return False
 return True

def guard_ok(g,baseline):
 return g==baseline and g['pause']==1 and g['speed_slot']==0 and not any(g['markers'].values())

def confidence_from_research(_):
 # No qualified per-unit confidence consumer or live positive/negative samples.
 return None

def front_hold_failure_from_frontage(_):
 # Combat frontage fullness is not manpower-caused strategic hold failure.
 return None
