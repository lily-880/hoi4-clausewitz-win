# Phase 2fl — NewFallback subject fields beyond +0x54

**Result:** `NEWFALLBACK_FIELDS_DEEPENED`  
**Base:** `24ac836` (2fk) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed

## Method

Live Capstone on ITA@1x for shared **Serialize `0x18e8a60` / Deserialize `0x18e2500` / IsValid `0x18df4b0`**
(NewFallback ≡ ReplaceFallback) plus NewFallback **Execute `0x18d8fc0`**.

Important: bytes after `int3` padding at `0x18e8ae3` belong to **COrderNewFrontCommand** serialize (`0x18e8af0`) — first auto-pass mixed those in; corrected map rejects that bleed.

## Proven field map (size `0x60`)

| off | name | evidence |
|-----|------|----------|
| +0x28 | `subject_handle` | IsValid `add rcx,0x28` → gate `0xbbb1e0`; ser handle writer; exec resolve |
| +0x30 | `units_data` | ser loop base; deser token `0x28a3` push; exec `lea rdx,[this+0x30]` |
| +0x3c | `units_count` | ser `mov eax,[this+0x3c]` loop count |
| +0x48 | `provinces_data` | ser token `0x174` province-array writer; exec `lea r8,[this+0x48]` |
| +0x54 | `fallback_flag_or_id` | IsValid `cmp dword [this+0x54],0` (2fi) |

Serialize tokens: header `0x3f` · unit `0x28a3` · province array `0x174`.

`ARMY_GROUP_FALLBACK` unchanged: `army_group@+0x28`, `fallback_flag@+0x30`.

## Live

```json
{
  "pid": 34188,
  "hours": 70,
  "ui_date": "1936-01-03 22:00",
  "speed_policy": "pause-or-1x only (never change speed)",
  "scenario": "ITA@1x NewFallback subject field deepen (no Post)",
  "cmdline_expect": "-gdpr-compliant -start_tag=ITA -start_speed=1"
}
```

**Next shortest blocker (NON-Post):** NON-Post: recover subject_handle semantic + units/provinces vector packing OR Assign/Unassign edge deepen; still NO ALLOW_POST

Script: `scripts/phase2fl_newfallback_fields.py`
