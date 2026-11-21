import copy,json,unittest
from pathlib import Path
from t211_native_keep_certificate import load,ongoing
Q=Path(__file__).resolve().parent
class NativeKeepCertificateTests(unittest.TestCase):
    def setUp(self): self.d=load(Q); self.ptr=self.d[0]['combats'][0]['ptr']
    def result(self): return ongoing(self.d,self.ptr)
    def side(self): return self.d[0]['combats'][0]['sides'][0]
    def test_two_current_positives(self):
        for index,cid in [(0,3096),(2,3097)]:
            with self.subTest(combat_id=cid):
                r=ongoing(self.d,self.d[0]['combats'][index]['ptr']);self.assertEqual((r['combat_id'],r['phase']),(cid,'ongoing'))
    def test_unknown_handle_3072_rejected(self): self.assertIsNone(ongoing(self.d,self.d[0]['combats'][1]['ptr']))
    def test_guard_mismatch(self): self.d[1]['guard']['hour_tick']+=1;self.assertIsNone(self.result())
    def test_removed_or_skipped(self): self.d[0]['combats'][0]['flags_51_52'][1]=1;self.assertIsNone(self.result())
    def test_uninitialized(self): self.d[0]['combats'][0]['flags_51_52'][0]=0;self.assertIsNone(self.result())
    def test_forced_end(self): self.side()['flagD9']=1;self.assertIsNone(self.result())
    def test_low_total(self): self.side()['members'][0]['raw420']=999;self.assertIsNone(self.result())
    def test_no_units(self): self.side()['members']=[];self.assertIsNone(self.result())
    def test_no_frontline(self): self.side()['frontline']=[];self.assertIsNone(self.result())
    def test_average_equal_threshold_ends(self): self.side()['members'][0]['raw428']=100000;self.assertIsNone(self.result())
    def test_no_active_hostility(self): self.d[1]['rows'][0]['flag49']=1;self.assertIsNone(self.result())
    def test_same_remapped_index_not_hostile(self): self.d[1]['rows'][0]['target_index']=self.d[1]['rows'][0]['source_index'];self.assertIsNone(self.result())
    def test_unbound_virtual_slot(self): self.d[2]['combat_slots'][self.ptr]['128']=0;self.assertIsNone(self.result())
    def test_duplicate_frontline(self): self.side()['frontline']*=2;self.assertIsNone(self.result())
    def test_native_overflow_unsupported(self): self.side()['members'][0]['raw428']=2**63-1;self.assertIsNone(self.result())
    def test_missing_country(self): self.side()['countrytags']=[];self.assertIsNone(self.result())
    def test_young_battle_omitted(self): self.d[0]['combats'][0]['clock44']=3;self.assertIsNone(self.result())
    def test_exact_phase_schema_enum(self):
        schema=json.loads((Q.parent/'calling/tables/generalissimo_input.schema.json').read_text(encoding='utf-8'))
        self.assertEqual(schema['$defs']['Combat']['properties']['phase']['enum'],['ongoing','ended']);self.assertIn(self.result()['phase'],schema['$defs']['Combat']['properties']['phase']['enum'])
if __name__=='__main__':unittest.main(verbosity=2)
