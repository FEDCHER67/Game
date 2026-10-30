# G27 — Buyer rules core v01.1

Date: 2026-10-16. Revision: v01.1, following the lead's decisions under Fedya's mandate. Status: **PASS for the pure C# rules and standalone NUnit run**. Unity was not opened or called. No commits, staging, pushes, scene edits, operation edits, patient edits, or operating-table edits were performed.

## v01.1 changes

1. **Meeting attendance and closure.** A meeting is missed only if no team member arrived or interacted before the wait expired. The saved `MeetingState.HadInteraction` flag is recorded by successful group start/loading, or by the host calling `RecordMeetingAttendance` for an arriving, present participant during the wait. Existing negotiation/reservation/sale state also establishes attendance when restoring an older snapshot. Negotiating without selling no longer incurs a timeout penalty. A failed deal costs exactly −1, including subsequent cancellation or timeout. Walking away after refused +5% is free. After any sale, both `CancelMeeting` and `CompleteMeeting` use the same successful-completion path, release outstanding reservations and close any active group without a penalty, before or after expiry. Untouched no-shows still cost −1 once; pre-arrival cancellation remains free.
2. **Wrong-group requests.** An item accepted by the buyer but submitted in another type's ordinary negotiation group now returns `InvalidRequest`, with no respect penalty, goods consumption, money or XP. `BUY48_PenaltyIsPerItemAndScopedToEachMeeting` now pins this behavior across repeated IDs, new IDs, different items, mixed batches and another meeting. Actual unsuitable goods still receive their once-per-instance penalty: unsupported merchandise, or failed order kind/quality/target/packaging requirements. The saved-penalty regression now uses an actual wrong-target special-order item instead of a group mismatch.
3. **Failed-deal reservations.** A second refusal immediately releases only the failed product type's meeting reservations. Goods retain their holder and remain unsold; other types remain reserved. A regression deposits a released kidney into an accepted special-order stash immediately and then sells the other reserved type.
4. **Loading validation.** `LoadItem` rejects kinds the buyer does not buy before reserving them. The original bool API is preserved; an added `out SaleError` overload reports `InvalidRequest`. Eight parameter cases reject all six organ kinds at C01 and both blood kinds at the organ buyer, without penalties or attendance being recorded by invalid loading.
5. **Strengthened existing tests.** BUY-30 starts at 41 respect, remains at 40 after failure, and proves that a fresh offer ID cannot bypass the 3 h ban while the respect gate is satisfied. It also accepts the original offer after the cooldown and price agreement. The constant-arithmetic assertion was removed from BUY-29/47; its real transaction still checks the payout. BUY-17 now quotes and sells the same first-unit kidney at ten respect values spanning all level boundaries and confirms the same $250 price.
6. **Missing regressions added.** The table below names the new tests for acceptance-time respect, occupied order slot, accepting player identity, absent-player handoff, downward-only quality updates, penalty-free `NotReserved`, blood-only negotiation ban, post-bag introductory syringe XP, and every rule in items 1–4.
7. **Clock origin and evidence.** The integration contract and `IBuyerClock` documentation now explicitly require **game time 0 = 00:00**; saturation uses integer game days from that origin. The requested standalone script was rerun against the original linked sources: **130 total, 130 passed, 0 failed, 0 skipped**, up from 93 cases. The output verifier and file inventories were refreshed. No mutation-testing result is claimed for v01.1; the 52/63 result was supplied by the lead for v01.

