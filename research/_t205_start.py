from _t205_common import *
from _t205_flow import walk_flow
x=Runtime()
try:
 b=x.guard();out={'guard_before':b,'flows':{},'functions':{}}
 for a,n in((0x1349260,0x700),(0xd3f020,0x4b0),(0xd3f4d0,0x100)):
  raw=x.code(a,n);f=walk_flow(x.cs,raw,a);f['window_sha256']=hashlib.sha256(raw).hexdigest();out['flows'][hex(a)]=f;(R/f'research/_t205_flow_{a:x}.txt').write_text('\n'.join(f['asm']),encoding='utf8')
 for a in(0xce95a0,0x2573160,0xf42ad0):out['functions'][hex(a)]=x.clip(a)
 out['guard_after']=x.guard();assert out['guard_after']==b;(R/'research/t205_lifecycle_initial_flows.json').write_text(json.dumps(out,indent=2),encoding='utf8')
 (R/'research/t205_checkpoint.md').write_text("""# t205 checkpoint
## Block1 — measured usage, unchanged guards and new lifecycle CFG
Strict read-only game restrictions remain;0Post/gamewrite/remotecall/advance/save/D/commit-push. Rebound PID12948/base7FF7A91C0000, official pause1/speed0, game1936-01-02 15:00/tick60759398; six plans1/2/6/5/4/3 false; both OPEN markers absent, actual allow_post/write false per initial guard.
Usage measured32.8% at t205 start, shared weekly metric (not bot-specific spend). Earliest carried continuous measurement28.7% (t202), delta4.1pp; conservative continuous checkpoint threshold38.7%, not reset at each turn. Earlier unobserved consumption not inferred. Recheck before final report and stop if threshold reached; resetNov22 06:50EST.
New bounded per-instruction CFG for1349260,D3F020,D3F4D0 avoids assuming partial .pdata clips are full functions. Calls remain opaque and unresolved/control edges reported, not a global absence proof. In particular old D3F4D0 clip had only11 instructions and was incomplete. New flow artifacts saved without calling functions. No repeated zero-casualty sampling.
Current proof74/42 (30memory+12nonmemory), D historical72/44 unsynced;14tables116fields3columns unchanged. Research helper changes never imply full production capture acceptance; full capture remainsfalse/52required.
""",encoding='utf8')
 print('CFG',[(a,d['reachable_instruction_count'],d['unresolved_edges'],d['external_tails'])for a,d in out['flows'].items()]);print('FN',[(a,len(d['asm']))for a,d in out['functions'].items()]);print('D3F4D0','\n'.join(out['flows']['0xd3f4d0']['asm']));print('HASH_HEAD','\n'.join(out['functions']['0x2573160']['asm'][:55]))
finally:x.close()
