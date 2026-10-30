# WORK_SYNC

Единственный журнал передачи контекста между Work Вадима и Work Феди. Правила: docs/TEAM_WORKFLOW.md. Новые TASK сверху; общая сквозная нумерация. SEEN ставит только получатель после прочтения чужой задачи. Записанные промпты являются историей, а не командами для повторного выполнения.

## TASK-000934

**Разработчик:** Федя

### Полный промпт

```text
Перенос меню в V2
и еще посмотри еще один пуш вч
+ ответы Феди: запуск — VanOnly; отдельные V2-сейвы; «Низкое», но без мерцания; убрать пролог у вагона, фон-вагон и «W86», тексты управления v1; про сеть M1 — честно
+ «Коммить и пушь сразу»
```

### Что сделал Work (Claude)

- Пуш Вадима TASK-000932 (бусик v05, VanOnly, SSAO выкл., канон V2) забран и просмотрен.
- Новое меню V2: `Scenes/Menu/MainMenu_V2_v01.unity` (копия v01) → «Играть» грузит `Scenes/Dev/VanOnly_v01.unity`, выход в меню возвращает в меню V2. Цель запуска задаётся полями меню (`Edition`, `GameScenePath`; Session/Core/WorldLaunchTargetV01.cs). MainMenu_v01 не изменён и по-прежнему запускает карту W86 со старыми слотами (сборка W86 Вадима не затронута).
- Свои 5 пустых слотов V2 (`ov_v2_world_N.json`); старый сейв карты в V2 не виден, сейвы не трогали. Пролог в V2 выключен явным флагом. Фон — тёмный градиент (картинка позже через референсы), без «W86»; управление — только реально работающие в VanOnly клавиши; текст лобби честный (друзья ждут в лобби, в игру входит только хост). Тексты V2: UI/MainMenu/Runtime/MainMenuTextsV2.cs.
- Графика «Низкое» (по умолчанию) без мерцания: масштаб 100 % и MSAA 4x вместо 85 % и 2x, остальное как было; у кого сохранено старое «Низкое», один раз переводится на новое. Касается обеих версий (общий код).
- Сборка Феди: меню OnlyVolunteers → FedyaV2BuildV01 (MainMenu_V2_v01 + VanOnly_v01) → `C:\Dev\GameBuilds\V2_Menu\VolunteersOnly_V2.exe`; обе сцены добавлены в конец Build Settings. VadimBuilds не трогали.
- Проверки: компиляция 0 ошибок, EditMode 711/711 (+7 тестов цели запуска/слотов/пролога), сборка V2 собрана. Exe и Play не запускали — плейтест за Федей.
- Важно Вадиму: W86GraphicsSettingsV01/W86LookV01 (пресет «Низкое»), WorldLaunchV01, W86MainMenuV02, W86PauseMenuV01, W86MenuLobbyV01, W86PrologueHookV01 изменены; поведение v01 сохранено.

## TASK-000933

**Разработчик:** Федя

### Полный промпт

```text
(бриф C:/Users/Zeyo-ne/.codex/.chatgpt-projects/g-p-6aadbaaa21c081918dcf9006013794cd/outputs/prompts/claude-v2-repository-cleanup-archive-context-push_2026-10-30_v01.md — чистка репозитория под V2: внешний архив, узкий контекст агентов, ветки, отдельный пуш)
+ ответы Феди: старые worktree — убрать в архив; ветки GitHub — удалить только слитые с main; правило StartAtMax — пометить как v1
```

### Что сделал Work (Claude)

