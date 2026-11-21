import unittest,json,copy,ast
from pathlib import Path
import t224_captured_reveal_replay as m
Q=Path(__file__).parent
class RevealGateTests(unittest.TestCase):
    def setUp(self):
        self.d={p.name:json.loads(p.read_text()) for p in Q.glob('t224_*.json') if 'before' in json.loads(p.read_text())}
        self.n='t224_native_positive_negative_controls.json';self.r='t224_reveal_operand_verification.json'
    def bad(self):
        with self.assertRaises(m.Unproved):m.replay(self.d)

    def test_01_real399_revealed_positive(self):
        r=m.replay(self.d);self.assertEqual(r['visible_units'],[{'unit_id':399,'visibility':{'spotted':True}}])

    def test_02_real481_native_negative_not_emitted(self):
        r=m.replay(self.d);self.assertEqual(r['control_audit']['481'],{'native_byte':0,'spotted':False});self.assertNotIn(481,[x['unit_id'] for x in r['visible_units']])

    def test_03_general_plate_is_not_spotted_cutoff(self):
        lit=self.d['t224_consumer_semantic_literals.json']['consumer_literals'];self.assertTrue(any(x['consumer']=='0x170bda0' and x['literal']=='deployed_general_base_plate' for x in lit));self.assertTrue(m.native_revealed(150))

    def test_04_named_revealed_literal_required(self):
        next(x for x in self.d['t224_consumer_semantic_literals.json']['consumer_literals'] if x['site']=='0x134af80')['literal']='UNRELATED';self.bad()

    def test_05_warflag49_branch_cannot_be_assumed(self):
        self.d[self.n]['war_flag49']=1;self.bad()

    def test_06_warrelation_receiver_not_generic_war(self):
        self.d[self.n]['war_class']='.?AVCWar@@';self.bad()

    def test_07_negative_requires_raw_zero_tier_header(self):
        next(x for x in self.d[self.r]['rows'] if x['unit_id']==481)['observer_table_header_hex']='00000000000000000100000001000000';self.bad()

    def test_08_negative_cannot_ignore_tier1(self):
        self.d[self.n]['negative']['tier_from_table_or_default']=1;self.bad()

    def test_09_fresh_province_join_required(self):
        self.d[self.n]['negative']['province_id']+=1;self.bad()

    def test_10_bounded_two_candidates_not_full_feed(self):
        r=m.replay(self.d);self.assertFalse(r['complete_visible_feed']);self.assertFalse(r['complete_input']);self.assertEqual(self.d[self.n]['inspected_candidates'],2)

    def test_11_full_feed_claim_rejected(self):
        self.d[self.n]['complete_visible_feed']=True;self.bad()

    def test_12_native_reveal_boundary149_150(self):
        self.assertFalse(m.native_revealed(149));self.assertTrue(m.native_revealed(150))

    def test_13_qualified_branch_not_semantic250_threshold(self):
        self.assertTrue(m.native_revealed(150));
        with self.assertRaises(m.Unproved):m.qualified_revealed(150)

    def test_14_confidence_not_opacity_normalization(self):
        r=m.replay(self.d);self.assertFalse(r['confidence_exported']);self.assertNotIn('confidence',r['visible_units'][0]['visibility'])

    def test_15_relation_not_fabricated_from_warflag(self):
        r=m.replay(self.d);self.assertFalse(r['relation_exported']);self.assertNotIn('relation_to_player',r['visible_units'][0])

    def test_16_live_negative_is_mandatory(self):
        self.d[self.n]['negative']=None;self.bad()

    def test_17_live_positive_is_mandatory(self):
        self.d[self.n]['positive']=None;self.bad()

    def test_18_low_overlay_positive_not_enough(self):
        self.d[self.n]['positive']['province_overlay']=150;next(x for x in self.d[self.r]['rows'] if x['unit_id']==399)['province_overlay_byte']=150;self.bad()

    def test_19_shared_gate_51_unchanged(self):
        self.d[self.n]['negative']['handle_type']=4713;self.bad()

    def test_20_shared_gate_remap(self):
        self.d[self.r]['remap_indices']['443']=3;self.bad()

    def test_21_shared_gate_fog(self):
        self.d[self.r]['fog_enabled_byte']=0;self.bad()

    def test_22_shared_gate_modifier(self):
        d=self.d[self.r];d['modifier_id_list']=sorted(d['modifier_id_list']+[587]);d['modifier_entry_count']+=1;self.bad()

    def test_23_shared_gate_geometry(self):
        self.d[self.n]['negative']['geometry_low_bits']=0;self.bad()

    def test_24_shared_integrity_bytes(self):
        f=self.d['t224_native_reveal_chain.json']['functions']['0x134ae00'];f['raw_hex']='00'+f['raw_hex'][2:];self.bad()

    def test_25_shared_integrity_session(self):
        self.d[self.n]['after']['hour_tick']+=1;self.bad()

    def test_26_shared_integrity_no_live_backend(self):
        tree=ast.parse((Q/'t224_captured_reveal_replay.py').read_text());names=[n.name for x in ast.walk(tree) if isinstance(x,(ast.Import,ast.ImportFrom)) for n in x.names];self.assertEqual(names,['hashlib','struct'])
