# claude_c04：把已证明的字段接进总司令采集

2026-11-23，Claude。只改总司令专用的容错采集 `calling/live_input.py`；封存的生产四文件和清单都没有动。测试局：ETH 1936 第二局，pid 12576。

## 背景
实采对照 116 字段清单时，有 12 个字段在研究中已证明能读，但从未接入采集。本次接入其中 7 个，另外 5 个暂缓，理由见下。

## 已接入（7 个）
| 字段 | 读法与依据 | 实测（1936-01-04 12:00） |
|---|---|---|
| shortages.manpower.affected_unit_ids | 每个师的引擎缺额 max(需求−当前, 0) > 0（CArmyManpower，0xCC6480 公式，已有读取函数） | [1810] |
| combats.phase | 官方活跃战斗管理器（GS+0x268）里的战斗记为 ongoing；结束的战斗会离开列表，所以从不填 ended | 3 场均为 ongoing |
| combats.casualties | t217：每个战斗方对象 CLandCombatant +0x180 = 本方累计承受的地面组织度伤害（原始值 ÷100000）。按我方所在一侧拆成 our_org_loss / enemy_org_loss；人员伤亡不填 | 战斗 2：我方 11.78，敌方 0.70 |
| own_units.order.eta（只填 progress） | t209 原生取值函数 0xC51970：行军原始进度（CArmy+0x240）÷ 当前这一跳的边长度。边长度取邻接记录（步长 0x30）+0x18，只认普通陆地边。剩余小时不填 | 三个增援师约 0.61，与每小时 16800、边长约 123 万的推进速度吻合 |
| wars.a / wars.b / wars.state | t186/t225：玩家外交关系表里每个 +0x2E8 交战关系对象，第一方 +0x10、第二方 +0x14，+0x49==0 为 at_war；按对象去重 | ITA 对 ETH，at_war |

决策也用上了这些信息：态势说明写明交战对象；我方组织度损失超过敌方 2 倍的战斗，会标注为「明显不利」。

## 暂缓（5 个）
- **shortages.equipment.demanded**：t219/t220 的证明依赖每日缓存交叉核对，以及 6 种装备类型各自的门控条件；没有逐项复刻，宁可不填也不填错。
- **crises.kind / unit_ids / province_ids / notes**：t227 要解析 CInGameIdler+0x7A8 的警报管理器，确认 alert4 的因果，再和 CE4F10 补给判定交叉核对；单凭「缺补给」不能冒充危机。

## 结果
- 实采后对封存输入 schema 校验，错误从历史采集的 49 个降到 23 个；新字段零错误。剩下的错误来自未证明的字段，以及由配置提供的 allow_write / geography_scope（这两项在总司令循环里会补上）。
- 再跑一拍完整循环：正常结束，确认暂停。
- 离线测试：commander 38 项、live_trial 6 项，全部通过。
