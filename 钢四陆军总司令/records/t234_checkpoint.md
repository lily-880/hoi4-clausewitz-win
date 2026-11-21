# t234 checkpoint — diplomatic 33EB090 enqueue is a shared flush, not a stored flag

Resumed under pt207u and t205u noquota from t233 inventory 87/29 SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3. C authority: C:\Users\Lenovo\Documents\钢四陆军总司令. Box mirror: /workspace/hoi4-docs-latest.

## Session
Actual current PID31576/base0x7ff72fc80000/version1.19.5.0.7c6c/SOV3. Runtime freshly derives roots before every memory block. pause1/speed0/tick60781105; both OPEN gates false. Old10288 invalid. Final seal separately rechecks all93 native windows and production/fingerprints before SHA-sync.

## Result: no promotion
Live LEA arithmetic shows F7BB20, F7BCE0 and F7E1C0 both enqueue and process EndBundle scope 33EB090. NotifyControllerChanged/F7B940 remains 33EB020 and is not diplomatic war-change proof. F6A071 stays an invalid-key assertion, not a stored flag. Enemy-key first-controller mismatches versus front+70 were not reused as invalid entries.

Independently named consumer 118DEF0 contains DIPLOMACY_JOINED_WAR_ENEMY/ALLY/TITLE, WAR, and pWarRelation && "Missing War Relation". It requires [rcx+0x68]==2, then ends with xor ecx,ecx; call F7E1C0 — a null list, not an explicit enqueue of the two war participants. The same null-ecx F7E1C0 flush appears in REVOKE_GUARANTEE_ACTION_THREAT and in the peace-conference winner/loser war-relation consumer. Event-FROM scope also uses it. Faction-removal, volunteer arrival/return (F7BCE0), and "Removing Theater %s from %s" (F7BB20) share 33EB090. Direct callers: 20 (18+1+1). 33EB090 is therefore a shared relation/theatre rebuild queue, not official wars.front_invalidated.

F7E1C0(null) copies a global pending country-pointer list through D56B10 (object/data 33EA908, count 33EA914) then F6F9B0 inserts listed countries into 33EB090 and may add further countries via unnamed 748490/DA37F0 (no literals; not assumed at-war). F70F40 still rebuilds fronts only when the scope has countries. One-shot pending observation: count 0, data null, player not listed — status only, not a schema false. Schema front_invalidated positive 0 / negative 0. No samples manufactured.

A bounded intel-name presence check hit 40 INTEL_LEVEL strings (NNavy strength-estimate defines and TRIGGER_INTEL_LEVEL_OVER). That search budget saturated; it is not a visibility.confidence consumer and does not prove other needles absent.

## Unique tests and attempts
17 distinct offline unittest methods, 1 collection/start, 1 completed suite, 17 invocations, 17 pass / 0 fail / 0 error / 0 collection failures. No reruns, old or Windows suites. Coverage: exact 33EB090/33EB020 LEA split, named joined-war literals, null-ecx prelude, type==2 gate, shared revoke/peace/volunteer/theater callers, 20-caller accounting, D56B10 copy, empty pending not schema-false, unnamed predicates, F6F9B0 related-insert calls, navy-define rejection, 34-window integrity, session-guard mutations, mandatory schema omission, INTEL_LEVEL budget saturation. Mutations are offline only.

Research launches: 3, all successful, 0 failed starts. Final seal separately recorded in t234_final_seal.json (UTF-8 from the start). No background jobs.

## Inventory and boundaries
87 verified / 29 unverified (17 memory + 12 nonmemory), 14 tables / 116 fields / 3 columns; 0 changed rows. Inventory SHA256: 8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3. Production 51 / four hashes / fingerprint gates untouched. Game writes / Post / native calls / formatter calls / save access / time advance / pause-speed / UI changes / full capture / commit-push / generic production changes all 0.

## Next productive target
visible_units.visibility.confidence via an independently named unit-intel confidence consumer. Exclude NNavy INTEL_LEVEL_* strength-estimate defines, do not treat TRIGGER_INTEL_LEVEL_OVER as confidence unless separately proved, and never map opacity/tier. Do not resume 33EB090 empty-scope or pending-zero polls, F6A071 diagnostics, or unnamed 748490-as-war scans. Fresh-bind before any reads.

C final seal/manifest/archive and independent box SHA receipt record actual synchronization counts. This is a research checkpoint, NEVER game-save access.
