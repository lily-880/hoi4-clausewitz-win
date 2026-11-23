# 《陆军总司令函数接口》与输入 schema 对照

> 2026-11-23，Claude 离线对照。只读了两份文件，没有连接游戏、没有运行项目代码、没有修改 schema 或清单。
>
> - 接口文档：`陆军总司令函数接口.md`（Grok Bot 定稿 2026-11-06，原件末尾截断）
> - schema：`calling/tables/generalissimo_input.schema.json`（SHA256 `9a941dd3…b45ee`，t243 封存值未变）
> - 字段证据状态：`态势信息读取能力清单.md`（87/29）
>
> 本文只列事实差异和需要用户决定的问题，**不改任何字段状态**。

## 1. 结论摘要

1. **输入部分：schema 是接口文档输入契约的忠实编码。** 全部字段名、类型、可选/必填、枚举值逐项一致，未发现漂移。schema 自带注释说明它转录自同一份 Canvas（`4688f13e…`），只描述完整快照形状，不负责运行周期里的增量传输。
2. **输出部分在仓库里完全没有对应物。** orders / alerts / brief / intents 没有 schema、没有代码；全仓库搜不到 `GeneralissimoOutput`、`expands_to_order_seqs`、`new_ref`。接口定义了 36 种写入命令，历史研究只碰过其中少数几种（见第 4 节）。
3. **接口文档内部有一处结构性矛盾，被原样带进了 schema**：`feedback.last_orders[].type` 允许的值覆盖不了大部分输出命令（21 种输出命令无法回执），另有一个回执值 `reassign_unit` 没有对应的输出命令（见第 3 节）。
4. **「读不到就省略」和「必填」冲突**：接口原则是读不到的字段标可选，但它自己把几项目前读不到、且没有 `unknown` 取值的字段定为必填。这是 `complete_input=false` 的直接原因之一（见第 2 节）。
5. **`geography_scope` 文档已过时**：接口写「现行宪章为 null」，而你在 2026-11-22 已选定 global，`calling/tables/commander_policy.json` 存的是 `{"kind":"global"}`。

## 2. 输入：必填但目前读不到的字段

schema 的必填（R）完全照搬接口。下表只列「接口要求必填」与「清单未验证或只窄验证」相撞的字段，以及有没有合法的退路取值。

| 字段 | 接口/schema | 清单状态 | 有无合法退路 |
|---|---|---|---|
| `world.plans[].type` | 必填，枚举 frontline/offensive_line/garrison/area_defense | 未验证（raw type2 前线与 Fallback 共用） | **无**：枚举没有 unknown。只要输出任何计划就必须编一个类型，或整个 plans 留空 |
| `world.crises[].severity` | 必填，watch/high/critical | 未验证 | **无**：只要报危机就必须编严重度，或 crises 留空 |
| `world.visible_units[]` 的 Unit 必填项（`in_combat`、`order.type`、`order.target_province_ids`、`order.path_province_ids` 等） | 「结构与 Unit 相同」，全部必填 | 清单只覆盖 visible_units 过滤、`spotted`、`relation`、`confidence`，敌军的行军/命令不在清单内 | 部分：`order.type` 可填 unknown，但路径数组必须给，空数组会被读成「没有路径」，语义不对 |
| `world.visible_units[].relation_to_player` | 必填 | 未验证 | 有：Relation 枚举含 unknown |
| `world.own_units[].order.type` | 必填 | 只验证了 strategic_redeploy 窄分支 | 有：OrderType 含 unknown |
| `world.combats[].phase` | 必填，ongoing/ended | 只验证 3 场的 ongoing | 正在进行的战斗可填；ended 不能输出 |
| `meta.geography_scope` | 必填，可为 null | 配置项，未验证 | 有：t250 已能从配置读出 global（尚未接入 `capture()`） |

接口文档说「规模可用粗粒度（师数、估测兵力）」，但 schema 和接口表格都没有放粗粒度估计的字段，只能按单个师填。

