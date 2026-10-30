# G37 — Network test harness (M0 part 1)

Date: 2026-10-18 (Europe/Moscow).

**Verdict after review round 1: fixes verified with synthetic data and PowerShell 5.1/7 unit tests and dry runs. No game executable or Unity was launched in this review round. Real-executable re-validation of this revision (net04 37/22 and v02/net02) is a separate, pending step.** The retained pre-review operations v04 evidence records **host 37 PASS / client 22 PASS**. Its multi-client attempts failed because identical client drivers competed for tools/organs. Those historical runs do not validate the revised launcher or close the full M0 milestone.

Source of truth: `C:\Dev\Game\docs\specs\NETWORK_MAP_PLAN_v01.md`, read in full, including the accepted Q1–Q8 decisions. Implementation is limited to section 6's external harness and comparator, the suite wrapper, usage documentation and their validation. The v02/v04 launchers and the argument parsing in `OperationNetworkProbe.cs` and `NetworkSession.cs` were read as references.

## Delivered behavior

- `C:\Dev\Game\Working\Reviews\Network\run-net.ps1`: one host plus 1–3 clients; hidden launches; readiness polling every 0.5 seconds for the existing `[OV Network] server started` line; at most 60 seconds for readiness; clients start only after readiness, one second apart.
- All peers receive scenario, role, index, expected external-client count (`-net-clients N`), evidence, port and latency/loss flags. The cohort-count argument lets the future barrier know whether it should wait for 2, 3 or 4 total roles. The old build ignores these new `-net-*` arguments and retains its existing `-ops-*` driver.
- Legacy `-ExtraArgs '-ops-scenario net-host'` keeps `net-host` on the host and maps it to `net-client` on each client. The harness supplies `-ops-test`, `-ops-quit` and per-role `-ops-evidence` itself.
- Per-role player logs and evidence directories; recorded launch commands, PIDs, exit codes, readiness/duration and cleanup events; `summary.txt` and `summary.json`. Each PASS/FAIL/RESULT/SUB RESULT/NET event is collected once from its player log. Traffic samples are averaged per role/phase when available.
- Executed roles require at least one PASS check and exactly one final RESULT. Any failed check/result, zero checks, duplicate/missing final result, optional expected-count mismatch, missing simulation acknowledgement, nonzero/missing exit code, missing peer, timeout or cleanup termination produces exit 1. Dry runs are explicitly DRY_RUN, never PASS.
- Existing run/suite folders are preserved using `_02`, `_03`, etc. Evidence paths must stay under the allowed Network directory, including after normalization; junctions/symlinks and reserved argument overrides are rejected. A UDP-port preflight avoids attaching clients to another running game by accident.
- Cleanup retains original native process handles/PIDs. A Windows Job Object assigns only directly launched players atomically at creation and terminates them if its owner dies; player descendants break away. It never kills by process name or kills a process tree.
- `C:\Dev\Game\Working\Reviews\Network\run-net-suite.ps1`: scenarios run in sequence, failures do not skip later entries, child output is saved and one final summary table is printed. The suite exits 1 if any entry fails.
- `C:\Dev\Game\Working\Reviews\Network\tools\compare_traces.py`: Python standard library only; exact source-server-tick/entity/phase matching; coordinate-frame validation; mean/RMS/p95/max position errors, worst tick and missing-tick counts. Coverage uses the full HOST range or an explicit required window, defaults to 95%, and also requires ten matched samples per entity/phase. Unknown entity/phase filters error; optional rotation p95/max appear in text and JSON.

## Historical real existing-build runs (before review fixes)

Executable: `C:\Dev\Game\Working\Reviews\Operations\stage1_v4\build\OperationsStage1v04.exe`.

SHA-256: `95D2E699E1429223213E3D38FC53544C7BBF28334B1F54BA7B00180E77548479`.

No rebuild was performed. All runs below use the actual `net-host` / `net-client` operations drivers at zero requested latency/loss.

