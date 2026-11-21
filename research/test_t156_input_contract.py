import copy,json,unittest
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]
SCHEMA=json.loads((ROOT/'calling/tables/generalissimo_input.schema.json').read_text(encoding='utf-8'))
V=Draft202012Validator(SCHEMA)
class InputContractTests(unittest.TestCase):
 def full(self):
  return {'meta':{'game_time':{'year':1936,'month':1,'day':1,'hour':12},'player_country':{'index':44},'speed':'pause','allow_write':False,'geography_scope':None},'policy':{},'world':{**{k:[] for k in ('own_units','visible_units','army_groups','armies','leaders','provinces','plans','combats','crises','wars')},'shortages':{'equipment':[],'manpower':{}}},'feedback':{'last_orders':[]}}
 def unit(self):return {'unit_id':1,'province_id':1,'owner':{'index':44},'relation_to_player':'self','in_combat':False,'order':{'type':'idle','target_province_ids':[],'path_province_ids':[]}}
 def test_artificial_complete_shape(self):V.validate(self.full())
 def test_missing_required_order(self):
  a=self.full();u=self.unit();del u['order'];a['world']['own_units']=[u];self.assertFalse(V.is_valid(a))
 def test_visible_requires_visibility(self):
  a=self.full();a['world']['visible_units']=[self.unit()];self.assertFalse(V.is_valid(a))
 def test_template_requires_id(self):
  a=self.full();u=self.unit();u['template']={'name':'test'};a['world']['own_units']=[u];self.assertFalse(V.is_valid(a))
 def test_ratio_bounds(self):
  a=self.full();u=self.unit();u['strength']={'equipment_ratio':1.2};a['world']['own_units']=[u];self.assertFalse(V.is_valid(a))
 def test_real_live_partial_rejected(self):
  a=json.loads((ROOT/'research/t156_live_capture.json').read_text(encoding='utf-8'));self.assertFalse(a['complete_input']);self.assertFalse(V.is_valid(a['observation']))
 def test_live_templates_nonempty_and_typed(self):
  a=json.loads((ROOT/'research/t156_live_capture.json').read_text(encoding='utf-8'));us=a['observation']['world']['own_units'];self.assertEqual(len(us),21)
  ts={u['template']['template_id']:u['template'] for u in us};self.assertEqual(len(ts),4)
  self.assertEqual({r['type']:r['count'] for r in ts[587]['battalions']},{'infantry':4,'cavalry':1})
  self.assertEqual(ts[588]['battalions'],[{'type':'infantry','count':4}])
  self.assertTrue(all('manpower' not in u['strength'] and 'in_combat' not in u and 'order' not in u for u in us))
 def test_live_own_country_area_proof(self):
  a=json.loads((ROOT/'research/t156_live_capture.json').read_text(encoding='utf-8'))
  self.assertEqual(a['evidence']['registered_self_provinces'],{'controller':34,'owner':34})
  self.assertTrue(all(p['owner']['index']==44 and p['controller']['index']==44 for p in a['observation']['world']['provinces']))
 def test_live_terrain_not_enum_guess(self):
  a=json.loads((ROOT/'research/t156_live_capture.json').read_text(encoding='utf-8'));ps=a['observation']['world']['provinces'];self.assertEqual(len(ps),12)
  self.assertEqual({p['terrain'] for p in ps},{'mountain','hills','desert'})
  self.assertEqual(next(p['terrain'] for p in ps if p['province_id']==5010),'mountain')
if __name__=='__main__':unittest.main()
