# t254：owner-join 相等断言的范围

t253 的 unit 1101、type 51 是已提交事实：`CArmy+0x1D8` 为 16/ITA，`CArmy+0x1E0` 为 3/SOV，两词的 remap 结果也不相等。两个语义角色都仍是 UNASSIGNED。这里不把它们叫成 owner 或 controller，不改偏移，不生成关系枚举。

## 证实

相等断言 `remap(int[CArmy+0x1D8]) == int[CArmy+0x1E0]` 写在研究采集器 `research/t240_current_owner_directional_operands.py`。它当时只对 combat 3072 的 unit 399 执行，并把 `+0x1D8` 标成 raw owner、把 `+0x1E0` 标成 canonical owner。399 和 490 上两词相等，不能推出所有 type 51 都相等。1101 否定的是把这条断言普遍化。

生产己方师读取在封存文件 `calling/input_observation.py` 的 `observe_own_divisions`。它只解 `+0x1E0` 的 i32，要求该值等于调用者给出的 `player_index`，然后才写 `owner.index` 和 `relation_to_player=self`。这段代码不读 `+0x1D8`，也没有 remap 相等断言。因此 1101 的不等没有打进这条生产谓词。

清单里已验证的 `world.own_units.owner.index` 和 `world.own_units.relation_to_player` 仍只覆盖“己方数组中该 i32 等于玩家序号，关系仅为 self”。`world.visible_units.relation_to_player` 仍是未验证。1101 没有被写成 self、ally、enemy 或 unknown。

## 风险，不撤销原范围

`+0x1E0` 在生产源码里的变量名是 owner，但这次审计没有新的具名 consumer 证明这个名字。1101 的 handle type 是 51，即 `0x33`，会通过生产的 type 门；它的 `+0x1E0` 又等于当时玩家序号 3。若同一个对象也出现在玩家 `CO_ARMIES` 里，现有生产读取会把它当成己方 self。t253 只把它记在当前 attacker 列表的后续条目里，没有证明它属于玩家国家数组，所以这是条件风险，不是已输出己方行的否证。在 consumer 证据出来之前，不撤销原先限定的己方证明，也不把 visible 关系补成任何枚举。

应隔离的输出是 t240 式 owner-join 和任何把 combat 列表单位直接送进 `own_units` 的采集。不要隔离或改写已经只按 `+0x1E0 == player_index` 发出的己方 self 行。

## 留给实机的最小问题

现有实机 worker 若继续，只登记：在同一 1.19.5.0.7c6c 映像上，哪个具名函数读取 `CArmy+0x1D8`，哪个读取 `CArmy+0x1E0`，接收者的 RTTI 是什么。不要同时泛扫，不要凭 16/ITA 与 3/SOV 的差给两边命名。四个封存生产文件这次没有改。