| Run | Clients | Host PASS/FAIL | Client PASS/FAIL | Harness/suite result | Duration | Host ready |
|---|---:|---|---|---|---:|---:|
| Original reproduction | 1 | 37 / 0 | 22 / 0 | PASS, exit 0 | 36.875 s | 3.651 s |
| Two-client attempt | 2 | 37 / 0 | c1: 16 / 2; c2: 19 / 1 | FAIL, exit 1 | 35.753 s | 3.664 s |
| Three-client attempt | 3 | 37 / 0 | c1: 19 / 1; c2: 16 / 2; c3: 15 / 3 | FAIL, exit 1 | 36.720 s | 3.639 s |
| Pre-review handoff, Windows PowerShell 5.1 | 1 | 37 / 0 | 22 / 0 | PASS, exit 0 | 37.224 s | 3.692 s |

Every game process in these runs exited naturally with native exit code 0. No game-run timeout or cleanup kill occurred. The multi-client failures were detected from check/result lines despite those zero process exit codes.

Evidence directories:

- `C:\Dev\Game\Working\Reviews\Network\validation\net04-baseline`
- `C:\Dev\Game\Working\Reviews\Network\validation\net04-multi\01_net04-two-clients`
- `C:\Dev\Game\Working\Reviews\Network\validation\net04-multi\02_net04-three-clients`
- `C:\Dev\Game\Working\Reviews\Network\validation\net04-handoff\01_net04`

The two-entry multi-client suite printed **72 PASS / 3 FAIL** and **87 PASS / 6 FAIL**, returned exit 1, and ran its second entry after the first failed. Its table is `C:\Dev\Game\Working\Reviews\Network\validation\net04-multi\suite-summary.txt`. The final suite printed **59 PASS / 0 FAIL**, exit 0, in `C:\Dev\Game\Working\Reviews\Network\validation\net04-handoff\suite-summary.txt`.

Claude removed the superseded intermediate one-client repetitions, earlier fixture runs, all recorded `frames` folders and `.bak` files during review. The retained `net04-handoff`, `net04-baseline` and `net04-multi` directories support only the original pre-review numbers above. `FILES_CREATED.txt` has been regenerated against retained files and excludes deleted paths, frames and backups.

Historical pre-review reproduction, executed inside Windows PowerShell 5.1 (not executed during review round 1):

```powershell
& 'C:\Dev\Game\Working\Reviews\Network\run-net-suite.ps1' `
  -Exe 'C:\Dev\Game\Working\Reviews\Operations\stage1_v4\build\OperationsStage1v04.exe' `
  -Run 'C:\Dev\Game\Working\Reviews\Network\validation\net04-handoff' `
  -Scenarios @('net04') -ClientCounts @(1) -Port 17962 -TimeoutSec 180 `
  -ExtraArgs '-ops-scenario net-host'
```

The multi-client sequence was executed with the same executable/extra arguments, `-Scenarios @('net04-two-clients','net04-three-clients') -ClientCounts @(2,3) -Port 17961 -TimeoutSec 180`, with its Run path set to the `net04-multi` directory above. A direct PowerShell 7.6.5 `run-net.ps1` invocation produced the original baseline, using port 17960 and Run `net04-baseline`.

### What the additional clients actually proved

The three-client player logs record owner IDs 0, 1, 2 and 3, all with the same patient ID. Thus four processes connected and acquired their own players. The old test is still a one-remote-client action script: every additional client tries to select the same scalpel, extract the same kidney and initiate the same liver pull/disconnect flow.

Observed failing checks were `key Digit4 -> Scalpel` and `detached organ is in hand (held at the cursor)`. The two-client run had three failed checks; the three-client run had six. These are preserved as failures. Neither attempt is presented as a passing four-player gameplay test. Coordinated per-role scenarios/barriers are required in part 2.

## Historical harness and comparator verification (pre-review)

**Historical PASS — 11 controlled process checks on the pre-review revision**, using Windows PowerShell 5.1:

```powershell
& 'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe' -NoLogo -NoProfile -NonInteractive `
  -File 'C:\Dev\Game\Working\Reviews\Network\tests\verify-harness.ps1' `
  -Run 'C:\Dev\Game\Working\Reviews\Network\validation\harness-checks-handoff'
```

This launches controlled PowerShell fixture peers, not Unity or game builds. It checks normal one-client/four-process completion, failed checks with RESULT PASS, RESULT FAIL, failed sub-results, sub-results without a final result, missing results, native exit code 7, overall timeout, absent readiness and early host exit. It also checks paths containing spaces, expected-cohort argument forwarding, NET phase averages and that every fixture PID has exited after cleanup. The parent test process and other already-running processes remain alive. The table and JSON are in `C:\Dev\Game\Working\Reviews\Network\validation\harness-checks-handoff`. Timeout fixtures exercised actual cleanup of the harness-owned processes; the no-readiness fixture started no client.

