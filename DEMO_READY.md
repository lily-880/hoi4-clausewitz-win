# DEMO_READY — 明日演示勾选清单

日期：2026-11-02 准备 / 明日使用 · Asia/Shanghai  
仓库：`Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win`  
远端：https://github.com/lily-880/hoi4-clausewitz-win

## 环境

- [ ] `HOI4_PATH` 指向本机 1.19.4 安装目录
- [ ] Python 可 import `calling/`（在仓库根目录执行）
- [ ] `git rev-parse HEAD` 与 `origin/main` 一致（验收推送后核对）
- [ ] `allow_post == False`；无 `research/safe_land_tool_gate.OPEN`

## 游戏

- [ ] `hoi4.exe` 存活；`find_pid` = **最大 WS**（防僵尸）
- [ ] 已进图（非前端）；推荐 ETH 战时 / 历史续跑
- [ ] 速度 **pause 或 1x**（禁止 5x）
- [ ] 日历若卡住：空格解 pause，或  
  `python launch_into_map.py --start-tag ETH --speed 1 --allow-ai`

## 只读冒烟（优先，不必 Post）

```powershell
cd "$env:USERPROFILE\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win"
$env:HOI4_PATH = "D:\STEAM\steam\steamapps\common\Hearts of Iron IV"
python clausewitz_win.py doctor
python clausewitz_win.py status
python -c "import sys; sys.path.insert(0,'calling'); from process import find_pid; print('pid', find_pid())"
```

期望：doctor 通过；status 有 ui 日期与陆军；pid 非空。

## 可选：最小 gated Post 冒烟（仅当 RO 不够时）

1. 开闸（脚本内一般会自管；若手开务必成对关闭）  
2. Strategic 或 Attack **一次** dry-run → 可选一次 live  
3. **立刻**恢复 `allow_post=False` 并删除 marker  

更稳妥：直接跑验收战役并依赖脚本收尾关闸：

```powershell
python -u scripts\phase2ikr_strategic_anchor_peel_attack.py
```

## 演示中要投影的文件

- `README.md`（本阶段验收说明）
- `DEMO_TOMORROW.md`（步骤与红线）
- `docs/PHASE2IKR_STRATEGIC_ANCHOR_PEEL_ATTACK.md`
- `reports/phase2ikr_strategic_anchor_peel_attack_summary.json`

## 关闸确认（演示结束必做）

```powershell
python -c "import sys,os; sys.path.insert(0,'calling'); from pathlib import Path; from config import allow_post; print(allow_post()); print('marker', Path('research/safe_land_tool_gate.OPEN').exists())"
```

期望：`False` / `marker False`。

## 话术边界

**可以说：** Strategic / Move / Cancel / Attack Post HIT；durable stack≥2 hold-through-Attack。  
**不说：** Retreat 已通；一定打到 1886；Instant 已打通。

## 本机冒烟结果（2026-11-02 准备时 Asia/Shanghai）

- doctor: **ready**；attach OK；pid **36496**（SELF-RELAUNCH ETH @1x）
- status: armies_count **17**；player_tag **15**；ui ~1936-01-03
- allow_post **False**；markers **absent**
- 速度策略：pause/1x；未写 5x
