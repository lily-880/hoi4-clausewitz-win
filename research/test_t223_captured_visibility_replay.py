import unittest,json,copy,ast
from pathlib import Path
import t223_captured_visibility_replay as m
Q=Path(__file__).parent
class VisibilityEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.d={p.name:json.loads(p.read_text()) for p in Q.glob('t223_*.json') if 'before' in json.loads(p.read_text())}
        self.n='t223_live_province_overlay_controls.json'
    def bad(self):
        with self.assertRaises(m.Unproved):m.replay(self.d)

    def test_01_activity_is_deployment_not_battleplan(self):
        self.assertFalse(m.replay(self.d)['equipment_affected_plans_promoted']);self.assertEqual(m.replay(self.d)['own_plan_arrays_read'],0)

    def test_02_wrong_plan_alias_rejected(self):
        self.d['t223_activity_receiver_identity.json']['status_class']='.?AVCOrderInstance@@';self.bad()

    def test_03_timed_progress_half_threshold_preserved(self):
        self.d['t223_timed_activity_equipment_consumers.json']['functions']['0xb88640']['asm'].remove('b887ff cmp qword ptr [rax], 0xc350');self.bad()

    def test_04_three_foreign_byte250_real_controls(self):
        self.assertEqual(m.replay(self.d)['foreign_byte250_count'],3)

    def test_05_two_foreign_byte255_real_controls(self):
        r=m.replay(self.d);self.assertEqual(sum(not x['own'] and x['native_renderer_byte']==255 for x in r['subjects']),2)

    def test_06_own_direct_shortcut_three(self):
        self.assertEqual(sum(x['own'] and x['native_renderer_byte']==255 for x in m.replay(self.d)['subjects']),3)

    def test_07_empty_tiers_not_invisible(self):
        r=m.replay(self.d);self.assertEqual(r['foreign_count'],5);self.assertTrue(all(x['passes250'] for x in r['subjects']))

    def test_08_tier0_overlay0_hidden_fragment(self):
        self.assertEqual(m.ordinary_land_opacity(0,0),0)

    def test_09_tier1_is150_not_one_third(self):
        self.assertEqual(m.ordinary_land_opacity(1,0),150)

    def test_10_tier2_is250(self):
        self.assertEqual(m.ordinary_land_opacity(2,0),250)

    def test_11_tier3_same_land250_not255(self):
        self.assertEqual(m.ordinary_land_opacity(3,0),250)

    def test_12_overlay255_dominates_empty_tier(self):
        self.assertEqual(m.ordinary_land_opacity(0,255),255)

    def test_13_overlay250_dominates_tier1(self):
        self.assertEqual(m.ordinary_land_opacity(1,250),250)

    def test_14_nonzero_modifier_not_silently_applied(self):
        self.d['t223_renderer_modifier_absence_control.json']['matches']=[{'id':587,'raw_value':100}];self.bad()

    def test_15_conditional_modifier_id_present_rejected(self):
        d=self.d['t223_renderer_modifier_absence_control.json'];d['id_list']=sorted(d['id_list']+[587]);d['entry_count']+=1;self.bad()

    def test_16_water_overlay_selector_rejected(self):
        self.d[self.n]['rows'][0]['geometry_low_bits']=0;self.bad()

    def test_17_sharing_override_interval_not_guessed(self):
        next(x for x in self.d[self.n]['rows'] if not x['own'])['raw_province_overlay_byte']=150;self.bad()

    def test_18_invalid_signed_tier_rejected(self):
        
        with self.assertRaises(m.Unproved):m.ordinary_land_opacity(-1,0)

    def test_19_invalid_overlay_byte_rejected(self):
        
        with self.assertRaises(m.Unproved):m.ordinary_land_opacity(0,256)

    def test_20_type4713_not_a_visibility_positive(self):
        self.d[self.n]['rows'][0]['handle_type']=4713;self.bad()

    def test_21_native150_threshold_not_relaxed(self):
        self.d['t223_visibility_renderer_root_and_gate.json']['functions']['0x131c770']['asm'].remove('131c833 cmp al, 0x96');self.bad()

    def test_22_independent250_threshold_required(self):
        self.d['t223_independent_counter_opacity_consumers.json']['functions']['0x170bda0']['asm'].remove('170bf8a cmp al, 0xfa');self.bad()

    def test_23_fog_enabled_not_bypass(self):
        self.d['t223_visibility_bypass_and_sharing_predicate.json']['bypass_switch_byte']=0;self.bad()

    def test_24_no_confidence_or_field_export(self):
        r=m.replay(self.d);self.assertFalse(any(r[k] for k in ['visible_units_promoted','spotted_promoted','confidence_promoted']));self.assertFalse(hasattr(m,'export_visible_units'));self.assertFalse(hasattr(m,'confidence'))

    def test_25_shared_integrity_native_bytes(self):
        f=self.d['t223_observer_visibility_getter.json']['functions']['0x16b2eb0'];f['raw_hex']='00'+f['raw_hex'][2:];self.bad()

    def test_26_shared_integrity_unclosed_cfg(self):
        self.d['t223_observer_visibility_getter.json']['functions']['0xc539d0']['unresolved_edges']=[{}];self.bad()

    def test_27_shared_integrity_mixed_tick(self):
        self.d[self.n]['after']['hour_tick']+=1;self.bad()

    def test_28_foreign_remap_shortcut_not_assumed_distinct(self):
        self.d['t223_subject_country_remap_control.json']['remap_indices']['443']=3
        self.bad()
