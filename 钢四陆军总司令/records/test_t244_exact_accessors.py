import unittest,json,base64
from pathlib import Path
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
J=json.loads((Path(__file__).parent/'t244_targeted_evidence.json').read_text())
class ExactAccessorChecks(unittest.TestCase):
 def test_d47370_exact_leaf_returns_raw_qword_at_38_only(self):
  w=J['windows'][1];raw=base64.b64decode(w['raw_base64']);self.assertEqual(raw[:5],bytes.fromhex('488b4138c3'));ins=list(Cs(CS_ARCH_X86,CS_MODE_64).disasm(raw[:5],0xd47370));self.assertEqual([(x.mnemonic,x.op_str) for x in ins],[('mov','rax, qword ptr [rcx + 0x38]'),('ret','')])
 def test_147ea30_exposes_mutating_marker_and_exact_receiver_chain_not_id_getter(self):
  a=J['windows'][0]['entry_linear_disassembly_until_first_ret_or_jump'];self.assertIn('147ea36 mov byte ptr [rcx + 0x52], 1',a);self.assertIn('147ea3d mov rcx, qword ptr [rcx + 0x28]',a);self.assertIn('147ea47 mov rcx, qword ptr [rbx + 0x30]',a);self.assertIn('147ea81 mov rcx, qword ptr [rbx + 0x38]',a);self.assertEqual(a[-1],'147ea8d jmp 0xef1040');self.assertFalse(J['windows'][0]['complete_cfg_claimed'])
if __name__=='__main__':unittest.main(verbosity=2)
