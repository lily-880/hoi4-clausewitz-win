# t230 checkpoint — own-front membership proved, missing_divisions not promoted

## Target closed without promotion
The independently named native quantity in 0x697db0 is `_TotalFrontDesiredNrDivisions`. That is desired force, not missing divisions, and must not be relabeled or subtracted into an official shortage field. `REQ_DIVS` at 0x177de53 lives in the same UI window as `garrison_order_headline` and `GARRISON_ORDER_CONF` (also `BATTLE_PLANS_X_WILL_BE_ASSIGNED`). It is a garrison-order required-divisions label, the window is PARTIAL because of unresolved indirect jump 0x177d3fa, and required is still not automatically missing. Volunteer-required, frontage-full, AI wanted/desired, and CAIFront unassigned/balance methods are likewise rejected substitutes.

## Current own-front membership
The official country+0x168 theatre array has exactly one CTheatre, `0x23e02f93b20`. Its +0x50 list has five CFront objects, IDs 1278, 76, 70, 1734, 1735. Every one has kind 66 and +0x18 back-pointer equal to that same player theatre. This is current own-theatre membership. No official missing/shortfall value was read from these fronts, and no positive/negative missing samples exist because no named missing consumer was found.

## Research correction, preserved transparently
A first 0x800-byte scan of the player theatre appeared to find additional CFront vectors at +0x230/+0x410/+0x5f0/+0x7d0 (counts 3, 73, 3, 8). Those offsets overlap packed neighboring CTheatre objects at stride 0x1e0; each neighbor is a real CTheatre whose own +0x50 list back-points to itself. None of those theaters is in the official country theatre array. They are recorded only as a non-own neighborhood, not as player fronts. CFront vtable 0x29f23b0 was resolved from the live CTheatre RTTI control. Loader 0xf7be60 names invalid country-tag and missing-province load errors; it is not a staffing consumer.

## Tests
30 unique methods (25 task/scope + 5 shared). 2 suite starts: first collection failed (0 invocations) because the adjudicator used non-ASCII bytes literals; after a UTF-8 encode fix the second run passed 30/30. Total invocations 30, not 60 unique tests. Windows replay 0, old suites 0. No promotions.

## Inventory and scope preservation
0 promotions / 0 inventory rows changed; 87 verified / 29 unverified (17 memory + 12 nonmemory), 14 tables 116 fields 3 columns. SHA 8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3 unchanged.
Do not infer combats.result from selector XOR defensive_victory. Crisis notes remain group-level cached advice from 3/25 members; kind composed; no severity/full feed. Isolated still lacks positives; relation still lacks a foreign-friendly sample; signed remainder is not a derived nonnegative deficit.

## Safety
Fresh Runtime before each memory block verified PID10288 / base 0x7ff758fc0000 / version 1.19.5.0.7c6c / SOV3 / pause1 / speed0 / tick 60781105 / both OPEN gates false. Heap roots were freshly derived; overlapping neighbor theatres were not treated as stale own-front pointers. Production 51 and fingerprint gates/hashes unchanged. 0 game writes/Post/native calls/save access/time advance/pause-speed/UI changes; no commit/push/cloud/generic production changes; no quota polling.

## Next target
world.crises.severity via an independently named severity consumer on the already-qualified alert/crisis witness. Do not infer severity from alert 3/4 names or supply thresholds, and do not expand the 3/25 member census, notes, or full Crisis/feed/Input scope.
