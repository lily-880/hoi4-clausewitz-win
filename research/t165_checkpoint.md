VERSION ERRATUM: t167/t168 supersedes HP source claims below: on1.19.5 CA+420 is CURRENT, not max. See t168_hp_version_errata.json; old snapshot max equality is not semantic proof.

# t165 substantive checkpoint

- Windows-only live process, PID29000, executable1.19.5.0.7c6c fingerprint gated. Own player index44 tagETH; current campaign1936-01-01 12h; UI1x, observed stable clock; official pause bit still unproved. No game writes/Post/save reads or writes/UI actions/commit/push.
- D original document updated and UTF8 reread:116 unchanged field names,14 tables,3 columns,34 verified /82 unverified (baseline21/95). All13 promotions conservatively scoped. SHA256: b1e6603a6d11a6089e32678729e6e7deb089a54f778be76205346835788bae8f.
- Added current player/own owner runtime tag via actual GS+358 MSVC table, not old shipped tag JSON; province VP i32+38 via named writer, optional stored rename+40; no default localized name invented.
- Added four used templates combat_width from semantically proved SubUnitDefinition qword+58 /100000:587=10,588=8,589=12,590=8. Supports currently empty.
- Added20 own army leaders: serialized CId index+0c (type+8, NOT direct division-officer IDs); exact CCharacter+a8 pointer connects display string+28 and key+48; all20 full display names matched. Named writer proves overall skill and four attributes. Trait string starts+10, including complete SSO and heap names. assigned_to remains omitted.
- Infrastructure accepted ONLY province5010/state271 present undamaged level2 (level+40, healthy_levels+42); other11 occupied provinces absent building NOT inferred zero.
- Actual collectors: calling/input_loaded_fields.py; calling/input_capture_live.py; offsets_input_windows_1.19.5.json updated. Two live observations exactly equal;21 own units,4 templates,12 provinces,20 leaders;551 dependent reads rechecked.38 tests pass; py_compile pass. Full Input schema still FAILS78 errors; Unit.in_combat/order mandatory still missing; complete_input:false.
- Technical evidence: t165_semantic_proofs.json; t165_validation_summary.json; t165_live_capture*.json; t165_document_update_verification.json; t165_95_field_dependency_audit.json and t165_remaining82_dependency_audit.json. Latest repo document mirror t165_态势信息读取能力清单_修订.md.

## Independent work and rejected guesses

- Bounded actual world inventory found99 theatre objects; orders_group/field_marshal_group/theater_group arrays all empty; GS combat manager list empty. This is a current-state fact, NOT a permanent blocker or permission to fabricate empty/false contract states.
- CArmy secondary serializer vtable atCA+10, RVA29d6f78; writerCED2E0. Main vtable is NOT the serialization interface. Secondary offsets need +10 conversion. Named army_manpower atsecondary+3c0 -> CA+3d0 CArmyManpower.
- Real manpower sub-tables: value token36fb atmanpower+8 -> array+10, need token36fc at+28 -> array+30; stride8 {i32 country_index,i32 amount}. Own21 current/need tables both sum105000. Bounded402 foreign samples across8 countries also equal; NO contrasting current-vs-required sample. Keep strength.manpower unverified until source/mutation proof; do not reinstate CA+4f0.
- Named army_current_supply_ratio token4ced is CA+610, but all21 observed fixed-decoded values72, not accepted0..1. Do not emit as supply.ratio. max_supply atCA+600=108. No supply promotion.
- CA+420 serializer labelstrength alone does NOT resolve current/max split; keep current unverified, caution in offset profile, do not claim damage contrast. Prior max baseline is opening/full-HP equivalence only.
- CCountryManpower+10 value450000 is serializedratio, NOT available manpower. +c namedcurrent still needs free-available semantics proof.
- Next independent high-value block: trace CArmyManpower value/need getters and mutation/source flow statically; trace current-strength vs template/max getter; inspect loaded building-type registry for province forts, building absence-to-zero accessor; country current/free manpower and equipment getters. No user operation necessary for these steps. Current lack of battle/formation samples does NOT justify stopping other independent work.
- No usage-gate claim:96.9% was tracking baseline, not current-segment consumption. No further usage polling/payment changes.
