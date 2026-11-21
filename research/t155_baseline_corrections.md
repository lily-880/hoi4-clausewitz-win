| 字段名 | 已验证/未验证 | 一句简短说明 |
| --- | --- | --- |
| strength.manpower | 未验证 | 当前师人力，尚未与满编人力区分。 |
| strength.current | 未验证 | 师当前生命值。 |
| strength.max | 已验证 | 师编制生命值上限，历史21师已对照。 |
| relation_to_player.self | 已验证 | 与玩家国家索引相同的己方关系。 |
| relation_to_player.其他关系 | 未验证 | 盟友、敌人、附庸等非己方关系。 |

| 字段名 | 已验证/未验证 | 一句简短说明 |
| --- | --- | --- |
| meta.allow_write | 未验证 | 由配置提供的写入许可，默认false，非内存发现。 |
| meta.geography_scope | 未验证 | 由配置提供的指挥范围，默认null，非内存发现。 |
| policy.stance | 未验证 | 由玩家方针或接口默认值提供，非内存发现。 |
| policy.instructions | 未验证 | 由玩家提供的方针原文，非内存发现。 |
| meta.speed | 未验证 | 当前暂停或1x状态，尚无已证明的暂停标志。 |

| 字段名 | 已验证/未验证 | 一句简短说明 |
| --- | --- | --- |
| order.type | 未验证 | 师当前任务类型，不能从空路径推成待机。 |
| order.path_province_ids | 未验证 | 师按顺序经过的省份，尚无非空路径对照。 |
| in_combat | 未验证 | 师是否正在作战。 |
| template.template_id | 未验证 | 师编制的内部编号。 |
| supply | 未验证 | 师的真实补给状态。 |
| visible_units.visibility | 未验证 | 玩家战争迷雾下确实可见的其他陆部队。 |
