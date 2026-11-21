T169 CORRECTION:1552CF0 is a description STRING formatter, NOT an effective numeric level getter. Country parameter is formatting context. Actual total-level entry1201750. Named lookup now proved; see t169_checkpoint/semantic proofs.

# t168 checkpoint — 2026-11-18T09:33:13.523074-05:00 (EST)

This is a substantive continuation checkpoint, NOT a user-assistance blocker. Further independent work remains. Began09:13EST. No usage poll/purchase/plan change. No game action, memory write, injection/Post, saves, speed change, commit/push or cloud work.

## Accepted results
- Original D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md successfully updated and exact UTF8 bytes read back.
- 116 unchanged field names /14 tables /3 columns.39 verified,77 unverified (was37/79).
- SHA256 459f3e8eb6f26093d574d96eaf4faa7c64b51789e66bbde8dc1394f1674673c3
- New world.shortages.equipment.equipment_type and .stockpile: LIMITED to own currently present stockpile buckets with exactly integral quantities. Actual current train_equipment=5. Not all demanded types or shortages; absent type !=0; unknown demanded/deficit/affected IDs remain omitted.
- Proof is actual typed CStockpiledEquipmentDeleteCommand execution flow, NOT mere object names/numerical match.1A3A240 resolves country+F68 CProductionStatus ->production+200 live CEquipmentVariantPool. Ordinary delete branch1A3A319..32A sets selected variant CURRENT amount0 via10980E0. We only disassembled; NEVER executed it.
- Type entries stride24 ptr/begin/count/totalFIXED; variant entries stride16 ptr/quantityFIXED.10980E0 subtracts old via NEG2574BA0, adds new and stores new; begin/count construction traced. All current live type quantities equal their variants and backlinks. Quantity scale100000 supported by one-item construction and explicit truncation method1098860. Fractional integer rounding remains unproved: collector deliberately omits stockpile if fractional, rather than guess rounding.
- C53170 LEA+200 is compiler-folded/shared across unrelated classes (including CArmy path). NEVER type it as universally a production getter. Correct typed caller plus both RTTI checks is mandatory.

## HP all-use correction
- Removed misleading CA_MAX_STRENGTH key from calling/offsets.py AND historical research/_t144_patch_offsets.py generator; renamed CA_STRENGTH_420_RAW with version warning. No callers of old key found in bounded calling/scripts/research root Python audit.
- observe_own_divisions no longer has historical_max mode or default max emission. Default unclassified emits no HP; version-gated1.19.5 explicitly emits current. Variable maximum renamed. Tests enforce historical_max rejection and explicit current/no max.
- Production1.19.5 continues independent max getter CDF460 (primary virtual+108):max(100,qword(*(army+138)+288))/100000. CA+420 signed qword is CURRENT, as actual damage subtraction proves.
- t168_hp_version_errata.json plus per-file .errata.json sidecars clarify older opening snapshots while preserving raw evidence bytes; t165_checkpoint.md now begins version correction. Old1.19.4 equality retained RAW, not portable semantic proof.

## Automatic implementation and actual acceptance
- calling/input_loaded_fields.py new own_equipment_stockpile with typed roots, bounded ranges, all variants covered exactly once, no overlaps, type backlink and aggregate equality, stability journal, fractional/absent-value policy.
- calling/input_capture_live.py calls it and ACTUALLY runs bundled full schema on every capture; full_schema_validated:true means checked, schema_validation.valid:false remains. complete_input:false retained, never inferred from shape alone.
- Updated offsets_input_windows_1.19.5.json; no source control commits.
-66 tests pass; modules compile. New research/test_t168_input_stockpile.py plus HP regression and infrastructure overlay guard tests.
- Final two live observations EXACTLY equal:pid29000,version1.19.5.0.7c6c,ETH44,21 units,4 templates,12 provinces,20 leaders,train stock5.821 dependent reads rechecked. Clock/player header stable; UI speed1x. Pause bit still unknown and omitted.
- Full schema actually reports77 errors, DIFFERENT concept from77 unverified fields. Missing Unit.order and in_combat remain; not complete Input.
- research/t168_live_capture.json,_repeat.json; t168_validation_summary.json; t168_equipment_semantic_proofs.json; t168_document_update_verification.json; t168_remaining77_fields.json.

## Building progress (NOT field promotions)
- Typed CBuildingDatabase constructor6C86F0 ->allocation caller198CE6 ->store198CEC gives globalRVA33DD268; live RTTI CBuildingDatabase.
- db+40 actual loaded template array56 including null; templates CBuildingTemplate+2E0 runtime index1infra,9bunker,10coastal confirmed current live. db+58 MSVC+hash entries stride40 /55 names parallel-order association still candidate, NOT accepted general name lookup. Dynamic bunker token577A/coastal577B are current loaded values, NOT portable constants.
- CProvince writerEF2A50 atEF2C54..5B explicitly emits buildings token2F59 from province+190. THIS is proven province building status root.
- Important candidate correction: diagnostic500-byte province read also saw RTTI at+3A0. This is NOT proven inside same CProvince (may neighboring allocation). Never treat+3A0 as another same-province status; candidate JSON explicitly corrected.
- CBuildingStatus+20 i32 map[template+2E0] ->index into status+38 CBuilding pointers.12017E0 actual base-level getter returns0 for missing slot, otherwise signed short+40 PLUS1162FE0 overlays (max active non-additive +sum active additive, pointer arrays+10/+28, overlay+48 levels,+94 inactive flag). Not yet complete effective-level semantics.
-1203890 uses healthy+42 (level-(level-healthy)) then calls1552CF0 with country, so cannot equate simple stored level/healthy to all effective fort/infrastructure values until country modifications traced.
- Added infrastructure fail-closed guard for NONEMPTY overlay arrays. Current5010 building level=healthy2 and BOTH arrays empty; previous limited field scope unchanged. No damaged/worldwide infrastructure promotion.
- All technical t168_building*.json, t168_province_building_serialization.json and conservative offsets research roots saved.

## Next independent block, no user involvement needed yet
1. Continue building effective getter1552CF0 and template lookup/name association; use proven province+190. Then bounded known country/province roots to find actual foreign nonzero forts for structure proof ONLY, never export fog-hidden objects or widen own-visible output.
2. Equipment demand: follow typed production request/need methods using accepted current pool, not mixed C53170 xrefs. Current free stockpile is not total national equipment and not demanded count. Avoid redoing old current=need402 samples.
3. Other remaining items from t168_remaining77_fields.json. Current empty combat/orders are scene facts, not permanent blockers; no state manipulation authorized. If genuinely needing changed gameplay, give parent minimal experiment; no such blocker now.
