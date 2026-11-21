import ast,inspect,unittest,copy
from pathlib import Path
import t230_frozen_adjudication as m

def base_payload():
    inventory=(Path(__file__).resolve().parent/'t230_inventory_before.md').read_bytes()
    literals=[{'text':m.DESIRED_NAME+' >= 0 && '+m.DESIRED_NAME+' < 1000 && "The following equations need some rework"'},{'text':'REQ_DIVS'},{'text':'garrison_order_headline'}]
    desired={'function':'0x697db0','literals':[{'site':'0x697f75','text':literals[0]['text']}]}
    membership={'req_divs_literals':[
        {'text':'garrison_order_headline'},{'text':'REQ_DIVS'},{'text':'GARRISON_ORDER_CONF'},{'text':'BATTLE_PLANS_X_WILL_BE_ASSIGNED'}
    ],'exported_fields':{},'treat_desired_as_missing':False,'treat_req_divs_as_missing':False,'treat_neighbor_fronts_as_own':False,
      'derived_required_minus_assigned_as_official_missing':False,'infer_combat_result_from_selector_xor':False}
    correction={'player_theatre':m.PLAYER_THEATRE,'country_theatre_array_count':1,'overlap_offsets_are_neighbor_theatre_plus_50':True,
                'neighbor_front_counts':[3,73,3,8],'own_fronts':[
                    {'id':1278,'kind':66,'theatre_back':m.PLAYER_THEATRE,'back_is_this_theatre':True},
                    {'id':76,'kind':66,'theatre_back':m.PLAYER_THEATRE,'back_is_this_theatre':True},
                    {'id':70,'kind':66,'theatre_back':m.PLAYER_THEATRE,'back_is_this_theatre':True},
                    {'id':1734,'kind':66,'theatre_back':m.PLAYER_THEATRE,'back_is_this_theatre':True},
                    {'id':1735,'kind':66,'theatre_back':m.PLAYER_THEATRE,'back_is_this_theatre':True},
                ]}
    session={'pid':10288,'base':'0x7ff758fc0000','country_index':3,'pause':1,'speed_slot':0,'hour_tick':60781105,'markers':{'safe_land_tool_gate.OPEN':False,'strategic_only_tool_gate.OPEN':False}}
    windows={va:{'window_size':p['window_size'],'sha256':p['sha256'],'unresolved_edges':list(p['unresolved']),'external_tails':[]} for va,p in m.ACCEPTED.items()}
    return dict(literals=literals,desired=desired,membership=membership,correction=correction,inventory_bytes=inventory,inventory_sha=m.INVENTORY_SHA,production=dict(m.PROD),session=session,native_windows=windows)

def replay_ok(**updates):
    p=base_payload();
    for k,v in updates.items():
        if k in p and isinstance(p[k],dict) and isinstance(v,dict): p[k]=copy.deepcopy(p[k])|v
        else: p[k]=v
    return m.replay(**p)

