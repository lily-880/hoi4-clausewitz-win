"""t207 narrow host-specific proof: fielded manpower-missing membership, not casualties."""
import struct,sys,json,datetime,hashlib,unittest
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path[:0]=[str(R/'research'),str(R/'calling')]
from _t207_session import Runtime
from input_loaded_fields import unit_current_manpower

def missing(current,need):
 if type(current)is not int or type(need)is not int or min(current,need)<0:raise ValueError('nonnegative integer persons required')
 return max(need-current,0)
def positive_ids(rows):
 ids=[]
 for x in rows:
  d=missing(x['current'],x['need'])
  if d:
   if x['handle_type']!=51 or x['id']<=0:raise ValueError('unsupported positive unit identity')
   ids.append(x['id'])
 if len(ids)!=len(set(ids)):raise ValueError('duplicate positive identity')
 return sorted(ids)
def table(rt,t):
 p,cap,n=struct.unpack('<QII',rt.pr.read(t+8,16));assert 0<=n<=cap<=256 and (not n or p>=0x10000)
 pairs=list(struct.iter_unpack('<ii',rt.pr.read(p,n*8))) if n else []
 assert all(k>=0 and v>=0 for k,v in pairs) and len({k for k,v in pairs})==n
 return pairs
class NarrowTests(unittest.TestCase):
 def test_true_missing_not_remaining_or_losses(self):self.assertEqual(missing(3228,4000),772)
 def test_full_and_excess_have_no_missing(self):self.assertEqual((missing(4000,4000),missing(5000,4000)),(0,0))
 def test_unknown_positive_handle_fails_closed(self):
  with self.assertRaises(ValueError):positive_ids([{'id':7,'handle_type':4713,'current':1,'need':2}])
 def test_unknown_full_handle_is_not_given_an_id(self):self.assertEqual(positive_ids([{'id':7,'handle_type':4713,'current':2,'need':2}]),[])
 def test_noninteger_or_negative_rejected(self):
  for a,b in ((-1,0),(0,-1),(True,3),(1.2,4)):
   with self.assertRaises(ValueError):missing(a,b)
if __name__=='__main__':
 import io
 stream=io.StringIO();res=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NarrowTests));(R/'research/t207_manpower_tests.log').write_text(stream.getvalue(),encoding='utf-8');assert res.wasSuccessful()
 rt=Runtime()
 try:
  before=rt.guard();assert before['pause']==1;r=rt.reader();rows=[]
  for up in r.array(rt.country+0x290,4096):
   r.require(up,'CArmy');mp=up+0x3d0;r.require(mp,'CArmyManpower');assert rt.q(mp+0x48)==up
   v=table(rt,mp+8);n=table(rt,mp+0x28);cur=sum(x[1]for x in v);need=sum(x[1]for x in n)
   existing,ev=unit_current_manpower(r,up);assert cur==existing and need==ev['engine_need_total'] and missing(cur,need)==ev['engine_missing_formula']
   row={'ptr':hex(up),'id':r.i(up+0x1c),'handle_type':r.i(up+0x18),'owner_raw1d8':r.i(up+0x1d8),'current':cur,'need':need,'missing':missing(cur,need),'current_by_country':v,'need_by_country':n}
   if row['missing']:assert row['owner_raw1d8']==rt.index
   rows.append(row)
  ids=positive_ids(rows);assert ids==[388,428,462,490,2781,2787]
  r.stable();after=rt.guard();assert before==after
  native=json.loads((R/'research/t207_native_new_entrances.json').read_text(encoding='utf-8'))['functions']['0xcc6480'];assert not native['unresolved_edges'] and native['reachable_instruction_count']==17
  proof={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':before,'after':after,'field':'world.shortages.manpower.affected_unit_ids','affected_unit_ids':ids,'units_checked':len(rows),'positive_units':[x for x in rows if x['missing']],'all_unit_audit':rows,'sum_missing_for_audit_only':sum(x['missing']for x in rows),'sum_not_accepted_as_national_needed_or_deficit':True,'scope':'Current actual fielded own-unit manpower need exceeds current value. No claim of war-caused losses or national aggregate needed/deficit. Three nonstandard identity tags have zero missing and no fabricated emitted IDs.','proof_chain':['CC7A50 names value36FB and need36FC','CC6570 integer country/person sums','CC6480 exact17-insn max(need-current,0), independently re-read loaded image','15A8743->15A874E passes unit+3D0 and branches on positive missing','49 live own-unit tables/backlinks and independent direct parsing match existing strict reader;6 positive valid handle51 units; owner index3 each'],'tests_run':res.testsRun,'tests_failures':len(res.failures),'tests_errors':len(res.errors),'full_capture_run':False,'production_code_changed':False}
  (R/'research/t207_manpower_missing_proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:proof[k]for k in ('field','affected_unit_ids','units_checked','sum_missing_for_audit_only','tests_run','tests_failures','tests_errors')},indent=2));print(stream.getvalue())
 finally:rt.close()