**PASS — 3 preflight rejection checks:** an exclusively occupied UDP port, evidence outside Network, and an `ExtraArgs` evidence override all returned 1 without creating their requested run directory. Exact argument arrays and results are recorded in `C:\Dev\Game\Working\Reviews\Network\validation\preflight-checks\checks.json`.

**PASS — 19 Python comparison checks:**

```powershell
python -B 'C:\Dev\Game\Working\Reviews\Network\tests\test_compare_traces.py'
```

Pre-review output: `C:\Dev\Game\Working\Reviews\Network\validation\compare-unit-tests-final.txt`. These 19 checks predate the coverage and minimum-sample corrections below; the current suite has 29 checks.

**PASS — CLI checks on explicitly synthetic data:**

- `synthetic-host.jsonl` versus `synthetic-client.jsonl`: 3 matched ticks, 100% coverage, mean 0.133333 m, RMS 0.141421 m, max/p95 0.2 m; exit 0 at a 0.3 m limit.
- Versus `synthetic-client-bad.jsonl`: max 0.4 m; exit 1 at that limit.
- Outputs/expected codes: `C:\Dev\Game\Working\Reviews\Network\validation\compare-cli-checks.json`, `compare-pass.json`, `compare-fail.json` and accompanying text logs in the same directory.

## Trace and simulation limitations

**NOT AVAILABLE — real tick-trace comparison.** Inspection of the game evidence found role state snapshots (`final-state.json`, `client-state.json`, the test save) and harness summaries, but no JSONL/CSV/server-tick pose traces. The inventory is `C:\Dev\Game\Working\Reviews\Network\validation\game-trace-inventory.json`. Running the comparator against the real host/client state snapshots correctly returned **exit 2**, reporting that state snapshots without `serverTick` samples are not traces. Its output is `C:\Dev\Game\Working\Reviews\Network\validation\compare-existing-state.txt`. The synthetic results above are not gameplay measurements.

**NOT VERIFIED against a real build — applied latency/loss, measured RTT or bandwidth.** The old build does not implement the simulation flags or telemetry. The revised harness now FAILS a nonzero latency/loss request unless every role logs matching `NET SIM latencyMs=<L> lossPct=<X>` acknowledgement after applying it. Positive acknowledgements were verified only with synthetic logs, not a FishNet runtime or independent RTT measurement. No machine-wide traffic configuration changed.

**NOT RUN — remaining milestone gates.** No Unity Editor actions, rebuilds, EditMode/PlayMode tests, sandbox join scenarios, input-wrapper checks, map scene checks, v02/net02 build regression or human LAN/feel tests were performed. These are outside this authorized harness-only task and remain required where the plan says so.

## M0 part 2 handoff, after G35

1. **Session split and sandbox.** Preserve `-ov-host`, `-ov-client [address]`, `-ov-port` and the exact server-readiness line while moving test spawns out of `NetworkSession`. Add the planned sandbox through its builder after G35 is accepted. Supply a development player executable to this harness; this delivery creates no scene or build.
2. **Native argument contract.** `NetArgs`/`NetScenarioDriver` must consume `-net-scenario`, `-net-role host|client1|client2|client3`, `-net-index 0..3`, `-net-clients N` and `-net-evidence <absolute role directory>`. Expected total roles are N+1. Seed remains available through `-ExtraArgs '-net-seed 37'`.
3. **Simulation and telemetry.** Map `-ov-latency` / `-ov-loss` to FishNet's `TransportManager.LatencySimulator` in development builds. After actual configuration every role must print `NET SIM latencyMs=<effective integer L> lossPct=<effective invariant decimal X>`, matching the request. Missing/mismatched acknowledgement fails the run. Separately report measured RTT and emit `NET up=... down=... KB/s phase=...` once per second. State the latency convention so the requested value and measured RTT can be assessed correctly.
4. **Coordinated real input.** Extend the OR input wrapper on G35's accepted files. The new driver should play through virtual devices and named `NetTestBarrier` steps for every expected role. The harness's one-second process spacing does not synchronize actions. The old operations net04 path remains a regression command, with its supported one-client action flow.
5. **Evidence/result lifecycle.** Use the supplied role directory directly, write `run-log.txt`, screenshots and final state there, print exactly one final `RESULT PASS` or `RESULT FAIL ...`, then quit the standalone process. A stalled/unimplemented driver will correctly time out or fail for a missing final result.
6. **Trace producer contract.** Write `trace.jsonl` under every role's evidence directory. Each sample requires `serverTick` (nonnegative, unwrapped source server tick), stable `entity` and metre `position`; optional `phase`, `frame` and quaternion `rotation` follow the README schema. A rendered/interpolated client pose must carry the tick it represents, not its current local tick or elapsed wall time. Use matching cadence and carrier frames on both peers; stamp van-local cargo consistently. Feed those files to the comparator with the milestone's actual tolerance and compare every relevant client/entity/phase.
7. **Acceptance still to do.** `net-m0-join` with 1 and 3 clients must assert N+1 distinct players/owners, log RTT/NET and pass all roles; demonstrate the requested latency effect. Then run the remaining gates from the plan. This report does not close the full M0 milestone.

