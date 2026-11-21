# t199 checkpoint（严格只读）

本段禁止Post、WriteProcessMemory、remote Execute、改变pause/speed、读写存档及commit/push。用户授权本机活体只读采集与本地代码修复。没有导入或调用Post helper；未打开闸门。pid12948开段pause1、speed槽0、日期1936-01-02 15:00，4个已读计划均executing=false。

## 块1：完整capture原始端到端
calling/input_capture_live.py --out research/t199_full_capture.json 已成功完成，21师/12省/4模板/4计划/2战斗，5个师有in_combat=true。新增字段无schema类型/额外键错误；但完整schema有53个缺少必填字段错误，complete_input=false，不能称全合同通过。计划path非空[2072,7944]、战斗成员对应t198活体证据。没有把其余16师的未知状态填成false。
发现旧入口没有接上早已验证的meta.speed、army/army_group与师formation，且evidence仍写pause unresolved。已修复这些本地导出接线，添加官方pause位前后读取一致性检查，不改任何游戏状态；清单不因此增加字段。

## 块2：现存证据的离线语义排查
保存t199_named_strings/xrefs和_t199_clip_*纯静态反汇编。未调用这些地址。
- Combat writer0x147fe80的day/duration是整数（现有23/23），不能直接当started_at/ended_at。主vt+0x60只比较duration与全局阈值，不足以命名为HasEnded；主vt+0x48进一步检查双方阵营集合和单位非空，也不能擅命名phase。无结束样本，不由“表里有对象”直接升格ongoing。
- CCombatant+0xB8 token losses走0x2545f90定点序列化；当前双方均0，且没有证明这是schema要求的人力伤亡或组织损失。HP损耗不等于人力损耗。casualties不升格。
- CArmy+0x240 token movement_progress是qword定点，不是float；它不提供ETA小时，未证明是schema预期的归一化progress。保留原始证据，不将453600机械塞进eta。
- 官方命名断言仍只有ORDER_MOVE=1、ORDER_INVASION=3；现有全部type2，且Fallback命令也产生type2，故不能凭命令名统一输出frontline。axis/status未有独立语义链。
- CSupplyConsumer writer仅有disrupted_supply/motorization_level/countries；CSupplyConsumer身份及供应计算关系仍未接上己方CArmy。受损/参战本身不能证明缺补给或孤立，不能虚构ratio。

## 暂停故障：仅离线边界
保留t198_order_sample.json历史命令顺序与Post返回、t198_pause_recovery.json；没有复现、没有新预制暂停命令、没有调用游戏Execute。返回1不代表异步消费后状态已改变；具体原因未由历史数据唯一确定，不将创建顺序或队列延迟假设冒充根因。

## 块3：独立装备不足名单（新证明）
完整capture揭示补充请求只有15师，不能当全部不足师。进一步严格只读遍历全部21师，使用此前官方证明的template+0x120编制类型需求与CArmy+0x348实装类型池作独立比较；两侧均为相同canonical infantry_equipment，有20师需求大于实装，1843恰480/480不入名单。特别是参战1831/1832/1833/1834/1841没有补充请求但确实不足；1829请求need=2而物理缺额=4，进一步证明请求表不能替代实装。
升格world.shortages.equipment.affected_unit_ids，严格限定已证实的infantry_equipment类型，未知装备类型跳过，缺当前桶不补零而整类省略。仅表达“当前编制未足额”的成员，不宣称对计划的因果影响，不将物理缺额和1940请求需求冒称国家demanded/deficit，不将装备不足或HP损耗称人力伤亡。
新reader已接入capture；清单待复制后读回SHA：4219d8b0fa9c800fdb34ce3f2b12256c0a28490b21cf12da411f8dbe73aba91a。本段新升格1项；应为72已验证/44未验证。

## 块4：最终端到端与逐类剩余边界
修复及新字段后已完成双次完整只读capture：observation逐值相同；前后pid/pause/speed/时钟字节/全部计划执行位完全相同。21师、12省、2集团军、1集团军群、4计划、2陆战，5师参战正例；infantry_equipment不足名单20师正确导出，1843不在名单。新增字段没有类型/枚举/额外键错误。完整schema仍有50条缺少必填字段错误（修复前53条）；它们是完整合同缺口而非声称capture全合同通过，complete_input仍false。
清单原格式14表116字段3列、无BOM；已验证72，未验证44=12非内存配置/feedback+32内存候选；D盘读回SHA256一致：4219d8b0fa9c800fdb34ce3f2b12256c0a28490b21cf12da411f8dbe73aba91a。
剩余逐类边界：
1. 补给3项：缺CArmy→正式补给消费者与satisfaction/isolated语义链，参战/HP损耗不是补给正例。
2. 行军type/target/eta3项：commandlist/full_path仍空，path不是target，movement_progress既不能当小时，也没有schema进度归一化证明。
3. 可见单位4项：仍缺陆军FoW可见门及0–1 confidence getter；己方陆战对手不是通用visible_units表。
4. 计划type/axis/status3项：type2无官方命名且Fallback也为2，不能与frontline硬绑；axis/status缺独立官方读取链。
5. 战斗phase/result/casualties/start/end5项：活动对象成员链不等于已命名phase；day/duration不等于GameTime；losses定点0无非空人力/组织伤亡类型证明；没有结束样本。
6. crisis5项及front_invalidated1项：缺正式事件/无效化来源，不能由HP、缺装、边境结构代造策略判断。
7. 其余短缺8项：国家equipment demanded/deficit缺独立存值交叉核对及完整类型门；affected_plan_ids的因果影响不能由成员关联代证；manpower needed/deficit/affected_unit_ids没有当前非空人力缺口，HP不是人力；front_cannot_hold和missing_divisions缺官方判据。
现有静态样本没有上述字段可独立完成的剩余正例；因此停止，不推进时间、不制造样本、不循环重复探测。
全段游戏写入0、Post0、远程函数调用0；不读写存档、不commit/push。最终官方pause1，speed槽0（1x），游戏日期仍1936-01-02 15:00，4计划executing=false，闸门文件不存在。
