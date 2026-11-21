import unittest,json,copy,ast
from pathlib import Path
import t222_captured_connectivity_replay as m
Q=Path(__file__).parent
class ConnectivityTests(unittest.TestCase):
    def setUp(self):
        self.d={p.name:json.loads(p.read_text()) for p in Q.glob('t222_*.json') if 'before' in json.loads(p.read_text())}
        self.n='t222_home_landmass_fallback_positive_controls.json'
    def bad(self):
        with self.assertRaises(m.Unproved): m.replay(self.d)

    def test_01_supported_46_not_all49(self):
        self.assertEqual((m.replay(self.d)['supported_units'],m.replay(self.d)['rejected_units']),(46,3))

    def test_02_sixteen_flagzero_connected_not_isolated(self):
        self.assertEqual(len(m.replay(self.d)['flag_zero_but_connected']),16)

    def test_03_thirty_native_flag_shortcuts(self):
        self.assertEqual(m.replay(self.d)['flag_shortcut_count'],30)

    def test_04_no_disconnected_positive_no_promotion(self):
        r=m.replay(self.d);self.assertEqual(r['native_disconnected_count'],0);self.assertFalse(r['isolated_promoted'])

    def test_05_controllerarea_not_landmass(self):
        self.assertEqual(m.replay(self.d)['component_type'],'CControllerArea')

    def test_06_ratio_low_is_not_isolation(self):
        row=next(r for r in self.d[self.n]['rows'] if r['unit_id']==383);self.assertEqual(row['source_ratio_raw'],6655);self.assertTrue(m.replay(self.d)['results'][383]['native_connected'])

    def test_07_ratio_zero_no_change(self):
        self.d[self.n]['rows'][0]['source_ratio_raw']=0;self.assertTrue(m.replay(self.d)['results'][500]['native_connected'])

    def test_08_special_shortcut_pure_offline(self):
        row=copy.deepcopy(self.d[self.n]['rows'][0]);row.update(special=True,flag_1e=0,landmass='0x999');self.assertEqual(m.native_connected_short_branch(row,'0x123'),(True,'special'))

    def test_09_differentarea_fails_closed(self):
        row=copy.deepcopy(self.d[self.n]['rows'][3]);row.update(flag_1e=0,landmass='0x999');
        with self.assertRaises(m.Unproved):m.native_connected_short_branch(row,'0x123')

    def test_10_unsupported_type(self):
        row=self.d[self.n]['rows'][0];row['handle_type']=4713;
        with self.assertRaises(m.Unproved):m.native_connected_short_branch(row,self.d[self.n]['home_landmass'])

    def test_11_boolean_flag(self):
        self.d[self.n]['rows'][0]['flag_1e']=True;self.bad()

    def test_12_invalid_flag_value(self):
        self.d[self.n]['rows'][0]['flag_1e']=2;self.bad()

    def test_13_nonarmy_kind(self):
        self.d[self.n]['rows'][0]['kind']=1;self.bad()

    def test_14_wrong_selected_country(self):
        self.d[self.n]['rows'][0]['selected_country_tag']=4;self.bad()

    def test_15_wrong_capital_component(self):
        self.d[self.n]['home_landmass']='0x999';self.bad()

    def test_16_empty_capital_provinces(self):
        self.d[self.n]['capital_provinces']=[];self.bad()

    def test_17_provisional_landmass_name_rejected(self):
        self.d['t222_area_identity_control.json']['rows'][0]['area_class']='.?AVCLandmass@@';self.bad()

    def test_18_stale_connected_result(self):
        self.d[self.n]['rows'][0]['native_connected']=False;self.bad()

    def test_19_forged_isolation_positive(self):
        self.d[self.n]['isolation_positive_samples']=1;self.bad()

    def test_20_duplicate_unit_id(self):
        self.d[self.n]['rows'].append(copy.deepcopy(self.d[self.n]['rows'][0]));self.bad()

    def test_21_changed_tick(self):
        self.d[self.n]['after']['hour_tick']+=1;self.bad()

    def test_22_mixed_pid_session(self):
        self.d[self.n]['before']['pid']=6496;self.d[self.n]['after']['pid']=6496;self.bad()

    def test_23_open_gate(self):
        self.d[self.n]['before']['markers']['safe_land_tool_gate.OPEN']=True;self.d[self.n]['after']['markers']['safe_land_tool_gate.OPEN']=True;self.bad()

    def test_24_changed_native_bytes(self):
        f=self.d['t222_isolation_entrances.json']['functions']['0xe64c50'];f['raw_hex']='00'+f['raw_hex'][2:];self.bad()

    def test_25_unclosed_required_cfg(self):
        self.d['t222_named_encirclement_predicates.json']['functions']['0xc47c40']['unresolved_edges']=[{}];self.bad()

    def test_26_wrong_warning_polarity(self):
        self.d['t222_named_encirclement_predicates.json']['functions']['0xc47c40']['asm'].remove('c47c7b jne 0xc47c84');self.bad()

    def test_27_wrong_official_token(self):
        refs=self.d['t222_encircled_token_xrefs.json']['refs'];next(x for x in refs if x['site']=='0x173f5e6')['literal']='SOME_OTHER_TOKEN';self.bad()

    def test_28_missing_area_hash_fallback(self):
        self.d['t222_isolation_entrances.json']['functions']['0xe64c50']['asm'].remove('e64d18 call 0x12b6690');self.bad()

    def test_29_unsupported_cannot_be_accepted(self):
        next(r for r in self.d[self.n]['rows'] if r['handle_type']!=51)['accepted_identity']=True;self.bad()

    def test_30_no_live_imports_or_field_export(self):
        tree=ast.parse((Q/'t222_captured_connectivity_replay.py').read_text());names=[n.name for x in ast.walk(tree) if isinstance(x,(ast.Import,ast.ImportFrom)) for n in x.names];self.assertEqual(names,['hashlib']);self.assertFalse(hasattr(m,'export_isolated'))
