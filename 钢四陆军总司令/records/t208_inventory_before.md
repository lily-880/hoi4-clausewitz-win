| 字段名 | 已验证/未验证 | 说明 |
| --- | --- | --- |
| meta.game_time.year | 已验证 | 游戏内当前年份。 |
| meta.game_time.month | 已验证 | 游戏内当前月份。 |
| meta.game_time.day | 已验证 | 游戏内当前日。 |
| meta.game_time.hour | 已验证 | 游戏内当前小时。 |
| meta.player_country.index | 已验证 | 当前玩家控制国家的引擎序号。 |
| meta.player_country.tag | 已验证 | 当前运行时国家表中玩家国家的三字母代号。 |
| meta.speed | 已验证 | 官方暂停标志与速度档，现场状态须另行核实。 |
| meta.allow_write | 未验证 | 由配置提供的写入许可，默认false，非内存发现。 |
| meta.geography_scope | 未验证 | 由配置提供的指挥范围，默认null，非内存发现。 |

| 字段名 | 已验证/未验证 | 说明 |
| --- | --- | --- |
| policy.stance | 未验证 | 由玩家方针或接口默认值提供，非内存发现。 |
| policy.instructions | 未验证 | 由玩家提供的方针原文，非内存发现。 |

| 字段名 | 已验证/未验证 | 说明 |
| --- | --- | --- |
| world.own_units.unit_id | 已验证 | 师的内部编号。 |
| world.own_units.name | 已验证 | 师的显示名称。 |
| world.own_units.province_id | 已验证 | 师当前所在省份编号。 |
| world.own_units.owner.index | 已验证 | 当前己方师所属国家的引擎序号。 |
| world.own_units.owner.tag | 已验证 | 当前己方师所属国家在运行时国家表中的代号。 |
| world.own_units.relation_to_player | 已验证 | 仅已验证与玩家同国的self关系。 |
| world.own_units.template.template_id | 已验证 | 当前21个己方师所用四种模板的内部编号。 |
| world.own_units.template.name | 已验证 | 当前师模板名称。 |
| world.own_units.template.battalions | 已验证 | 当前四种己方模板内非空主战营的类型和数量。 |
| world.own_units.template.combat_width | 已验证 | 当前四种己方模板由已加载主战营宽度求和的战斗宽度。 |
| world.own_units.organization | 已验证 | 师当前原始组织度。 |
| world.own_units.strength.manpower | 已验证 | 当前己方21师按国籍人数表合计的实际人力。 |
| world.own_units.strength.current | 已验证 | 当前己方21个师的剩余生命值。 |
| world.own_units.strength.max | 已验证 | 当前己方21个师由引擎聚合属性提供的生命值上限。 |
| world.own_units.strength.equipment_ratio | 已验证 | 师装备配齐比例，当前开局样本已重验。 |
| world.own_units.supply.in_supply | 已验证 | 官方缺补给判定的反值，非仅有正配送。 |
| world.own_units.supply.ratio | 已验证 | 官方工具提示的有效补给满足比例。 |
| world.own_units.supply.isolated | 未验证 | 师是否与补给来源隔绝。 |
| world.own_units.in_combat | 已验证 | 仅验证己方参战师的作战正例。 |
| world.own_units.combat_id | 已验证 | 师当前参加的战斗编号。 |
| world.own_units.order.type | 未验证 | 师当前任务类型。 |
| world.own_units.order.target_province_ids | 未验证 | 师当前任务的目标省份。 |
| world.own_units.order.path_province_ids | 已验证 | 师当前行军路径，取自 CArmy+0x200 的有序 u32 省份数组；活体邻省行军后非空。 |
| world.own_units.order.eta | 未验证 | 该师当前命令的预计到达时间或进度。 |
| world.own_units.formation.army_id | 已验证 | 师所属集团军编号，取自 CArmy+0xC0 的 COrdersGroup*；与该集团军成员表互证。 |
| world.own_units.formation.army_group_id | 已验证 | 师所属集团军群编号。 |
| world.own_units.leader_id | 已验证 | 直接挂在师上的军官编号。 |

| 字段名 | 已验证/未验证 | 说明 |
| --- | --- | --- |
| world.visible_units | 未验证 | 战争迷雾下玩家实际可见的其他陆部队。 |
| world.visible_units.relation_to_player | 未验证 | 可见其他部队与玩家的关系。 |
| world.visible_units.visibility.spotted | 未验证 | 该部队是否确实处于玩家可见范围。 |
| world.visible_units.visibility.confidence | 未验证 | 对该可见部队情报的置信度。 |

