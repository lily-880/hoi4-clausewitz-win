# t169 checkpoint 2026-11-18T09:53:27.841970-05:00 EST

Continuation checkpoint after~20min, NOT a user-assistance blocker. Further independent work remains; no current need for user intervention. Began09:33EST. No game writes/Post/injection/UI/speed change/saves, no commit/push or cloud. PID29000 responsive,1.19.5.0.7c6c,ETH44,UI1x,stable Jan1 clock; pause bit still unknown and not emitted. No usage polling/purchase/plan change.

## Delivered
-41 verified /75 unverified (was39/77). Original116 field names,14 tables,3 columns preserved. D original written and exact UTF8 readback.
- D path:D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md
- SHA256:4d9f3b10ec11d1bb2fa3448abb74eb8dd27dd4f1f078eb84e609bcdc29b8b24f
- New world.provinces.fort_level and coastal_fort_level. Scope: own observed provinces; absent native0 OR undamaged present building with empty extra-level overlays. Damaged/overlay-bearing states omitted, NOT guessed.
- Existing infrastructure field expanded ONLY with independently reproduced native getter/name lookup to12 actual own observed provinces, NOT global extrapolation from5010.5010/state271 remains2; other11 have explicit registered native-absence0.
- Formal automatic capture now contains fort/coast/infra for12 own provinces. Own fort/coast currently0; proof not based solely on0: bounded59 France provinces found4 actual nonzero objects, newly implemented reader independently reproduces land10,10 andcoastal1,1. No foreign research province IDs or troops exported to observation/visible_units.
-81 unit tests pass; modules compile. Final double live observations equal;1026 loaded dependent reads rechecked.21 own units,4 templates,12 own provinces,20 leaders,train stock5 unchanged.
- Full schema checked INSIDE capture:54 errors (was77), separate from75 unverified fields. complete_input:false. Unit.order and in_combat still absent. No invented empty unknown collections or policy/visibility values.

## Real proof and corrected misconception
-1552CF0 is a DESCRIPTION STRING formatter, NOT a numeric effective-level getter. It initializes MSVC output atRDX, localizes desc key, appends bonuses using country and supplied healthy level. Old t168 hypothesis corrected in version profile and t168 checkpoint prefix; t169_building_getter_errata.json.
- True numeric entry1201750. Specific-template tag165 attemplate+2C4 branches to12017E0: status+20 i32 map attemplate+2E0 ->status+38 actual CBuilding pointer; missing/empty/null returns0 at120182A..36. Presence returns signed short+40 plus1162FE0 active overlays. Accepted no overlays andlevel=healthy+42; otherwise omitted.
- Named building DB lookup PROVED, no longer parallel-array guess:6CE380 literal bunker and6CE430 coastal_bunker call6C6970. It asserts names+1=template count, compares lowercaseFNV1a hash andstring; matchj returnsptrarray[j+1] at6C6A54. C1F080 computes hash. Current tokens577A/577B remain dynamically loaded, not hardcoded.
- Existing CBuildingDatabase global33DD268, db+40templates/db+58stride40 names+hash. Proven CProvince+190 named buildings. +3A0 remains UNACCEPTED likely adjacent allocation; never use as same province member.
- calling/input_loaded_fields.py: building_name_hash,resolve_building_templates,building_status_level,province_fort_level; infrastructure production path uses same validated named-template/native map path; old2arg narrow reader retained for compatibility.
- calling/input_capture_live.py integrates; calling/tables/offsets_input_windows_1.19.5.json records current offsets/proof/scope; no commits.

## Next independent block: REAL NONEMPTY equipment requests found
- Actual roots via RTTI: country+F98 CLogisticsStatus; +F70 CDeploymentStatus; +F78 CReinforcementStatus; +FD0 CCountryOccupationStatus; +15A8 CCountryOperationManager. DO NOT labelF70 airforce orFD0 deployment (initial function-reading hypotheses were wrong; actual live RTTI resolves them).
- Nonempty current own CReinforcementStatus+20 array has1 CArmyReinforcementRequests; group+28 array has1 CReinforcementRequest at0x1b108bb67a0.
- Request+38 is CEquipmentVariantPool CURRENT; +78 CEquipmentArcheTypePool REQUIRED. Actual infantry_equipment raw300000 (3) vs8000000 (80). Difference77 is a CANDIDATE request shortfall, NOT accepted whole-country demanded/deficit and not exported. No unit receiver link established. Do NOT conclude existing own-unit equipment_ratio proof wrong merely from this unlinked request; investigate ownership/receiver first.
- Reproducible version-gated,1x,read-only bounded probe saved AND executed: python research/t169_probe_reinforcement_requests.py ->t169_reinforcement_probe_repeat.json. Max4 groups/8 requests each; current1/1. Fingerprint gate, player re-resolution, dependent rereads; no hardcoded PID/country pointers in saved probe.
- UI demand source trace:1E1F6A0 actual cache writer. Country717350 returns+F98.1409630 obtains category15 currentstock value with special convoy/etc handling;1409810 ->1409890 plus14080C0 sums request deficits.1409890 includes deploymentF70 then reinforcementF78, adds140A400(occupationFD0),1409E50(logistics+28 transient requests gatedtype),140A600(operations+15A8). Need complete predicates/specialcases before country demand output.
- IMPORTANT multiinheritance: logistics GUI secondary this offset18hex. Tooltip1E1B7A0 uses received secondarythis directly. Its+5F8 labelarmyreinforcements corresponds PRIMARY+610, notprimary+5F8. Primary+5F8 from1409630 subsequently subtracts1409810 totalneeded; do not confuse cached stockpile/netneed with armyreinforcement demand.
-10948A0 reads required archetype pool stride16 aftertype->538, and1094900 reads current variant bucket stride24 using type runtime+478. Missing entries return0 natively, but complete branches and semantics not yet integrated. Existing stockpile collector still present-integral types only.
- Current typed roots occupation+28 empty, logistics+28 empty, operations+10 empty are scene facts only; do not assert permanent absence. Deployment/other special equipment/receiver identity remains independently traceable; no need for gameplay changes yet.

## Files
- research/t169_building_semantic_proofs.json, t169_building_getter_errata.json, t169_buildings_typed_live_proof.json, t169_foreign_collector_acceptance.json(post-refactor rechecked), t169_validation_summary.json
- t169_live_capture.json,_repeat.json; t169_document_update_verification.json; t169_态势信息读取能力清单_修订.md and更新前 backup; t169_remaining75_fields.json
- research/test_t169_input_buildings.py (15 new tests;81total)
- Demand static traces:t169_logistics_demand_ui_xrefs.json,t169_logistics_demand_cache_writes.json,t169_logistics_demand_getters.json,t169_logistics_current_need_dataflow.json,t169_current_need_army_and_garrison_branches.json,t169_equipment_demand_component_getters.json,t169_unit_equipment_need_pool_getters.json,t169_need_components_live_roots.json,t169_nonempty_reinforcement_requests.json,t169_reinforcement_receiver_link_candidate.json. File names containingarmy/garrison initially reflect hypotheses; use actual RTTI above, not filename as proof.

One transient Shell unreachable message occurred but script HAD executed and saved JSON; existence checked before continuing. No permission refusal, no workaround. All commands now complete, no background processes left.
