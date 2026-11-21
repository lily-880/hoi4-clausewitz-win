import sys,json,unittest,struct,ctypes
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calling'))

CONST=0x29C55C0

def hour_residue(tick):
    r8=ctypes.c_int32(tick-CONST).value
    prod=ctypes.c_int32(0x2AAAAAAB).value*ctypes.c_int32(r8).value
    edx=ctypes.c_int32((prod>>32)&0xffffffff).value>>2
    edx=edx+(1 if edx<0 else 0)
    eax=(edx+edx*2)<<3
    return ctypes.c_int32(r8-eax).value

def unit_residue(uid):
    prod=(0xAAAAAAAB*(uid&0xffffffff))&0xffffffffffffffff
    edx=((prod>>32)&0xffffffff)>>4
    eax=(edx+edx*2)<<3
    return ctypes.c_int32(uid-eax).value

class Tests(unittest.TestCase):
 def test_magic_matches_mod24_for_current_tick(self):
  self.assertEqual(hour_residue(60759371),11)
  self.assertEqual(hour_residue(60759371),(60759371-CONST)%24)
  self.assertEqual(CONST,43800000)

 def test_unit_id_magic_is_mod24(self):
  for uid in range(1829,1850):
   self.assertEqual(unit_residue(uid),uid%24)
  self.assertEqual(unit_residue(1835),11)
  matches=[uid for uid in range(1829,1850) if unit_residue(uid)==hour_residue(60759371)]
  self.assertEqual(matches,[1835])

 def test_live_stamp_equals_only_matching_unit(self):
  ev=json.loads((ROOT/'research/t172_stagger_live.json').read_text(encoding='utf-8'))
  self.assertEqual(ev['hour_tick'],60759371)
  self.assertEqual(ev['hour_residue_mod24'],11)
  self.assertEqual(ev['matching_unit_ids'],[1835])
  self.assertEqual(ev['stamped_unit_ids'],[1835])
  # other short units are not in this hour's slot
  self.assertNotIn(1830,ev['matching_unit_ids'])
  self.assertNotIn(1842,ev['matching_unit_ids'])

 def test_not_promoted_as_national_affected_or_demanded(self):
  # stagger explains the single live request; it does not make [1835] or 77 a verified contract field
  cap=ROOT/'research/t171_live_capture.json'
  data=json.loads(cap.read_text(encoding='utf-8'))
  eq=data['observation']['world']['shortages']['equipment']
  self.assertEqual(eq,[{'equipment_type':'train_equipment','stockpile':5}])
  self.assertNotIn('demanded',eq[0])
  self.assertNotIn('affected_unit_ids',eq[0])
  self.assertFalse(data['complete_input'])
  need=data['evidence']['official_country_need_collection']
  self.assertEqual(need['totals_by_type']['infantry_equipment'],77)
  self.assertEqual(need['official_contributors_from_these_components'],[1835])

if __name__=='__main__':
 unittest.main()