| 字段名 | 已验证/未验证 | 说明 |
| --- | --- | --- |
| world.army_groups.army_group_id | 已验证 | 集团军群编号，取自 CTheatre+0x98 下 CArmyGroup 句柄 id（类型 53，与集团军相同，需靠 RTTI 区分）。 |
| world.army_groups.name | 已验证 | 集团军群名称，取自 CArmyGroup+0x160；新建后为默认本地化名。 |
| world.army_groups.leader_id | 已验证 | 集团军群司令编号，取自 CArmyGroup+0x88 将领指针的句柄 id；未任命时为空。 |
| world.army_groups.army_ids | 已验证 | 集团军群下属集团军编号，取自 CArmyGroup+0x230 的 COrdersGroup* 数组。 |

| 字段名 | 已验证/未验证 | 说明 |
| --- | --- | --- |
| world.armies.army_id | 已验证 | 集团军编号，取自 CTheatre+0x80 下 COrdersGroup 句柄 id（类型 53）。 |
| world.armies.name | 已验证 | 集团军名称，取自 COrdersGroup+0x160；新建后为默认本地化名。 |
| world.armies.leader_id | 已验证 | 集团军司令编号，取自 COrdersGroup+0x88 将领指针的句柄 id；未任命时为空。 |
| world.armies.unit_ids | 已验证 | 编入集团军的师编号，取自 COrdersGroup+0x50 成员指针经虚函数回主对象后的 CArmy 句柄。 |
| world.armies.plan_id | 已验证 | 集团军绑定的计划编号，取自 COrdersGroup+0x98 的 COrderInstance 的 instance_id（+0x244）。 |

| 字段名 | 已验证/未验证 | 说明 |
| --- | --- | --- |
| world.leaders.leader_id | 已验证 | 当前己方20名陆军将领档案编号，非师军官编号。 |
| world.leaders.name | 已验证 | 当前己方20名陆军将领的人物档案完整显示姓名。 |
| world.leaders.skill | 已验证 | 当前己方20名陆军将领的总等级。 |
| world.leaders.attack | 已验证 | 当前己方20名陆军将领的进攻属性。 |
| world.leaders.defense | 已验证 | 当前己方20名陆军将领的防御属性。 |
| world.leaders.planning | 已验证 | 当前己方20名陆军将领的计划属性。 |
| world.leaders.logistics | 已验证 | 当前己方20名陆军将领的后勤属性。 |
| world.leaders.traits | 已验证 | 当前己方20名陆军将领的完整内部特性名称。 |
| world.leaders.assigned_to | 已验证 | 将领任职目标，取自 CArmyLeader+0x1048 的 {type,id} 句柄。 |

| 字段名 | 已验证/未验证 | 说明 |
| --- | --- | --- |
| world.provinces.province_id | 已验证 | 当前己方师所在省份的编号。 |
| world.provinces.controller | 已验证 | 当前己方登记区域的占领国编号，未验省份易手。 |
| world.provinces.owner | 已验证 | 当前己方登记区域的法理归属国编号，未验归属变化。 |
| world.provinces.terrain | 已验证 | 当前己方师所在12省的引擎地形名称。 |
| world.provinces.infrastructure | 已验证 | 己方已观察省份所属州基建等级，限未建或无损且无额外加级。 |
| world.provinces.fort_level | 已验证 | 己方省份陆地要塞等级，限未建或无损且无额外加级。 |
| world.provinces.coastal_fort_level | 已验证 | 己方省份海岸要塞等级，限未建或无损且无额外加级。 |
| world.provinces.victory_points | 已验证 | 当前己方师所在12省的胜利点分值及已有重命名。 |
| world.provinces.neighbors | 已验证 | 当前己方师所在省份的陆地邻接编号，含渡河边，不含海与不可通行。 |
| world.provinces.has_river_crossing | 已验证 | 当前己方师所在省份各陆地邻接边是否渡河。 |

| 字段名 | 已验证/未验证 | 说明 |
| --- | --- | --- |
| world.plans.plan_id | 已验证 | 玩家计划对象编号，取自挂在 COrdersGroup+0x98 上的 COrderInstance+0x244；不是边境 CFront。 |
| world.plans.type | 未验证 | 前线、进攻线、驻防或区域防御类型。 |
| world.plans.vertex_province_ids | 已验证 | 计划有序折线控制点。 |
| world.plans.assigned_army_ids | 已验证 | 计划绑定的集团军编号，取自该 COrderInstance 所挂的 COrdersGroup 句柄 id。 |
| world.plans.assigned_unit_ids | 已验证 | 计划绑定的师编号，取自 COrderInstance+0x210 数组（官方 writer 0x10d1450 token scheduled_member 0x30b1）。 |
| world.plans.executing | 已验证 | 计划是否正在执行，取自 COrderInstance+0x248。 |
| world.plans.axis_province_ids | 未验证 | 计划推进方向或进攻轴。 |
| world.plans.status | 未验证 | 计划可执行、受阻、停滞或失效状态。 |