class MissingDivisionsTests(unittest.TestCase):
    def test_01_named_desired_is_present_and_not_exported_as_missing(self):
        r=replay_ok(); self.assertEqual(r['desired_named'],m.DESIRED_NAME); self.assertFalse(r['missing_divisions_promoted'])
    def test_02_desired_relabeled_as_missing_rejected(self):
        p=base_payload(); p['membership']['treat_desired_as_missing']=True
        with self.assertRaisesRegex(m.Rejected,'desired is not missing'): m.replay(**p)
    def test_03_req_divs_is_garrison_order_ui(self):
        r=replay_ok(); self.assertEqual(r['req_divs_scope'],'garrison_order_ui_partial')
    def test_04_req_divs_as_missing_rejected(self):
        p=base_payload(); p['membership']['treat_req_divs_as_missing']=True
        with self.assertRaisesRegex(m.Rejected,'garrison REQ_DIVS is not missing'): m.replay(**p)
    def test_05_req_divs_without_garrison_context_rejected(self):
        p=base_payload(); p['membership']['req_divs_literals']=[{'text':'REQ_DIVS'}]
        with self.assertRaisesRegex(m.Rejected,'req_divs garrison context'): m.replay(**p)
    def test_06_five_own_fronts_backpoint_to_player_theatre(self):
        r=replay_ok(); self.assertEqual(r['own_front_ids'],[1278,76,70,1734,1735]); self.assertEqual(r['own_front_count'],5)
    def test_07_neighbor_73_not_own_membership(self):
        p=base_payload(); p['membership']['treat_neighbor_fronts_as_own']=True
        with self.assertRaisesRegex(m.Rejected,'neighbors are not own'): m.replay(**p)
    def test_08_stride_overlap_must_stay_corrected(self):
        p=base_payload(); p['correction']['overlap_offsets_are_neighbor_theatre_plus_50']=False
        with self.assertRaisesRegex(m.Rejected,'stride correction'): m.replay(**p)
    def test_09_wrong_backpointer_rejected(self):
        p=base_payload(); p['correction']['own_fronts'][0]['theatre_back']='0x23e02f93d00'; p['correction']['own_fronts'][0]['back_is_this_theatre']=False
        with self.assertRaisesRegex(m.Rejected,'own back-pointer'): m.replay(**p)
    def test_10_kind_not_id_or_missing_count(self):
        p=base_payload(); p['correction']['own_fronts'][1]['kind']=1
        with self.assertRaisesRegex(m.Rejected,'own back-pointer'): m.replay(**p)
    def test_11_derived_required_minus_assigned_rejected(self):
        p=base_payload(); p['membership']['derived_required_minus_assigned_as_official_missing']=True
        with self.assertRaisesRegex(m.Rejected,'no derived official missing'): m.replay(**p)
    def test_12_export_missing_divisions_rejected(self):
        p=base_payload(); p['membership']['exported_fields']={'world.shortages.missing_divisions':[1,2,3]}
        with self.assertRaisesRegex(m.Rejected,'no missing_divisions export'): m.replay(**p)
    def test_13_combat_result_not_inferred_from_selector_xor(self):
        p=base_payload(); p['membership']['infer_combat_result_from_selector_xor']=True
        with self.assertRaisesRegex(m.Rejected,'no combat result inference'): m.replay(**p)
    def test_14_req_divs_window_stays_partial(self):
        p=base_payload(); p['native_windows']['0x177d240']['unresolved_edges']=[]
        with self.assertRaisesRegex(m.Rejected,'expected partial unresolved'): m.replay(**p)
    def test_15_desired_window_unexpected_tail_rejected(self):
        p=base_payload(); p['native_windows']['0x697db0']['external_tails']=[{'site':'0x1','target':'0x2'}]
        with self.assertRaisesRegex(m.Rejected,'unexpected tails'): m.replay(**p)
    def test_16_loader_is_not_staffing_and_hash_pinned(self):
        r=replay_ok(); self.assertNotIn('world.shortages.missing_divisions', r['promoted_fields'])
        self.assertEqual(m.ACCEPTED['0xf7be60']['sha256'],'1206a93105a587a509e03ff64da35e671253fbfa04aaef6aec406d7990d8a5c1')
    def test_17_official_theatre_array_is_one(self):
        p=base_payload(); p['correction']['country_theatre_array_count']=5
        with self.assertRaisesRegex(m.Rejected,'single official theatre'): m.replay(**p)
    def test_18_own_id_set_cannot_be_silently_extended(self):
        p=base_payload(); p['correction']['own_fronts'].append({'id':83,'kind':66,'theatre_back':m.PLAYER_THEATRE,'back_is_this_theatre':True})
        with self.assertRaisesRegex(m.Rejected,'own front ids'): m.replay(**p)
    def test_19_volunteer_or_frontage_names_are_not_required_for_proof_and_not_exported(self):
        r=replay_ok(); self.assertEqual(r['promoted_fields'],[])
    def test_20_wrong_desired_function_rejected(self):
        p=base_payload(); p['desired']['function']='0x177d240'
        with self.assertRaisesRegex(m.Rejected,'desired function'): m.replay(**p)
    def test_21_missing_desired_literal_rejected(self):
        p=base_payload(); p['desired']['literals']=[{'text':'some other assert'}]
        with self.assertRaisesRegex(m.Rejected,'desired literal present'): m.replay(**p)
    def test_22_neighbor_counts_are_recorded_not_owned(self):
        p=base_payload(); p['correction']['neighbor_front_counts']=[73]
        with self.assertRaisesRegex(m.Rejected,'neighbor counts recorded, not owned'): m.replay(**p)
    def test_23_existing_crisis_scope_not_expanded_by_this_certificate(self):
        r=replay_ok(); self.assertNotIn('world.crises.severity', r['promoted_fields'])
    def test_24_partial_req_divs_does_not_block_desired_pin(self):
        r=replay_ok(); self.assertEqual(r['desired_named'],m.DESIRED_NAME)
    def test_25_shared_inventory_byte_identical87_29(self):
        raw=(Path(__file__).resolve().parent/'t230_inventory_before.md').read_bytes()
        self.assertEqual(__import__('hashlib').sha256(raw).hexdigest(),m.INVENTORY_SHA)
        r=replay_ok(); self.assertEqual(r['promoted_fields'],[])
    def test_26_shared_native_integrity(self):
        self.assertEqual(m.NATIVE_CONTROLS['0x147c330'],'d47cee77d6354b55c8409394903552842feb1b9034e84a6b99cc88ee9bb735e6')
        replay_ok()
    def test_27_shared_session_drift_rejected(self):
        p=base_payload(); p['session']['hour_tick']=1
        with self.assertRaisesRegex(m.Rejected,'session clock'): m.replay(**p)
    def test_28_shared_production51_four_hash_baseline(self):
        p=base_payload(); p['production']=dict(p['production']); p['production']['calling/input_observation.py']='0'*64
        with self.assertRaisesRegex(m.Rejected,'production hashes'): m.replay(**p)
    def test_29_shared_adjudicator_has_no_IO_or_game_backend(self):
        src=inspect.getsource(m)
        forbidden=('open(','Path(','Runtime','requests','socket','subprocess','urllib','win32','Proc(')
        self.assertTrue(all(tok not in src for tok in forbidden))
        tree=ast.parse(src)
        calls={node.func.id for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)}
        self.assertNotIn('open',calls)
    def test_30_shared_gate_open_rejected(self):
        p=base_payload(); p['session']['markers']={'safe_land_tool_gate.OPEN':True,'strategic_only_tool_gate.OPEN':False}
        with self.assertRaisesRegex(m.Rejected,'open gates'): m.replay(**p)

if __name__=='__main__':
    unittest.main()
