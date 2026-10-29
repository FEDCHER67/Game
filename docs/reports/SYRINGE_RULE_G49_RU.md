# G49 — правило шприца

28.10.2026, Феде. **Правила, предметные данные и разрешённые подключения готовы; Unity EditMode: 356/356 PASS, 0 FAIL, 0 skipped.** Полная игровая продажа C01 и сохранение полевого/сетевого инвентаря требуют вставок Claude в защищённые файлы. Они здесь не редактировались. Точные вставки — приложение [SYRINGE_RULE_G49_HOOKS_RU.md](SYRINGE_RULE_G49_HOOKS_RU.md), часть этого отчёта.

## Что сделано

- У экземпляра шприца собственный строковый ItemId, тип, постоянный PersonId, содержимое с отдельным PortionId. Числовые ID определений — 303 (кровь) и 304 (наркоз), размер 1, не складываются. Они добавлены в Inventory/Items/ItemDatabase; каталог Capture/карта и магазин не менялись.
- Проверка чужого PersonId предшествует забору/расходу. Отмена частичного забора удаляет лишь незавершённый прогресс; завершённая порция/инъекция привязывает экземпляр. Две порции оставляют NPC живым, третья смертельна, кровь из трупа запрещена и на старом входе FillBlood. Счётчик пациента не сбрасывается.
- Перенос ItemStack, локальный drop/pickup, сетевой сериализатор, WorldItem и состояние стола несут экземпляр. Опустошение и упаковка не очищают привязку; PortionId переходит в пакет. История legacy без доказанного PersonId блокирует использование, а не делает шприц новым.
- C01: первая порция в шприце $10, далее $8, без торга. Возврат по умолчанию сохраняет тот же ItemId и PersonId; «оставить» помечает экземпляр списанным. Pure-правило передаёт сумму/XP/готовое состояние одному адаптеру существующей выплаты. Оно не содержит баланса или записи денег. Повтор подтверждения, новый TransactionId для проданной порции и продажа её пакетом не дают вторую выплату. В Buyers Core снят старый запрет второй продажи.
- Утреннее правило: один командный record, граница 06:00, постоянный ID world/wagon/syringe/morning; start/join/load используют тот же record. Неактивный мир не выдаёт предметы; несобранный экземпляр сохраняется один. Дополнительные точки — пустой авторский массив SyringeFindData.ExtraSpots, автоматической гарантии нет. Координаты и физический спавн намеренно не авторились.
- Убраны бесплатные стартовые запасы полевого наркоза/стяжек и пополнение наркоза у базы. Смена пациента на столе не обновляет шприц/его привязку. Старый вспомогательный kit-слот пока сохраняет существующий способ выбора инструментов; полное пустое начало/постановка пролога остаются интеграцией Capture, не новой системой инвентаря.

## Цены G48

Единственная точка чтения — BuyerCatalog.SyringePrice(id), интерфейс ISyringePriceLookup. Временно разрешённый fallback находится только там: 2/2/10/8. G48 уже появился; реализован G48SyringePriceLookup(EconomyCatalog), читающий его данные одним lookup. Bootstrap после загрузки каталога: `BuyerCatalog.SyringePrices = new G48SyringePriceLookup(economy);`.

| ID G49 | ID данных G48 | Значение | § |
|---|---|---:|---|
| syringe_blood | syringe_blood | 2 | 5 / 15 A29 |
| syringe_anaesthesia | syringe_anaesthesia | 2 | 5 / 15 A29 |
| c01_blood_first | blood_syringe_first | 10 | 5.3 / 15 A25 |
| c01_blood_repeat | blood_syringe_repeat | 8 | 5.3 / 15 A25 |

## Правило → тесты

S = Inventory/Tests/EditMode/SyringeRulesTests; O = Operation/Stage1/Tests/OperationSyringeTests; B = Buyers/Tests/BuyerSyringeTests. Все находятся под C:\Dev\Game\Assets\OnlyVolunteers.

| Правило | Проверки |
|---|---|
| Первое успешное применение, два типа, hover/fail/cancel без привязки | S.FirstSuccessfulUseBindsAndSamePersonRemainsValid, FailedAttemptHoverAndCancellationDoNotBind, TypesCannotBeInterchangedAndGonePersonNeverMakesNew; O.CancelledDrawBindsNobodyAndDoesNotIncrementCounter |
| Чужой NPC отвергается до забора/инъекции | S.AnotherPersonRefusedBeforeAnyDrawOrDose; O.RefusalHappensBeforeExistingDrawAndLeavesCounterAndFillIntact, DoseRefusedBeforeConsumptionAndFirstActualDoseBinds |
| Тот же NPC: лимиты и запрет трупа | O.SameNpcKeepsCounterTwoLivingPortionsThirdFatalNoFourth, CorpseRejectedAtBothOldAndNewEntryPoints |
| Перенос, drop, пустой возврат, упаковка, save/load, legacy | S.HandOverDropEmptyPackAndSaveKeepSameInstanceAndBinding, UnknownLegacyHistoryIsNeverCleanedOnLoad; O.OperationSaveRoundTripPreservesItemPersonAndPortionIds |
| Цена $2 и ID G48 | S.PriceUsesOneLookupById, G48JsonAdapterReadsActualSyringeAndC01DataByAlias |
| C01 $10→$8, общий флаг, default/leave, ровно одна выплата/XP | S.FirstSaleReturnChoiceSameItemBindingAndOnePayout, DefaultReturnsEmptyAndTeamFlagSurvivesLoadNewSyringeAndNewParticipant, FailedPayoutLeavesPortionBindingAndFirstFlagUntouched, ConcurrentConfirmationsOfSamePortionBookOnePayout; B.RepeatSyringeAfterSnapshotReloadHasEightDollarsAndNoNewBonus |
| Порцию нельзя продать шприцем и пакетом | S.OnePortionCannotBePaidAsSyringeThenBagOrWithAnotherTransactionId, BagFirstDoesNotRepeatFirstBloodXpAndPackedPortionCannotStayInSyringe; B.PortionCannotSellAsSyringeThenBagWithDifferentMerchandiseIds |
| Активная свежесть | S.FreshnessUsesOnlyActiveSecondsAndExpiredSaleNeverCallsPayout |
| Суточная находка без дублей и накопления | S.DailyStartJoinLoadSameIdNoDoublingAndNewSyringeAtSix, UncollectedNeverPilesUpAndClosedWorldNeverGrantsOrBackfills, BeforeSixAndAdditionalAuthoredSpotsDoNotGuaranteeExtraItems |