| 字段名 | 已验证/未验证 | 说明 |
| --- | --- | --- |
| world.combats.combat_id | 已验证 | 陆战内部编号。 |
| world.combats.province_id | 已验证 | 陆战所在省份。 |
| world.combats.attacker_unit_ids | 已验证 | 陆战攻击方师编号。 |
| world.combats.defender_unit_ids | 已验证 | 陆战防守方师编号。 |
| world.combats.phase | 未验证 | 陆战进行或结束状态。 |
| world.combats.result | 未验证 | 陆战胜负结果。 |
| world.combats.casualties | 未验证 | 双方人力或组织度损失。 |
| world.combats.started_at | 未验证 | 陆战开始时间。 |
| world.combats.ended_at | 未验证 | 陆战结束时间。 |

| 字段名 | 已验证/未验证 | 说明 |
| --- | --- | --- |
| world.crises.kind | 未验证 | 被包围、断补给或计划失败等危机类型。 |
| world.crises.unit_ids | 未验证 | 危机涉及的师编号。 |
| world.crises.province_ids | 未验证 | 危机涉及的省份编号。 |
| world.crises.severity | 未验证 | 危机严重程度。 |
| world.crises.notes | 未验证 | 危机补充说明。 |

| 字段名 | 已验证/未验证 | 说明 |
| --- | --- | --- |
| world.wars.a | 已验证 | 官方 CWarRelation.first 的国家编号与代号；当前样本为 ITA（index 16）。 |
| world.wars.b | 已验证 | 官方 CWarRelation.second 的国家编号与代号；当前样本为 ETH（index 44）。 |
| world.wars.state | 已验证 | 当前局内唯一战争 ITA–ETH 为交战 at_war（双方 CRelationStatus+0x2e8 指向同一对象，cancel 与 +0x49 均为 0 且不写 end_date）。 |
| world.wars.front_invalidated | 未验证 | 战争关系变化是否使前线失效。 |

| 字段名 | 已验证/未验证 | 说明 |
| --- | --- | --- |
| world.shortages.equipment.equipment_type | 已验证 | 当前己方已检出库存装备的内部类型名。 |
| world.shortages.equipment.stockpile | 已验证 | 当前己方已检出整件库存类型的可用件数。 |
| world.shortages.equipment.demanded | 未验证 | 该类装备当前需求量。 |
| world.shortages.equipment.deficit | 未验证 | 该类装备当前缺口数量。 |
| world.shortages.equipment.affected_unit_ids | 已验证 | 已证步兵装备类型下当前编制未足额的师编号。 |
| world.shortages.equipment.affected_plan_ids | 未验证 | 缺装备影响的计划编号。 |
| world.shortages.manpower.available | 已验证 | 当前玩家国家中央池与登记州可用人数之和。 |
| world.shortages.manpower.needed | 未验证 | 当前所需补充人力。 |
| world.shortages.manpower.deficit | 未验证 | 当前人力缺口数量。 |
| world.shortages.manpower.affected_unit_ids | 已验证 | 当前官方人力缺口为正的己方师编号，非累计伤亡。 |
| world.shortages.manpower.front_cannot_hold | 未验证 | 缺人是否导致战线无法维持。 |
| world.shortages.missing_divisions | 未验证 | 某段战线现有兵力无法维持时缺少的师。 |

| 字段名 | 已验证/未验证 | 说明 |
| --- | --- | --- |
| feedback.last_orders.order_seq | 未验证 | 上一拍已发命令的序号，由回执账本提供。 |
| feedback.last_orders.type | 未验证 | 上一拍命令类型，由回执账本提供。 |
| feedback.last_orders.subject_ids | 未验证 | 上一拍命令作用对象编号。 |
| feedback.last_orders.target_province_ids | 未验证 | 上一拍命令目标省份。 |
| feedback.last_orders.plan_id | 未验证 | 上一拍命令相关计划编号。 |
| feedback.last_orders.accepted | 未验证 | 上一拍命令实际落地结果。 |
| feedback.last_orders.error | 未验证 | 上一拍命令失败原因。 |
| feedback.ticks_since_issue | 未验证 | 命令发出后经过的节拍数。 |
