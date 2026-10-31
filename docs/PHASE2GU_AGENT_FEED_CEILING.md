# Phase 2gu — Agent feed ceiling catalog polish (RO)

**Result:** `AGENT_FEED_CEILING_CATALOG_POLISH`
**Live:** pid 30352 · 1936-01-11 17:00 · hours=257 · tag=15 · @1x
**Feed:** can_feed=6 · hard_deny/empty=6

**allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb/2gk **NOT executed**

## Can feed land agent today (see LAND_POST §6d)

- **CArmy locate** — handle type=51 + country_tag · `HIT` · src 2gp
- **CArmy+0x200 multi-prov path candidates** — tag-FP filtered; not demangled dest · `LIVE path nonempty=6 multi=3` · src 2gm/2gs
- **Instance+0x70/+0x88 order/front maps** — ≠ army midflight dest; ⊀ +0x200 (2gn) · `HIT` · src 2gm/2gn
- **OG+0x50 ≡ CArmy+0xB8 membership proxy** — MI VT 0x29d6fb8 · `walkback 376/376` · src 2gp–2gs
- **Assign units type=51 → CArmy** — when Assign sighted; oi@+0x48 often 0 · `HIT (oi=0 unset typical)` · src 2gp
- **Live clock/counters** — hours/UI/pending/stage/drain/exec RO · `HIT` · src live_meta

## HARD_DENY / honest-empty

- **CMove/SA/Cancel midflight hex (bit_identical)** — `HONEST_EMPTY (2gt move=0 cancel=0)` · src 2gj/2gt
- **Named movement_dest demangle** — `HONEST_EMPTY` · src 2go
- **Assign units↔OI when order_index≠0** — `QUIET (2gt assign_oi≠0=0)` · src 2gq/2gr/2gt
- **ring_embed / Dummy recreate in-process** — `STUBBED — needs SAFE Post` · src 2gk
- **Any Post / tool-gate / 2fb|2gk recipe execute** — `HARD_DENY allow_post=False` · src standing
- **Demangled OG+0x50 / MI field name** — `STUBBED` · src 2gp+

**Ceiling note:** Non-interactive RO cannot raise midflight/oi≠0 ceiling further without human leave midflight or SAFE Post for ring_embed. Catalog consolidates what agent may already consume RO.

## Works / stubbed

- Works: §6d feed ceiling; SAFE_POST 2gu; minimal live_meta
- Stubbed: midflight hex; named dest; ring_embed; Post; Assign oi≠0 HIT

**Next shortest blocker (NON-Post):** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0; push when GitHub reachable; still **NO ALLOW_POST**.

Script: `scripts/phase2gu_agent_feed_ceiling_polish.py`
Reports: `reports/phase2gu_agent_feed_ceiling.json`, `reports/phase2gu_summary.json`

*Phase 2gu · 2026-10-31 15:58 Asia/Shanghai*
