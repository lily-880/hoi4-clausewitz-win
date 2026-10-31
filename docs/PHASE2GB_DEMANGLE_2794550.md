# Phase 2gb — Demangle soft VT RVA 0x2794550 (Instance+0x100)

**Slice:** B (cheapest RO). War-dense (A) and NF midflight (C) skipped.  
**allow_post:** False. Never 5x. No Post / inject / tool-gate / 2fb / Capstone.

## Result

`vt_2794550_CPdxNewDeleteAllocator__not_e100_elem_class`

Soft VT RVA **0x2794550** (recurring in 2ga Instance+0x100 packed twin opaque qwords) demangles via MSVC COL→TypeDescriptor to:

**`CPdxNewDeleteAllocator`**

- COL sig=1, offset=0; TD name `.?AVCPdxNewDeleteAllocator@@`
- 6/8 probed vtable method slots land in `.text`
- Live soft-hit recount still nonempty (allocator pointers still visible in +0x100 buffer views)

## Implication (no invent)

This **names the soft VT**, not the +0x100 element type. The recurring “opaque ptr VT” is an **allocator**, not a Clausewitz province/army/order elem class. Instance+0x100 remains a packed/heterogeneous size-twin of +0xe0 with **unnamed elem layout**. Do not treat +0x100 as `CPdxArray<CPdxNewDeleteAllocator*>`.

## Method

1. Static PE (`research/re-dumps/hoi4_1.19.4.exe`): `vtable[-1]` → COL → TD+0x10 name; slot sanity in `.text`.
2. Live RO recount via phase2ga `read_inst` / +0x100 ptr samples (pause-or-1x only).

## Stubbed / next

War-dense CArmy path; NF/RF midflight; named +0x100 elem class beyond allocator soft-VT; Post path closed.

**Next shortest NON-Post blocker:** bounded NF/RF midflight OR war-dense named CArmy path — still **NO ALLOW_POST**.
