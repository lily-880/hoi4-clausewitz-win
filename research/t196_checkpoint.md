# t196 checkpoint

授权：`pt182u`（继续）+ `pt180u`（写入/代下最小指令）。每次 Post 后立刻关闸；`allow_post=false`。只允许暂停/1x，未 5x，未写存档，未 commit/push。

## 会话

- machineId `a849f760-4114-424f-af9c-d10eef8ca3e8`，LAPTOP-6FQIF6OJ。
- 新 pid **12948**（旧 8500 已在 t195 因 `0xC0000005` 退出；26976 更早已不在）。句柄与对象指针全部重绑，未复用旧会话。
- 只读探测：已在局内，不是主菜单；未自行点开局。
- 版本 Windows 1.19.5.0.7c6c，SHA256 `709F916AFBEBCFE64A26678702691AEB40945D206074C2A80DE8E9D601FCE148`。base `0x7ff7a91c0000`。
- 开局对照为新的 ETH 1936-01-01 12:00（官方暂停 +0x6c1=1，速度档 0），21 个未编入师，无集团军/集团军群/计划。结束时日期为 **1936-01-01 13:00**（短时 1x 走过一个小时 tick），仍官方暂停，速度档 0。
- 进程至本检查点仍存活，未崩溃。t195「从工厂对象 +0x8 整段清零」的写法未再使用；本轮按 t192 只写必要槽、只清已知残留（NewRoot 仅 +0x60/+0x6c）。

## 实际发出的命令

推荐脚手架在当前局内、避开意大利前线重建。已升格字段只当脚手架，不再升一次。

1. **CMoveCommand** factory 1402：师 1829，5010→8036。Post 成功；师仍在 5010，路径 `[8036]`。全程保持官方暂停即可写路径。
2. **COrderGroupCommand** factory 2983：theatre `{67,43}` + 师 1838。干跑 IsValid=1 后 Post，`wait=0`、`post_rax=1`，未超时。建成集团军 1「第1集团军」。
3. **CSetArmyLeaderCommand** factory 3369：312 → 集团军 `{53,1}`，+0x30 已打包，+0x38=0。IsValid=1，`post_rax=1`。中途快照 `theatre_after_ag` 可见集团军 +0x88 已有将领指针。
4. **CArmyGroupCommand** factory 5433：建成集团军群 2「第1集团军群」，下属集团军 1。
5. **CSetArmyLeaderCommand**：313 → 集团军群 `{53,2}`。IsValid=1，`post_rax=1`。中途快照 `theatre_after_oa` 可见集团军群 +0x88 已有将领指针。
6. **COrderNewRootCommand** factory 4096：在集团军 1 上建计划实例 id=1，type=2，省份 5097/7944 落入 +0x258/+0x25c；官方 path +0x70 为空。
7. **COrderNewFrontCommand**：path size +0x5c=2，attach_id +0x68=1，集团军句柄已打包。IsValid=1，`post_rax=1`，但 **没有出现新实例**，官方 +0x70 仍空。不把 +0x258 当 vertex/path。
8. **COrderAssignCommand**：+0x28 师 1838 句柄数组，+0x40 集团军句柄，+0x48 实例 id=1。IsValid=1，`post_rax=1`。之后实例 **+0x210**（writer token `scheduled_member` 0x30b1）长度为 1，元素经 vt+0x20 / this-adjust +0xB8 还原为 CArmy 1838，句柄 `{51,1838}`。
9. **CSetArmyLeaderCommand** 将领 314 → 师句柄 `{51,1846}`：干跑 IsValid=1 后最小 Post，`post_rax=1`，但 314 的 +0x1048 未出现任职。随后 `theatre_final` 与活体回读中，集团军/集团军群 +0x88 与全部将领 +0x1048 均为 0。最可疑的是在已有集团军/集团军群任职之后，对 **师句柄** 再发 SetArmyLeader（1x 与 Execute 也在同一窗口）。本轮不再重试任职，不把 unit kind 当成已证实。
10. **CPauseGame** factory 1732：+0x48=0 解除暂停，出现非空对照（路径仍在、+0x240 变化）后立即 +0x48=1 恢复暂停。速度档本就是 0，未改。日期 12:00→13:00。1829 仍在 5010，路径仍为 `[8036]`；`commandlist` 与 `full_path` 仍空；+0x240 原始值为 `0x000041a0`（16800），不是 0-1 进度。
11. **COrderExecuteCommand**：保持官方暂停，Execute 后不开 1x。`post_rax=1`。实例 +0x248 由 0 变为 1，与反汇编 `mov byte [rcx+0x248], dl` 一致。

