# t251 checkpoint：t250 已在 GitHub，C 尚未同步

状态：配置读取这一阶段已经提交并推送。本文件只把恢复边界落盘，不改 global/annihilate 行为，不扩大写权限，不改清单。

## 已保存

- 分支 `cursor/t244-t245-records-01bd`
- t250 提交 `247c3bc3cd3625cb2ba6bc0334bd25359284ae25` 已在 `origin` 上
- 用户原句在 `calling/tables/commander_policy.json`
- `load_commander_policy` / `merge_commander_policy` 会给出 `{"kind":"global"}` 和 `stance=annihilate`
- 缺文件、缺键、null、非法值、冲突值会拒绝。null 不会变成 global，缺 stance 不会补成 annihilate
- 上一阶段离线测试 10 项通过。本 checkpoint 没有重跑测试，也没有跑 live capture、doctor 或 status

## 未完成，不能当成做完

- `calling/input_capture_live.py` 仍是封存哈希 `e10bf427df1059c3f16873960bcbdabef826ef1dc058ad5e087b5a67d8087d37`，`capture()` 不会调用配置合并
- 因此实机观察对象还不会带上这两项
- 清单文件没有改，仍是 87/29。这不是清单晋级
- `complete_input` 仍是 false。annihilate 只是枚举，没有作战实现
- 云端不能访问 C。复制文件之前不能说 C 或 Windows checkout 的 git HEAD 已同步
- `main` 仍是 `bc043f9e40f5b2f32698702534cc73a035b02c86`，未合并

## 父级恢复

增量包只含 t250 的五个新文件和本 checkpoint。四个封存生产文件不在包内，不要覆盖它们。

对清单里每个路径：目标不存在就按包内字节新建；已存在且 SHA256 相同就跳过；SHA256 不同就停止，不要覆盖。写完再算一次 SHA256。这只是文件字节对齐，不是 git checkout，也不是本地 HEAD 已同步。