## Проверки и числа

- **PASS: Unity 6000.5.11f1, все EditMode 356/356** (финальный job edf94b9a7f28431b80003859a0969e88; предварительный 7a7d4ee40eb546b8b2676dc8864762eb). Состав: 323 прежних случая, включая 31 G48 и 27 Economy Claude, плюс 33 G49: 25 Inventory, 2 Buyers, 6 Operation. Отдельный запуск *до* изменений G49 не проводился; 323 — сопоставление состава финального прогона, а не заявленный baseline PASS. Два прежних ожидания обновлены по прямому разрешению: повторный шприц принимается; труп кровь не даёт.
- **PASS: Unity compilation / Console 0 ошибок** после Refresh и domain reload; Roslyn всех затронутых сборок COMPILE_OK. Unity CLI 1.0.0-beta.14 установлен, Pipeline отсутствует; использован единственный существующий CoplayDev bridge согласно docs/AgentRules.md. Новый мост/процесс Editor не создавался.
- Ранние чистые проверки: 171/171 до подключения runtime; затем 173/173 после двух регрессий Buyers; финальная .NET-проверка **175/175**, включая настоящий JSON G48 и конкурирующие подтверждения. Финальный Unity-прогон сделан после последнего изменения исходников, включая round-trip позы мирового шприца.
- Результаты: [unity-editmode-final.json](../../Working/Tests/G49/Results/unity-editmode-final.json), [pure-final.trx](../../Working/Tests/G49/Results/pure-final.trx); ранние [unity-editmode-all.json](../../Working/Tests/G49/Results/unity-editmode-all.json), [pure-before-hooks.trx](../../Working/Tests/G49/Results/pure-before-hooks.trx), [pure-after-hooks.trx](../../Working/Tests/G49/Results/pure-after-hooks.trx). PlayMode/ручной кооператив не запускались: защищённые сохранение/выплата/сетевой перенос ещё не подключены.
- Точный Editor: Game@b321844a, C:/Dev/Game, 6000.5.11f1, PID 11892. Play=false до/после, та же Map_W85_Play_v02. Lock G49 получен перед обращениями и освобождён с -Done сразу после тестов.

## Плейтест после вставок Claude

1. Получить новый кровяной шприц; отменить неполный забор — постоянной привязки нет. Закончить порцию на A, попробовать B: «Этот шприц уже использован на другом человеке», прогресс/кровь/препарат B не меняются.
2. Продать C01 без пакета. По умолчанию забрать тот же пустой экземпляр, снова наполнить на A: после первой $10 следующая $8, бонус XP не повторяется. «Оставить покупателю» убирает шприц. Повтор подтверждения/того же PortionId не платит снова.
3. Передать, выбросить/поднять, упаковать кровь, сохранить/загрузить: PersonId прежний. На другом NPC по-прежнему отказ. После двух порций A жив, третья смертельна; из трупа не брать.
4. Start/join/load не удваивают утреннюю находку. До 06:00 новой нет; в 06:00 одна, если прежняя собрана. Несобранная не накапливается; закрытый мир не выдаёт новые.

## Открыто

Приложение содержит точные вставки в FieldKitSave/CaptureSaveData, CaptureSave, NetworkInventory и общий payout helper ящика. Они **не применены** по границе владения. Существующий ящик — органная заглушка, в нём нет runtime-учёта XP/встреч C01: подключение команды XP и атомарного сохранения с payout делает Claude; нельзя вызывать ConfirmSale ради второй денежной проводки. До этого полный игровой сценарий C01/сохранения полевого инвентаря не считается готовым. Начальная постановка NPC, физическая точка у вагона, дополнительные точки, закупки/доставка, смерть/поимка владельца и полноценный disconnect/rejoin требуют соответствующего Capture/Inventory адаптера; новые pure records сами не заменяют эти пути. Неизвестный legacy-шприц блокируется намеренно. Начальный инвентарь по-прежнему содержит вспомогательный kit-item 301, пока владелец Capture не изменит его выдачу. Длительность свежести взята из существующего OperationTuning; новые подтверждённые 120 секунд не вводились.

## Файлы

Полный список абсолютных путей с проверкой существования, sha256 и причиной для каждого исходника/данных: [SYRINGE_RULE_G49_FILES.md](SYRINGE_RULE_G49_FILES.md). Там же перечислены созданные файлы проверки и генерируемые локальные результаты. Все пути проверены внутри C:\Dev\Game. Чужие изменения не откатывались; Git staging/commit/push не выполнялись.
