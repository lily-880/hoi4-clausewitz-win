# t243 final offline-only evidence review before user-requested STOPPED checkpoint.
import unittest,json,hashlib,io
from pathlib import Path
Q=Path(__file__).resolve().parent
load=lambda n:json.loads((Q/(n+'.json')).read_text(encoding='utf-8'))
P=load('t243_secondary_base_parser');C=load('t243_combat_logger_identity_callers');G=load('t243_fresh_guard');F={**P['functions'],**C['functions']};a=lambda k:'\n'.join(F[k]['asm'])
class Targeted(unittest.TestCase):
 def test_01_parser_preserves_secondary_receiver_argument(self):
  s=a('0xc58600');self.assertIn('c5861f mov rdi, rdx',s);self.assertIn('c58622 mov r14, rcx',s)
 def test_02_token_dispatch_not_native_runtime_isolation(self):
  s=a('0xc58600');self.assertIn('cmp r8d, 0x2ede',s);self.assertIn('cmp r8d, 0x286d',s);self.assertIn('call 0x2543530',s);self.assertIn('call 0x2543360',s)
 def test_03_real_loader_diagnostics_not_save_access(self):
  literals={x['text'] for x in F['0xc58600']['literals']};self.assertTrue(any('enemy territory' in x for x in literals));self.assertTrue(any('invalid location' in x for x in literals))
 def test_04_alias_register_changes_prevent_blanket_base_inference(self):
  s=a('0xc58600');self.assertIn('lea r15, [rcx + 0x1f0]',s);self.assertIn('mov r14, rax',s);self.assertIn('mov qword ptr [r14 + 0x1e8], rax',s)
 def test_05_distinct_combat_result_pivot_explicit(self):
  self.assertEqual(C['independent_pivot_field'],'world.combats.result');self.assertEqual(C['live_history_samples'],0);self.assertEqual(C['exact_callee'],'0xd3b6d0')
 def test_06_exact_reachable_caller_not_e8_byte_false_positive(self):
  rows=C['direct_call_candidates'];self.assertEqual(len(rows),1);self.assertTrue(rows[0]['admitted']);self.assertEqual(rows[0]['site'],'0x1349680');self.assertEqual(rows[0]['pdata'][:2],['0x1349260','0x134977a']);self.assertIn(dict(site='0x1349680',operand='0xd3b6d0'),F['0x1349260']['calls'])
 def test_07_observer_side_structure_not_active_history_id_bridge(self):
  s=a('0x1349260')
  for x in ['mov rsi, qword ptr [rcx + 0x30]','mov r13, qword ptr [rcx + 0x28]','lea r12, [rsi + 0x1d0]']:self.assertIn(x,s)
 def test_08_logger_actual_argument_chain(self):
  s=a('0x1349260')
  for x in ['1349677 mov r8, rax','134967a mov rdx, rdi','134967d mov rcx, r12','1349680 call 0xd3b6d0']:self.assertIn(x,s)
 def test_09_no_promotion_or_live_outcome_sample(self):
  self.assertEqual(P['promotions'],[]);self.assertEqual(C['promotions'],[]);self.assertEqual(C['live_history_samples'],0);self.assertIn('no result inference',C['scope'])
class Shared(unittest.TestCase):
 def test_10_two_new_native_hashes_and_pdata_bounds(self):
  self.assertEqual(len(F),2)
  for f in F.values():
   raw=bytes.fromhex(f['raw_hex']);self.assertEqual(hashlib.sha256(raw).hexdigest(),f['sha256']);self.assertEqual(len(raw),f['window_size']);self.assertEqual(f['window_start'],f['pdata'][0]);self.assertEqual(len(raw),int(f['pdata'][1],16)-int(f['pdata'][0],16));self.assertEqual(f['unresolved_edges'],[]);self.assertEqual(f['external_tails'],[])
 def test_11_same_safe_session_and_production_inventory(self):
  for d in [P,C,G]:self.assertEqual(d['before'],d['after']);self.assertEqual(d['before'],G['before'])
  b=G['before'];self.assertEqual((b['pause'],b['speed_slot'],b['hour_tick']),(1,0,60781105));self.assertFalse(any(b['markers'].values()));self.assertEqual(G['production_baseline_fields'],51);self.assertEqual(len(G['production_hashes']),4);self.assertEqual(hashlib.sha256(Path('/workspace/hoi4-docs-latest/态势信息读取能力清单.md').read_bytes()).hexdigest(),'8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3')
 def test_12_all_prior_pins_retained_and_two_new_exact_windows(self):
  old=load('t243_prior_all_native_pins');pins=load('t243_all_native_pins');self.assertEqual((len(old),len(pins)),(180,182));self.assertTrue(old.items()<=pins.items())
  for f in F.values():self.assertEqual(pins[f['window_start']+'/'+str(f['window_size'])]['sha256'],f['sha256'])
if __name__=='__main__':
 loader=unittest.TestLoader();suite=unittest.TestSuite([loader.loadTestsFromTestCase(Targeted),loader.loadTestsFromTestCase(Shared)]);ids=[t.id() for sub in suite for t in sub];out=io.StringIO();r=unittest.TextTestRunner(stream=out,verbosity=2).run(suite);report=dict(successful=r.wasSuccessful(),unique_methods=len(set(ids)),total_test_invocations=r.testsRun,targeted_methods=9,shared_methods=3,suite_starts=1,completed_suite_runs=1,failures=len(r.failures),errors=len(r.errors),collection_failures=0,method_ids=ids,output=out.getvalue());(Q/'t243_regression_attempt1.json').write_text(json.dumps(report,indent=2)+'\n');print(out.getvalue());raise SystemExit(not r.wasSuccessful())
