# t252 恢复入口：仅文件同步已完成，未恢复游戏验证

GitHub交付提交：7ff178386d3bdb8d5138d76a6f4919ce9c43da0c
分支：cursor/t244-t245-records-01bd
PR：https://github.com/lily-880/hoi4-clausewitz-win/pull/1；main未合并。

已按云端固定SHA包，将7个新增文件用CreateNew/同SHA跳过规则保存现有Windows checkout；5份records亦保存C权威和box。逐文件SHA/字节/C路径见同目录 t252_local_sync_receipt.json。异SHA禁止覆盖；本次没有冲突、覆盖或git命令。旧t251文件中“C尚未同步”为历史状态，本入口是其后的实际同步回执。复制字节不等于local gitHEAD与分支对齐。GitHub提交来源为父级CloudAgent已提交交付；本次独立校验固定包及manifest，没有重新读取GitHub blob。

C权威：C:\Users\Lenovo\Documents\钢四陆军总司令
Windows checkout：C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win
box镜像：/workspace/hoi4-docs-latest/records
两份calling文件的box增量备份：/workspace/hoi4-t252-sync/payload/calling/
七文件manifest：/workspace/hoi4-t252-sync/seven_files_manifest.json

用户选择global/annihilate已原字节保存，commander_config仅配置读取/合并。capture()尚未接入，不等于实机完成，更不代表annihilate战术已实现。清单仍87/29，complete_input=false，生产51/captureclosed边界不变，四个封存生产文件完全未触碰。没有自行晋级或放开写权限。

本次没有运行模块/import/测试：云端已报告10项通过，文件传输用SHA验收即可。未运行game/capture/doctor/status/save/Post，无进程/live读取，无法据此断言当前游戏PID、暂停或运行状态。无后台任务。t216本次优先保存，不自动恢复旧逆向路径。

后续未完成：capture配置集成需独立审查并处理封存hash约束；配置来源验收不能冒充内存字段；29项未证项、feedback真实回执及自然正反样本仍需相应证据。现有未证状态保持，禁止靠阈值/空样本推断。退休D文档路径不访问。