闸门在每次 Post 后关闭。结束时 `allow_post=false`，`safe_land_tool_gate.OPEN` 不存在。

## 升格

只升格本轮活体证实的新字段，已升格脚手架不再升一次。

- `world.plans.assigned_unit_ids`：COrderInstance+0x210，官方 writer 0x10d1450 token `scheduled_member` 0x30b1；this-adjust +0xB8；COrderAssignCommand 后对照师 1838。
- `world.plans.executing`：COrderInstance+0x248，官方 token `can_execute` 0x30b2（非零才写出）；COrderExecuteCommand 在官方暂停下把它从 0 写成 1。

`own_plans` 现在同时给出 `assigned_unit_ids` 与 `executing`。offsets 增加 `OI_SCHEDULED_MEMBER = 0x210`，并增加键 `plan_execute_assign_t196`。

## 诚实未升格

- `world.plans.type`：活体仍为 2。GetOrderType 仍只命名 1=ORDER_MOVE、3=ORDER_INVASION。无新的官方命名对照。
- `world.plans.vertex_province_ids`：官方 +0x70 在 NewFront Post 成功后仍空；+0x258/+0x25c 不是官方 vertex/path。
- `world.plans.axis_province_ids`、`world.plans.status`：无新对照。
- `world.own_units.order.type` / `target_province_ids` / `eta`：短时 1x 后 commandlist、full_path 仍空；不把非空路径当成 OrderType，不把路径末省当成 target；+0x240 的 16800 不是 ETA。
- `world.leaders.assigned_to` 的 unit kind：IsValid 通过并 Post 成功，但 +0x1048 未指向师，且可能清掉了已有集团军/集团军群任职。不升格。army / army_group 两种 kind 仍以 t192/t193 为准。

战斗、损伤、补给、拆建筑、危机仍未做。

## 清单

- 路径：`D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md`
- 仍是 14 表、116 字段、3 列，无附录。
- **64 已验证 / 52 未验证**，`complete_input=false`。
- SHA256 **`a159657f42fa0ec4ab65e7342473c7a4432a763d91d378ff07c37b2059f5a4d2`**（Copy-Item 后回读，无 BOM）。
- 为避免旧测试钉死活清单，已冻结 `test_t193_input_army_group_plan.py` 对活 D SHA 的断言（改为只钉 t193 记录哈希）。`test_t188` 的历史 `not plans.executing` 证据 JSON 未改。
- `python -m unittest discover -s research -p "test_t*.py"`：**233 OK**（原先 229 + 本轮 4）。

## 打包与 Post 课

- t195 主要嫌疑（工厂对象从 +0x8 整段清零）在本轮被避开。COrderGroupCommand 按 t192 打包后 Post 成功，进程未崩。
- 超时即停、不连续重试的闸仍保留；本轮 OrderGroup 未超时。
- 不要因为 CSetArmyLeader 对师句柄 `{51,id}` 的 IsValid=1 就 Post。本轮在已有集团军任职之后发了这条，结束时任职槽被清空。在弄清 Execute 语义前不要再对师句柄发该命令，也不要为补任职而重试同一条 Post。

## 停止状态

- pid 12948 仍在，官方暂停 +0x6c1=1，速度档 0，日期 1936-01-01 13:00（America/New_York 墙钟以当时探测为准）。
- 1829 仍在 5010，路径 `[8036]`。
- 集团军 1（成员 1838）⊂ 集团军群 2；计划 1 正在执行，`assigned_unit_ids=[1838]`。将领槽当前为空。
- 闸门关闭。未重启游戏，未写存档，未 commit/push，未给用户发消息。

## 阻塞与下一步

剩余未验证仍包括：`plans.type`（需要新的官方命名）、`vertex_province_ids`（需要真正写入官方 +0x70 的命令）、`axis_province_ids`、`plans.status`、`order.type` / `target` / `eta`，以及 `assigned_to` 的 unit kind（需单独、可逆、且不再误伤集团军任职的配方）。若再崩溃：立刻停、关闸、写检查点，不要重启、不要重试同一条 Post。
