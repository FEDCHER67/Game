# G29 — Buyer data definitions v01

Дата: 16.10.2026 (Europe/Moscow). Статус: исходники и данные подготовлены; компиляция и импорт оставлены Claude по прямому указанию пользователя.

## Источники и границы

- `C:\Dev\Game\docs\specs\BUYERS_SPEC_2026-10-15_v02.md` — основная спецификация.
- `C:\Dev\Game\docs\specs\OPERATIONS_SPEC_2026-10-15_v01.md` — органы, качество и упаковка.
- `C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Items\Item_*.asset` — существующие числовые ID.
- `C:\Dev\Game\docs\drafts\buyer_messages.json` — новые тексты G28 появились во время работы и подключены до завершения.
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Core\BuyerCatalog.cs` — прочитан для согласования интеграционного ключа и палитры с G27. Файлы Core не входят в итоговые изменения G29.

Unity не открывался и не запускался. Импортёр не запускался. Git stage/commit/push не выполнялись. Сцены, Operation, стол и модель пациента не редактировались. Существующие посторонние изменения оставлены как были. Все итоговые файлы G29 находятся только под `C:\Dev\Game`.

## Классы и сборки

Namespace данных: `OnlyVolunteers.Buyers.Data`.

| Класс | Содержимое |
| --- | --- |
| BuyerDefinition | ID, RU/EN, принимаемый товар с существующим itemId, минимум качества, часы, base/point, насыщение, voiceId, декларативное условие открытия, textIds |
| QualityTierTable | Пять записей 1–5, EN/RU, процентная подпись, множитель, Unity Color |
| RespectLevelTable | Шкала 0–100, старт 30, пять уровней с включительными границами |
| SpecialOrderDefinition | Тип и обязательная индивидуальная идентичность NPC из наводки, орган, качество, упаковка, срок, премия, тексты, фото, тайник, условия появления, доступность в первой версии |
| BuyerDataFields | Только сериализуемые вложенные поля MerchandiseDefinition, WorkingHours, UnlockCondition и UnlockRequirement |

`OnlyVolunteers.Buyers.Data.asmdef` использует UnityEngine и не ссылается на Core: данные хранят простые идентификаторы и числа, поэтому зависимость не нужна. `OnlyVolunteers.Buyers.Editor.asmdef` доступен только Editor и ссылается только на Data. В SO нет вычисления цены, торга, насыщения, таймеров, респекта, XP или проверки принятия заказа; эти правила принадлежат G27. Валидация импортёра проверяет структуру контента, не исполняет торговлю.

Декларативные условия — все записи массива `unlockCondition.all` одновременно: `contact_available`, `first_successful_blood_sale`, `respect_at_least`, `owns_tool`, `district_access`. `subjectId` — ключ соответствующей внешней системы. Это договор данных, а не реализованный обработчик условий. Неизвестные/PLACEHOLDER ключи нельзя считать выполненными.

## Подготовленные JSON

| Файл | Данные |
| --- | --- |
| Buyer_C01_v01.json | C01, кровь, 24/7, к базе, без насыщения и качества; пакет $50; учебный шприц один раз $10 без торга |
| Buyer_FirstOrganFence_v01.json | ORGANS_01, все шесть существующих типов органов, минимум 1, 24/7, выбранная точка, насыщение; открытие после первой успешной продажи крови C01 |
| SpecialOrder_HamletBodybuilderKidney_v01.json | SO_HAMLET_BODYBUILDER_KIDNEY, HAMLET_BODYBUILDER, почка 102, Good/Хорошее (3, 60%), запечатанный индивидуальный пакет, 48 игровых часов, +25%, респект 40 |
| SpecialOrder_OldStreamerBrain_v01.json | SO_OLD_STREAMER_BRAIN, OLD_STREAMER, мозг 105, Perfect/Отличное (4, 80%), такая же упаковка/срок/премия; пила, Даунтаун, респект 40; вне первой версии |
| QualityTierTable_v01.json | Убитое / Сойдёт / Хорошее / Отличное / Идеальное; 20/40/60/80/100%; 0.3/1/1.6/2.6/4.2 |
| RespectLevelTable_v01.json | ууу хиляк 0–19; новобранец 20–39; бывалый 40–59; проверенный 60–79; своячок 80–100 |

Все JSON расположены рядом с классами в `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data` и непосредственно соответствуют сериализуемым полям SO без обёртки.

Числовые ID Inventory: сердце 101, почка 102, печень 103, лёгкие 104, мозг 105, глаз 106. Шесть типов дают восемь физических органов: две почки, два глаза, парные лёгкие одним предметом. Скальпель 201 не добавлен в товар. Новые Inventory ID не выделялись.

`ORGANS_01` согласован с `BuyerCatalog.OrganBuyer` G27; связь с каноническими C02/C03 остаётся открытой в спецификации. Новые `c02.*` тексты G28 используются как тексты роли первого скупщика, без переименования ключа Core. Соответствие шаблонов G27: SO_HAMLET_BODYBUILDER_KIDNEY → OrderTemplate.HamletKidney; SO_OLD_STREAMER_BRAIN → OrderTemplate.StreamerBrain. Автоматический адаптер SO → Core не входит в этот пакет.

`minimumTier = 0` только у C01 означает «качество неприменимо», а не нулевую ступень органа. Для крови itemId = 0 и itemIdUnresolved = true: в указанном каталоге Item_*.asset нет определения крови. Это блокирующая заглушка интеграции Inventory, не действительный ID. Импорт authoring-ассетов допускается с предупреждением; торговлю подключать после назначения существующих/утверждённых ID пакета и заполненного шприца.

`none` означает отсутствие требования упаковки обычной продажи, не запрет упакованного товара. `sealed_blood_bag`, `filled_syringe`, `sealed_individual_organ_bag` — семантические описания состояния упаковки, не Inventory ID. Органный пакет не заменяет охлаждение. Экземпляр принятого заказа должен сохранить конкретного NPC из наводки: совпадения одного targetNpcTypeId недостаточно.

Палитра совпадает с текущим пресетом G27: #8C7B6B / #C2B23A / #4DC25A / #3E8DFF / #A75CFF. Семейства цветов подтверждены, точные RGBA — пресет. Английские имена уровней респекта и описательные имена покупателей — рабочая локализация, не дополнительные решения о персонажах.

## Подключённые тексты G28

- `Buyer_C01_v01.json`: `c01.first.01`, `c01.first.02`, `c01.first.03`, `c01.first.syringes_01`, `c01.first.syringes_02`, `c01.first.bags_rule`, `c01.offer.01`, `c01.intro_c02.01`, `c01.intro_c02.02`.
- `Buyer_FirstOrganFence_v01.json`: `c02.first.01`, `c02.first.02`, `c02.offer.01`, `c02.meeting.arrived_01`, `c02.meeting.waiting_01`, `c02.meeting.finish_group`.
- `SpecialOrder_HamletBodybuilderKidney_v01.json`: `c02.special.hamlet_bodybuilder.pitch`, `c02.special.hamlet_bodybuilder.clue_card`.
- `SpecialOrder_OldStreamerBrain_v01.json`: `special.old_streamer.pitch`, `special.old_streamer.clue_card`.

Текстовых ID с PLACEHOLDER больше нет. Объединённые `clue_card` содержат фото, место, часы, область поиска и требования; runtime подставляет именованные параметры. Для стримера точное место/часы/область пока не определены, это параметры контента, а не выдуманные значения. Наводка качка: турник на площади Хутора, 06:00–10:00.

## Оставшиеся заглушки

- `PLACEHOLDER.BUYER.LATE_ORDER_PROVIDER` — `SpecialOrder_OldStreamerBrain_v01.json: offeringBuyerId`; `SpecialOrder_OldStreamerBrain_v01.json: unlockCondition.all[0].subjectId`.
- `PLACEHOLDER.CONTACT.C01_INITIAL` — `Buyer_C01_v01.json: unlockCondition.all[0].subjectId`.
- `PLACEHOLDER.DISTRICT.DOWNTOWN` — `SpecialOrder_OldStreamerBrain_v01.json: unlockCondition.all[2].subjectId`.
- `PLACEHOLDER.PHOTO.HAMLET_BODYBUILDER` — `SpecialOrder_HamletBodybuilderKidney_v01.json: cluePhotoId`.
- `PLACEHOLDER.PHOTO.OLD_STREAMER` — `SpecialOrder_OldStreamerBrain_v01.json: cluePhotoId`.
- `PLACEHOLDER.STASH.HAMLET_BODYBUILDER_KIDNEY` — `SpecialOrder_HamletBodybuilderKidney_v01.json: stashId`.
- `PLACEHOLDER.STASH.OLD_STREAMER_BRAIN` — `SpecialOrder_OldStreamerBrain_v01.json: stashId`.
- `PLACEHOLDER.TOOL.SAW` — `SpecialOrder_OldStreamerBrain_v01.json: unlockCondition.all[1].subjectId`.
- `PLACEHOLDER.VOICE.C01` — `Buyer_C01_v01.json: voiceId`.
- `PLACEHOLDER.VOICE.FIRST_ORGAN_FENCE` — `Buyer_FirstOrganFence_v01.json: voiceId`.

Дополнительно: itemId 0 для blood_bag и blood_syringe (два явно помеченных неразрешённых ID); ORGANS_01 — согласованный с G27 временный ключ первого скупщика до канонической сверки. Фотографии, точки и тайники этим заданием не создаются.

## Что создаст импортёр

Меню: `OnlyVolunteers/Buyers/Import JSON v01`. Вызов вручную после компиляции Claude; автоматических startup/reimport-хуков нет.

- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\Buyer_C01_v01.asset`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\Buyer_FirstOrganFence_v01.asset`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\QualityTierTable_v01.asset`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\RespectLevelTable_v01.asset`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\SpecialOrder_HamletBodybuilderKidney_v01.asset`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\SpecialOrder_OldStreamerBrain_v01.asset`

Итого шесть .asset плюс Unity-generated .meta для них. Сейчас эти .asset не создавались. Поздний заказ импортируется как определение с availableInFirstVersion=false; потребитель обязан исключать его из пула первой версии и проверять все условия открытия.

Перед первой записью импортёр читает все шесть JSON, проверяет схему/уникальность ID, обязательные поля, пять ступеней/уровней, непрерывность диапазонов, существующие Inventory ID и типы уже существующих целевых ассетов. Для PLACEHOLDER и явно неразрешённых ID крови выдаёт предупреждения. Повторный запуск обновляет ассеты на месте, сохраняя GUID. Сохраняет только свои шесть ассетов через SaveAssetIfDirty, не все dirty assets проекта. Ошибка ввода-вывода на стадии сохранения может оставить частичный импорт; после устранения причины меню можно повторить. Формат JSON и соответствие исходным полям проверены статически; поведение Unity API ещё не проверено.

## Проверки

- PASS — Python 3.12.10, инлайн-проверка через PowerShell here-string → `python -`, cwd `C:\Dev\Game`: все шесть JSON синтаксически корректны, корневые и вложенные ключи точно соответствуют public-полям C#; числа/строки/булевы значения и RGBA проверены.
- PASS — та же проверка: реальные ID из Item_*.asset, товар/качество/часы/насыщение покупателей, оба NPC/органа/порога/упаковка/48 часов/25%, поздние ограничения, точные таблицы качества и респекта.
- PASS — все 19 используемых текстовых ID найдены в актуальном buyer_messages.json G28; текстовых заглушек 0.
- PASS — JSON обоих asmdef, Editor-only ограничение и отсутствие зависимости Data от Core/Inventory/Operation; парные .meta файлов Data и Editor.
- PASS — итоговая проверка абсолютных путей и наличия всех перечисленных ниже файлов под `C:\Dev\Game`.
- NOT RUN — C# compilation, Unity, menu importer, проверка созданных .asset в Unity. Они оставлены Claude по заданию пользователя.

## Полный список итоговых созданных файлов G29

Каждый путь проверен на существование и принадлежность `C:\Dev\Game`. Существующие файлы не перезаписывались, кроме правок вновь созданных исходников этого же задания. Промежуточные .meta Core, попавшие в первый проход генерации метаданных G29, были немедленно отменены с проверкой точного собственного содержимого; итоговых изменений Core от G29 нет.

- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\BuyerDataFields.cs`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\BuyerDataFields.cs.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\BuyerDefinition.cs`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\BuyerDefinition.cs.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\Buyer_C01_v01.json`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\Buyer_C01_v01.json.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\Buyer_FirstOrganFence_v01.json`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\Buyer_FirstOrganFence_v01.json.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\OnlyVolunteers.Buyers.Data.asmdef`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\OnlyVolunteers.Buyers.Data.asmdef.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\QualityTierTable.cs`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\QualityTierTable.cs.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\QualityTierTable_v01.json`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\QualityTierTable_v01.json.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\RespectLevelTable.cs`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\RespectLevelTable.cs.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\RespectLevelTable_v01.json`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\RespectLevelTable_v01.json.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\SpecialOrderDefinition.cs`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\SpecialOrderDefinition.cs.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\SpecialOrder_HamletBodybuilderKidney_v01.json`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\SpecialOrder_HamletBodybuilderKidney_v01.json.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\SpecialOrder_OldStreamerBrain_v01.json`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\SpecialOrder_OldStreamerBrain_v01.json.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Editor.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Editor\BuyerJsonImporter.cs`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Editor\BuyerJsonImporter.cs.meta`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Editor\OnlyVolunteers.Buyers.Editor.asmdef`
- `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Editor\OnlyVolunteers.Buyers.Editor.asmdef.meta`
- `C:\Dev\Game\docs\reports\BUYERS_DATA_v01.md`
