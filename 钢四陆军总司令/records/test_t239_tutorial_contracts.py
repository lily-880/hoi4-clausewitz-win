# Box-only offline native-evidence regression. Synthetic callback/vector cases do not call/write the game.
import json,hashlib,unittest
from pathlib import Path
Q=Path(__file__).resolve().parent;L=lambda n:json.loads((Q/(n+'.json')).read_text());H=lambda b:hashlib.sha256(b).hexdigest()
G=L('t239_fresh_guard');A=L('t239_tutorial_helper_contracts');B=L('t239_country_handle_and_offensive_consumer');C=L('t239_exact_helper_continuations');D=L('t239_country_lookup_and_subject_relation_pivot');V=L('t239_verified_vertex_exclusion');asm=lambda d,k:'\n'.join(d['functions'][k]['asm'])
def synthetic_matches(node,target,out=None):
 # Acyclic input only, native recursion model checks children, NOT the input root's vector.
 out=[] if out is None else out
 for child in node['children']:
  if target in child['vertices'] and child['id'] not in out:out.append(child['id'])
  synthetic_matches(child,target,out)
 return out
class Contract(unittest.TestCase):
 def test_01_both_exact_helpers_reachable_flow_closed(self):
  self.assertEqual(set(A['functions']),{'0x1a57380','0x1a57590'})
  for f in A['functions'].values():self.assertEqual(f['unresolved_edges'],[]);self.assertEqual(f['external_tails'],[])
 def test_02_completion_writes_and_named_event_not_safe_getter(self):
  for key,site in [('0x1a57380','1a57544'),('0x1a57590','1a576f0')]:
   a=asm(A,key);self.assertIn(site+' mov byte ptr [rax + 0x50], 1',a);self.assertIn('call 0xe49580',a);self.assertIn('call qword ptr [rax + 0xf8]',a);self.assertIn('tutorial_objective_done',{x['text'] for x in A['functions'][key]['literals']})
 def test_03_synthetic_completion_once_not_native_invocation(self):
  transition=lambda completed,found:(completed or found,int(found and not completed))
  self.assertEqual(transition(False,False),(False,0));self.assertEqual(transition(False,True),(True,1));self.assertEqual(transition(True,True),(True,0))
 def test_04_front_enum2_is_not_sufficient(self):
  a=asm(A,'0x1a57380')
  for x in ['cmp dword ptr [rax + 0x30], 2','mov rcx, qword ptr [rax + 0xa8]','test rcx, rcx','call qword ptr [rax + 8]','call 0xc085f0']:self.assertIn(x,a)
 def test_05_inline_target_is_eth_not_generic_front_type(self):
  x=B['inline_target_constant'];self.assertEqual(x['rva'],'0x2aa1804');self.assertTrue(bytes.fromhex(x['raw_hex']).startswith(b'ETH\0'));self.assertEqual(x['ascii_prefix'],'ETH')
 def test_06_country_theatre_orders_root_membership_path(self):
  for key in A['functions']:
   a=asm(A,key)
   for x in ['call 0xc07bf0','[rax + 0x168]','[rax + 0x174]','[rax + 0x80]','[rax + 0x8c]','[rax + 0x98]','[rax + 0xa4]']:self.assertIn(x,a)
 def test_07_country_lookup_is_table_pointer_output(self):
  a=asm(B,'0xc07bf0')
  for x in ['cmp dword ptr [rbx], 0','call 0xc08790','[rdi + 0x310]','mov rax, qword ptr [rax + rcx*8]']:self.assertIn(x,a)
 def test_08_country_normalization_is_gs340_map(self):
  a=asm(C,'0xc08790_full')
  for x in ['movsxd rdx, dword ptr [rbx]','[rcx + 0x340]','mov eax, dword ptr [rax + rdx*4]']:self.assertIn(x,a)
  remap=[0,3,2,3];self.assertEqual(remap[1],remap[3]);self.assertNotEqual(1,3)
 def test_09_equivalence_is_same_canonical_id_not_diplomacy(self):
  a=asm(C,'0xc085f0_full')
  for x in ['[r8 + 0x340]','[r8 + rdi*4]','cmp dword ptr [r8 + rdx*4], ecx','sete al']:self.assertIn(x,a)
  self.assertNotIn('call 0x10b9240',a)
 def test_10_actual_current_selected_country_scalar_control(self):
  self.assertEqual(B['selected_country_slots'],{'0x520':3,'0x524':0});self.assertEqual(D['country_lookup_sample'],dict(raw_index=3,canonical_index=3,matches_fresh_runtime_country=True,country_tag='SOV'))
 def test_11_partial_pdata_fragments_not_full_claim(self):
  for k,sz in [('0xc085f0',154),('0x10b9240',55)]:
   f=B['functions'][k];full=C['functions'][k+'_full'];self.assertEqual(f['window_size'],sz);self.assertTrue(f['unresolved_edges']);self.assertTrue(full['raw_hex'].startswith(f['raw_hex']));self.assertEqual(full['window_size'],1024);self.assertEqual(full['unresolved_edges'],[]);self.assertEqual(full['external_tails'],[])
 def test_12_offensive_consumer_is_recursive_children(self):
  a=asm(C,'0x10b9240_full')
  for x in ['[rcx + 0x1f8]','[rcx + 0x204]','mov r12d, r8d','mov r14, rdx','call 0x10b9240']:self.assertIn(x,a)
 def test_13_matching_vertex_membership_and_dedup_not_axis(self):
  a=asm(C,'0x10b9240_full')
  for x in ['[rbp + 0x70]','[rbp + 0x7c]','cmp dword ptr [rax], r12d','add rax, 4','cmp qword ptr [rcx], rbp','mov qword ptr [rax + rdx*8], rbp']:self.assertIn(x,a)
  self.assertIn('[r8 + 0x58]',asm(A,'0x1a57590'));self.assertIn('cmp dword ptr [rsp + 0x2c], 0',asm(A,'0x1a57590'))
 def test_14_synthetic_vector_controls_not_live_plan_samples(self):
  leaf=lambda i,v:dict(id=i,vertices=v,children=[])
  root=leaf(1,[9]);self.assertEqual(synthetic_matches(root,9),[])
  child=leaf(2,[9,9]);root['children']=[child,child];self.assertEqual(synthetic_matches(root,9),[2]);self.assertEqual(synthetic_matches(root,8),[])
  child['children']=[leaf(3,[8])];self.assertEqual(synthetic_matches(root,8),[3])
 def test_15_existing_verified_vertex_reader_hash_not_new_axis(self):
  self.assertEqual(V['source_sha256'],G['production_hashes']['calling/input_loaded_fields.py']);self.assertEqual(V['offset'],'0x70');self.assertEqual(V['already_verified_field'],'world.plans.vertex_province_ids');self.assertFalse(V['new_field_promotion']);e='\n'.join(V['excerpt']);self.assertIn('ip + 0x70',e);self.assertIn("'vertex_province_ids': path",e)
 def test_16_distinct_subject_relation_named_consumers(self):
  self.assertEqual({x['text'] for x in D['names']},{'TRIGGER_IS_PUPPET','TRIGGER_IS_SUBJECT','is_puppet','is_subject'});self.assertIn('TRIGGER_IS_PUPPET',{x['text'] for x in D['functions']['0x441970']['literals']});self.assertIn('TRIGGER_IS_SUBJECT',{x['text'] for x in D['functions']['0x442b60']['literals']})
 def test_17_large_keyword_initializer_not_captured_or_type_proof(self):
  self.assertNotIn('0x83760',D['functions']);r=[x for x in D['references'] if x['name']=='is_subject'][0];self.assertGreater(int(r['pdata'][1],16)-int(r['pdata'][0],16),0x8000);self.assertEqual(D['promotions'],[])
 def test_18_shared_fresh_guard_and_scope(self):
  self.assertTrue(G['safe']);self.assertEqual(G['before'],G['after']);self.assertEqual(G['rechecked_prior_native_windows'],154);self.assertEqual(G['before']['pause'],1);self.assertEqual(G['before']['speed_slot'],0);self.assertFalse(any(G['before']['markers'].values()))
  for d in (A,B,C,D):self.assertEqual(d['before'],G['before']);self.assertEqual(d['after'],G['before']);self.assertEqual(d['promotions'],[])
 def test_19_shared_raw_hashes_and_window_identity(self):
  self.assertEqual(len(L('t239_native_pins')),10);self.assertEqual(len(L('t239_all_native_pins')),164)
  for d in (A,B,C,D):
   for f in d['functions'].values():
    raw=bytes.fromhex(f['raw_hex']);self.assertEqual(len(raw),f['window_size']);self.assertEqual(H(raw),f['sha256']);self.assertIn(f'{f["window_start"]}/{len(raw)}',L('t239_native_pins'))
 def test_20_shared_inventory_production_gates(self):
  self.assertEqual(G['production_baseline_fields'],51);self.assertEqual(len(G['production_hashes']),4);self.assertEqual(G['version'],'1.19.5.0.7c6c');self.assertEqual(G['country_tag'],'SOV');self.assertEqual(H(Path('/workspace/hoi4-docs-latest/态势信息读取能力清单.md').read_bytes()),'8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3')
