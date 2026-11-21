"""Offline fixtures and exact artifact witnesses. Never imports Runtime or live commands."""
import json,struct,unittest
from pathlib import Path
from research._t203_delivery_reader import scalar_array,tag_index,robin_lookup,main_area,delivery_possible
from input_observation import ObservationError
ROOT=Path(__file__).resolve().parent
class Memory:
 def __init__(self):self.mem={};self.classes={}
 def put(self,a,fmt,*v):
  for k,b in enumerate(struct.pack(fmt,*v)):self.mem[a+k]=b
 def exact(self,a,n):
  try:return bytes(self.mem[a+k]for k in range(n))
  except KeyError:raise ObservationError('unmapped fixture read')
 def q(self,a):return struct.unpack('<Q',self.exact(a,8))[0]
 def i(self,a):return struct.unpack('<i',self.exact(a,4))[0]
 def require(self,a,c):
  if self.classes.get(a)!=c:raise ObservationError('wrong fixture RTTI')
 def array(self,a,b):
  p,n=scalar_array(self,a,8,b);return list(struct.unpack('<'+'Q'*n,self.exact(p,n*8)))if n else[]
 def arr(self,a,p,vs):self.put(a,'<QII',p,len(vs),len(vs));self.put(p,'<'+'Q'*len(vs),*vs)
def table(m,a,p,stride,probe,keyoff,valoff,wide=False,rows=()):
 m.put(a+0x28,'<Q',p);m.put(a+0x34,'<iB',0,3)
 for j in range(4):
  m.put(p+j*stride+probe,'<B',0);m.put(p+j*stride+keyoff,'<i',0);m.put(p+j*stride+valoff,'<Q'if wide else'<i',0)
 for j,k,v in rows:
  m.put(p+j*stride+probe,'<B',j+1);m.put(p+j*stride+keyoff,'<i',k);m.put(p+j*stride+valoff,'<Q'if wide else'<i',v)
def fixture():
 m=Memory();g,a,c,st,pp,mp,area,ma=(i*0x100000 for i in range(1,9))
 m.classes.update({a:'CArmy',c:'CCountry',st:'CState',pp:'CProvince',mp:'CProvince',area:'CControllerArea',ma:'CControllerArea'})
 m.put(a+0x2f8,'<Q',0);m.put(a+0x2e,'<B',0);m.put(a+0x1f0,'<Q',pp);m.put(a+0x1dc,'<i',0);m.put(a+0x1d8,'<i',0)
 m.put(pp+0xd0,'<Q',area);m.put(c+8,'<i',0);m.put(c+0x1018,'<i',1)
 m.arr(g+0x310,0x1100000,[c]);m.arr(g+0x2c8,0x1200000,[0,st]);m.arr(st+0x18,0x1300000,[mp]);m.put(mp+0x188,'<i',0);m.put(mp+0xd0,'<Q',ma);m.put(ma+0x3c,'<i',12)
 m.put(g+0x3d8,'<Q',0x1400000);m.put(0x1400108,'<Q',0x1500000);m.put(0x1500000,'<Q',0x1600000)
 m.put(g+0x698,'<Q',0x1700000);m.arr(area+0xb0,0x1800000,[pp]);m.put(pp+0xa4,'<i',7)
 table(m,0x1700000,0x1900000,24,4,8,16,True,[(0,7,0x123456789)])
 m.put(0x1600080,'<Q',0x1b00000);table(m,0x1b00000,0x1a00000,12,0,4,8,False,[(0,7,0)])
 return m,g,a,c,st,pp,mp,area,ma
