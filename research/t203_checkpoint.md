# t203 checkpoint

## 块1：续接与新链开段
会话已只读重绑，PID12948/base7FF7A91C0000，官方pause1/speed0/tick60759398，六计划均false，闸门关闭。0Post/0游戏写/0远程调用，不推进、不碰存档、不commit/push、不访问D。只读已加载代码/.pdata，生产exe磁盘指纹门未绕过。
已开始深查C4A420的CC6BF0上下文与19C9A20接收者，以及159FB30/15A6E40/1755D90的配送状态消费者；证据t203_initial_chains.json。当前本地74/42，D最后72/44未同步；新升格须独立证明。

## 块2：扣除性质和encircled官方文案桥
C4A420由C4C200的HQ/OrdersGroup流程调用；它的CC6BF0返回值是本次实际从师CArmyManpower当前表提取的人数，随即交19C9A20加到部署对象+88。19C9AC0返回max(+8C-+88,0)剩余需求；19C9BC0返回+88/+8C进度，1755D90用DEPLOYING_HQ_PROGRESS_MANPOWER显示它。当前两个真实OrdersGroup+188均空，未制造HQ部署样本。该链已排除为普通战斗累计伤亡，不能把需求缺口、本次抽调、部署已收集量、累计伤亡互换。
发现更直接的人力扣除链CC77D0：逐国家从表提取fraction数量，按stat+E8算回池部分，剩余记D7ABC0/D7B240统计，再通过CC7550写回old-removed并返回本次removed总人数。其战斗归属和累计范围继续追调用者，不能仅因出现统计writer就填战斗casualties。
配送消费者159FB30仅在REQUESTED_REINFORCEMENT_DELIVERING_TO与...BLOCKED之间切文案；15A6E40把同一布尔值传15A6510构建补充配送tooltip。本段另发现175D940的change_template_icon/divisions更新路径：E64C50=false明确在175DC38写按钮原因4；1739900原因4使用CHANGE_TEMPLATE_DISABLED_ENCIRCLED。这比possibly cut off文本更强，但继续核实读对象、图依赖与真实分支，尚不凭该文本直接升格。
21真实师省份+D0的RTTI均CControllerArea，而非此前候选统称supply area；当前同一area，5师+2E=0、16师+2E=1。+2F8均0。已纠正类身份，不能将地区指针当省份/父计划。区域/可达图静态函数存在.pdata分段；EEF530先前29/40行均非完整函数，本段用有界可达CFG补全至103指令，所有边已解析，明确其为全局海军基地映射存在性检查；不把被截断片段称完整证明。
原清单本地74/42，D最后72/44未同步；0游戏写/0Post/0远程调用，暂停与tick均不变。


## Block 3 — true manpower loss and delivery candidate
E64C50 research reproduction sampled 21 own + 9 existing enemy combatants without errors: flag2e true=25, capital main-area match=5. No isolated/port branch live positive; schema_emission=false, no promotion. Exact UI chain E64C50 false -> reason4 -> CHANGE_TEMPLATE_DISABLED_ENCIRCLED is now documented but missing live false sample.
CC77D0 has no direct E8 but leaf wrapper CC77B0 tail-jumps at CC77C1. Only wrapper direct caller CEC270 passes Army+3D0 and returns actual removed people. CEC270 direct callers CE7310 and CE84D0; latter adds returned integer to Army+678 (scope/lifecycle unproven). CArmy C0=CEC2E0 remains HP/org, NOT CEC270; no CEC270 .rdata references. D7ABC0 adds 64-bit totals +50/+58 by country side to object reached diplomatic relation+2E8; this is not yet battle-local casualty proof. Inventory remains74/42; D72/44 unsynced.
