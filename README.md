# hoi4-clausewitz-win — Path C 阶段验收（Stage Acceptance）

**Windows 侧 HOI4 1.19.4 陆战陆军代理桥接**（ReadProcessMemory + 已证明 Post ABI）。  
灵感来自 [smerss/Clausewitz-MCP](https://github.com/smerss/Clausewitz-MCP)（Linux-only）；本仓库是 Windows 后端与偏移工作台，**不是** 107-tool 克隆。

> **阶段状态（2026-11-02 Asia/Shanghai）：可演示验收。**  
> Path-C 诚实进度约 **~99%**（相对 ~60% 基线；**已过 70%**）。  
> 耐久堆叠 hold-through-Attack（stack≥2）已关闭 HIT；进攻目的地口袋 `any_at_1886` / Retreat 仍开放或 PARKED。

---

## Path C 是什么

目标：在 **战时 ETH** 续跑图上，用已证明 ABI 驱动陆军 **集结 / 进攻 / 取消 / 移动 / 战略转移**，偏向包围（encirclement bias），且：

- 速度 **仅 pause 或 1x（禁止 5x）**
- 默认 **`allow_post=False`**；开闸需 env + marker + checklist（G4–G6）
- 不发明 org/str / 邻接 / theater-frontline / Retreat factory
- Instant 空轮询与 PATH densify：**PARKED**

---

## 现在已经能做什么（Works NOW）

| 能力 | ABI / 模块 | 证据 |
|------|------------|------|
| **Strategic Redeploy** | type **4753** · `calling/strategic_order.py` | 多军集结 HIT；路径含目的地 |
| **Move** | type **1402** · `calling/move_order.py`（**ucrt_malloc** 远程缓冲） | PATH_CONTAINS_DEST |
| **Cancel movement** | type **1415** · `calling/cancel_order.py`（ucrt） | PATH_CLEARED / 锚点 peel 再集结 |
| **SupportAttack** | type **3620** · `calling/attack_order.py`（inline handle@+0x28 province@+0x30） | ATTACK_POSTED_STABLE |
| **Durable stack≥2 hold-through-Attack** | Phase **2ikr** hybrid | Post 时 stack=2；hold 窗 depths 全 2；`durable_stack_ge2=true`；early_stop=`DURABLE_STACK_GE2` |
| **RO 附着 / 科目** | `clausewitz_win.py status` · `army_subjects` | 读省份、路径、标签 |

**里程碑 SHA：** `8d6bfad` / HEAD `fedef1d`（phase2ikr DURABLE HIT）。报告：`reports/phase2ikr_strategic_anchor_peel_attack_summary.json`。

### 仍开放 / PARKED（勿在演示中宣称已完成）

| 项 | 状态 |
|----|------|
| **Retreat** | **HARD_DENY_PARKED** — 无已证明 Post ABI / `retreat_order.py` |
| **any_at_1886 / 进攻目的地口袋** | 仍开放（2ikr 耐久堆叠 HIT，但未到 1886） |
| **Instant** | PARKED（禁止空 poll / Instant×PATH densify） |
| **战斗 densify / 邻接** | **HONEST_EMPTY** — 不发明 |
| Capstone / 121 | 未作为本阶段目标 |

---

## 安全闸门（务必遵守）

1. **速度：** 仅 pause / 1x。禁止写 5x。日历卡住可空格点一下解 pause，或 `launch_into_map.py --start-tag ETH --speed 1 --allow-ai` 自重启。
2. **`CLAUSEWITZ_ALLOW_POST`：** 默认关。演示 Post 前开闸，结束后立刻关；删除 `research/safe_land_tool_gate.OPEN`（及 legacy strategic-only marker）。
3. **Checklist：** `research/safe_enable_checklist.json`（UTF-8；读写用 `utf-8-sig` 兼容 BOM）。
4. **VirtualFreeEx：** Post 线程可能仍在跑时不要急着释放远程缓冲。
5. **find_pid：** 取 **最大工作集** 的 `hoi4.exe`（防僵尸进程）。

---

## 快速开始（Windows）

```powershell
cd "$env:USERPROFILE\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win"
$env:HOI4_PATH = "D:\STEAM\steam\steamapps\common\Hearts of Iron IV"

# 只读体检（无需开闸）
python clausewitz_win.py doctor
python clausewitz_win.py peinfo
# 游戏已在地图上时：
python clausewitz_win.py status
# UI date/hour: docs/CLOCK_ALIGNMENT.md  (+0x478/+0x484 date; (u32(+0x468)%24)+1 hour)
python clausewitz_win.py redeploy 1042 758 --dry-run
```

### 进图 / 自重启（ETH @1x）

```powershell
python launch_into_map.py --start-tag ETH --speed 1 --allow-ai
# 等待地图就绪后再 status；速度保持 1x 或 pause
```

### 明日现场演示

见 **[DEMO_TOMORROW.md](DEMO_TOMORROW.md)** 与 **[DEMO_READY.md](DEMO_READY.md)**。  
推荐剧本：战时 ETH → Strategic 集结 → 堆叠后 Attack → 观察 durable stack≥2。  
**不要演示 / 不要宣称：** Retreat、已抵达 1886 口袋（除非当场证据为真）。

---

## 仓库导航

| 路径 | 说明 |
|------|------|
| `calling/strategic_order.py` | Strategic 4753 |
| `calling/move_order.py` | Move 1402（ucrt_malloc） |
| `calling/cancel_order.py` | Cancel 1415 |
| `calling/attack_order.py` | SupportAttack 3620 |
| `calling/army_subjects.py` | 陆军索引 / 省份 RO |
| `docs/LAND_ARMY_AGENT.md` | 陆战代理阶段日志 |
| `docs/SAFE_LAND_POST.md` | 安全 Post 闸门日志 |
| `docs/LAND_POST_READINESS.md` | Post 就绪长文 |
| `docs/PHASE2IKR_STRATEGIC_ANCHOR_PEEL_ATTACK.md` | 2ikr 耐久堆叠 HIT |
| `scripts/phase2ikr_strategic_anchor_peel_attack.py` | 耐久堆叠演示战役脚本 |
| `research/WINDOWS_OFFSETS.md` | 偏移再生说明 |

---

## Target pin

| Item | Value |
|------|--------|
| OS | Windows 11（本机测过 25H2） |
| Game | `hoi4.exe` **1.19.4.0** Operation Postern |
| 默认 Steam 路径 | `D:\STEAM\steam\steamapps\common\Hearts of Iron IV` |

游戏小版本更新通常要重生 RVA；Windows 小更新一般不用。

---

## Upstream credit

架构与逆向方法受 **Clausewitz-MCP**（MIT, smerss）启发。  
见其 [research/FINDINGS.md](https://github.com/smerss/Clausewitz-MCP/blob/main/research/FINDINGS.md)。  
本仓库的 Windows PE 后端与 1.19.4 表是独立工作。

## License

MIT — 见 [LICENSE](LICENSE)。
