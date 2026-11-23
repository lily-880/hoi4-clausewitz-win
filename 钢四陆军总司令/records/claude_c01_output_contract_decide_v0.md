# claude_c01：输出契约与 decide v0（离线）

2026-11-23，Claude。用户授权「以现有工作为基础自由推进，重大拍板再问」。本块全部离线：没有读进程、没有 Post、没有存档访问、没有改生产四文件或清单。编号用 `claude_c` 前缀，避免与其他 agent 的 tNNN 冲突。

## 为什么做这一块
接口文档定义了完整的 decide(input) → output，但仓库里只有输入侧。输出侧没有 schema、没有代码，总司令无法形成闭环。本块先把输出侧和一个只观察的决策函数做出来，让「读态势 → 决策 → 输出」可以离线端到端跑通。

## 新增文件
| 文件 | 内容 |
|---|---|
| `calling/generalissimo_output.py` | 输出契约的唯一来源：36 种写入命令表（机动 6、编成 8、将领 4、计划 15、任务 3），生成 JSON schema；外加 schema 表达不了的语义检查 |
| `calling/tables/generalissimo_output.schema.json` | 由上面生成，测试保证一致，不手改 |
| `calling/decide_v0.py` | decide() 第 0 版：只出告警和态势说明，**永远不下令**（即使 allow_write=true）；含离线 CLI |
| `calling/tests/test_commander_output.py` | 27 项离线测试 |

## 语义检查（validate_output）
- 闸门：allow_write 不为 true（含缺失）时 orders 必须为空。
- 地理范围：写入时 geography_scope 不能为 null；theater 时所有省份必须在范围内。
- 引用：师、集团军、集团军群、计划、将领 ID 必须存在于输入；输入缺对应集合时视为无法核实，拒绝。
- new_ref：唯一；plan_ref / parent_*_ref / post ref 必须指向本拍更早创建的同类对象。
- order_seq 唯一；intents 的 expands_to_order_seqs 必须指向本拍真实命令；brief.game_time 必须等于输入。
- disband_army_group 的 keep_armies 必须为 true；update_* 的 plan_id 与 plan_ref 恰好一个。

schema 设计取舍：brief 设为可选，因为运行周期表规定每小时一拍「不送」brief。

## decide v0 行为
- 告警：包围 → critical；即将被包、计划失败 → high；缺装、缺人（有受影响的师才报）→ watch；战斗有 result 才报大捷/大败。这些严重度是总司令自己的判断，不是引擎读数。
- 告警载荷只复制输入里实际存在的字段，绝不补 deficit 等未证字段。
- 态势说明：各计划执行状态与绑定兵力（含经集团军间接绑定的师）、我方防守中的战斗与组织度、引擎缺补给判定的师（注明「不代表被切断」）、输入缺了哪些 world 块。
- 方针：使用 policy.stance；缺省按接口文本「保部队优先」记为 preserve_force。CLI 默认合并 `commander_policy.json`（global/annihilate）。

## 验证
- `python -I calling/tests/test_commander_output.py -v`：27 项全部通过（1 轮、27 次调用、0 失败）。
- 用 t201 两份历史完整采集（ETH 1936-01-02，21 师）离线跑 decide_v0：输出通过 schema 与语义检查，orders 为空，1 条缺装告警，2 场防守战斗进风险。
- 既有 `test_input_capture_cli.py` 17 项仍全部通过；生产四文件哈希不变；清单 87/29 不变。

## 已知缺口（未处理，等用户拍板）
- 输入 schema 的 feedback.type 覆盖不了 21 种输出命令（测试 FeedbackGap 固化了这一事实）；改它需要动封存的输入 schema。
- v0 不下令。写入侧的命令模块（move/strategic/attack/cancel）是在 1.19.4 上做的，1.19.5 上未重新验证。
