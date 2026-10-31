# Phase 2fm — NewFallback subject semantic + CPdxArray packing

**Result:** `NEWFALLBACK_SUBJECT_PACKING_DEEPENED`  
**Base:** `34e5858` (2fl) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed

## CPdxArray (proven 2de)

`{T* data; i32 capacity; i32 size; void* alloc}` = **0x18**

## Units @ +0x30

| off | name | evidence |
|-----|------|----------|
| +0x30 | units_data | 2fl ser loop base; token 0x28a3 |
| +0x38 | units_capacity | CPdxArray.capacity |
| +0x3c | units_count (size) | 2fl ser `mov eax,[this+0x3c]` |
| +0x40 | units_alloc | CPdxArray.alloc |

Sibling: MassCancel/Unassign use data@+0x28 → size@+0x34 (=data+0xC).

## Provinces @ +0x48

| off | name | evidence |
|-----|------|----------|
| +0x48 | provinces_data | 2fl ser token 0x174 |
| +0x50 | provinces_capacity | CPdxArray.capacity |
| +0x54 | **provinces_size** | CPdxArray.size; IsValid `cmp dword [this+0x54],0` |
| +0x58 | provinces_alloc | CPdxArray.alloc; struct ends @0x60 |

**Reclassify:** 2fi name `fallback_flag_or_id@+0x54` → **`provinces_size`**. True `fallback_flag` remains on **ARMY_GROUP_FALLBACK@+0x30** only.

## subject_handle @ +0x28

Gate `0xbbb1e0` reads `{u32 type @+0x28, u32 index @+0x2c}` then validates (order-domain).

- IsValid gate `0xbbb1e0` (`isvalid_order_fallback_gate`)
- Ser handle writer `0x2285670`
- **Candidate:** battle-plan / order-subject handle (type+index), **not** raw CArmy* (units are the +0x30 array)

## Live

```json
{
  "pid": 34188,
  "hours": 98,
  "ui_date": "1936-01-05 02:00",
  "speed_policy": "pause-or-1x only (never change speed)",
  "scenario": "ITA@1x NewFallback subject semantic + CPdxArray packing (no Post)",
  "cmdline_expect": "-gdpr-compliant -start_tag=ITA -start_speed=1"
}
```

**Next shortest blocker (NON-Post):** NON-Post: live midflight NewFallback/ReplaceFallback hex to confirm handle type-id OR Assign/Unassign edge deepen; still NO ALLOW_POST
