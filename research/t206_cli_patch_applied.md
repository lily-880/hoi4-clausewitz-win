# t206 — cloud CLI patch applied and Windows OFFLINE acceptance

Recorded 2026-11-19T06:09:39.943559-05:00 (EST). Target https://github.com/lily-880/hoi4-clausewitz-win; actual workspace is the existing approved C user repository, not a new checkout.

## Baseline, conflict check, backup and application
- Read the delivered cloud report and patch. Patch changes only calling/input_capture_live.py and adds calling/tests/test_input_capture_cli.py. No implementation changes were authored locally.
- Pre-apply input_capture_live.py exactly matched baseline SHA256 3813c8badf52313d7daf7969ffb99e1035435968f5113d6a94c01b32ac6e273d; test destination was absent. Existing unrelated dirty/untracked work was not overwritten.
- Verbatim backup: C:\Users\Lenovo\agent-tools\t206_cli_patch_20261119_0607\input_capture_live.baseline.py; SHA256 3813c8badf52313d7daf7969ffb99e1035435968f5113d6a94c01b32ac6e273d.
- Patch transferred through sanctioned CopyFromBox to C:\Users\Lenovo\agent-tools\t206_cli_patch_20261119_0607\input-capture-cli.patch; SHA256 e6a2cee355e428f3deb33f90fbcc349bed1c7e77759eafbbe59da8c472f9191f.
- git apply --check succeeded before git apply; no force, reject repair, commit, push or PR.
- Before/after full porcelain status receipts are stored under C:\Users\Lenovo\agent-tools\t206_cli_patch_20261119_0607. Only intended new source-test/status entries and this research record are expected.

## Actual local OFFLINE results
- Python3.13.5: python -u calling/tests/test_input_capture_cli.py -v exited0; 17 test methods,0failures,0errors, elapsed2.286s per actual log. Do not substitute the cloud's subtest count: local subtests were not separately instrumented/count-reported.
- Attached in-process/injected/subprocess assertions passed: --json partial emits one JSON document, exit3, input_accepted=false; legacy --out partial retains summary keys and exit0; both full fixture outputs equal their inputs, complete_input=false and52 recomputed required-property errors each; reader/schema/fixture hashes and original capture-function prefix are unchanged.
- Help/usage/no-live-import checks in the supplied suite passed. Separate python -v calling/input_capture_live.py --help exited0; --out/--json present and no import trace for mem/pe/gamestate/handle/process/config. Output and import trace saved alongside the log.
- Tests used C-only TEMP/TMP under C:\Users\Lenovo\agent-tools\t206_cli_patch_20261119_0607\temp and disabled bytecode writes. No new dependency was installed.
- Initial PowerShell native-stderr redirection raised NativeCommandError and produced no completed-test receipt. The reported successful run used Python subprocess byte logging; this was a test-launch/logging correction only, not a source or test patch.

## Readback SHA256
- calling/input_capture_live.py: e10bf427df1059c3f16873960bcbdabef826ef1dc058ad5e087b5a67d8087d37 (exact cloud expected bytes).
- calling/tests/test_input_capture_cli.py: 94d73593392072ab42d8749b0d4e7bfcc9d342b7514cf58cfd17cb53e01963ad (Windows raw CRLF bytes,737lines). LF-normalized SHA256 9afcdcd699a79a32a0b3128a30becac31edcf83114c246e6071924a39723eeb0 exactly matches delivered cloud test. Git apply's Windows line endings are the only difference; no manual test edits.
- offline_tests.log: 8b65a71a7395013a1e1c9e02abacf60a0849a79a71921ca3b0f260f928b5ff94.
- help_stdout.txt: 08a831e49ca673c36a91953a0fe84fa820131bf2982e56640994a9289bdd61ce.
- help_import_trace.txt: c9a65bf670d745e38fc97d29ee1312d2c3f9e61cc0b757c549c442412f556561.

## Safety and acceptance boundary
Patch IS APPLIED and offline acceptance PASSED; production live capture remains NOT ACCEPTED/NOT RUN. No real capture() was invoked, no game process was opened/read/written, no Post or remote game function was called, and no time/pause/speed was changed. No D or save access. Original executable fingerprint/PE/version/pause/schema gates remain inside the unchanged capture() prefix. The two old exports remain partial, not new live observations. Field evidence remains74/42; D historical72/44 remains unsynced. No new field promotion or claim of live pause verification in this task.
