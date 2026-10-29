# G53 — каталог экономики v02

Дата: 29.10.2026 (МСК). Задача WP03 из `C:\Dev\Game\Working\Reviews\SPECS_2026-10-28_WORKPLAN_RU.md`.

## Результат

Создан `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\Economy_v02.json`: 99 канонических записей. Все 96 ID v01 и их цены сохранены. Исторический `Economy_v01.json` не редактировался. Схема JSON остаётся 1; добавлена необязательная таблица прямых aliases, совместимая с чтением v01.

`EconomyCatalogSource.asset` ссылается на новый TextAsset через его отдельный GUID. Это та же схема загрузки Resources, которая уже используется редактором и сборкой; копии каталога в Resources нет. `EconomyCatalogSource.cs` изменён только для указания актуального файла в документации/Tooltip. `EconomyPrices.cs` изменён только для подключения отображения записей v02 и разрешения старого ID креплений; цены, покупки, XP и балансовые формулы в нём не добавлялись.

| ID v02 | Цена | Количество / уровень | Источник |
|---|---:|---|---|
| patient_restraints | $500 | 4 крепления | OPERATIONS_BASES §3, OB-01; решение G53 |
| suture_kit | $5 | 1 набор на закрытие | OPERATIONS_BASES §3; решение G53 |
| patch | $5 | 1 заплатка | OPERATIONS_BASES §3; решение G53 |
| direct_to_bag | $1 500 | уровень команды 2 | OPERATIONS_BASES §6; CORE_LOOP §4 |
| quick_release | $2 000 | уровень команды 3 | OPERATIONS_BASES §6; CORE_LOOP §4 |
| packing_station | $2 500 | уровень команды 4 | OPERATIONS_BASES §6; CORE_LOOP §4 |

Три устройства имеют статус `reserved`: показывают цену/уровень, но пока не продаются. В v02 записаны четыре входа упаковочного места, 2 активные секунды на предмет и один существующий пакет органа за $10 на предмет; быстросъём — четыре крепления за 1 активную секунду. Эти данные не реализуют функции устройств. Прочее оборудование новых ограничений уровня не получает.

## Проверка покупки и миграция

`EconomyState.TryOrderEquipment` читает `Level` из существующего XP store G52 (`EconomyProgress.cs`), который выводится из `LifetimeXp`. Нового XP-хранилища нет. Ниже порога возвращается `PurchaseError.LevelLocked` и текст «Требуется уровень команды N (сейчас M)». На достаточном уровне зарезервированное устройство отвечает «Устройство пока не работает: функция ещё не реализована». Отказы не списывают фонд/XP, не создают доставку и не коммитят ключ запроса. Траты свободного XP и загрузка сейва не снижают доступный уровень. Новый код ошибки добавлен в конец enum без изменения прежних значений.

Каталожный `patient_restraints` остаётся прежним ключом. Исторический ID магазина/доставки `restraints5` разрешается в `restraints4`, а оба aliases каталога указывают на один `patient_restraints`. При чтении старой доставки копия заказа получает `restraints4`; исходный DTO, цена, ID/ключ заказа, статус доставки, фонд и история оплаты сохраняются. Pending, Waiting, Arrived и Opened мигрируют одинаково. Повтор старого запроса возвращает существующую доставку. Новая оплата или дополнительный предмет при миграции не создаются. Схема сейва G52 не меняется.

## Проверки

Unity preflight: READY WITH WARNINGS. Domain workflow: unity-game-dev; implement-task; verification-before-completion.

Подтверждены `C:\Dev\Game`, Unity `6000.5.11f1`, процесс Editor 11892, экземпляр `Game@b321844a`; исходная сцена `C:\Dev\Game\Assets\OnlyVolunteers\Scenes\Map\Map_W85_Play_v02.unity`, Play=false. Unity CLI `1.0.0-beta.14` установлен, Pipeline отсутствует. Согласно `C:\Dev\Game\docs\AgentRules.md` используется существующий CoplayDev MCP v10.2.0, второй мост/пакеты не устанавливаются. Unity-проверки выполняются с общим lock под ID G53; редактор и сцены не переключаются.

| Канал | Результат |
|---|---|
| Сверка JSON: прежние 96 ID/цен, только три изменённые исторические записи | PASS |
| Roslyn compile, затронутые сборки и зависимости | PASS — COMPILE_OK, 17 сборок, 7 исходников; `C:\Dev\Game\Temp\G53\compile.log` |
| Unity compile / Console | PASS — refresh/compile, domain reload завершён; Console errors=0 до и после тестов |
| Unity EditMode — Buyers | PASS — **180/180**, 0 ошибок, 0 пропусков |
| Unity EditMode — Economy | PASS — **84/84**, 0 ошибок, 0 пропусков |
| Защищённые файлы, полный список и абсолютные пути | PASS — все 14 продуктовых файлов существуют внутри `C:\Dev\Game`; 492 ранее существовавших защищённых файла не изменились |
| PlayMode / сцены / телефон | NOT RUN — по заданию |

