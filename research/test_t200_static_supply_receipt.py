import json,sys,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'calling'))
from command_receipt import assess_pause_receipt
import post_abi
class Tests(unittest.TestCase):
 def test_accepted_does_not_mean_paused(self):
  d=assess_pause_receipt(accepted=True,requested_pause=True,observed_pause=0);self.assertFalse(d['state_change_confirmed']);self.assertFalse(d['official_pause_confirmed'])
 def test_missing_state_cannot_be_confirmed(self):
  d=assess_pause_receipt(accepted=True,requested_pause=True,observed_pause=None);self.assertTrue(d['needs_readonly_verification']);self.assertFalse(d['state_change_confirmed'])
 def test_actual_state_is_authoritative(self):
  d=assess_pause_receipt(accepted=True,requested_pause=True,observed_pause=1);self.assertTrue(d['state_change_confirmed']);self.assertTrue(d['official_pause_confirmed'])
 def test_historical_failure_and_recovery(self):
  a=json.loads((R/'research/t198_order_sample.json').read_text());b=json.loads((R/'research/t198_pause_recovery.json').read_text());self.assertFalse(assess_pause_receipt(accepted=a['posts'][-1]['post_rax']==1,requested_pause=True,observed_pause=a['pause'])['state_change_confirmed']);self.assertTrue(assess_pause_receipt(accepted=b['post']['post_rax']==1,requested_pause=True,observed_pause=b['after'])['state_change_confirmed'])
 def test_static_execution_addresses(self):
  self.assertEqual(post_abi.FN_EXECUTE_LOOP,0x22c4780);self.assertEqual(post_abi.EXECUTE_SITE_A,0x22c6d0d);self.assertEqual(post_abi.EXECUTE_SITE_B,0x22c484d);self.assertEqual(post_abi.CCommand_VT_TYPE_TOKEN,0x58)
 def test_new_supply_identity_proof(self):
  d=json.loads((R/'research/t200_rtti_hierarchies.json').read_text());s=next(x for x in d['CArmy']['bases']if x['name']=='.?AVCSupplyConsumer@@');self.assertEqual((s['mdisp'],s['pdisp']),(16,-1))
 def test_remaining_candidates_not_invented(self):
  d=json.loads((R/'research/t200_candidate_triage.json').read_text());self.assertEqual(sum(len(x)for x in d['groups'].values()),32)
 def test_no_automatic_recovery_actuator(self):
  text=(R/'calling/command_receipt.py').read_text();self.assertNotIn('import ',text);self.assertNotIn('do_post(',text);self.assertNotIn('_remote(',text)
if __name__=='__main__':unittest.main()
