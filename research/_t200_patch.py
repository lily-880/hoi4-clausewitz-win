from pathlib import Path
import py_compile
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win')
p=R/'calling/post_abi.py';s=p.read_text(encoding='utf-8')
for a,b in [('FN_EXECUTE_LOOP = 0x22C4710','FN_EXECUTE_LOOP = 0x22C4780  # t200 PE .pdata + static vt+0x50 call proof; old value was INSIDE Post'),('EXECUTE_SITE_A = 0x22C6C9D','EXECUTE_SITE_A = 0x22C6D0D'),('EXECUTE_SITE_B = 0x22C47DD','EXECUTE_SITE_B = 0x22C484D'),('CCommand_VT_POSTEXEC = 0x58','CCommand_VT_TYPE_TOKEN = 0x58  # CPauseGame e56c30 returns token0x29ec; NOT PostExec\nCCommand_VT_POSTEXEC = CCommand_VT_TYPE_TOKEN  # historical compatibility alias only; never an actuator')]:
 assert s.count(a)==1,a;s=s.replace(a,b)
s=s.replace('Proven against HOI4 1.19.4.1 (Operation Postern) on Windows — Haiti SP.','Current addresses: HOI4 1.19.5.0.7c6c. t200 static lifecycle audit.\nPost acknowledgement is sink acceptance, never proof of an observed state change.')
p.write_text(s,encoding='utf-8');py_compile.compile(str(p),doraise=True)
p=R/'calling/command_receipt.py';assert not p.exists()
p.write_text('''"""Pure offline receipt assessment. No process, Post, recovery action, or game calls.

Keep observed state distinct from a request/queue acknowledgement. This module
cannot and must not try to pause a game. It only evaluates supplied evidence.
"""
def assess_pause_receipt(*, accepted, requested_pause, observed_pause):
    if type(accepted) is not bool or type(requested_pause) is not bool:
        raise ValueError('receipt/request must be boolean')
    if observed_pause is not None and (type(observed_pause) is not int or observed_pause not in (0, 1)):
        raise ValueError('observed official pause must be 0, 1, or unknown')
    confirmed = observed_pause is not None and observed_pause == int(requested_pause)
    return {'queue_accepted': accepted, 'requested_pause': requested_pause,
            'observed_pause': observed_pause, 'state_change_confirmed': confirmed,
            'official_pause_confirmed': observed_pause == 1,
            'needs_readonly_verification': observed_pause is None,
            'acknowledgement_is_not_execution_proof': True}
''',encoding='utf-8');py_compile.compile(str(p),doraise=True)
with (R/'research/t200_checkpoint.md').open('a',encoding='utf-8')as f:f.write('''\n## 块5：仅本地可靠性修复\n已修正post_abi.py三处旧地址常量（真正Loop/两个Execute site），并将slot+0x58纠正命名为TYPE_TOKEN；CPauseGame在0xE56C30返回0x29EC就是类型token，不是PostExec回调。保留旧名兼容别名但明确禁止当actuator。该模块仍不执行Post。新增纯离线command_receipt.assess_pause_receipt，仅根据提供的实际pause值判定确认，不因queue accepted而写成已暂停；没有任何恢复动作或远程调用。\n补给访问器第一批0xF47840/0xF46B86经进一步反汇编被排除：它们操作按province/state索引的0x78字节行与dirty bits4/8，不是CSupplyConsumer+0x70字段，因此没有把它们冒称isolated。0xC50000–0xC5C000短函数扫描也没有找到可直接命名的ratio getter；下一步应从消费分配调用者/UI标签反向追，而非继续邻近地址猜测。\n''')
print('LOCAL ONLY: ABI documentation corrected; pure receipt model added')