## 3. 回执与输出命令对不上

接口的「下达 → 观察 → 失败则改下法」靠 `feedback.last_orders[].type` 对照上一拍命令。它允许的值是 OrderType 加 PlanCommandType；拿接口自己的输出命令去对：

| 输出类别 | 能回执 | **不能回执** |
|---|---|---|
| maneuver | move、strategic_redeploy、attack、support_attack、retreat | cancel |
| formation | create_army、create_army_group | modify_army、disband_army、modify_army_group、disband_army_group、assign_units、unassign_units |
| leaders | assign_leader、use_leader_ability | unassign_leader、reassign_leader |
| plans | create_frontline、create_offensive_line、create_garrison、assign_to_plan | update_frontline、delete_frontline、update_offensive_line、delete_offensive_line、create_area_defense、update_garrison、update_area_defense、delete_garrison、delete_area_defense、set_plan_execution、unassign_from_plan |
| tasks | train、exercise | cancel_task |

- 合计 **21 种输出命令无法写进回执**；而回执里的 `reassign_unit` 在输出命令表里不存在。
- 回执的 `subject_ids` 是一个平铺的 int 数组，输出命令的 `subject` 却分 unit_ids / army_ids / army_group_ids。回执丢掉了 ID 属于哪一类；而师和集团军的句柄编号空间并不保证互不重叠（清单记录过类型 51/53/4713 的区分问题）。
- 输出用 `new_ref` 引用本拍新建、尚无编号的集团军或计划，回执却没有字段把 `new_ref` 映射回引擎实际分配的 ID。
- `accepted` 只有 true/false，表达不了「已入队未消费」或「结果不明」。历史暂停事故正是「Post 返回成功、实际没生效」，t246 也已记录这一点。
- `ticks_since_issue` 是整个 feedback 一个值，不是每条命令一个。

## 4. 输出命令与历史研究证据

接口共定义 36 种写入命令（maneuver 6、formation 8、leaders 4、plans 15、tasks 3）。仓库与交接说明里有证据的只有：

| 接口命令 | 历史证据 | 强度 |
|---|---|---|
| move | `CMoveCommand` 工厂/布局；一次受控 Post | 那次 Post 超时，路径空、省份未变，**不是成功移动** |
| strategic_redeploy | `CStrategicRedeploymentCommand`；一次授权 Post | 未证明到达 |
| cancel | `CCancelMovementCommand` 目录 | 无成功执行回执 |
| support_attack | `CSupportAttackCommand` 目录 | 无执行回执 |
| plans 相关 | Orders Assign/Unassign/Execute/NewFallback/Delete 工厂目录；t198 计划插入前线、新建后撤线的实例回读 | 只证明控制点；而且接口里**没有** fallback（后撤线）这一计划类型 |
| attack、retreat、全部 formation、leaders、tasks | 无 | — |

所以接口的输出层目前是纯设计，没有实现，也没有一条命令完整验收过「下达 → 消费 → 状态改变 → 回执」。

## 5. 需要你决定的事

下面每一项都是改设计契约，属于你的决定，我不会自行修改 schema（它是封存的生产四文件之一）或清单：

1. **回执类型**：要不要把 feedback 的 type 改成「输出命令 type 全集」，并补上 subject 分类、`new_ref` 映射和「结果不明」状态？
2. **必填冲突**：`plans.type`、`crises.severity` 是改为可选，还是在枚举里加 `unknown`？visible_units 是否改用一个精简的「可见单位」结构，不再强制带完整 Unit？
3. **接口文档更新**：把 geography_scope 改成现行 global；补齐被截断的「每月」brief 段；配套《陆军总司令权限宪章》是否找得到？
4. **后撤线**：接口没有 fallback 计划类型，而历史研究做过 NewFallback；撤退是只走 `retreat` 命令，还是要加后撤线类型？