## Scope and file inventory

No Unity Editor was opened or controlled; no Assets or ProjectSettings files were written; no player rebuild, staging, commit or push was performed. Work used `C:\Dev\Game` as the working directory. The initial validation launched hidden players while another game (PID 7060) and Unity processes were present. The review correctly flags that a separate free port is not permission for activity during a human playtest. Do not repeat real-player runs while Fedya is playing or another agent holds Unity. In review round 1 only Python/PowerShell unit-test runtimes were launched, and only their own fixture PIDs were terminated. No game window was activated, controlled or terminated.

Primary deliverable paths:

- `C:\Dev\Game\Working\Reviews\Network\run-net.ps1`
- `C:\Dev\Game\Working\Reviews\Network\run-net-suite.ps1`
- `C:\Dev\Game\Working\Reviews\Network\tools\compare_traces.py`
- `C:\Dev\Game\Working\Reviews\Network\README.md`
- `C:\Dev\Game\docs\reports\NETWORK_HARNESS_M0A.md`

Reusable checks and synthetic fixtures are under `C:\Dev\Game\Working\Reviews\Network\tests`; retained logs, summaries and screenshots are under `C:\Dev\Game\Working\Reviews\Network\validation`. No frame folders or backups were regenerated. The original `validation\provenance.json` and `validation\FINAL_VERIFICATION.json` are labelled as pre-review history; current review evidence is under `validation\review-round1`. **Retained output paths, excluding deleted files/frames/backups and the read-only reviewer document, are listed in `C:\Dev\Game\Working\Reviews\Network\FILES_CREATED.txt`; all files created/changed by this review are listed in `C:\Dev\Game\Working\Reviews\Network\FILES_CHANGED_REVIEW1.txt`.**

## Review round 1 fixes

Review: `C:\Dev\Game\Working\Reviews\Network\REVIEW_G37_claude.md`, read in full. The current instructions prohibit real-game re-validation; the results below use unit tests, synthetic traces/logs and PowerShell 5.1/7 parse/dry runs only.