| Decision / missing case | Regression methods (fixture keys below) |
|---|---|
| Untouched miss, interaction, attendance and its validity/persistence | M `BUY08_MissingMeetingPenalizesOnceAndAllowsRebooking`, `BUY08_LoadingGoodsRecordsInteractionAndTimeoutReleasesThem`, `BUY08_NegotiatedMeetingWithoutSaleIsNotMissed`, `BUY08_AttendanceWithoutNegotiationPreventsMissPenaltyAndSurvivesSave`, `BUY08_AttendanceRequiresPresentPlayerWithinWait` |
| Exactly one failed-deal penalty / free +5% walk-away | M `BUY08_BUY21_FailedDealCostsExactlyOneIncludingCancelOrTimeout`, `BUY08_BUY20_WalkingAwayAfterFivePercentRefusalIsFree` |
| Cancel/Complete after sale, including another active group and expiry | M `BUY08_CancelAndCompleteAfterSaleAreFree` (8 cases) |
| Wrong negotiation group is a request error | O `BUY48_PenaltyIsPerItemAndScopedToEachMeeting` |
| Failed type's reservations released immediately | M `BUY21_FailedTypeReleasesOnlyItsGoodsImmediatelySoTheyCanBeStashed` |
| Loading unsupported merchandise is rejected without penalty | M `BUY10_BUY48_LoadRejectsKindsBuyerDoesNotBuyWithoutPenalty` (8 cases) |
| Respect rechecked on acceptance | O `BUY25_BUY28_RespectIsRecheckedAtOrderAcceptance` |
| Another order already occupies the team slot | O `BUY26_AcceptingSecondNegotiatedOfferWhileOrderActiveFails` |
| Only the current negotiator may accept; authorized handoff changes that player | O `BUY28_OnlyCurrentNegotiatorMayAcceptOrderUntilHandoff` |
| An absent registered player or an unknown player cannot take over | M `BUY22_BUY41_AbsentParticipantCannotTakeOverMeeting`; O `BUY22_BUY41_AbsentParticipantCannotTakeOverOrder` |
| Quality cannot increase; an equal-tier report is idempotent | P `BUY14_UpdateQualityOnlyDegradesAndRejectsImprovement` |
| NotReserved costs no respect, for ordinary and special sales | O `BUY37_BUY48_NotReservedCostsNoRespect` |
| Blood failure bans blood, while organ trade stays available | M `BUY21_FailedBloodNegotiationBansBloodOnly` |
| Intro syringe after a bag gives 5 XP, no second +50 bonus | P `BUY44_IntroSyringeAfterBloodBagHasNoSecondFirstBloodBonus` |

Already-applied v01 penalties are not automatically refunded. Restoring a snapshot preserves its recorded balance and receipts; the new attendance logic governs future transitions.

## Sources and scope

- `C:\Dev\Game\docs\specs\BUYERS_SPEC_2026-10-15_v02.md` was read in full. Its confirmed decisions and v02 amendments take precedence.
- `C:\Dev\Game\docs\specs\OPERATIONS_SPEC_2026-10-15_v01.md` supplies the six base prices, five tier multipliers, packaging distinction, preservation boundary, and free/lifetime XP distinction. Its old sale-XP table is superseded.
- `C:\Dev\Game\docs\VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON.md`, particularly buyer/contact, storage, special-order, XP, and prologue sections, provides background. Older contact-location/unlock rules do not override buyer v02.
- `C:\Dev\Game\Assets\OnlyVolunteers\Operation\Stage1\Core\OperationState.cs` was read as the state-plus-rules pattern, without importing its Unity-dependent types or modifying it.

Implementation: `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Core\`. Namespace: `OnlyVolunteers.Buyers`. The core asmdef has `noEngineReferences=true` and no assembly references. The standalone core targets **.NET Standard 2.1**, with C# 9 and compiler warnings treated as errors. NUnit sources are in `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Tests\`, with an Editor-only test asmdef.

This is an independent, host-owned rules model, not a live replacement for the existing inventory, business fund, save system, phone, or FishNet authority. `BuyerItemState` is the merchandise projection supplied by the existing host inventory. A sold item becomes a retained tombstone and is unavailable to further sales. Physical destruction/removal and presentation belong to the eventual adapter. Do not run a separate live cash or inventory authority alongside this snapshot.

## Verification

Run from `C:\Dev\Game`:

```powershell
& 'C:\Dev\Game\ArtSource\Dev\Buyers_staging\Run-Tests.ps1'
```

The script redirects CLI state, temporary files, NuGet packages/caches, build outputs and results under `C:\Dev\Game\ArtSource\Dev\Buyers_staging\`. Both project files use `Compile Include` with `Link` metadata pointing at the original Assets sources: **there are no source copies**. A .NET 8 test project references the .NET Standard 2.1 core project. No Unity assemblies are used by either standalone project.

Actual final console summary:

```text
Test Run Successful.
Total tests: 130
     Passed: 130
 Total time: 0,4724 Seconds
