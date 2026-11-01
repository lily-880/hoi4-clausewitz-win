# 明日演示脚本（DEMO TOMORROW）— Path C Stage Acceptance

**时区：** Asia/Shanghai  
**目标：** 用 **已证明** ABI 现场展示陆战代理能力；诚实边界说清楚。  
**速度：** 仅 **pause / 1x**。禁止 5x。

---

## 开场白（30 秒）

本仓库是 HOI4 Windows RPM 桥。Path C = 战时陆军 **集结 → 进攻 → 取消/再集结**，偏向堆叠与包围。  
**已证明：** Strategic 4753、Move 1402（ucrt）、Cancel 1415、Attack 3620；以及 **堆叠≥2 扛过 Attack Post**（phase2ikr）。  
**未证明 / 勿宣称：** Retreat；部队一定到达进攻格 1886；Instant densify。

---

## 演示前（5 分钟）

1. 打开仓库目录：
   ```powershell
   cd "$env:USERPROFILE\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win"
   $env:HOI4_PATH = "D:\STEAM\steam\steamapps\common\Hearts of Iron IV"
   ```
2. 确认 `allow_post` 关闭、无 marker：
   ```powershell
   python -c "import sys; sys.path.insert(0,'calling'); from config import allow_post; print(allow_post())"
   # 期望 False；且 research\safe_land_tool_gate.OPEN 不存在
   ```
3. 游戏：若无图或 WS 异常塌缩，自重启：
   ```powershell
   python launch_into_map.py --start-tag ETH --speed 1 --allow-ai
   ```
   等到地图可见、日历在 1x 推进或可 pause。`find_pid` 取最大 WS。
4. RO 冒烟：
   ```powershell
   python clausewitz_win.py doctor
   python clausewitz_win.py status
   ```

完整勾选清单见 [DEMO_READY.md](DEMO_READY.md)。

---

## 推荐演示路径（约 10–15 分钟）

### A. 只读附着（必做）

```powershell
python clausewitz_win.py status
```

展示：ui 日期、player tag（ETH=15）、陆军省份可读。

### B. Dry-run Post（不开闸也可讲 ABI）

```powershell
python clausewitz_win.py redeploy <army_index> <province> --dry-run
```

说明 IsValid / Strategic 4753 形状；**不要**在未开闸时强行 live Post。

### C. 耐久堆叠战役（核心；开闸 → 跑完立刻关闸）

使用已验收脚本（2ikr）：

```powershell
python -u scripts\phase2ikr_strategic_anchor_peel_attack.py
```

**期望证据（与 `reports/phase2ikr_*_summary.json` 同构）：**

- Strategic HIT（或 SKIP 已在集结格）
- Attack HIT×N，`attackers` 在集结格堆叠
- `stack_depth_at_post >= 2`，hold 窗 depths 多为 2
- `durable_stack_ge2 = true` 或 early_stop `DURABLE_STACK_GE2`
- 结束：`final_allow_post = false`，marker 不存在
- 稳定：`responding_stayed=true`，`heap_exit=false`

**现场话术：** 「我们证明了战略集结 + 进攻指令，并且堆叠能扛过 Attack Post；这是代理能打出包围偏向的基础。」

### D. 收尾

```powershell
# 再确认闸门
python -c "import sys; sys.path.insert(0,'calling'); from config import allow_post; print('allow_post', allow_post())"
# 游戏保持 pause 或 1x Responding；不要 5x
```

---

## 禁止事项（演示红线）

- 不写速度到 5x  
- 不宣称 Retreat 已通  
- 不宣称 `any_at_1886` / 进攻口袋已关闭（除非当场 JSON 为 true）  
- 不做 Instant 空轮询 / PATH densify「刷证据」  
- 不发明邻接 / org / str  
- Post 演示后 **必须** `allow_post=False` 且无 OPEN marker  

---

## 诚实进度条

| 基线 | 现状 | 已过 70% |
|------|------|----------|
| ~60% | **~99%** | **YES** |

剩余最短 blocker：进攻目的地抵达（arrive-into-1886 / pocket）；Retreat（若可廉价证明）。