class DeliveryPure(unittest.TestCase):
 def test_scalar_valid(self):
  m=Memory();m.put(0x100,'<QII',0x20000,3,2);self.assertEqual(scalar_array(m,0x100,4,5),(0x20000,2))
 def test_scalar_bad_count(self):
  m=Memory();m.put(0x100,'<QII',0x20000,1,2)
  with self.assertRaises(ObservationError):scalar_array(m,0x100,4,5)
 def test_tag_alias(self):
  m=Memory();m.put(0x1340,'<QII',0x20000,3,3);m.put(0x20000,'<iii',0,4,4);self.assertEqual(tag_index(m,0x1000,2),4)
 def test_tag_out_of_range(self):
  m=Memory();m.put(0x1340,'<QII',0x20000,1,1)
  with self.assertRaises(ObservationError):tag_index(m,0x1000,2)
 def test_integer_route_zero(self):
  m=Memory();table(m,0x1000,0x20000,12,0,4,8,rows=[(0,7,0)]);self.assertEqual(robin_lookup(m,0x1000,7,12,0,4,8),0)
 def test_hash_absence(self):
  m=Memory();table(m,0x1000,0x20000,12,0,4,8);self.assertIsNone(robin_lookup(m,0x1000,7,12,0,4,8))
 def test_hash_collision(self):
  m=Memory();table(m,0x1000,0x20000,12,0,4,8,rows=[(0,7,8),(1,42,55)]);self.assertEqual(robin_lookup(m,0x1000,42,12,0,4,8),55)
 def test_pointer_not_truncated(self):
  m=Memory();table(m,0x1000,0x20000,24,4,8,16,True,[(0,7,0x123456789)]);self.assertEqual(robin_lookup(m,0x1000,7,24,4,8,16,True),0x123456789)
 def test_non_power_mask_rejected(self):
  m=Memory();table(m,0x1000,0x20000,12,0,4,8);m.put(0x1034,'<i',2)
  with self.assertRaises(ObservationError):robin_lookup(m,0x1000,7,12,0,4,8)
 def test_sentinel_fail_closed(self):
  m=Memory();table(m,0x1000,0x20000,12,0,4,8,rows=[(0,7,8)]);m.put(0x1038,'<B',0)
  with self.assertRaises(ObservationError):robin_lookup(m,0x1000,42,12,0,4,8)
 def test_special_fastpath(self):
  m,g,a,*_=fixture();m.put(a+0x2f8,'<Q',123);v,e=delivery_possible(m,g,a);self.assertTrue(v);self.assertEqual(e['branch'],'special2f8')
 def test_cached_fastpath(self):
  m,g,a,*_=fixture();m.put(a+0x2e,'<B',1);v,e=delivery_possible(m,g,a);self.assertTrue(v);self.assertEqual(e['branch'],'flag2e')
 def test_nonboolean_conservative_error(self):
  m,g,a,*_=fixture();m.put(a+0x2e,'<B',2)
  with self.assertRaises(ObservationError):delivery_possible(m,g,a)
 def test_main_area(self):
  m,g,a,c,st,pp,mp,area,ma=fixture();self.assertEqual(main_area(m,g,c)[0],ma)
 def test_equal_main(self):
  m,g,a,c,st,pp,mp,area,ma=fixture();m.put(pp+0xd0,'<Q',ma);v,e=delivery_possible(m,g,a);self.assertTrue(v);self.assertEqual(e['branch'],'main_area')
 def test_no_area(self):
  m,g,a,c,st,pp,*_=fixture();m.put(pp+0xd0,'<Q',0);v,e=delivery_possible(m,g,a);self.assertFalse(v);self.assertEqual(e['branch'],'no_area')
 def test_reachable_port_route_zero(self):
  m,g,a,*_=fixture();v,e=delivery_possible(m,g,a);self.assertTrue(v);self.assertEqual(e['branch'],'reachable_port');self.assertEqual(e['ports'][0]['route'],0)
 def test_negative_route_blocked(self):
  m,g,a,*_=fixture();m.put(0x1a00008,'<i',-1);v,e=delivery_possible(m,g,a);self.assertFalse(v);self.assertEqual(e['branch'],'blocked')
 def test_absent_naval_not_port(self):
  m,g,a,*_=fixture();m.put(0x1900004,'<B',0);v,e=delivery_possible(m,g,a);self.assertFalse(v);self.assertEqual(e['ports'],[])
 def test_missing_read_not_false(self):
  m,g,a,*_=fixture();del m.mem[0x1a00008]
  with self.assertRaises(ObservationError):delivery_possible(m,g,a)
