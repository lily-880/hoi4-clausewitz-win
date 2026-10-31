# Phase 2fp — Assign→order_index cross-link

**Result:** `ASSIGN_ORDER_CROSSLINK_DOCUMENTED`  
**Base:** `39a915c` (2fo) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb **NOT** executed

## Semantic (RO, no invent)

`COrderAssignCommand` binds `units[]` (CPdxArray of `{u32 type,u32 index}`, mostly `HANDLE_TYPE_ARMY=0x33`) to **`order_index@+0x48`** — a battle-plan order **slot index**.

Same integer space:
- `COrderExecuteCommand.order_index@+0x30`
- `COrderDeleteCommand.order_index@+0x30`

`COrderNewFallbackCommand.subject_handle@+0x28` is a separate order-domain `{type,index}` (gate `0xbbb1e0`), **not** the Assign slot index.

## Live sight (75.0s)

counts={"CHourlyTickCommand": 66008, "COrderAssignCommand": 2}  
assign_indices=[6, 25]  
overlap∩Execute=[] overlap∩Delete=[]  
NF_seen=False

### Examples
```json
[
  {
    "order_index": 6,
    "assign_to_minimum_order": 0,
    "army_lists": [
      [
        51,
        1810
      ],
      [
        51,
        1811
      ],
      [
        51,
        1816
      ],
      [
        51,
        1815
      ]
    ],
    "other_lists": [],
    "army_detail": [
      {
        "as_list": [
          51,
          1810
        ],
        "province_id": 13237,
        "country_tag": 44,
        "echo_matches": true
      },
      {
        "as_list": [
          51,
          1811
        ],
        "province_id": 1984,
        "country_tag": 44,
        "echo_matches": true
      },
      {
        "as_list": [
          51,
          1816
        ],
        "province_id": 13238,
        "country_tag": 44,
        "echo_matches": true
      },
      {
        "as_list": [
          51,
          1815
        ],
        "province_id": 13237,
        "country_tag": 44,
        "echo_matches": true
      }
    ]
  }
]
```

```json
{
  "pid": 34188,
  "hours": 180,
  "ui_date": "1936-01-08 12:00",
  "speed_policy": "pause-or-1x only (never change speed)",
  "scenario": "ITA@1x Assign\u2192order_index cross-link (no Post)"
}
```


## Stable live binding

- **order_index=6** (2fo + 2fp): armies `[51,1810/1811/1816/1815]`, tag=44 (ITA), provinces 13237/1984/13238/13237; `assign_to_minimum_order=0`; `u32@+0x40=0x35` observed unnamed.
- **order_index=1** (2fo): `[51,1803]` + non-ARMY `[4713,3906]` (type≥0x64 unresolved; no invent).
- **order_index=25** (2fp): empty units size=0 — slot-only / clear-ish edge; no invent.

No Execute/Delete/NewFallback this window — index-space sibling link remains catalog-proven; co-sight overlap still open.

**Next shortest blocker (NON-Post):** NON-Post: NewFallback/ReplaceFallback midflight subject type-id OR order_index→order-object table walk; still NO ALLOW_POST
