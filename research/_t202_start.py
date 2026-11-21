from _t202_common import *
x=Runtime()
try:
 before=x.guard();out={'before':before,'analysis_source':'Loaded image ReadProcessMemory, no disk image or D filesystem access','disk_exe_fingerprint':'not re-read; current PID/base, runtime RTTI/header and targeted code hashes recorded, no gate weakening','functions':{}}
 for a in(0xfcf8f0,0x12e6e20,0x147e600,0x133a150):
  d=x.clip(a);out['functions'][hex(a)]=d;print('FUNCTION',hex(a),'RANGE',d['start'],d['end'],'INSNS',len(d['asm']));print('\n'.join(d['asm'][:24]));print('DIRECT_CALLEES',sorted(set(s.split(' call ')[1]for s in d['asm']if ' call 0x'in s)))
 after=x.guard();assert before==after;out['after']=after;(R/'research/t202_initial_chains.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('GUARD',json.dumps(after,indent=2));(R/'research/t202_checkpoint.md').write_text('''# t202 checkpoint（继续严格只读）\n\n## 块1：会话重绑与目标调用链开段\n已重读t201记录、加载code-changes，按本机活体依赖例外。机器在线；重新发现PID/base/GS/idler/country，官方暂停、speed0、六实例executing=false、闸门关闭，读前后游戏时间不变。0Post/0游戏写入/0远程调用，不推进时间、不读写存档、不commit/push，历史写入脚本保持硬禁。\n本段不读取任何D盘文件（包括未重读exe文件）；新反汇编只读当前进程已加载代码/.pdata，RVA随新base绑定，记录代码段SHA。没有为完整capture绕过原exe文件指纹闸门；既有完整导出仍52required缺失、complete_input=false。\n已展开FCF8F0、12E6E20、147E600、133A150完整函数/UNWIND链，证据t202_initial_chains.json与_t202_clip_*.txt。接下来追各函数的数据来源和消费，不把path直接命名axis、不把边境战计时字段套普通陆战。\n本地证据74/42（内存剩30、非内存12）；D盘最后72/44，14表116字段3列，未读取/同步，pending文件保留。\n''',encoding='utf-8')
finally:x.close()