| Review item | Change and evidence |
|---|---|
| MAJOR-1 | Coverage denominator is all required HOST samples, never the client overlap. Default minimum coverage is 95%; `--min-matched` defaults to 10. Intentional windows use both `--start-tick` and `--end-tick`, and the host must cover that window. The previously wrong passing overlap test now expects FAIL. Host 0..999 vs client 0..49 gives 5% coverage/exit 1; one client tick gives 0.1%/exit 1. |
| MAJOR-2 | Shared child invocation redirects stdout/stderr separately, reads both asynchronously and records errors without 5.1 native-stderr exceptions. Each suite entry catches its own errors; summaries are written in `finally` after safe output allocation. Occupied-port preflight stderr, stderr with exit 0, absent child summary and configuration errors all produce recorded failures; later valid entries still run. |
| MAJOR-3 | Nonzero latency OR loss requires matching `NET SIM latencyMs=<L> lossPct=<X>` in every role's log. No matching acknowledgement, a wrong value, or an acknowledgement missing on a client fails with `latency not applied`. Loss-only and positive matching-acknowledgement cases are tested. |
| MAJOR-4 | Zero PASS checks fail unconditionally for an executed role. Optional `ExpectHostPass` / `ExpectClientPass` enforce exact counts; the suite accepts one count or per-scenario arrays. README's later net04 command requires 37/22. Synthetic host/client mismatches fail despite RESULT PASS and exit 0. |
| MINOR-1/2/3 | Any unknown requested entity/phase errors, even with valid filters. Exactly one final RESULT is required. UTF-8 Base64 transports raw ExtraArgs through the suite; embedded quotes/trailing backslashes survive both shells. |
| MINOR-4 | Windows Job Object uses atomic process-creation assignment and kill-on-close. It owns only directly launched players; descendants break away. In both shells, force-terminating the controlled fixture owner kills its two independently tracked players while a separate sentinel remains alive. |
| MINOR-5/6 | Exception log lines are counted in role JSON/text as warnings without changing a passing verdict. Quaternion p95/max statistics also appear in text output. |
| MINOR-7 | Real v02/net02 and current net04 re-validation is **NOT RUN**, as explicitly required by the review-round user instruction; perform it later when the shared game/Unity work is released. |
| MINOR-8 | Verification no longer aborts on a missing summary. New cases cover a killed client, host exit after readiness while a client runs, failing suite entries and Windows `CommandLineToArgvW` plus real received argument arrays. A discovered PowerShell 5.1 JSON-array wrapping issue in the checks was corrected so arguments and both child processes are checked individually. |
| MINOR-9/10 | README/report distinguish historical simultaneous-player activity from this no-game review round. All example game ports are 1796x; an exact-port probe is not a playtest/activity guard. README documents later owner-only force-add of ignored source/tool/test paths and exclusion of validation/cache/inventories; no Git changes were staged or committed. |

Current verification:

| Check | Result | Evidence under `C:\Dev\Game\Working\Reviews\Network\validation\review-round1` |
|---|---|---|
| Comparator standard-library unit tests | PASS, 29/29 | `python-unit-tests-final.txt` |
| Synthetic trace CLI | PASS, 6/6 expected exit codes | `trace-cli-final\checks.json` |
| Windows PowerShell 5.1 harness unit checks | PASS, 27/27 | `ps51-harness-final\checks.json` |
| PowerShell 7 harness unit checks | PASS, 27/27 | `ps7-harness-final\checks.json` |
| Windows PowerShell 5.1 suite checks | PASS, 8/8 | `ps51-suite-release\checks.json` |
| PowerShell 7 suite checks | PASS, 8/8 | `ps7-suite-release\checks.json` |
| Abrupt owner death/owned players only | PASS in both shells; 2 players each | `ps51-job-final\checks.json`, `ps7-job-final\checks.json` |
| Parse and production dry runs | PASS in both shells, all 11 PowerShell files parse; one and three clients planned, no PID launched; DRY_RUN, never PASS | `ps51-parse-final.json`, `ps7-parse-final.json`, `ps51-production-dry-confirmed`, `ps7-production-dry-confirmed` |

Commands used (run the PowerShell scripts inside each corresponding shell):

```powershell
python -I -B 'C:\Dev\Game\Working\Reviews\Network\tests\test_compare_traces.py'
& 'C:\Dev\Game\Working\Reviews\Network\tests\verify-harness.ps1' -Run 'C:\Dev\Game\Working\Reviews\Network\validation\review-round1\ps51-harness-final' -Port 17964
& 'C:\Dev\Game\Working\Reviews\Network\tests\verify-suite.ps1' -Run 'C:\Dev\Game\Working\Reviews\Network\validation\review-round1\ps51-suite-release' -Port 17968
& 'C:\Dev\Game\Working\Reviews\Network\tests\verify-job-lifetime.ps1' -Run 'C:\Dev\Game\Working\Reviews\Network\validation\review-round1\ps51-job-final'
```

PowerShell 7 uses the equivalent `ps7-*` directories and ports 17966/17969. The harness fixture refuses any executable except the invoking PowerShell engine. All production harness/suite logic remains intact except the test-only launch prefix/child-script path substitution; sources are not rewritten by tests. The independent job test only starts controlled PowerShell sleepers and retains their original handles.

The explicit three-sample synthetic README example now specifies `--min-matched 3`; without this deliberate override, it correctly fails the new default ten-sample gate. Positive simulation acknowledgements are synthetic contract checks, not measurements of FishNet or network quality. A fresh real-build regression remains pending and was not replaced with fabricated results.