class NativeArtifactWitnesses(unittest.TestCase):
 def text(self,n):return (ROOT/n).read_text(encoding='utf8')
 def test_hq_actual_transfer_and_collection(self):
  s=self.text('_t203_clip_c4a420.txt');self.assertIn('c4b0d4 call 0xcc6bf0',s);self.assertIn('c4b191 call 0x19c9a20',s)
 def test_loss_tail_wrapper(self):
  s=self.text('_t203_clip_cc77b0.txt');self.assertIn('cc77bd mov rdx, qword ptr [rax + 0x48]',s);self.assertIn('cc77c1 jmp 0xcc77d0',s)
 def test_people_loss_separate_from_c0(self):
  d=json.loads(self.text('t203_combat_manpower_chain.json'));self.assertEqual(d['slots']['0xc0'],'0xcec2e0');self.assertNotIn('0xcec270',d['slots'].values());self.assertIn('cec28d call 0xcc77b0','\n'.join(d['loss']['asm']))
 def test_delivery_negative_not_live_proved(self):
  d=json.loads(self.text('t203_delivery_live_candidate.json'));self.assertFalse(d['schema_emission']);self.assertEqual(d['errors'],[]);self.assertEqual(len(d['own'])+len(d['existing_enemy_combatants']),30);self.assertTrue(all(z['delivery_possible']for k in('own','existing_enemy_combatants')for z in d[k]))
 def test_war_relation_not_battle_record(self):
  d=json.loads(self.text('t203_existing_war_loss_candidates.json'));self.assertFalse(d['schema_emission']);self.assertEqual(d['records'][0]['war_class'],'.?AVCWarRelation@@');self.assertNotEqual(d['records'][0]['war_class'],'.?AVCLandCombat@@')
 def test_reason4_official_producer(self):
  s=self.text('_t203_clip_175d940.txt');self.assertIn('175dc29 call 0xe64c50',s);self.assertTrue(any(z.startswith('175dc38 ')and'[rbx + 8], 4'in z for z in s.splitlines()))
class BattlePeopleCandidate(unittest.TestCase):
 def test_synthetic_positive_is_still_not_schema(self):
  from research._t203_battle_reader import battle_people_loss_candidate
  m=Memory();m.classes={0x200000:'CLandCombatant',0x2001d0:'CStatsObserver@NCombatLog'};m.put(0x200230,'<i',17);d=battle_people_loss_candidate(m,0x200000);self.assertEqual(d['candidate_people_loss'],17);self.assertFalse(d['schema_emission']);self.assertTrue(d['positive_live_proof_required'])
 def test_wrong_inline_type_rejected(self):
  from research._t203_battle_reader import battle_people_loss_candidate
  m=Memory();m.classes={0x200000:'CLandCombatant',0x2001d0:'CCombatTactic'}
  with self.assertRaises(ObservationError):battle_people_loss_candidate(m,0x200000)
 def test_negative_counter_rejected(self):
  from research._t203_battle_reader import battle_people_loss_candidate
  m=Memory();m.classes={0x200000:'CLandCombatant',0x2001d0:'CStatsObserver@NCombatLog'};m.put(0x200230,'<i',-1)
  with self.assertRaises(ObservationError):battle_people_loss_candidate(m,0x200000)
 def test_true_people_source_to_observer(self):
  s=(ROOT/'_t203_clip_ce84d0.txt').read_text(encoding='utf8');self.assertIn('ce8877 call 0xcec270',s);self.assertIn('ce895d mov edx, esi',s);self.assertIn('ce8962 call 0xd3a5e0',s);s=(ROOT/'_t203_clip_d3a5e0.txt').read_text(encoding='utf8');self.assertIn('d3a64f add dword ptr [rbx + 0x60], edi',s)
 def test_local_scope_and_no_positive_live_yet(self):
  d=json.loads((ROOT/'t203_battle_people_loss_live_candidate.json').read_text(encoding='utf8'));self.assertFalse(d['schema_emission']);self.assertEqual(len(d['records']),4);self.assertTrue(all(z['inline_log_class']=='.?AVCStatsObserver@NCombatLog@@'and z['actual_people_loss_candidate']==0 for z in d['records']));g=json.loads((ROOT/'t203_battle_people_log_link.json').read_text(encoding='utf8'));self.assertIn('133a8d0 lea rax, [rcx + 0x1d0]',g['getter']['asm'])
if __name__=='__main__':unittest.main()
