# t250 用户地理范围与方针的配置读取

用户 2026-11-22 的 widget 回答已经原句写入 `calling/tables/commander_policy.json`：地理范围选 global，负责全球陆战；默认方针选 annihilate，歼灭敌军。

schema 里 global 的合法形状是 `{"kind":"global"}`，不能再带省份或“仅陆战”字段。`负责全球陆战` 只保留在 `statement`，没有变成第二种 scope。`annihilate` 只保存 schema 枚举，没有展开成作战决策。

`calling/commander_config.py` 的 `load_commander_policy` 和 `merge_commander_policy` 是这两个字段的读取与合并。文件缺失、缺键、JSON null、非法 kind、global 再带 province_ids、stance 不在枚举、夹带 instructions 或 allow_write，都会拒绝。null 不会改写成 global。只写了 scope 的文件不会补上 annihilate，只写了 stance 的文件也不会补上 global。观察对象里已有的不同 scope 或 stance 不会被覆盖。观察对象里已经存在的 instructions 会原样留下，本模块不新写原文。

输出只有 `meta.geography_scope` 和 `policy.stance`。不写 feedback、allow_write 或 complete_input。这不是完整 Input，也没有修改清单。清单仍是 87/29，等父级复核这两项是否算“配置来源已验证”。这里验证的是离线配置读取，不是实机集成，也不是整份 schema 已经能通过。

四个封存生产文件没有改，当前哈希仍是：

| 文件 | SHA256 |
|---|---|
| `calling/input_capture_live.py` | `e10bf427df1059c3f16873960bcbdabef826ef1dc058ad5e087b5a67d8087d37` |
| `calling/input_loaded_fields.py` | `1aecf151e7f221fa2f1a6b86b37a9d15bf2a44d0f7f649f552b2af8f808e65b5` |
| `calling/tables/generalissimo_input.schema.json` | `9a941dd3931b635591582b0d2ba3fe7ab1ceb3554a2d30af54154e61071b45ee` |
| `calling/input_observation.py` | `27a9a3ad6cab8a419e423486948b8952f4f4ee2bdc9084787a514c126738ccd6` |

实机观察对象只在 `input_capture_live.py` 的 `capture()` 里组装。要让那次实机结果带上这两项，需要在速度赋值之后调用 `merge_commander_policy(observation)`。那会改变上面的第一个哈希，所以没有自动改。`capture()` 仍不导入本模块，仍声明 geography 与 allow_write 不由内存提供。Backend 写门和 `allow_write()` 谓词没有改。

离线验收：

```
python "钢四陆军总司令/records/test_t250_commander_policy.py"
```

10 项通过。没有运行 live capture、doctor、status 或已有的 t249 四测试。