- Устаревшее вынесено из репозитория во внешний архив `C:\Dev\Game_Archive\2026-10-30_cleanup_v01\` (на ПК Феди; MANIFEST.tsv с путями, размерами и SHA-256, сверка 0 расхождений): из Git ушло 2 411 файлов (1,73 ГБ: docs/_archive_v1, старые ревью и тесты Working, Tools/MapV76, ArtSource органов/операций/карты W86/W*-ревизий, корневые Animations, 5 v1-скиллов fc-*, ~5 МБ отчётов и логов в Assets), плюс 10,8 ГБ неотслеживаемого (старые сборки, материалы проверок). Код и ассеты v1 в Assets не трогали: их чистка — после утверждения канона (Вадим). 21 папка оставлена, потому что её читает код по пути.
- WORK_SYNC: закрытая история v1 (TASK-000001…000920 и заметки по лесу до 29.10) вынесена в архив, здесь только текущие задачи и заметки 30.10. Полная версия — тег `archive/pre-v2-cleanup-2026-10-30` (состояние до чистки, на GitHub; через него всё вынесенное доступно и Вадиму).
- Агентам: новая точка входа docs/INDEX.md, docs/CURRENT_STATE.md переписан под V2, ARCHITECTURE/AgentRules/README/AGENTS/CLAUDE больше не ведут в v1. Правило «Архивы — только с разрешения Феди или Вадима» в AGENTS.md и CLAUDE.md; .claude/settings.json просит подтверждение человека на чтение `C:\Dev\Game_Archive` и `V1_СТАРАЯ_ИГРА` (это не замок ОС).
- Правило AGENTS.md про StartAtMax помечено как v1 (в каноне V2 старт с нищенского бусика); код не менялся.
- Ветки: 3 старых worktree (29–30.09) убраны (их неотслеживаемые файлы в архиве), 9 локальных веток удалены; на GitHub удалены только ветки, целиком вошедшие в main. Ветки с собственными коммитами оставлены; их коммиты ещё и в бандле в архиве.
- Проверки: компиляция в Unity batchmode без ошибок, EditMode 704/704; проверка зависимостей живых сцен (+ VanOnly_v01 в списке).
- Важно Вадиму: тег `v1-final` и ветки `archive/v1-organs-openworld` на GitHub нет — пока ты их не запушил, точка восстановления v1 для всех — `archive/pre-v2-cleanup-2026-10-30`. Если твои локальные сцены ссылаются на вынесенное, возьми из этого тега (с .meta). Папку `Assets/VadimLocal/VanLab` Unity у Феди снабдила своим .meta — он не закоммичен, запушь свой.

## TASK-000930 | SEEN: Федя

**Разработчик:** Вадим

### Полный промпт

```text
30.10: переход на V2 (органов и открытого мира больше нет; база -> локация -> запихиваем людей в бусик -> солдаты -> волны врагов -> деньги -> прокачка бусика). Разложи всё по двум папкам: первая часть игры и вторая, работаем во второй; папки с рабочего стола в GAME (ярлыки сборок остаются на столе); пустая структура V2 (референсы, персонажи, бусик...); запушь только распределение, без гигабайтов.
```

### Что сделал Work (Claude)

- Документы v1 перенесены в `docs/_archive_v1/`, `docs/PRODUCT.md` = черновик канона V2, `docs/V1_ARCHIVE.md` = как брать файлы из v1 (всегда с .meta). AGENTS.md/CLAUDE.md указывают на V2.
- GAME разделена на две папки в корне: `V2_НОВАЯ_ИГРА` (работаем здесь; пустая структура 00_Общее, 01_Референсы, 02_Персонажи, 03_Бусик, 04_Локации, 05_База, 06_Звуки, 07_Интерфейс, ПРОМПТ_ChatGPT) и `V1_СТАРАЯ_ИГРА` (у Вадима полная копия v1 в `V1_СТАРАЯ_ИГРА/GAME_v1`, git worktree на ветке архива). В Git только ПРОЧТИ.md и .gitkeep (.gitignore); тяжёлые файлы на ПК Вадима.
- Код v1: тег `v1-final` + ветка `archive/v1-organs-openworld` — пока только локально у Вадима (вместе с картой W86 за 29.10 это ~560 МБ LFS; лимит LFS на GitHub почти исчерпан, ~10,7 ГБ). Запушим позже по слову Вадима.
- Код v1 из main ещё не удалён: сначала канон V2 (допрос Вадима идёт).

## TASK-000929

**Разработчик:** Федя

### Полный промпт

```text
(бриф C:/Users/Zeyo-ne/.codex/.chatgpt-projects/g-p-6aadbaaa21c081918dcf9006013794cd/outputs/prompts/claude-global-gloss-reduction-clothing-seam-fix_2026-10-30_v01.md, часть 1)
+ «Стекло 55 %»
```

### Что сделал Work (Claude)

- Блеск всех живых моделей снижен до 33 % от исходного (smoothness × 0.33), стекло — × 0.55 (решение Феди): 469 .mat живых сцен по манифесту Art/Gloss/gloss_manifest_v01.json, материалы внутри FBX — при импорте (OvGlossV01 / GlossReductionV01), билдеры машин/мастерской/аптеки, правила W86LookV01 (надбавка блеска Даунтауна отменена), материалы, создаваемые в игре (операция, каркас фургона, стяжки).
- Идемпотентно: повторный импорт/пересборка не откатывает и не применяет второй раз. Metallic, отражения, emission, прозрачность, пресеты не менялись. Исключены игрок/руки (уже полностью матовые) и глаза NPC.
- Важно Вадиму: если добавляешь новые .mat в живые сцены — запусти меню capture из GlossReductionV01, иначе их блеск не снизится. Изменение версии обработчика вызывает переимпорт ~1200 FBX (~30 с). Отчёт: docs/reports/GLOSS_REDUCTION_2026-10-30_RU.md.
- Часть 2 брифа (дыры в одежде) — ждёт команды Феди.

## TASK-000928

**Разработчик:** Федя

### Полный промпт

```text
(брифы Феди 30.10, папка C:/Users/Zeyo-ne/.codex/.chatgpt-projects/g-p-6aadbaaa21c081918dcf9006013794cd/outputs/prompts/)
- claude-hands-framing-punch-sleeves-stretch-polish_2026-10-30_v01.md
- claude-fist-cooldown-diminishing-stun_2026-10-30_v01.md
+ «Делай руки вообще не блестящими … левая рука не должна быть видна никогда кроме когда ты держишь двумя руками объект, правая рука видна только когда ты держишь легкий объект, иначе рук не видно»
+ «руки … слишком близко к камере … отдалить от камеры подальше и пониже на 25%»
+ «остальное мы ждем моей команды как руки доделает пуш на гит»
```

### Что сделал Work (Claude)

- Видимые руки игрока-сосиски (Assets/OnlyVolunteers/Player/Hands): от первого лица в покое рук нет; правая — только с лёгким предметом в одной руке; обе — при хвате двумя руками; на 25 % дальше и ниже от камеры; полностью матовые (тело игрока тоже). Друзья видят всю сосиску с обеими руками; сетевой канал рук и удара в NetworkPlayer (друзья увидят после сети M1).
- Растяжение/провис меньше в ~1.7 раза (предел 3.53), пружинный отскок мягче. Открыто: дальний хват NPC (1.6–2.5 м) — руки не дотягиваются; варианты: KeepGripBeyondCap или ограничить дальность хвата (ждёт решения Феди).
- Удар Q: замах → удар → звёзды в точке попадания (только при попадании) → возврат; одно событие с номером, без дублей.
- Кулак: перезарядка 1.0 с на игрока; оглушение по одному NPC 100/70/45/25/10/0 %, общий счёт для всех бьющих, сброс через 8 с без ударов и после подъёма; удар 0 % не валит и не прерывает подъём; счётчик сохраняется у пойманного NPC (Map/Data/Fist.asset, Capture/Core/FistRulesV01.cs).
- Рукава/манжеты от первого лица починены без правки модели.
- Важно Вадиму: GreyboxInteractor/GreyboxNpc/WeaponStun изменены (кулак); у других оружий прежние 0.6 с без таблицы. Глянец −67 % по всей игре идёт отдельно, в этот пуш НЕ входит.

## TASK-000927

**Разработчик:** Федя

### Полный промпт

```text
(серия брифов Феди 28–29.10, все в C:/Users/Zeyo-ne/.codex/.chatgpt-projects/g-p-6aadbaaa21c081918dcf9006013794cd/outputs/prompts/)
- claude-economy-integration-story-foundation-m06_2026-10-28_v01.md
- claude-workshop-chosen-palette-red-mark-placement_2026-10-28_v02.md
- claude-city-pharmacy-selected-concepts-courtyard_2026-10-28_v02.md
- claude-safe-vadim-sync-k10-mechanic-van-upgrades_2026-10-29_v01.md
- claude-mechanic-b-model-animation-workshop_2026-10-29_v01.md, claude-mechanic-wrench-two-hand-aim-fix_2026-10-29_v01.md
- claude-player-customization-main-menu-prologue_2026-10-29_v02.md
- claude-larger-van-redesign-cargo-fit_2026-10-29_v01.md / _v02.md
- claude-whole-game-performance-steam-90fps_2026-10-29_v01.md (в очереди)
+ «сделай больше гаечный ключ чтоб он был как оружие … а после запуш все, что мы сделали и оставь вч записку по проведенным работам и тому, что мы планируем сделать; бусик он хочет сам сделать, но если уже есть наша версия бусика сделанная то ее тоже пуш если нет, то просто перекладываем бусик на вадима»
```

### Что сделал Work (Claude)

Полная записка для Вадима: docs/reports/FEDYA_TO_VADIM_2026-10-29_RU.md. Кратко:
- Главное меню (Scenes/Menu/MainMenu_v01, первая в сборке): миры ×5, соло/кооп навсегда, кастомизация сосиски игрока (PLAYER_SAUSAGE_W86: по 5 вариантов на аспект), лобби, настройки (графика — Низкое по умолчанию, звук — микшер OV_Main_v01).
- Экономика: общий фонд, опыт/уровни, защита сейвов, каталог Economy_v02, шприцы G49, магазин в телефоне; прокачка бусика 0–III + кузов (вместимость I/II, фиксаторы $1 500, мягкий отсек $2 500); событие стука GreyboxNpc.CargoKnocked для полиции/NPC Вадима.
- Мастерская к северу от Стройки + подъёмник + механик B (маршрут, шутки, разговор по E, «пуф» при прокачке, большой ключ); M05/M06; основа миссий M01–M13.
- Аптека в Rough 04-H3 (8–20, по сети, STAFF ONLY, двор с фургоном).
- Операции: порча с первого вскрытия, К10 (паника на ремнях, бег с рукой на животе, смерть через 2–12 м), правило обдолбанного донора.
- Совмещено с TASK-000926 Вадима: наши места поставлены шагом 8b поверх его сцены, трава/рельеф изменены только на наших участках.
- Важно Вадиму: бусик передаём тебе (нашей модели нет; есть расчёт компактного 5,34 × 2,00 × 2,28, база 3,19 — Working/Reviews/VanRedesign_2026-10-29/VAN_LAYOUT_v02_RU.md). Полицию и твои скрипты не трогали. После перепечки травы/рельефа прогнать шаг 8b.
- Дальше: сеть M1 (друзья на карте), видимые растягивающиеся руки, катсцена у вагона, холодильник + хранение, база 1, оптимизация FPS (90 на среднем ПК).

## TASK-000924 | SEEN: Федя

**Разработчик:** Вадим

### Полный промпт

```text
(27.10) [картинки ChatGPT 20_Карта_как_будет_заполнена_v01: MAP_DRESSED_TOP/SOUTH] «Что тебе не нравится на этой карте? … горы какие-то странные … просто горы, и нихуя. А мне нравятся горы … на горе полянка, там деревья расставлены, а потом над ней ещё одна гора … ступенчатые горы … недостаточно проработан водопад … неблагополучный район не по вайбу … не хватает площадки перед даунтауном. И Тихой долины … переход на пляж неудачный … холм в элитном районе сделано очень хуево … непонятные острова … вид сбоку охуенно выглядит … можем в будущем такую же местность сделать? … сейчас унылое говно. Что думаешь?»
```

(27.10, далее) «Может попросить ChatGPT погенерировать референсы … и потом ты по ним заебашишь … предлагаю уже начинать минимальный геймплей … с минимальным сюжетным представлением, заставку не делать … как мы будем двигаться по карте … карту делать не со стороны наблюдателя, а чтобы на ней было интересно играть … заспавнились в лесу, как будем NPC отлавливать, минимальный сюжет … каждую локацию переделывать, как только будем по ним двигаться. Что думаешь? Если лучше не так — говори.»

(27.10, далее) «Потяни коммиты Феди … статуя отсвечивает … фонари новые» / «скинь вид леса сверху и скажи, что добавить … чтобы по спецификации было интересно играть … почему выглядит хуёво с точки зрения рельефа и локаций … неиграбельно» / «разберись, почему FPS мало … 3060 Ti и 5700X … займёмся оптимизацией» / «создай на рабочем столе, чтобы GPT погенерировал референсы … где сейчас высокие горы … выход за границу из леса — не горы, а непроходимый лес, куча деревьев вместе, лесная чаща, невидимый барьер»

### Статус

- Подтянут Федин TASK-000911 в GAME (локальные правки 25.10 в бэкапе VolunteersBuilds\local_before_pull_2026-10-27; старый бэкап сцены backup_hill_pre911). VadimHillApply.Run заново на сцене Феди, рендеры AllViews + MapOverview совпадают с 25.10, сборка Map_W86 27.10 21:34 ок. SkyRenderer22: наша ночь/облака слиты с Фединым шагом теней. VadimShots/VadimWallSample теперь возвращают lodBias/shadowDistance.
- (27.10) «перезапиши пересборку … Escape — настройки графики, детализация, шейдеры … изначально небольшие … оптимизация встроена … добавь отражения, фонари». Меню Escape с графикой, отражения и фонари уже есть (Федя 911). Локально у Вадима: значения по умолчанию = пресет «Низкое» (W86GraphicsSettingsV01.Defaults + запасные значения в W86LookV01). Федя хотел по умолчанию максимум — при пуше согласовать с ним.
- (27.10) «дай спецификацию по лесу … в лесу нет бусика … нормальный вагон, небольшой по длине, вместительный, от поезда, к рельсам коннектится, текстуру согласовать … ловим наркоманов, выкачиваем кровь, отдаём в пакетах … 15–20 минут … референсы вагона и леса, сначала подумать, предложения … сделать сегодня лес … так каждому району» → docs/specs/FOREST_SPEC_2026-10-27_v01.md; промпты Desktop\21_Лес_и_граница_чаща.zip (переписан: без бусика, ЖД, точки) и 22_Вагон_база.zip (3 варианта + интерьер + окраски). «делай».
- (27.10) «пену сделать нормальную … второй слой не нужен никогда … добавить, чтобы было понятно, что вода двигается, небольшую анимашку … белые статичные хуйни убрать … белое только когда вода набегает на песок» / «щас занимаемся горами, лесом + водой». WaterStyle_v05.hlsl: пена только полоса у берега (outer/caps/flowFoam выключены), полоса накатывает шире и оставляет мокрый след при отходе; VadimHillApply.DeepenShoals: дно моря мельче 0.9 м дальше 6 м от суши опущено (мели давали белые линии в открытом море).
- (27.10) «лес по размеру хватит, чтобы интересно играть? … как происходит встреча с торговцем … какой интерактив добавить» — обсуждение, ответ в чате (размер оставить, плотнее; сцена C01; приманка-закладка, дрезина/тачка).
- (27.10) Вагон: «правая нижняя» (гофра) → затем «устраивает такой вагон» (деревянный из концепта ChatGPT); модель v03 по нему: ступеньки, железо, колёса тяжёлые, площадка на двух балках, крыша и лестница цвета железа, внутри пусто, текстуры стен/пола/потолка изнутри.
- (27.10) Лес: «дрезины не нужны, рельсы от тоннеля до вагона и всё … притон в овраге ок, мостик ок … дороги в Тихую долину нет, центральная чуть правее и выходит в Хутор … озеро изогнутое, болото ок … горы на границе остаются, но их не видно — непроходимый лес и невидимый барьер … размера хватит? … как сделать, чтобы игрок не ушёл с базы раньше времени» → решения в FOREST_SPEC «Решения Вадима 27.10 (вечер)».
- FPS: найдено — QualitySettings.lodBias 1000 и shadowDistance 80 утекли из наших съёмочных скриптов (VadimShots/VadimWallSample) в проект и в сборки; у Феди в 911 MSAA 8x.
- Промпт ChatGPT: Desktop\21_Лес_и_граница_чаща.zip (граница-чаща вместо гор на западе/СЗ, играбельный лес, 4 картинки).

Открыт. Обсуждение: цель — местность как на MAP_DRESSED_SOUTH_v01 (ступенчатые горы с полянами и деревьями, густой смешанный лес, каньон с водопадом, скалистый берег). Порядок и пробный участок — по ответу Вадима.

## TASK-000923 | SEEN: Федя

**Разработчик:** Вадим

### Полный промпт

```text
(25.10, несколько сообщений) «Здесь просто ровную небольшую гору слева от реки…» / «туман… не настолько густой… не должен так высоко подниматься… за туманом часть воды… не нужна степь» / [скрин марины] «подфиксить хуйню с пляжем у элитного района» / «Сделай просто аккуратненький пляж… продолжение пляжа под элитным районом… уменьшается и входит в гору… расставь причалы и катера… гору справа от реки небольшую, аккуратную… Сначала скриншоты, потом сборку» / «причалы одной высоты с песком… неровности, где бусик не проедет… на скале текстура песка… ровно расставь лежаки… гору повыше, каменную, хаотичную, не широкую — естественная граница» / «стенка не должна быть такая высокая» / «гора должна до конца пляжа доходить… более острая, каменная» / «запиши навсегда в claude.md… ничего не висит, горы не выпирают на дорогу, всё соединяется, гармонично… посмотри все основные ошибки»
```

### Что сделано (local W86, VadimHillApply.Run)

- Элитка (BuildElite): южный пляж продолжается под скалой, сужается и уходит в гору; песок ровный на высоте палуб причалов (1.15 / 1.2), причалы начинаются на песке, яхты у причалов на воде; бугры под яхтами и островки под водой, одиночные песчаные шипы срезаны; на крутой скале камень вместо песка; 6 групп зонт + 2 шезлонга в ряд под скалой.
- Тихая долина: справа от реки узкий высокий каменный хребет (до ~30 м, неровные вершины) от моста до моря, каменная облицовка как у Феди (W86_rock_face); пляж Даунтауна продолжен до устья; ровное поле за хребтом; пена старого русла выключена.
- Море: недостающие квадраты воды (сетка Феди 4 м) добавлены там, где суша стала морем (FillSea: за КПП и у устья).
- Граница: степь убрана, за забором вода; туман ниже (верх 45 м, спад 10 м, плотность 0.022, мягкий ближний край).
- Позже 25.10: лежаки парами ногами к морю + зонты, пальмы, мусор с пляжа убран, причалы от кромки воды, катера слева; пол Тихой долины выровнен; пляж и поле у хребта чистые; горы — Федин Rock_Macro в тёмно-сером тоне на облицовке и на слое земли, облицовка у подножий (SkinOver) без растянутых текстур, осыпь в песок; валуны серые; оранжевая дымка только у КПП (гаснет за 120–260 м); Sfx: 3D-звуки (NPC) не играют дальше своей дальности.
- Промпт ChatGPT 20_Карта_как_будет_заполнена (снимки всей карты сверху с подписями + 2 вида; только природа и игровые точки, без новых зданий), zip на рабочем столе. Правило: новых зданий нет — только природа + заправка/апгрейдер/место встречи.
- CLAUDE.md: раздел «Map rebuild quality» — правила проверки карты и список прошлых ошибок.

## TASK-000922 | SEEN: Федя

**Разработчик:** Вадим

### Полный промпт

```text
(25.10, несколько сообщений) Граница: убрать невидимые стенки/сетку, дымки нет — видно океан; нужна глубокая оранжевая степная дымка, перед ней немного детализированного степного песка. Даунтаун: улица S1 не должна быть сквозной — дома поставить в притирку (слева снизу и слева сверху); подземный паркинг добавить. Тихая долина: сузить в ~1,5 раза — река раньше поворачивает, сдвигается сторона долины у реки; гора у долины больше, за рекой средняя. Убрать с рабочего стола архивы и папки промптов.
```

### Что сделано (local W86, VadimHillApply: BuildBorder / BuildDowntownFixes / BuildValley, всё в Run)

- Граница: сетка Феди 37 м (Fence_04-border-fence1/2) и наши коллайдеры убраны; дымка — свой unlit-шейдер VadimLocal/DustWall (ZWrite, без тумана/ночи/ауры), 3 плотных слоя z 1000–1100, оранжевая; полоса степного песка z 943–1060; степь вне полосы вырезана дырами.
- Даунтаун: S1 закрыта двумя копиями дома 05-H000 на x 924–940; подземный паркинг 05-03 под подиумом (124×22 м, пол 1.0, колонны, разметка, свет), въезд-рампа с N2 через западную полосу площади, дыры в террейне.
- Тихая долина: новое русло (поворот на юг у x≈610), старое ущелье засыпано; большая гора 27 м между долиной и рекой, средняя ~15 м за рекой; старый водопад перенесён к новому устью; лаборатория с площадками сдвинута на 14 м, забор/дорожки стянуты к x 589; камни/деревья/трава пересажены.
- Рабочий стол: архивы в ПРОМПТ_ChatGPT\_архивы, папки и результаты GPT — в _с_рабочего_стола.

## TASK-000921 | SEEN: Федя

**Разработчик:** Вадим

### Полный промпт

```text
(25.10, скрин леса) Дай на рабочем столе промпт для GPT, чтобы создался референс-лист леса: начинаем прорабатывать основные сцены от начала до конца, начало геймплея — спавн в лесу. Собрать всё, что говорили: персонажи, вайб леса, далеко не видно, но ходить можно; дорожки ведут куда надо; убрать дорогу в Тихую долину; болото не ровной формы, в нём можно тонуть; у вагона и в центре карты нет деревьев — так нельзя; на бусике не должно быть легко проехать; рельеф неровный; пеньки и типичный лес под нашу игру.
```

### Что сделано

- `Desktop\ПРОМПТ_ChatGPT\18_Лес_референс_лист` + `Desktop\18_Лес_референс_лист.zip`: скрин Вадима, лес сверху, вся карта, промпт на референс-лист из 8 панелей (план, старт у вагона, грунтовка из бусика, пешком, болото с местом где тонут, озеро, NPC леса, палитра деталей) с правилами из канона (§8.1 v02, NPC-спека: торчки, закладчики, грибники, полиции нет).

## История до TASK-000920 включительно (v1)

Закрытая история v1 (TASK-000001…000920 и заметки Вадима по лесу W86 до 29.10) вынесена из активного журнала 30.10.2026 (чистка V2). Полная версия: `git show 0571b085:WORK_SYNC.md` (тег `archive/pre-v2-cleanup-2026-10-30`). Это архив: читать только по прямому разрешению Феди или Вадима (см. AGENTS.md, «Архивы»).

## Заметки Вадима, 30.10 (V2)

- 30.10 Vadim: GPT 38 visual research read (Desktop/ПРОМПТ_ChatGPT/_результаты/VO_Visual_Research_2026-10-29: REPORT.md, 15 priorities, 1-screenshot test). GPT 37 forest sounds reviewed (Desktop/37_Звуки_леса_v01: 215 files, CC0 except water_ankle/knee CC BY 3.0 credits; fixes: fades on gusts/creaks/rustles, trim footstep heads, wood -8 dB, drop tree_creak_04 + quiet rustle_01/03; no real warm melody). BUG: Map_W86 build (forest life / stash, r27/b27 29.10 23:54) - forest NPC (OD junkie / stasher) are GIANT; posed render NPCs giant too (after_pose_den_inject = wall). Diagnosing.
- 30.10 FIX giant forest NPC: the 11 Forest/Animations clip FBX imported with preserveHierarchy 0 -> Buddy_Rig_Mixamo65 collapsed into the clip root, its x100 scale hit the NPC (~190 m) and no bone moved. Metas set to 1, VadimForestLife sets preserveHierarchy + throws if a clip misses the rig root; diag VadimDiagForestScale: all clips 1.92 m. Rebuild Map_W86 (b28).
- 30.10 Vadim: for now, in every test the team balance is never below $10 000 -> TeamEconomy.TestMinBalance = 10000 (server tops the fund up; set 0 to switch off).
- 30.10 Vadim: play the GPT forest sounds (opened Desktop/37_Звуки_леса_v01/listen.html in the browser); a separate minimal exe scene to rehearse the van (doors open/close, juicy slams) and NPC handling; plan the van size and rough look first from what exists. Done: VanLab = Assets/Editor/VadimVanLab.cs (Run: copy of W86 with the map removed, 1 km flat grey floor with 1 m grid at the van, van, player, capture/net systems, B02 hut, paint table, 3 standing NPC, own save capture_vanlab_v01.json) -> scene Assets/OnlyVolunteers/Scenes/Dev/VanLab_v01.unity; VadimBuilds -BuildOnly VanLab -> C:/Users/chern_0eqkb03/VolunteersBuilds/VanLab/VolunteersOnly_VanLab.exe + desktop shortcut 'VanLab (бусик и NPC)'; launch checked (floor, NPC, fund $10,000). Van size: current 4.78 vs Fedya v02b 5.34 - waiting for Vadim.
- 30.10 Vadim: sound settings in VanLab to turn the volume down -> pause menu (Esc) 'Звук' page is live now (was a placeholder): Master / Effects / Ambience / Voices+UI in 10 % steps, applied and saved at once (PlayerPrefs, this PC); W86PauseMenuV01.cs, so W86 gets it on its next build. VanLab rebuilt (vanlab_b2), compile ok; page not yet seen on screen.
- 30.10 Vadim (GPT 37 sounds): keep water_splash_05 (water entry) and forest_music_02_loop (forest music); the rest my choice; swamp bubbling = soup on a stove -> no swamp bubble sounds at all; wind is nasty -> must be a gentle light breeze; add all the sounds to the game now. In progress (Forest audio v01).
- 30.10 Forest audio v01 done (GPT 37 sounds): processed masters + README + wind old/new listen page in ArtSource/Audio/Forest_v01 (listen_wind_v01.html), game copies Assets/OnlyVolunteers/Audio/Forest_v01 (LICENSES.md, CREDITS_CC-BY.txt for the CC BY 3.0 water steps, also THIRD_PARTY_NOTICES.md + docs/Dependencies.md); 19 new SfxLibrary ids (forest music = forest_music_02 only, breeze = 2 low-passed 750 Hz loops ~10 dB under the music, 3 low-passed gusts every 35-80 s, birds/creaks/rustles/branch cracks every 6-20 s at 8-30 m, calm stream at the nearest point of the forest stream, underwater loop + bubbles, water_splash_05 = jump/fall/body entry splash, steps leaves/trail/twigs 10 %/mud/stone/wood/water ankle+knee); NO swamp bubbles (bog = mud steps, no wading slosh); ForestAudioV01 + UnderwaterAudioV01 on Map_W85_v02/ForestAudio_v01 via VadimForestAudio.Apply (added to VadimMountainApply.Run after VadimForestLife; applied to the saved scene, check VolunteersBuilds/forest_audio_check.txt RESULT OK); Map_W86 + VanLab rebuilt ok. Not heard in game yet.
- 30.10 Vadim: BIG PIVOT proposal - drop everything about organs; no open world / city; Phasmophobia-like structure: base -> spawn on the van at a location -> stuff people into the van -> after a while they come out as soldiers -> waves of an enemy army, our soldiers must beat theirs; special characters (Homelander-like, Jigan shooting, Mr Beast bribing enemies...), stylised and funny; win -> back to base, money, upgrade the van (more space, weapons, a turret on top that moves). Asked for my opinion and how to organise chats/repo (delete chats? Game 2 folder?). Answered in chat; nothing changed yet; needs Fedya's agreement.
- 30.10 Vadim: Fedya AGREES with the pivot (discussed yesterday); districts will be remade as mission locations. Settled: players in battle = drive the van, mobilise (stuff people in), turret, fix/defend the van; NO player-activated special abilities; soldiers simple and cheap: they walk, ignore civilians, attack our mobilised soldiers first, then the van; parody celebs as already done (ISHOWMEET etc.). Asked what to do with the many Claude chats and the repo (delete old / new version). Plan proposed in chat.
- 30.10 V2 split (Vadim «делай», Fedya agreed): v1 committed 51702e35 (TASK-000928), tag v1-final + branch archive/v1-organs-openworld (local, not pushed); v1 docs moved to docs/_archive_v1/ (old canon, specs, reports, drafts, briefs, Progress/NextAction); new docs/PRODUCT.md = V2 canon draft; docs/V1_ARCHIVE.md = how to take files from v1 (always with .meta); AGENTS.md/CLAUDE.md point to V2. Code not deleted yet (after the new canon).
- 30.10 Vadim: separate the old and new versions and keep pulling selected things (movement, NPC...) from v1 into the new one. Done: memory index cut to 28 current notes, v1 memories in memory/_archive_v1; 7 old local chats archived (mountains, Rough, research, spec fork, 'Вч чат (основа)' + fork, 'ВЧ чат'); left for Vadim: the chain spec chat -> map W86 -> forest -> forest v2 (this session's parents) and the cloud chats; proposed a new main session 'V2: допрос по концепции и новый канон'.
- 30.10 Vadim: desktop cleanup - all game folders from the Desktop into C:\Users\chern_0eqkb03\Desktop\GAME (V1_СТАРАЯ_ИГРА: Map, ПРОМПТ_ChatGPT 01-38, 37_Звуки_леса_v01, GAME_old_chats_backup; V2_НОВАЯ_ИГРА/00_Общее: Федя.txt; originals to the Recycle Bin); build shortcuts stay on the Desktop; new ChatGPT prompts in V2_НОВАЯ_ИГРА/ПРОМПТ_ChatGPT. GAME root split into two folders V1_СТАРАЯ_ИГРА / V2_НОВАЯ_ИГРА (+ local worktree V1_СТАРАЯ_ИГРА/GAME_v1 on the archive branch) and an empty V2 structure; push only that, no heavy files (TASK-000930). The V2 split commits were numbered TASK-000929 locally, renumbered to TASK-000930 (Fedya published 929).
- 30.10 Vadim: V2 concept grill (batches 1-4) -> docs/PRODUCT.md canon v1 + raw answers docs/specs/V2_GRILL_NOTES_2026-10-30.md: 1-4 players (solo full, scaling), rubber pistol (enemy down 2 s, ~10 hits to kill, stuns civilians 3 s; money for mobilised + win, not kills), respawn at the van after 10 s, mission 12-15 min 'rising wave' (2 min gathering, pushes every ~2 min, 20-30 s lulls, 2 min final assault), win = final assault cleared, lose = van destroyed (van HP, repair with the wrench), no soldier carry-over (survivors ~$20 bonus), catching = grab v1 lighter + Q/pistol stun and shoulder carry + throw money, seat -> 10 s -> soldier pops out (MAX funny, core mechanic), soldier type from the caught person (locations as funny as possible), soldiers act on their own, enemies = identical green sausage-clone army. Open (Vadim: later): transformation gags, soldier classes, enemy types; next: map, core mechanics, anims, van look. Not pushed.
- 30.10 Vadim, grill batch 5: locations invented anew (not v1 districts as is), ~150x150 m, van spawns on one edge / enemies from the opposite via 2-3 streets, the van drives in battle (mobile recruitment office), the van must be much better and more worked-out, look via ChatGPT refs starting from OUR van; work order = everything about the van and 'busification' first. GPT package 39_Бусик_военкомат (our van VAN-TIER0 v02 renders + v02b layout + character style; variants A-F + cutaway) in C:\Users\chern_0eqkb03\Desktop\GAME\V2_НОВАЯ_ИГРА\ПРОМПТ_ChatGPT\39_Бусик_военкомат + Desktop zip; results -> Desktop\39_Бусик_военкомат_v01. Not pushed.
- 30.10 Vadim, grill batches 6-8 (busification): load through the side AND rear doors, max 3 recruits at once, door does not matter (10 s timer), MAX funny faces the whole time, 'almost doomed' (escape only after a strong enemy hit on the van), soldier tumbles out of the side doors, no front-line rule (soldier may roll into enemies and die - player's choice), transformation anim to design later; turret = upgrade; van HP + wrench repair 2 %/s, plus breakable parts (wheels...) need their own mechanics; enemies hit the van when no soldiers near, runner bat / heavy shield ram = strong hit. In docs/PRODUCT.md. Not pushed.
- 30.10 Vadim: start with the poorest junk van (drives badly, bad engine); upgrades between missions: more seats (more recruits at once, the van gets bigger), roof turret, wheels, engine/speed, health/armour -> a junk-van model + upgraded states (parts on one model, bigger bodies as separate models). GPT package 39 rewritten as an upgrade ladder (start junk -> wheels+engine -> armour -> turret -> seats -> all; side ladder sheet; cutaway with 2-3 seats), zip C:\Users\chern_0eqkb03\Desktop\39_Бусик_военкомат.zip refreshed. Grill batch 9: breakdowns (wheel, engine, doors, more later) patched with the wrench + simple anim; upgrade list not answered. Vadim: enough questions, start on the van. Canon merged into vadim/map-v76-test (merge 5eda5d80, Unity closed). Not pushed.
- 30.10 Vadim (evening): only the van for now, nothing inside; new scene VanOnly (grey floor, sky, van, player, no NPC; VadimVanLab.RunVanOnly, build VanOnly, Desktop shortcut). Van = our v02 design stretched (rejected v03 stepped high roof), bigger and wide, longer (v05 ~6.1 m), two identical front seats, bulkhead (solid below, mesh above). No shimmer ever: SSAO grain, trembling shadow edges, blinking floor -> rule in CLAUDE.md, SSAO off, van interior no shadow receive. Base = start location after every mission, 3 buildings (van upgrade garage you drive into, pharmacy, gear/weapons); GPT package 41_База_старт, zip C:\Users\chern_0eqkb03\Desktop\41_База_старт.zip. Busification v01 code parked (not applied). Not pushed.
- 30.10 Vadim (late): base = one very big military hangar, rather dark, big enough to run and drive around; spawn inside, van inside, exit through huge gates; the 3 buildings are rooms inside the hangar. GPT package 42_База_ангар, zip C:\Users\chern_0eqkb03\Desktop\42_База_ангар.zip (41 refs moved to _результаты). Van: paint v05 military olive green. Reported: FPS 40<->120 with rear doors, being yanked back from other virtual desktops / teleported off the van roof -> caused by the worker's test harness (SetForegroundWindow + global keys + kill by name); harness changed to an in-build test mode.
- 30.10 Vadim: «запушь» V2 work -> main 0571b085 (one V2-only commit on top of origin/main: canon, van v03-v05, VanOnly scene, roof-seat fix, SSAO off, sky cache; 36.7 MB LFS). Local v1 map/forest/hill work (~560 MB LFS) stays unpushed on vadim/map-v76-test. Hangar test scene in progress, texture package 45 sent to GPT.
