import unittest,json,copy,struct,hashlib,ast
from pathlib import Path
import t228_cached_note_replay as m
Q=Path(__file__).resolve().parent
BASE=tuple(json.loads((Q/n).read_text()) for n in ('t228_cached_notes_probe.json','t228_scope_and_text_consumers.json','t228_native_text_chain.json'))
def patch(d,a,raw):
 seen=set()
 for row in d['raw_dependencies']:
  lo=int(row['address'],16);b=bytearray.fromhex(row['hex'])
  for i,v in enumerate(raw):
   if lo<=a+i<lo+len(b):b[a+i-lo]=v;seen.add(i)
  row['hex']=b.hex()
 assert len(seen)==len(raw)
class CachedNoteTests(unittest.TestCase):
 def setUp(self):self.p,self.s,self.c=copy.deepcopy(BASE)
 def run_note(self):return m.replay(self.p,self.s,self.c)
 def entry(self):return self.p['rows'][1]['entries'][0]
 def ep(self):return int(self.entry()['entry'],16)
 def manager(self):return int(self.p['rows'][1]['master'],16)-4*0x468
 def bad(self,reason):
  with self.assertRaisesRegex(m.Unproved,reason):self.run_note()
 def test_01_actual_active_cached_672_bytes(self):
  r=self.run_note();self.assertEqual(r['note_byte_length'],672);self.assertTrue(r['qualified_fields']['notes'].startswith('单位正严重缺乏补给。'))
 def test_02_genuine_absent3_not_low_master(self):
  self.assertEqual(self.p['rows'][0]['active_count'],0);self.assertNotEqual(self.run_note()['qualified_fields']['notes'],self.p['rows'][0]['master_delayed']['text'])
 def test_03_active_extended_not_53byte_master(self):
  self.assertEqual(self.p['rows'][1]['master_delayed']['length'],53);self.assertNotEqual(self.run_note()['qualified_fields']['notes'],self.p['rows'][1]['master_delayed']['text'])
 def test_04_delayed_not_22byte_instant(self):
  self.assertEqual(self.entry()['instant']['length'],22);self.assertNotEqual(self.run_note()['qualified_fields']['notes'],self.entry()['instant']['text'])
 def test_05_actual_newlines_and_11_richcodes_unchanged(self):
  t=self.run_note()['qualified_fields']['notes'];self.assertIn('\n\n',t);self.assertIn('\x11G右键点击\x11!',t);self.assertEqual(t.encode().hex(),self.entry()['delayed']['raw_hex'])
 def test_06_utf8_byte_count_not_character_count(self):
  t=self.run_note()['qualified_fields']['notes'];self.assertEqual(len(t.encode()),672);self.assertLess(len(t),672)
 def test_07_json_escape_roundtrip_no_rewrite(self):
  r=self.run_note();self.assertEqual(json.loads(json.dumps(r))['qualified_fields']['notes'],self.entry()['delayed']['text'])
 def test_08_different_group_scope_rejected(self):
  self.s['theater_group']=hex(int(self.s['theater_group'],16)+8);self.bad('native group membership')
 def test_09_nonzero_key0_rejected(self):
  for d in (self.p,self.s):patch(d,self.ep()+0x438,struct.pack('<Q',1))
  self.bad('active context keys')
 def test_10_nonzero_key3_rejected(self):
  for d in (self.p,self.s):patch(d,self.ep()+0x450,struct.pack('<Q',1))
  self.bad('active context keys')
 def test_11_no_active_cache_no_template_fallback(self):
  a=self.manager()+(4+0xf0e)*24;patch(self.p,a+12,struct.pack('<I',0));self.p['rows'][1]['active_count']=0;self.p['rows'][1]['entries']=[];self.bad('actual active4 not master fallback')
 def test_12_synthetic_localization_key_rejected(self):
  with self.assertRaisesRegex(m.Unproved,'localization key'):m.body_text('LOW_SUPPLIES_TIPS')
 def test_13_synthetic_unexpanded_placeholder_rejected(self):
  with self.assertRaisesRegex(m.Unproved,'unexpanded placeholder'):m.body_text('单位 $UNIT$ 缺补给')
 def test_14_malformed_cached_utf8_rejected(self):
  f=m.Frozen(self.p);ptr=f.q(self.ep()+0x28);patch(self.p,ptr,b'\xff');self.bad('cached UTF-8')
 def test_15_missing_raw_text_dependency_rejected(self):
  a=self.ep()+0x28;self.p['raw_dependencies']=[x for x in self.p['raw_dependencies'] if not int(x['address'],16)<=a<int(x['address'],16)+x['size']];self.bad('missing raw dependency')
 def test_16_overbound_string_length_rejected(self):
  patch(self.p,self.ep()+0x38,struct.pack('<Q',4097));self.bad('string byte length/capacity')
 def test_17_capacity_below_length_rejected(self):
  patch(self.p,self.ep()+0x40,struct.pack('<Q',1));self.bad('string byte length/capacity')
 def test_18_declared_note_without_raw_bytes_rejected(self):
  self.entry()['delayed']['text']='伪造说明';self.bad('raw cached metadata')
 def test_19_synthetic_sso_decoder_not_live_positive(self):
  raw=bytearray(32);raw[:2]=b'ok';struct.pack_into('<QQ',raw,16,2,15);f=m.Frozen({'raw_dependencies':[{'address':'0x1000','size':32,'hex':raw.hex()}]});meta={'length':2,'capacity':15,'raw_hex':'6f6b','text':'ok'};self.assertEqual(m.raw_text(f,0x1000,meta),'ok')
 def test_20_synthetic_unknown_control_rejected(self):
  with self.assertRaisesRegex(m.Unproved,'unknown text control'):m.body_text('说明\x00')
 def test_21_three_of25_cannot_relax_to_full_census(self):
  self.s['sample_count']=25;self.bad('three-of25 scope')
 def test_22_real_479_causal_predicate_still_mandatory(self):
  next(x for x in self.s['controls'] if x['unit_id']==479)['out_of_supply']=False;self.bad('raw witness controls')
 def test_23_independent_registration_producer_mandatory(self):
  del self.c['functions']['0xb61660'];self.bad('missing independent native producer')
 def test_24_named_advice_key_is_proof_not_emitted_note(self):
  self.s['literals']['0x29c5118']['ascii_prefix']='OTHER';self.bad('named cached advice producer')
 def test_25_group_advice_not_witness_diagnosis_or_severity(self):
  r=self.run_note();self.assertEqual(r['qualified_fields']['unit_ids'],[479]);self.assertEqual(r['qualified_fields']['province_ids'],[1780]);self.assertIn('如果通过海路运输',r['qualified_fields']['notes']);self.assertEqual(set(r['qualified_fields']),{'kind','unit_ids','province_ids','notes'});self.assertTrue(r['kind_is_composed_not_native_enum']);self.assertFalse(r['severity_exported']);self.assertFalse(r['complete_crisis_record']);self.assertFalse(r['complete_crisis_feed']);self.assertFalse(r['complete_input']);self.assertEqual((r['sampled_members'],r['native_member_count']),(3,25))
 def test_26_shared_inventory_exact_one_existing_row(self):
  a=(Q/'t228_inventory_before.md').read_bytes();b=(Q/'t228_inventory_proposed.md').read_bytes();self.assertEqual(hashlib.sha256(a).hexdigest(),'8c51a0318d5d72dc3b0d2a67325462c16c42629abffddb1438f18b774e636740');self.assertEqual(hashlib.sha256(b).hexdigest(),'8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3');aa=a.splitlines(keepends=True);bb=b.splitlines(keepends=True);self.assertEqual(len(aa),len(bb));self.assertEqual(sum(x!=y for x,y in zip(aa,bb)),1);s=b.decode();self.assertEqual(s.count('| 字段名 | 已验证/未验证 | 说明 |'),14);self.assertEqual(s.count('| 已验证 |'),87);self.assertEqual(s.count('| 未验证 |'),29);self.assertEqual(sum('| 已验证 |' in x or '| 未验证 |' in x for x in s.splitlines()),116)
 def test_27_shared_native_integrity_pins(self):
  self.c['functions']['0xb79d00']['raw_hex']='00';self.bad('native text integrity')
 def test_28_shared_unstable_session_rejected(self):
  self.p['after']['hour_tick']+=1;self.bad('unstable guard')
 def test_29_shared_production51_four_hashes_preserved(self):
  old=json.loads((Q/'t227_final_seal.json').read_text());self.assertEqual(old['production_baseline_fields'],51);self.assertEqual(len(old['production_hashes']),4);self.assertEqual(self.p['production_hashes'],old['production_hashes'])
 def test_30_shared_frozen_adapter_no_backend_or_io(self):
  a=ast.parse((Q/'t228_cached_note_replay.py').read_text());imports={n.module for n in ast.walk(a) if isinstance(n,ast.ImportFrom)}|{v.name for n in ast.walk(a) if isinstance(n,ast.Import) for v in n.names};self.assertLessEqual(imports,{'hashlib','re','struct','t227_qualified_crisis_replay'});self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in {'open','exec','eval','Runtime','Proc'} for n in ast.walk(a)))
