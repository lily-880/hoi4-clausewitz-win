# claude_c10: Second mock exam (commander builds its own ORBAT and draws its own front lines)

2026-11-24, Claude. Continues from c09's from-scratch practice game (opening save `GER_1939_08_14_base`, 1939-08-14 → 08-19, the commander built its own ORBAT). The mock exam continued from 1939-08-19 12:00 at 12 hours per tick.
Command: `python -I scripts/commander_loop.py --decider decide_llm --hours 12 --max-ticks 200 --key-moments`.

## Result
| Metric | Baseline game (c06/c07) | This game |
|---|---|---|
| Date Poland stopped resisting | 1939-10-15 (62 days) | **1939-10-12 (59 days)**: Poland's province count went from 84 straight to 0 between 10-11 24h and 10-12 12h |
| DeepSeek cost, from war declaration to capitulation | about ¥8.23 | **about ¥6.70** (from-scratch practice ¥0.68 + mock exam ¥6.02, 113 calls, about 4.1 million tokens) |
| Western front | Commander pulled the West Wall apart itself; by the late stage the French-German border wasn't even fully manned | Never fewer than 2 divisions per province; after Poland's capitulation 87 divisions moved west, 7 to 14 per province |
| Homeland | — | **Not occupied**. The same 7 French provinces faced Germany throughout; France's province count stayed at 618 |

Poland's province count, sampled every few ticks: 144 → 138 → 134 → 132 → 128 → 126 → 124 → 119 → 117 → 112 → 108 → 103 → 100 → 95 → 90 → 86 → 84 → 0.

## Problems found
1. **The scorer read stale data for the whole run** (fixed).
   - `commander_loop.py` picked the latest capture by sorting on file name. An old `tick_20261124_practice_0826_capture.json` always sorted last, so `target_provinces` stuck at 136.
   - As a result, Poland's capitulation was not detected and the loop **ran 90 more ticks (10-12 → 11-27)**, wasting money.
   - The "key moment" detection used the same data, so **it never fired once this run** (user point 5 was not met this time).
   - Fix: pick the newest capture by modification time.
2. **After capitulation the war relation is still "at war"** (Poland's government in exile keeps the war going). Capitulation can't be judged from the war relation; rely on the controlled province count reaching 0.
3. 74 of our controlled provinces disappeared around 11-07 (445 → 371). The western border was unchanged and France gained no provinces. It's former Polish territory handed over after the capitulation, not the homeland.
4. After Poland's capitulation the commander correctly switched to the defensive in the west: it judged the French border to be all level-10 forts, probed only province 678 (hills, no forts) with one army, and didn't waste divisions. It also never put a garrison on the Dutch, Belgian, or Luxembourg borders.

## Next steps
1. Rerun the opening save once with the fixed scorer, to confirm that key moments pause the game as intended and that it stops at capitulation.
2. Army groups are still unused, and two armies' front ranges overlap. Have the commander bring in army groups and marshals.
3. In the middle stage (September) each 3 days still took only about 4 to 6 provinces. Next, look at whether the offensive lines are deep enough and whether the armored divisions are concentrated in the main direction.

## Correction: army groups must be commanded by field marshals (user pointed this out, 2026-11-24)
- **The problem**: In the mock exam the commander formed "1st Army Group" (5 armies) but appointed General Bock as its commander, and the 6th Army belonged to no army group. Earlier, in c09, I had also had generals Rundstedt, Bock and Leeb command army groups. The game doesn't block this, but it isn't a proper chain of command.
- **How rank is read**: The game's own triggers `is_field_marshal` / `is_corps_commander` read leader object **+0xE7C**: 0 = field marshal, 1 = general (corps commander). The game follows history, so in 1939 Rundstedt, Bock and Leeb are all generals (historically they weren't promoted until 1940).
- **Field marshals on the roster but unusable**: Mackensen (only available on the "German Civil War" focus path) and Blomberg (retired in 1938). Tested: the game removes them within an hour of being appointed. They're now in `calling/tables/unavailable_leaders.json`. Any later appointment the game revokes is added to the list automatically, and those leaders are no longer offered as candidates.
- **Promotion**: CPromoteUnitLeaderCommand (factory 0x13FB150, size 0x30, vtable 0x2A2DDA0, validity check 0x1400CA0; +0x28 = leader handle {4713, id}). Its execution turns a leader with +0xE7C = 1 into a field marshal. Tested: after promoting Bock and appointing him to 1st Army Group, he was still in place 6 hours later.
- **Hard rules** (`plan_orders.validate`): armies may only be commanded by generals; army groups only by field marshals; only free generals can be promoted. Appointments and promotions are read back from the game afterwards to confirm they took effect.
- **Situation summary**: shows each leader's rank, `field_marshals_total`, and `command_rule_violations` (armies not in an army group, armies commanded by a field marshal, army groups not commanded by a field marshal). The prompt requires the commander to fix these first, and to promote a general if there aren't enough field marshals.
- **Practice run** (test game, 1939-11-28 → 11-30): without my involvement, the commander promoted Weichs to field marshal on its own and appointed him to command 2nd Army Group. Bock commands 1st Army Group. The violation list is now empty.
