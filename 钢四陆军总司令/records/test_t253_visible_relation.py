"""Frozen t253 evidence checks only; no process/game/backend imports.
Run: python3 records/test_t253_visible_relation.py
Not independent engine experiments or foreign-friendly live controls.
"""
import json
from pathlib import Path
import unittest
E=json.loads(Path(__file__).with_name("t253_visible_relation_evidence.json").read_text(encoding="utf-8"))
class EvidenceTests(unittest.TestCase):
 def test_exact_schema_not_binary_friend_enemy(self):
  self.assertEqual(E["schema"]["relation"]["enum"],["self","ally","enemy","neutral","subject","overlord","unknown"])
  self.assertIn("relation_to_player",E["schema"]["visible_required"])
  self.assertFalse(E["conclusion"]["all_relation_cases_qualified"])
 def test_fresh_enemy_and_self_nonwar_control(self):
  a,b=E["action1"]["units"]
  self.assertEqual((a["unit_id"],a["country_tag"],a["source_index"]),(490,"SOV",3))
  self.assertFalse(a["named_has_war_with_projection"])
  self.assertEqual((b["unit_id"],b["ref_1d8_raw"],b["ref_1e0_raw"],b["country_tag"]),(399,368,368,"D04"))
  self.assertEqual((b["province_id"],b["overlay_byte"],b["native_byte_projection"]),(10544,250,250))
  self.assertTrue(b["named_has_war_with_projection"] and b["reverse_named_has_war_with_projection"])
  self.assertEqual((b["relation_target_canonical"],b["reverse_target_index"]),(3,368))
  self.assertFalse(b["schema_emitted"])
 def test_actual_country_words_refute_universal_join(self):
  r=E["action4_error_preservation"]["rows"][1];a,b=r["references"]
  self.assertEqual(r["unit_id"],1101)
  self.assertEqual((a["raw_int"],a["remapped_index"],a["country_tag"]),(16,16,"ITA"))
  self.assertEqual((b["raw_int"],b["remapped_index"],b["country_tag"]),(3,3,"SOV"))
  self.assertNotEqual(a["remapped_index"],b["raw_int"])
  self.assertTrue(all(x["semantic_role"]=="UNASSIGNED" for x in (a,b)))
 def test_actual_army_rtti_cannot_override51(self):
  r=E["action4_error_preservation"]["rows"][0]
  self.assertEqual((r["unit_id"],r["class_name"],r["handle_type"]),(4652,".?AVCArmy@@",4713))
  self.assertFalse(r["production51_accepted"] or r["references_read"] or r["schema_emitted"])
 def test_attempts_and_no_promotion_honest(self):
  a=E["accounting"];self.assertEqual((a["research_collection_launches"],a["sealed_successes"],a["failed_collection_executions"]),(4,2,2))
  self.assertEqual(len(set(a["unique_units"])),4)
  self.assertEqual(E["action4_error_preservation"]["new_candidates"],0)
  self.assertEqual(E["conclusion"]["current_foreign_friendly_positive"],0)
  self.assertEqual(E["conclusion"]["promoted_fields"],[])
  self.assertEqual((E["session"]["access"],E["session"]["pause"],E["session"]["speed_slot"]),("0x410",1,0))
  self.assertEqual((E["preservation"]["inventory_verified"],E["preservation"]["inventory_unverified"]),(87,29))
if __name__=="__main__":unittest.main(verbosity=2)