```

Results: `C:\Dev\Game\ArtSource\Dev\Buyers_staging\TestResults\buyers-results.trx`.
Full log: `C:\Dev\Game\ArtSource\Dev\Buyers_staging\test-output.txt`.

An initial run exposed an incorrect expected batch sum in a test: eight $250 organs yield $1662.50 before rounding, hence $1663 under the selected rounding preset. The test expectation was corrected. An initial intermediate-output-path warning was removed by placing the shared MSBuild configuration in `Directory.Build.props`; the final compilation has no such warning. The runner reports that it overwrites its previous TRX result on subsequent runs; this is an evidence-file notification, not a compiler or test failure.

**PASS:** all 130 NUnit cases, including the v01.1 regressions, concurrent confirmation, overflow rollback, and an in-memory DataContract save round trip. **NOT RUN:** Unity import/EditMode execution, actual inventory/network/save adapters, UI/audio, driving/parking, police integration, subjective playtesting. These are outside this pure C# task.

Standalone test dependencies only (Unity packages were not changed): Microsoft.NET.Test.Sdk 17.11.1 (MIT, https://github.com/microsoft/vstest), NUnit 3.14.0 (MIT, https://github.com/nunit/nunit), NUnit3TestAdapter 4.6.0 (MIT, https://github.com/nunit/nunit3-vs-adapter). Exact versions and restored transitive dependencies are in the staging project/assets files. Rollback consists of ceasing to use the throwaway staging project; no game package or existing runtime file was replaced.

## BUY acceptance mapping

Names below are the exact NUnit method names, without fixture prefixes or parameter suffixes. Fixture files are:

- **P:** `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Tests\BuyerPriceAndProgressionTests.cs`
- **M:** `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Tests\BuyerNegotiationAndMeetingTests.cs`
- **O:** `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Tests\BuyerOrderAndTransactionTests.cs`

53 IDs have rule-level coverage. BUY-27, BUY-39 and BUY-40 have no pure-rule acceptance claim. Mixed requirements are explicitly limited to their rule/data portions.

| BUY ID | Tests | Coverage boundary |
|---|---|---|
| BUY-01 | P `BUY01_FirstBloodUnlocksOrganContact` | Contact flag; message delivery is an adapter. |
| BUY-02 | P `BUY02_BUY44_IntroSyringeIsTenDollarsOnceNoBargainingAndFirstBloodRewards` | $10, one exception, no ask. |
| BUY-03 | P `BUY03_BUY04_BloodHasFixedBaseAndNoQualityCoolingOrSaturation` | $50 base; quality/cooling ignored. No second blood-decay simulation. |
| BUY-04 | Same as BUY-03 | Repeated bags do not increment saturation. |
| BUY-05 | M `BUY05_BothStartingBuyersAvailableAtAnyHour` | Day/night availability at three hours. |
| BUY-06 | M `BUY06_AuthoredLocationAndBaseAreFixedForMeeting` | Fixed base/authored-point ID; no vehicle movement or phone UI. |
| BUY-07 | M `BUY07_ArrivesInOneHourAndWaitsThreeWithExactBoundaries` | Absolute active-game arrival/expiry values; phone rendering excluded. |
| BUY-08 | M `BUY08_CancelBeforeArrivalFreeAfterArrivalOnceAndImmediateRebooking`, `BUY08_MissingMeetingPenalizesOnceAndAllowsRebooking`, `BUY08_SuccessfulMeetingCanCompleteWithoutCancelPenaltyAndRebook`; v01.1 meeting regressions above | Untouched miss only; attendance, free walk-away, exactly one failed-deal penalty, free post-sale Cancel/Complete, immediate rebooking. |
| BUY-09 | M `BUY09_ParallelMeetingsPerBuyerOnlyOneEach` | Independent buyers/timers, duplicate rejection. |
| BUY-10 | M `BUY10_OnlyPhysicalHolderLoadsAndOnlyNegotiatorConfirms` | Host-reported holder IDs and confirmation authority; physical grabbing excluded. |
| BUY-11 | P `BUY11_BUY12_CooledDeliverySurvivesInspectionAndUncooledCostsTenPercent` | Delivered-cooled provenance survives reservation/inspection. |
| BUY-12 | Same as BUY-11 | Warm organ price ×0.90. |
| BUY-13 | P `BUY13_AllFiveTiersSellWithoutPackaging`, `BUY13_AllSixOrganKindsUseOperationBasePrices` | All six kinds, five grades, no ordinary packaging gate. |
| BUY-14 | P `BUY14_ConfirmationUsesActualQualityAndOptionalPriceGuard` | Updated quality is used at confirm; stale estimate can be rejected. Actual decay belongs to operations/storage. |
| BUY-15 | P `BUY15_BUY16_PerUnitSaturationStopsAtSeventyAndResetsAtMidnight`, `BUY15_MidnightBetweenQuoteAndConfirmRecomputesSaturation` | Full sequence/floor, midnight, quote/confirm boundary. |
| BUY-16 | P `BUY15_BUY16_PerUnitSaturationStopsAtSeventyAndResetsAtMidnight` | Whole batch sum with sequential units. |
| BUY-17 | P `BUY17_DifferentTypesHaveSeparateTermsAndRespectDoesNotMultiplyPrice` | Separate chains/counters and fixed base formula. |
| BUY-18 | M `BUY18_BUY19_AllChanceCellsAndEverySkillRank`, `BUY18_RngUsesStrictChanceBoundary` | All 15 cells and success/failure threshold. |
| BUY-19 | M `BUY18_BUY19_AllChanceCellsAndEverySkillRank` | All four skill ranks across all cells, cap 95. |
| BUY-20 | M `BUY20_FirstRefusalAllowsCounterOrOnlySmallerSecondAsk`, `BUY20_FivePercentRefusalLeavesBaseOrWalkAway` | Counter acceptance, smaller-only retry, base/leave after +5 refusal. |
| BUY-21 | M `BUY21_SecondRefusalBansOnlyThatTypeThreeHoursKeepsGoods` | −1, type-specific ban, boundary reopening on another meeting, item retained. |
| BUY-22 | M `BUY22_BUY41_HandoffKeepsAttemptAndTimerButUsesNewSkill`; O `BUY22_BUY41_OrderHandoffPreservesTermsAttemptsAndUsesReplacementSkill` | Meeting and offer handoffs. Actual disconnect routing excluded. |
| BUY-23 | P `BUY23_BUY24_BUY51_RespectStartsThirtyAndAcquaintanceOnlyOnce`, `BUY23_BUY51_RespectRangesAndNames`, `BUY23_RespectClampsAtBothEnds` | Shared 0–100 state/start/ranges. UI must show names, not raw host points. |
| BUY-24 | P `BUY23_BUY24_BUY51_RespectStartsThirtyAndAcquaintanceOnlyOnce`, `BUY02_BUY44_IntroSyringeIsTenDollarsOnceNoBargainingAndFirstBloodRewards` | First meeting, first/repeat organs and blood. |
| BUY-25 | P `BUY25_ZeroRespectAllowsTradingButFortyRequiredForNewOrders` | Ordinary trade at zero; new-order threshold 40. |
| BUY-26 | O `BUY26_BUY28_OrderAcceptedAfterNegotiationOneTeamSlotAndFortyEightHours`, `BUY26_BUY35_BUY48_WrongItemPreviewAndOnePenaltyPerInstance` | One slot; correct concrete NPC and type, kidney, Good minimum, packaging. |
| BUY-27 | No rule-level test | Photo, location hint, appearance hours, search region and absence of an exact NPC marker are authored content/map UI. No fabricated content. |
| BUY-28 | O `BUY26_BUY28_OrderAcceptedAfterNegotiationOneTeamSlotAndFortyEightHours` | Acceptance after negotiation starts 48 h; preobtained item valid. |
| BUY-29 | O `BUY29_BUY47_SpecialMultipliersAreSequentialIgnoreSaturationAndAllowNoCooler` | Real sale checks all multipliers and saturation exemption. |
| BUY-30 | O `BUY30_FailedOrderNegotiationNoSlotOrDeadlineAndThreeHourOfferBan` | −1, same-offer cooldown, no active deadline, no new-ID bypass. |
| BUY-31 | O `BUY31_BUY43_BUY53_OnTimeOrderStacksRespectOrganXpAnd150Each` | +5 and next-contact flag. Buyer identity/conditions are undecided. |
| BUY-32 | O `BUY32_BUY42_DeadlineAppliesMinusFourOnceKeepsSlotAndNegotiatedPercent` | Exact deadline, −4 once, slot retained, late delivery allowed. |
| BUY-33 | O `BUY33_RefusalBeforeDeadlineMinusTwoAfterDeadlineNoExtraPenalty` | Before/after deadline, release slot and stash reservation. |
| BUY-34 | O `BUY34_StashOpensOnAcceptanceCanWithdrawUntilConfirmedThenPaysImmediately` | Open flag, deposit, withdrawal, sale/XP and sold tombstone. Physical stash excluded. |
| BUY-35 | O `BUY26_BUY35_BUY48_WrongItemPreviewAndOnePenaltyPerInstance` | Wrong item stays owned and unsold; −1 once. |
| BUY-36 | P `BUY36_BUY52_AbdominalSetAndBloodPays630TeamXpAndOnlyOnlinePlayers` | Shared cash; each session participant gets full XP; team gets sum; remote location irrelevant. |
| BUY-37 | O `BUY37_ConcurrentConfirmationsWithSameIdPublishOnceAndReturnOriginalReceipt`, `BUY37_CompetingIdsAndInvalidBatchCannotPartiallySellOrReward`, `BUY37_SoldIdentityCannotBeRegisteredOrSoldAgainInAnotherGroup`, `BUY37_OverflowRollsBackAllSaleChangesAndNoReceiptIsPublished` | 32 same-ID calls, 16 competing IDs, rejected batch, sold ID, overflow rollback. One in-process authority. |
| BUY-38 | O `BUY38_SaveRoundTripRetainsRelationsContactsXpTimersSaturationOrdersAndReceipts`, `BUY38_SavedBansNegotiationAttemptsAndWrongItemPenaltiesCannotReset` | Serializable snapshot/resume and retained receipts/bans/attempts/penalties. Real save-file/network integration excluded. |
| BUY-39 | No rule-level test | Audio ownership, proximity, speakerphone and three character voices require audio/network/presentation. |
| BUY-40 | No rule-level test | Witnesses, patrol scheduling and staged-deal content require world/police integration. The core emits no patrol or ambush events, which alone cannot prove world behavior. |
| BUY-41 | Same tests as BUY-22 | New player's skill is used, spent attempts retained. |
| BUY-42 | O `BUY32_BUY42_DeadlineAppliesMinusFourOnceKeepsSlotAndNegotiatedPercent` | Late sale retains +20 negotiation, loses only +25 order premium. |
| BUY-43 | O `BUY31_BUY43_BUY53_OnTimeOrderStacksRespectOrganXpAnd150Each`, `BUY43_RepeatOrganSpecialStacksOnePlusFiveRespect` | +2/+1 normal respect stacks with +5. |
| BUY-44 | P `BUY02_BUY44_IntroSyringeIsTenDollarsOnceNoBargainingAndFirstBloodRewards` | Syringe 55 XP each/+2, next bag 5 XP/+1. |
| BUY-45 | M `BUY45_ReopeningAddingGoodsAndChangingPlayerCannotRestartChain` | Added goods, new player, reopen preserve attempts/terms. |
| BUY-46 | O `BUY46_BestQualityFirstRegardlessOfLoadOrRequestOrder` | Both request orders produce $1121; receipt lists highest tier first. |
| BUY-47 | O `BUY29_BUY47_SpecialMultipliersAreSequentialIgnoreSaturationAndAllowNoCooler` | Packaged Good item without cooler accepted at ×0.90. |
| BUY-48 | O `BUY26_BUY35_BUY48_WrongItemPreviewAndOnePenaltyPerInstance`, `BUY48_PenaltyIsPerItemAndScopedToEachMeeting`, `BUY37_BUY48_NotReservedCostsNoRespect`; M load-rejection test above; O saved-penalty test under BUY-38 | Actual unsuitable items retain deduplicated penalties; wrong negotiation groups, NotReserved and invalid loads are penalty-free. |
| BUY-49 | O `BUY49_RespectDropDoesNotInvalidateAcceptedOrder` | New low respect does not interrupt existing terms. |
| BUY-50 | M `BUY50_CurrentGroupFinishesAfterTimeoutButNextCannotStart` | Current group can negotiate/confirm late; next group and conflicting appointment blocked. |
| BUY-51 | P `BUY23_BUY51_RespectRangesAndNames`, `BUY23_BUY24_BUY51_RespectStartsThirtyAndAcquaintanceOnlyOnce` | All five names and range endpoints as data; actual UI excluded. |
| BUY-52 | P `BUY52_NewTypeBonusOncePerSaveOnlyFirstUnit`, `BUY36_BUY52_AbdominalSetAndBloodPays630TeamXpAndOnlyOnlinePlayers` | All six bonuses, multiunit first batch, repeats, global catalog flags. |
| BUY-53 | O `BUY31_BUY43_BUY53_OnTimeOrderStacksRespectOrganXpAnd150Each`, `BUY43_RepeatOrganSpecialStacksOnePlusFiveRespect` | +150 to each online participant in addition to organ XP. |
| BUY-54 | P `BUY54_TierLabelsAndColorData`; O `BUY54_BUY56_StreamerRequiresPerfectTierAndCorrectNpc`; O wrong-item test under BUY-26 | Five labels/palette data, ordinal minimum-tier comparison. No rendered color claim. |
| BUY-55 | P `BUY55_UpgradesOrderedAndSpendOnlyFreeTeamXp` | 500/1000/2000, prerequisites, duplicate/insufficient-XP rejection, lifetime/personal XP retained. |
| BUY-56 | O `BUY56_StreamerOfferNeedsSawAndDowntown`, `BUY54_BUY56_StreamerRequiresPerfectTierAndCorrectNpc` | Both gates, OLD_STREAMER provenance, Perfect minimum. Late template only; no first-version brain gameplay. |

## Rules and integration contract

1. Inject `IBuyerClock.GameSeconds` as monotonic **game-world seconds**, with **game time 0 = 00:00**. Saturation computes its day as `GameSeconds / 86400`, so every multiple of 86400 must correspond to 00:00; a session clock starting at another time of day must be converted to this origin by the host adapter. Advance it only while the world is active. Restore the clock at the saved `LastGameSeconds`; do not translate real elapsed time into game deadlines. `IBuyerRandom.NextPercent()` supplies an integer 0–99; invalid requests do not roll. This core has no `DateTime`, timers, Unity types or hidden random generator.
2. `SetPresentParticipants` means players in the whole session, not players standing beside the buyer. It retains absent players' personal statistics. `RegisterItem` accepts a unique host item ID and reported holder. The host must maintain physical ownership and inventory consistency.
3. `DeliveredCooled` records transport provenance. Inspection/reservation does not change it. `Packaged` records an individual sealed organ bag. The BloodBag kind already denotes sealed blood. Special orders require packaging and current minimum tier; cooling is optional and affects price.
4. Before quote/confirm, operations/storage must call `UpdateQuality` for any loss. That method only permits degradation. This library deliberately does not duplicate spoilage, cooler capacity, electricity or patient logic. Operations owns the 5 min room / 25 min portable / paused powered-fridge rules; portable capacity is 8, stationary capacity 24. Price reads the latest supplied tier at confirmation. The intro-syringe freshness preset remains outside this buyer core.
5. Ordinary flow: schedule meeting → report attendance/load host-owned accepted items → begin one type group → ask or accept price → quote → confirm. `FinishGroup` leaves that type's negotiation intact. The host calls `RecordMeetingAttendance` when a participant arrives without loading goods or starting negotiation. Only an untouched no-show incurs the missed-meeting penalty. Cancellation after arrival without attendance/interaction still costs −1; negotiating, a failed deal or walking away after refusal does not acquire an extra closing/timeout penalty. After any sale, `CancelMeeting` and `CompleteMeeting` both complete the meeting freely and release outstanding reservations. Expired active groups remain finishable, while further groups cannot start. A failed negotiation releases its type's reservations immediately.
6. Special flow: create a template offer bound to a concrete NPC/stash → negotiate → explicitly accept → deposit → preview → quote/confirm or withdraw. Only explicit acceptance starts the deadline and opens the stash. A failed offer is reopened through the same saved offer after its cooldown; assigning another ID to its pending template does not bypass it.
7. `ConfirmSale` checks the whole batch under a lock on a private state copy. It then publishes sold tombstones, cash, all participant XP, lifetime/free XP, respect, first-sale flags, saturation, order completion and a receipt together. Overflow throws before publication. Invalid goods do not partially sell. A confirmed unsuitable-item attempt is an explicit rejection transition that may charge its one allowed respect penalty; independent clock-driven midnight/late/miss events can also occur.
8. Confirmation IDs are global in the save, not scoped to a meeting. Both success and rejection receipts are retained. Any repeat ID returns its original result before advancing time, even if the repeated payload differs; corrected requests need a new ID. Keep receipts, used meeting IDs, item tombstones, catalog flags and penalty scopes in the saved snapshot. Do not prune them without another persistent deduplication scheme.
9. `Snapshot` and inputs are copied; consumers cannot mutate live rules state through them. Persist and restore the entire DTO. The concurrent guarantee is for one authoritative `BuyerRules` instance owning one save; separate instances/processes must not operate on the same save concurrently. External physical inventory/network/disk operations are not made transactional by an in-process lock.

## Open questions and explicit implementation choices

These choices make v01 executable; they do not convert draft details into confirmed design.

| Ambiguity | Choice in this version |
|---|---|
| Exact first counter-offer | Configurable `BuyerTuning`: refusals on +5/+10/+20 counter with +0/+5/+10 respectively. A second ask must still be strictly smaller than the first ask. |
| Rounding money | Decimal arithmetic; multiply each unit completely, sum the batch, round once to whole dollars, halves away from zero (operations T-10 direction). Configurable decimal places 0–2. No intermediate percent or unit rounding. |
| Midnight between preview and confirmation | Confirmation uses its current day and fresh tier. `ExpectedTotal` can reject changed totals without selling; omit it to accept the current computed value. Saturation resets independently of a ban. |
| Persistent saturation counter size | Per buyer/type/day, cap stored Units at 6 because every subsequent unit has the same 70% price. There is no daily rejection limit. |
| Equal-quality unit ordering | Stable item-ID ordinal ordering after descending quality. Load/request order cannot affect payout. Different cooling status on equal-tier items follows that same deterministic tie break. |
| Deadline equality | On time means `now < Deadline`. At exactly 48 h, apply −4 once and remove the order premium. Meeting arrival is inclusive, and starting a group at exactly expiry is too late. |
| Meeting attendance and ending after a successful partial sale | Decided by the lead for v01.1: interaction/attendance prevents a missed-meeting penalty, even without a sale. A failed deal costs exactly −1 and a +5% walk-away is free. After any sale, Cancel and Complete share free completion, including an active next group or expired wait. |
| Added goods after meeting expiry | The already active type group remains valid; no new type group can start. Added units of that active type keep the same chain/terms. The spec does not define a frozen physical batch at expiry. |
| Leaving after first refusal | Ends that type's chain for this meeting, without the second-refusal penalty or ban. A failed second refusal applies both; reloading/reopening the same meeting does not restore attempts. |
| Negotiation skill ownership | Ranks are per participant, paid from shared free team XP, matching the named negotiator/new-negotiator skill rule. The operations team-wide formula skill does not implicitly make every negotiator equally skilled. Personal XP remains unspent statistics. |
| First-sale respect versus XP | Respect's first-type flags belong to each buyer relationship; novelty-XP flags belong to the whole save. The current implementation has only C01 and the generic first organ buyer, not a speculative specialized-buyer catalog. |
| C02/C03 identity and conflicting old canon | Use `C01` and neutral `ORGANS_01`; do not claim the latter is finally C02. v02 first-blood unlock and authored rotating meeting points win over the older van/receiving-building sequence. Next-contact unlock is a flag only. |
| Stash confirmation actor | Any currently present participant can confirm a special-order stash; the negotiated price is locked, so no new negotiator is needed. Ordinary meeting confirmation remains restricted to that meeting's negotiator. Physical ownership is required for deposit/withdraw. |
| Wrong batch contents | Validate in submitted order and sell none on failure. An accepted kind in the wrong ordinary group returns InvalidRequest with no penalty. Only actually unsuitable merchandise is penalized once per item/scope. Invalid IDs, stale reservation, duplicate IDs and missing items are not unsuitable-goods penalties. Preview never penalizes. |
| One-time introductory syringe | One exception per save. It counts as first blood if blood has not yet been sold; if a bag was sold earlier it does not grant a second first-blood bonus. No second syringe is accepted. |
| Order retry and content generation | No automatic quest generation. A concrete NPC ID is required from content. Failed offers retain their ID/cooldown; the accepted or completed template cannot be rerolled for new terms. Refused offers need a newly authored offer ID. Successful templates are recorded as completed. |
| First-order versus late-order authoring | Hamlet kidney is the first-version template, requiring HAMLET_BODYBUILDER/Good/packaging. Streamer brain is a late template gated by saw plus Downtown, requiring OLD_STREAMER/Perfect/packaging. Actual offering sequence and next specialized buyer remain content work. |
| Exact tier palette | Existing operation palette was reused as data. The specs confirm color families, not these exact hex values. No new visual approval is claimed. |
| Save exploitation / offline time | Save includes receipts, attempt chains, acquaintance, bans, saturation day, deadlines and wrong-item keys. Load a paused game clock from the same snapshot. Actual disk persistence and cross-session player identity migration remain adapter decisions. |
| Phone voices, stash/parking choreography, specialized buyer | Left open. No invented identity, accepted-merchandise restrictions, scene objects, map changes, audio files, police behavior or patient changes. |

## File inventory

The complete absolute-path inventory, including generated staging/build/NuGet evidence files, is written to `C:\Dev\Game\ArtSource\Dev\Buyers_staging\created-and-changed-files.txt`. The final path check requires every listed entry to exist as a file inside `C:\Dev\Game\`; its results are in `C:\Dev\Game\ArtSource\Dev\Buyers_staging\verification-summary.txt`.

The exact list of files created or changed during this v01.1 follow-up, including rebuilt binaries and refreshed evidence, is `C:\Dev\Game\ArtSource\Dev\Buyers_staging\v01.1-created-and-changed-files.txt`. It is determined against content hashes recorded before editing; every listed file is checked to exist under `C:\Dev\Game\`.

Existing adjacent buyer Data/Editor files from another workstream were left untouched. Existing root-folder metadata was preserved. No files were written under a Codex project, sandbox or user-profile directory by this task's commands.
