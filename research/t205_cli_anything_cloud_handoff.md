# CLI-Anything small-scope cloud handoff — NOT implemented locally

## Decision / authoritative target
Target existing HOI4 read-only collector, NOT HKUDS/CLI-Anything itself. Local source root on connected Windows laptop: C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win. Source-provider URL is not established here; do not invent one. The parent must supply the correct cloud repo and the latest untracked inputs before launching. No clone, code upload, cloud launch, commit/push or PR was done by this executor.
Fresh git status shows all3 input files untracked (??). Windows live backend is machine-specific, but the selected argument/JSON/error/exit-code boundary is ordinary Python and can be implemented/tested cloud-side with injected fixtures. Therefore this generic improvement does NOT earn the local-machine exception. User expressly requested handoff in this case; no local source patch is claimed. Physical Windows live acceptance is a separate, currently restricted phase.

Authoritative source SHA256:
- calling/input_capture_live.py:3813c8badf52313d7daf7969ffb99e1035435968f5113d6a94c01b32ac6e273d
- calling/input_loaded_fields.py:1aecf151e7f221fa2f1a6b86b37a9d15bf2a44d0f7f649f552b2af8f808e65b5
- calling/input_observation.py:27a9a3ad6cab8a419e423486948b8952f4f4ee2bdc9084787a514c126738ccd6

## Actual external reading / bounded reference
Read remotely with GitHub read-only file surfaces, no installation or execution. Revision34f519533bc175d2fe287ab8316b0dd99bb9cc43:
- https://github.com/HKUDS/CLI-Anything/blob/34f519533bc175d2fe287ab8316b0dd99bb9cc43/README.md
- https://github.com/HKUDS/CLI-Anything/blob/34f519533bc175d2fe287ab8316b0dd99bb9cc43/cli-anything-plugin/HARNESS.md
Relevant HARNESS sections actually read: Phase2 output format; Phase3 backend/error boundary; Phase4 test plan; Phase5 unit/native/subprocess output verification; CLI Design “Fail loudly and clearly”, introspection and JSON mode; testing real output rather than trusting exit success. These are design references, not permission to add mutation commands, REPL state, installs or fallback engines.

## Problem / requested outcome for cloud agent
Current capture() lazily imports the Windows backend, enforces executable SHA/PE/version gate, builds partial observation/evidence, runs strict JSON schema validation and deliberately leaves complete_input=False. Bottom entry (currently lines290-298) parses required --out, calls capture(), writes result file, prints a JSON summary. It has no explicit machine-readable error/partial-result process contract. Investigate independently; do not treat a guessed root cause as prescribed.
Make a small change scoped to this entry boundary and focused tests:
1. Validate missing/empty/invalid arguments before opening a process or touching output; help/usage should not import mem. Avoid new dependencies or broad refactor.
2. Preserve existing capture() API, observation/evidence/omitted/unknown markers, result file shape, required --out call compatibility and existing summary keys. An explicit opt-in machine mode is acceptable if needed for compatibility.
3. In machine mode emit exactly one parseable JSON document to stdout; diagnostics go to stderr. Give explicit status partial/error (never imply complete when complete_input=False), stage/code/message for argument/backend/fingerprint/output errors, and distinguish artifact written from complete Input accepted.
4. Document and test stable exit codes. Distinguish usage failure, backend/fingerprint failure, export failure and usable-but-incomplete result. Existing callers must not silently break; if strict partial exit needs a new opt-in mode, make that explicit. Do not convert an exception into a fake observation or zeros.
5. Do not change any production version/SHA/PE/pause/validator gate, call policy or reader semantics. No skip-fingerprint/offline-live substitution flags. Keep complete_input=False even if a shape-only test happens to pass. Do not swallow/remove52 required-property errors from latest full exports. Preserve unwitnessed fields as omitted/unverified.
6. No game write, Post, remote execution, pause/clock change, save access, additional mutation backend, background game control, or retries of uncertain operations. No new write destinations: retain only existing explicit export behavior. No D access; no commit/push. Produce a reviewable patch/artifact without committing under this task's boundary.

## Acceptance plan (before implementation)
- Offline unit tests with injected backend: valid complete-shaped fixture still flagged incomplete unless independently accepted; real partial fixture retains all52 required errors and blocking_checks/omitted markers; invalid args; backend unavailable; fingerprint mismatch; permission failure; output IO failure; non-ASCII JSON; stdout/stderr separation; repeated invocation; legacy call compatibility.
- Subprocess tests for actual CLI entry, help/invalid args without importing Windows backend; machine JSON roundtrip and exact exit statuses using an explicit test seam, not an advertised production fake-live flag. No fake environment acceptance.
- Golden full fixtures: research/t201_full_capture_recursive_a.json SHA88dff7111ab117a3d94c9d57a219c2e55b62c6108e6f62a20021c7f5d964147e and b SHA8f6bad1187e8a0adb8782211417afee9bd0f505b61eb96d92a49f5223d75bda7. Validate against calling/tables/generalissimo_input.schema.json; each must remain complete_input=false,52 required errors. They are local/unuploaded inputs; do not assume cloud already sees them.
- Existing research suite:135 passed, including26 t205 tests; this is recovered existing coverage, NOT validation of an unimplemented CLI patch.
- Windows read-only guard acceptance: only after cloud patch is reviewed and brought to approved C root. Production capture currently needs opening p.image_path on denied D for mandatory SHA/PE gate. Full production live capture CANNOT be run now; do not bypass. Narrow existing Runtime.guard may separately confirm official pause/six plans, but is NOT complete-capture or new CLI full acceptance.

## Parent return message context
Recipient/context: original waiting user chat relayed by “github探索者”. Please relay status, not a false completion claim: actual CLI-Anything reading and exact handoff are ready; generic CLI source patch remains for cloud per user's conditional instruction. No message/draft was sent/created in an outside app by this executor.
