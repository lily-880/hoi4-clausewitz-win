"""t249 fixed-evidence regression only. Run: python3 records/test_t249_evidence.py
No process/backend access. Tests recorded instructions, NOT live gameplay controls.
"""
import json
from pathlib import Path
import unittest
E=json.loads(Path(__file__).with_name("t249_ready_for_plan_evidence.json").read_text(encoding="utf-8"))
W={w["name"]:w for w in E["windows"]}
def ins(name,rva):
    return next((i["mnemonic"],i["operands"]) for i in W[name]["instructions"] if int(i["rva"],16)==rva)
class EvidenceRegression(unittest.TestCase):
    def test_exact_named_registration(self):
        self.assertEqual(E["registration"]["exact_token_occurrences_in_rdata"],1)
        self.assertEqual(E["registration"]["exact_rip_lea_xrefs_in_text"],["0x7171d"])
        self.assertEqual(ins("registration",0x7171d),("lea","rdx, [rip + 0x296054c]"))
        self.assertEqual(0x71724+0x296054c,0x29d1c70)
        self.assertEqual(ins("registration",0x7173d),("call","0xc5c8f0"))
        self.assertEqual(ins("registration",0x71787),("call","0x1b8840"))
    def test_functor_identity_and_receiver_not_invented(self):
        self.assertEqual(ins("factory",0xc5c8f0),("lea","rax, [rip + 0x1d77901]"))
        self.assertEqual(0xc5c8f7+0x1d77901,0x29d41f8)
        self.assertEqual(E["registration"]["slots"],["0xc7f0a0","0xc7f0a0","0xc806e0"])
        self.assertIn("AEBVCEventScope",E["registration"]["rtti"])
        self.assertEqual(ins("compute",0xc806ef),("mov","rcx, r8"))
        self.assertEqual(ins("compute",0xc80705),("mov","rbx, rdx"))
        self.assertEqual(ins("scope_adapter",0x57cbe3),("call","0x2284870"))
        self.assertFalse(E["semantics"]["runtime_container_rtti_bound"])
    def test_fixedpoint_two_counter_output_not_categorical_status(self):
        self.assertEqual(ins("compute",0xc8074e),("call","0xc5fca0"))
        self.assertEqual(ins("compute",0xc80753),("movsxd","rcx, dword ptr [rsp + 0x58]"))
        self.assertEqual(ins("compute",0xc80771),("movsxd","rax, dword ptr [rsp + 0x48]"))
        self.assertEqual(ins("compute",0xc807a1),("idiv","rcx"))
        self.assertEqual(ins("compute",0xc8075c),("mov","qword ptr [rbx], 0"))
        self.assertEqual(ins("compute",0xc807b5),("mov","eax, 0xffffffff"))
        self.assertEqual(ins("compute",0xc807ba),("mov","qword ptr [rbx], rax"))
        self.assertFalse(E["promotion"])
    def test_nested_membership_counter_and_guarded_scope(self):
        for addr,expected in [(0xc5fd60,("movsxd","r12, dword ptr [r13 + 0x23c]")),(0xc5fd8e,("movsxd","rbp, dword ptr [r14 + 0x5c]")),(0xc5fdd3,("inc","dword ptr [rax]")),(0xc5fdd8,("inc","dword ptr [rax]")),(0xc5fde0,("jl","0xc5fda0")),(0xc5fde8,("jl","0xc5fd80"))]:
            self.assertEqual(ins("counter_continuation",addr),expected)
        self.assertFalse(E["semantics"]["exact_single_order_instance_id_bridge"])
        g=E["same_build"]
        self.assertEqual((g["pause"],g["speed_slot"],g["access"]),(1,0,"0x410"))
        self.assertEqual(g["tick_before"],g["tick_after"])
        self.assertEqual(E["semantics"]["live_plan_status_positive_controls"],0)
        self.assertEqual(E["semantics"]["live_plan_status_negative_controls"],0)
        self.assertFalse(E["boundary"]["complete_input"])
if __name__=="__main__": unittest.main(verbosity=2)