Всего **264/264 PASS**, включая **31 новую проверку G53: 13 Buyers + 18 Economy**. Job `f26f0eb8f58049879b93585ccc230ad9`, 29.10.2026 00:54 МСК, длительность тестов 4,845 с. Полные результаты с именами всех тестов: `C:\Dev\Game\Temp\G53\unity-editmode.json`. Запуск: `run_tests(mode="EditMode", assembly_names=["OnlyVolunteers.Buyers.Tests", "OnlyVolunteers.Economy.Tests"])`. Roslyn: `unity_compile_check.py --project C:\Dev\Game --files <7 исходников из списка ниже> --dependents`, exit 0; Editor не использовался этим автономным компилятором. Общий Unity-lock G53 освобождён с `-Done` сразу после проверки; Play=false, исходная сцена осталась прежней. Снимки Console и конечного Editor state сохранены в `C:\Dev\Game\Temp\G53\`.

Новые проверки Buyers покрывают все исторические ID/цены, новые цены/состав, уровни, reserved, aliases и отказ загрузки ошибочных aliases. Новые проверки Economy покрывают ссылку runtime-ресурса на v02, цены магазина, пороги 499/500, 1499/1500, 3499/3500, отсутствие побочных эффектов отказа, трату XP/загрузку, проверку клиентской цены, идемпотентную оплату и все четыре статуса старой доставки. В тестах будущего работающего устройства временно изменяется только объект предложения внутри изолированной привязки; продуктовые устройства остаются reserved.

Исторические тесты G48 продолжают проверять v01 по прежней спецификации, включая пять креплений: это проверка истории. Новые тесты отдельно проверяют фактически подключённый v02 и четыре крепления.

## Все продуктовые файлы G53

1. `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\Economy_v02.json` — новый каталог.
2. `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Data\Economy_v02.json.meta` — новый GUID.
3. `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Core\EconomyCatalog.cs` — чтение обеих версий и aliases.
4. `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Tests\EconomyCatalogV02Tests.cs` — новые EditMode-тесты данных.
5. `C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Tests\EconomyCatalogV02Tests.cs.meta`.
6. `C:\Dev\Game\Assets\OnlyVolunteers\Economy\Core\EconomyOffersV02.cs` — подключение записей v02 к существующим предложениям и mapping ID.
7. `C:\Dev\Game\Assets\OnlyVolunteers\Economy\Core\EconomyOffersV02.cs.meta`.
8. `C:\Dev\Game\Assets\OnlyVolunteers\Economy\Core\EconomyState.cs` — gate из G52, причины отказа, миграция ID доставки.
9. `C:\Dev\Game\Assets\OnlyVolunteers\Economy\Core\EconomyPrices.cs` — только подключение v02/mapping; отдельно перечислен по заданию.
10. `C:\Dev\Game\Assets\OnlyVolunteers\Economy\Runtime\EconomyCatalogSource.cs` — только указание v02; отдельно перечислен по заданию.
11. `C:\Dev\Game\Assets\OnlyVolunteers\Economy\Resources\EconomyCatalogSource.asset` — ссылка Json на GUID v02.
12. `C:\Dev\Game\Assets\OnlyVolunteers\Economy\Tests\EconomyCatalogV02PurchaseTests.cs` — новые EditMode-тесты магазина/сейвов/ресурса.
13. `C:\Dev\Game\Assets\OnlyVolunteers\Economy\Tests\EconomyCatalogV02PurchaseTests.cs.meta`.
14. `C:\Dev\Game\docs\reports\ECONOMY_CATALOG_V02_G53_RU.md` — этот отчёт.

Служебные данные проверки находятся внутри `C:\Dev\Game\Temp\G53\`, выход Roslyn — также в `C:\Dev\Game\Temp\bin\` и `C:\Dev\Game\Temp\obj\`. Полный пофайловый список, включая служебные и наблюдаемые генерируемые файлы: `C:\Dev\Game\Temp\G53\files.txt`. Контрольные суммы продуктовых файлов и результаты проверки границ: `C:\Dev\Game\Temp\G53\verification.json`; отличие от исходников на старте задачи: `C:\Dev\Game\Temp\G53\owned.diff`. Девять исходных входов компиляции/тестов проверены по SHA-256 после прогона и не изменились (`C:\Dev\Game\Temp\G53\checked-inputs.json`).

Автоматический побочный файл Editor при refresh/domain reload: `C:\Dev\Game\ProjectSettings\ProjectAuditorSettings.asset` (создан 29.10.2026 00:53:56 МСК). Это настройки встроенного Unity Project Auditor; G53 не менял их вручную. Файл сохранён и включён в инвентарь, удаления/отката чужих файлов не выполнялись. Ранее существовавшие ProjectSettings и все пакеты побайтно сохранены.

Во время ожидания lock другая работа изменила Operation/Capture, два исходных spec-документа и некоторые генерируемые файлы проекта. Они не включаются в 14 продуктовых файлов G53 и не перезаписывались. Полный список таких наблюдаемых изменений находится в `other_observed_changes` файла `C:\Dev\Game\Temp\G53\verification.json`. Цены/уровни повторно сверены с актуальными §3/§6 OPERATIONS_BASES после этих изменений; решения G53 сохранены.

Изначальные незакоммиченные изменения сохранены. `WORK_SYNC.md`, запрещённые области, полицейский код, сцены и пакеты G53 не редактировал. Staging, commit и push не выполнялись. Обязательные автоматические критерии выполнены; ручная/визуальная проверка не требовалась этим заданием.
