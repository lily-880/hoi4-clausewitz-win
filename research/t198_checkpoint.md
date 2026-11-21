# t198 checkpoint（逐块续写）
授权 pt183u。pid12948，ETH 1936-01-01 13:00，官方暂停，allow_post=false。

## 块1：官方路径
0x18d6660 = COrderInsertFrontCommand Execute，VT 0x2a852e0，factory0x18d01c0 size0x98，IsValid0x18df2a0。集团军411/实例2，front[2072,7944]、axis[7944,5097]、affected[2]、单位数组空，IsValid=1 后单次 Post，wait0/rax1。初次快照未见新实例，不靠空快照升格。
0x18d1150 是 COrderNewFallbackCommand Execute0x18d9030 的尾跳共享 helper，不是另一个独立工厂。已绑定 factory0x18d0330 size0x60，VT0x2a85520，IsValid0x18df520。集团军411、路径[2072,7944]、单位数组空，IsValid=1 后单次 Post，wait0/rax1；活体 +0xB0 实例6 和 +0xC8 实例5 的官方 +0x70=[2072,7944]，+0x258/+0x25c=0。两者均未执行。不能只看根列表+0x98。
升格 world.plans.vertex_province_ids；resolver 已加入三张实例数组、去重和官方路径。未动校验器/哨兵，未整段清零，未对师发 SetArmyLeader。下一块先关闭计划1执行并确认false，再做1x短对照。

## 块2：停止执行与暂停异常
已官方 execute_order=0，计划1回读false；其余已读计划也均false。解除暂停后8秒采样期间date/progress未变，预先构造的恢复暂停命令Post返回1但回读仍pause=0（脚本断言失败，非超时）。此后核查发现时间在继续推进；另构造当前状态下的官方CPauseGame pause=1并Post成功，已回读pause=1，最终日期1936-01-02 15:00，比开段推进26小时。期间速度档始终0（1x），没有发进攻，但超出了预期短时窗口；不能写成“立即暂停成功”。原因未确定，今后不再1x，先查预制pause命令/异步消费时序。1829仍5010→8036，commandlist/full_path仍空，movement_progress raw从16800到453600。

## 块3：自然出现的本人陆战
恢复暂停后，官方GS+0x268现在有两场CLandCombat；secondary serialization interface在主对象+0x10。官方writer 0x147fe80字段必须加这0x10，不能拿主vt错误slot当serializer。两场id1/2，省13237/13238；己方防守成员分别1831/1832与1833/1834/1841，与本国CArmy指针精确对应。攻击方读取的是本人实际参战对手，不输出其他世界战况，更不把它当visible_units。
升格6项：own_units.in_combat（只输出正例）、own_units.combat_id、combats.combat_id/province_id/attacker_unit_ids/defender_unit_ids。补上own_active_combats与own_unit_current_combat；无本人参与的战斗跳过。

## 安全停止与最终状态
恢复暂停后只读检查确认前线当前HP低于上限：1831=73.766/80，1832=78.326/80，1833=99.268/100，1834=99.748/100，1841=179.004/180。当前人力表仍满额，不宣称已证实人力伤亡；也不能宣称本次没有造成游戏损伤。此前GS战斗表为空，现在两场战斗duration23，符合这次异常延长推进期间自然陆战与HP损耗。按不可逆游戏损伤安全条件保守停止一切进一步游戏写入/Post，不再解除暂停；没有尝试回滚内存或读写存档。
新升格总计7项，清单14表116字段，已验证71，未验证45（12非内存配置/feedback +33内存候选）。SHA256: 072ff1b23057f141b761b524b2d7e99ad67d507e56c1539dfe7dc9cd90b0e4a1。已读回SHA一致、无BOM。进程pid12948存活，官方pause1，速度槽0即1x，游戏1936-01-02 15:00；计划1执行false，全部已读计划执行false；allow_post=false，闸门文件不存在。
剩余实质障碍：行军commandlist/full_path仍空，order type/target/eta不能由普通path或movement_progress擅自替代；计划type2未有官方命名、axis/status未验证；补给缺少官方消费链语义/孤立正例；可见敌军缺少FoW门；战斗phase/result/start/end/casualties仍缺对应schema语义，不能把day/duration当时间戳；短缺类仍缺非空官方需求/缺额与影响关联；crisis/invalidated等属推断或缺官方样本；leader unit assignment不再用SetArmyLeader试探。
注意：t197_final_status.py内置sha_ok只比较历史t197 SHA，t198更新后false是历史pin不匹配，不是D盘损坏。以t198_validation.json的实际SHA/结构计数为准。
已补input_capture_live.py实际部分导出的plans/combats与own_units参战正例，不输出不存在的false，也不扩大可见敌军范围。
工具限制记录：用户机没有rg、没有pytest；直接用内置unittest回归，不安装依赖。

离线回归首次发现t198 fake-memory测试的测试数据指针低于reader安全下限，已把假指针移到0x16000（不放宽生产检查）。t185旧测试仍要求实时清单in_combat=未验证，已冻结为其原有t185 evidence assertions，保留116/43/73历史断言，不与t198当前清单混用。
