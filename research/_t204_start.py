from _t204_common import *
from _t203_battle_reader import battle_people_loss_candidate
from jsonschema import Draft202012Validator
import config
x=Runtime()
try:
 b=x.guard();assert not config.allow_post()and not config.allow_write();r=x.reader();rows=[]
 for cp in r.array(x.gs+0x268,4096):
  for off in(0x28,0x30):rows.append({'combat':hex(cp),'side':hex(off),**battle_people_loss_candidate(r,r.q(cp+off))})
 r.stable();assert x.guard()==b;out={'rows':rows,'guard_before':b,'guard_after':x.guard(),'schema_emission':False};(R/'research/t204_battle_reader_live_audit.json').write_text(json.dumps(out,indent=2),encoding='utf8')
 schema=json.loads((R/'calling/tables/generalissimo_input.schema.json').read_text(encoding='utf8'));checks=[]
 for label in('a','b'):
  p=R/f'research/t201_full_capture_recursive_{label}.json';d=json.loads(p.read_text(encoding='utf8'));es=list(Draft202012Validator(schema).iter_errors(d['observation']));assert not d['complete_input']and len(es)==52 and all(e.validator=='required'for e in es);checks.append({'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'complete_input':False,'required_errors':len(es)})
 (R/'research/t204_full_export_offline_validation.json').write_text(json.dumps(checks,indent=2),encoding='utf8');pending=json.loads((R/'research/t202_promotions_pending_inventory.json').read_text(encoding='utf8'));pending['t204_new_promotions']=[];pending['t204_note']='Existing t201 rows only; D never accessed; resumed97 tests passed; fresh battle observer zeros remain candidate';(R/'research/t204_promotions_pending_inventory.json').write_text(json.dumps(pending,ensure_ascii=False,indent=2),encoding='utf8')
 (R/'research/t204_checkpoint.md').write_text("""# t204 checkpoint
## Block 1 — resumed read-only guards and deferred acceptance
Device reconnected; cause of temporary disconnect unknown, no network/sleep inference. Fresh PID12948/base7FF7A91C0000; official pause1/speed0;1936-01-02 15:00/tick60759398 unchanged; plans1/2/6/5/4/3 false; allow_post=false,allow_write=false; both OPEN markers absent (t204_initial_guard.json).
Recovered box t203_checkpoint_pending_block4.md to approved research; SHA readback603ecc29b61d825452836e7eddf4834b2aef9c7741aa793eacd7cb8d8603e48d. That document records historical non-execution; this checkpoint supersedes its pending status only as verified below.
Deferred97 regressions now all passed (97/0fail/0error), actual log/json t204_resumed_97_tests. Fresh narrow people reader passed4 typed live sides; all0, no promotion/schema emission. Existing two full exports independently revalidated offline, each complete_input=false with52 required errors. No production full capture rerun; its mandatory D executable SHA/PE gate not bypassed.
All t203 block4 chains retained in recovered document and original research JSON. Candidate CLandCombatant+1D0 CStatsObserver+60 (side+230) is now the primary lifecycle/UI trace. Current74/42, remaining30memory+12nonmemory, D historical72/44 unsynced. t204 pending patch keeps only existing t201 supply rows, applied=false. 14tables116fields3columns unchanged.
0Post/0game write/0remote call/0time advance/0save access/0commit/push/0D accesses. Historical writer not executed/imported.
""",encoding='utf8')
 print(json.dumps({'guard':b,'rows':rows,'exports':checks},indent=2))
finally:x.close()
