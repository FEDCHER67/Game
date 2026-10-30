# G18 — checkpoint P, ревизия 02

2026-10-14. **STOP: ждём художественного одобрения Феди.** Это проверка палитры, неба, тумана и первых бытовых деталей на геометрии v18 style-v3. Полная планировка v19, усиленный рельеф и новые маршрутные прогоны после checkpoint P ещё не выполнялись.

## Результат для просмотра

Две колонки в каждом листе: **v18 style-v3, текущее состояние | новая палитра v19**. Одинаковые координаты камеры, FOV, высота глаз и геометрия исходной карты. Листы предыдущей ревизии сохранены.

| Лист | Содержание |
|---|---|
| [Hamlet](C:/Dev/Game/Working/Reviews/Map_v19_Pilots/palette_test_hamlet_v02.jpg) | 5 прежних обзорных точек + крупный вид первого жилого двора |
| [Rough District](C:/Dev/Game/Working/Reviews/Map_v19_Pilots/palette_test_rough_v02.jpg) | 5 прежних точек + гаражи, граффити, вороны, провода и пасмурное небо |
| [Downtown](C:/Dev/Game/Working/Reviews/Map_v19_Pilots/palette_test_downtown_v02.jpg) | 3 точки |
| [Остальные районы](C:/Dev/Game/Working/Reviews/Map_v19_Pilots/palette_test_other_v02.jpg) | Forest, Construction, Port, Elite, Valley, Beach, Tramduro — по одной точке |
| [Переход Hamlet → дорога → Rough](C:/Dev/Game/Working/Reviews/Map_v19_Pilots/palette_test_transition_v02.jpg) | 4 последовательные точки вдоль hamlet_rough_e |

Итого 26 пар на листах. 27 новых исходных кадров 1920×1080: `Working/Reviews/Map_v19_Pilots/palette_new_v02r03_*.png`; дополнительный вид сада h20 оставлен в исходниках. Основные 20 кадров «до» взяты из неизменённой v01; для семи новых точек заново снята исходная v18 — `palette_current_v02_*.png`. Промежуточные v02/v02r02 кадры сохранены для истории, в итоговые листы не входят.

Манифест: `Working/Reviews/Map_v19_Pilots/palette_sheet_manifest_v02.json`. Позы: `palette_poses_v02.json` и `palette_garden_close_poses_v02.json`. Листы собраны без ретуши кадров; только уменьшение и подписи.

Сохранённая тестовая сцена: **`Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Palette_v02.unity`**. Отдельные материалы, terrain data, профили и небо: `Assets/OnlyVolunteers/Map/LookV3/Palette19/Test_v02/`.

## Что изменено

### Палитра, свет, небо

Все десять районов используют таблицу Феди. Значения t: Forest .50; Hamlet .80; Construction .60; Rough .50; Downtown .60; Port .55; Elite .75; Valley .75; Beach .75; Tramduro .60. Hamlet имеет самые высокие настройки солнечного и окружающего света; Rough — самые низкие. В Forest близкие, немного более мягкие значения. Естественная яркость конкретного кадра также зависит от материалов, теней и того, сколько неба попало в кадр.

В новой ревизии общий пространственный вес районов задаёт `DistrictBlend19.cs`: плавная полоса 60 м между соседними границами, без смены режима тумана. По тому же полю пересчитаны маска albedo и смешение слоёв terrain. Сами v07 текстуры и legacy Look-материалы не редактировались.

`DistrictWeather19V02.cs` управляет цветами зенита/горизонта, покрытием и плотностью процедурных облаков, солнцем, мягкостью теней, ambient, туманом и базовым цветокорректирующим Volume по положению камеры. Десять локальных URP Volumes с blend distance 60 м сохранены. Старый `DistrictAtmosphere19` в тестовой сцене выключен; одновременно работает только новый владелец атмосферы. После рендера каждой камеры глобальные параметры восстанавливаются.

- Hamlet: голубое небо, белые облака, яркий тёплый дневной свет; legacy apple-tree модели и красные яблоки сохранены.
- Rough: холодное низкое пасмурное небо, слабые мягкие тени, saturation −58, temperature −18, exposure +0.08. Это значительно ниже Hamlet (+0.70). **Настоящий линейный distance fog: начало 7 м, полностью непрозрачен на 65 м.** Высотный туман отдельно не добавлялся: вариант distance fog соответствует запросу.
- Forest: серо-зелёное небо, туман 8–70 м, холодная приглушённая палитра.
- Остальные районы получили свои солнечные, пыльные или морские варианты по таблице. Небо и туман показаны на общем листе.

### Первые истории и детали

**Hamlet, двор 02_v18_plot_04:** бельевая верёвка с одеждой, две клумбы, собачья будка, курятник с открытым выгулом, пень с топором и дровами, ведро и лейка, велосипед у ограды, корзина яблок, стол с лавками, кривой участок забора, качели у яблони и лёгкий дым у трубы. Расстановка сгруппирована вокруг домашних занятий. Существующие яблони, изгороди и заборы не заменены равномерным декором. Пять простых бабочек движутся около цветов. Крупный кадр h21 показывает первую группу деталей; это не завершённое наполнение всех дворов.

**Rough:** пять небольших декалей на гаражах, провода между опорами, три изношенных фонаря с процедурным мерцанием, антенны/тарелки/кондиционеры из BUILDING_DETAILS на восьми блоках. Шесть чёрных ворон сидят на гаражах, семь кружат с процедурным взмахом крыльев. Других видов птиц здесь не добавлено. У 1 403 деревьев изменён только prototype на голое дерево с постепенной вероятностью замены в переходной полосе; позиции всех 8 525 исходных tree instances сохранены. По краям остаются отдельные деревья с листвой.

Новый **PILOT_KIT_v02**: `ArtSource/Props/STYLE_KIT_v3/PILOT_KIT_v02/`, импорт — `Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v02/`. 15 оригинальных low-poly модулей, 4 596 треугольников суммарно, метрический масштаб, восемь прежних material roles, UV-палитра, fitted box proxies; птицы/бабочки и занавески декоративные. Дверной проём будки и проход в выгул не закрыты общим AABB.

Четырнадцать FBX используют `_v02`. Для голого дерева финальный файл — **`LEAFLESS_TREE_v03.fbx`**: при визуальной проверке удлинён ствол до всех корней ветвей. Отдельный master `SK3-PILOT-001_v03.blend`, validation и export audit относятся к этому исправлению. Исходные v02 файлы не перезаписаны. Для Unity Terrain сделан `LEAFLESS_TERRAIN_v03.prefab` с MeshRenderer в корне, геометрией в метрах и всеми 11 proxy-коллайдерами. Обычный wrapper с дочерним MeshRenderer был отвергнут Terrain; исправление проверено повторным рендером.

**decals_v02:** `ArtSource/Textures/StyleKit_v3/decals_v02/GRAFFITI_TORN_POSTERS_v02.png`, импортирован в `Assets/OnlyVolunteers/Art/StyleKit_v3/decals_v02/`. Новый прозрачный атлас: два сдержанных абстрактных граффити и две группы обрывков объявлений. Сделан встроенным imagegen по записанному в README запросу, без внешних загрузок и копирования реальных надписей/логотипов.

### Звук

Расширены существующие `AmbienceData`, `AmbienceBaker`, `AmbiencePlayer`; второй ambience manager не создавался. Новый `Assets/OnlyVolunteers/Audio/Resources/Ambience_v19.asset` использует **геометрию зон v18 только для checkpoint P**. Полный v19 bake должен обновить её по финальному плану. Пространственный crossfade 60 м включается только для v19; старые версии сохраняют прежнюю логику.

Использованы имеющиеся `amb_birds` (Hamlet, Elite, Valley), `amb_city` (Downtown), `amb_sea` (Beach), `amb_sea_gulls` (Port, Tramduro); существующие fountain/water emitters не заменялись. В саду есть тихий 3D emitter птиц. Для кур, ворон и далёкой собаки заданы именованные точки; без отсутствующих клипов они молчат. В Rough и тёмном Forest общий весёлый bird-loop выключен. Construction пока без собственного bed, поскольку подходящего звука техники в library нет.

Новые аудиофайлы не скачивались. Громкости и crossfade проверены по runtime-состоянию; субъективное прослушивание баланса человеком остаётся открытым. Полный характер всех районов по звуку пока **не готов**.

## Недостающие звуки и предлагаемые источники

Ниже — список для решения лида, **не разрешение на загрузку**. Страницы лицензий проверены 2026-10-14. Там, где указан Freesound, конкретная запись ещё не выбрана: требуется отбор только CC0 и проверка страницы самого файла. У Freesound есть разные лицензии; источник сам по себе не означает CC0. [Официальное описание лицензий](https://freesound.org/help/faq/).

| Звук | Район | Предлагаемый источник / лицензия |
|---|---|---|
| Карканье вороны | Rough, край Forest | [Crows singing, IgnasD](https://opengameart.org/content/crows-singing), CC0 |
| Ветер, порывы; отдельный шум кроны/поля | Rough, Forest, Valley | [wind1, Luke.RUSTLTD](https://opengameart.org/content/wind1), CC0; шум листвы — Freesound, отбор CC0 |
| Куры и петух | Hamlet | Freesound, запросы `hens clucking`, `rooster`; отбор CC0 |
| Далёкий собачий лай | Hamlet, Rough | Freesound, `distant dog bark`; отбор CC0 |
| Коровы вдали | Hamlet | Freesound, `cow moo distant`; отбор CC0. Резерв: [Farm animals, Secretlondon](https://opengameart.org/content/farm-animals), CC-BY-SA 3.0, отдельное согласование этой лицензии |
| Пчёлы, колокольчики на ветру | Hamlet | Freesound, `bees`, `wind chimes`; отбор CC0 |
| Далёкая автосигнализация, электрический гул мигающего фонаря | Rough | Freesound, `distant car alarm`, `fluorescent buzz`; отбор CC0 |
| Дятел, кукушка, сова | Forest | Freesound, отдельные записи `woodpecker`, `cuckoo`, `owl`; отбор CC0 |
| Голуби; отдельный разговорный фон; музыка вдали | Downtown | Freesound, `pigeons`, `crowd murmur`, музыка без узнаваемого произведения; отбор CC0. Общий `amb_city` уже есть |
| Далёкие голоса отдыхающих | Beach | Freesound, `beach crowd distant`; отбор CC0. Волны и gulls уже есть |
| Судовой гудок | Industrial Port | Freesound, `ship horn distant`; отбор CC0 |
| Кран, стук контейнеров, удары металла | Industrial Port | [Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds), CC0 — кандидат для ударов; запись работы крана отдельно на Freesound CC0 |
| Разбрызгиватели, газонокосилка вдали | Elite Hill | Freesound, `sprinkler`, `distant lawnmower`; отбор CC0. Birds/fountain уже есть |
| Жаворонок, сверчки | Quiet Valley | Freesound, `skylark`, `crickets`; отбор CC0. Generic birds и waterfall уже есть |
| Работа техники, молотки, радио стройки | Construction | Удары — Kenney Impact Sounds CC0; техника и нейтральное радио — Freesound, отбор CC0 |
| Военное радио без личных данных/узнаваемых передач; вертолёт вдали | Tramduro | Freesound, `radio static`, `helicopter distant`; отбор CC0. Gulls уже есть |

## Проверка

| Проверка | Результат / доказательство |
|---|---|
| Unity compile | **PASS** — Unity 6000.5.11f1, unityMCP `read_console(types=error)`: 0 ошибок после правок и после Play |
| Шейдер неба | **PASS** — `shader.isSupported=true`, кадры всех 10 районов через действующий URP проекта |
| Blender geometry | **PASS** — `blender --background --python ArtSource/Props/STYLE_KIT_v3/PILOT_KIT_v02/build_life_kit.py`; `validation_v02.json`: 15/15, 4 596 tris, closed/outward shells, UV, normals, детерминированность, proxies |
| FBX roundtrip | **PASS** — тот же script `--audit`: 15/15; дерево `--tree-repair`: отдельный `export_audit_v03_01.json`, максимальная ошибка bbox меньше 0.000001 м |
| Unity import | **PASS** — `V19PaletteP2.ImportKit()`, 15/15; `Working/Reviews/Map_v19_Pilots/kit_unity_import_v02.txt`, масштаб/оси и bounds в метрах |
| Bare-tree renderer | **PASS после исправления** — корневой renderer и объединённый metre-space mesh v03, повторные кадры Rough; 11 proxies сохранены |
| Play / движение | **PASS** — `Map_Look_v19_Palette_v02`, 600 инициализированных кадров, 10.000 с simulated time; ворона переместилась на 8.765 м. Frame stepping начат только после 18.068 с обычного Play, без стартовых KCC/VehicleEngineAudio NullReference |
| Fog / sky / audio blend | **PASS** — `palette_runtime_check_v02.txt`: Hamlet 95–520 м / sun 1.10; середина дороги 52.170–175.265 / sun .756; Rough 7–65 / .38; Forest 8–70 / .43. Bird bed плавно .200 → .132 → .076 → 0. После камеры глобальные настройки восстановлены: fog 60–400, sun 1.05 |
| Геометрия исходной карты | **PASS** — `palette_geometry_check_v02.txt`: max delta heightmap = 0, изменения позиций tree instances = 0/8 525, сумма весов в центрах всех районов = 1 |
| Защита прежних файлов | **PASS** — `palette_integrity_final_v02.json`: 3 462/3 462 SHA-256 совпали; общие Look, v07, старые сцены, Palette Test v01, Audio Resources и ProjectSettings не изменены |
| Git whitespace, изменённые Audio scripts | **PASS** — `git diff --check -- Assets/OnlyVolunteers/Audio/Editor/AmbienceBaker.cs Assets/OnlyVolunteers/Audio/Scripts/AmbienceData.cs Assets/OnlyVolunteers/Audio/Scripts/AmbiencePlayer.cs` |
| Git whitespace, весь репозиторий | **FAIL, существующий вне задачи** — предупреждения в уже изменённом SausageBuddy controller; эти строки не исправлялись |
| Визуальный просмотр | **PASS как техническая проверка** — проверены парные листы, крупный двор, Rough с исправленным деревом и провода, переход и все остальные районы. Художественное одобрение Феди **PENDING** |
| 15 маршрутов before18_g18_v02 и full v19 | **NOT RUN** — намеренная остановка на checkpoint P по указанию лида |

При refresh редактор один раз штатно закрылся; в логе нет crash. Он повторно открыт на том же проекте, чистой v18, затем работа продолжена. Unity background settings не менялись ни одним вызовом. Существующие предупреждения deprecated API и offscreen RenderTexture не скрывались очисткой Console.

## Файлы кода

Новые:

- `Assets/OnlyVolunteers/Map/LookV3/Palette19/DistrictBlend19.cs`
- `Assets/OnlyVolunteers/Map/LookV3/Palette19/DistrictWeather19V02.cs`
- `Assets/OnlyVolunteers/Map/LookV3/Palette19/DistrictSky19V02.shader`
- `Assets/OnlyVolunteers/Map/LookV3/Palette19/DistrictLife19V02.cs`
- `Assets/OnlyVolunteers/Map/LookV3/Editor/V19PaletteP2.cs`
- `Assets/OnlyVolunteers/Map/LookV3/Editor/V19PaletteP2Life.cs`

Изменены только названные в добавлении системы звука: `Audio/Scripts/AmbienceData.cs`, `Audio/Scripts/AmbiencePlayer.cs`, `Audio/Editor/AmbienceBaker.cs`. Скрипты/ассеты предыдущего palette test v01 сохранены побайтно. Legacy «latest plan» look menu не использовалось.

Для воспроизведения по новым свободным именам нужны шаги ImportKit → V19PaletteTest.Build(revision) → настройки P2 → Place → RefineFirstReview → RepairTreeContacts. Текущие helper paths зафиксированы под проверенный v02; повторный Build на те же имена защищён от перезаписи. Для просмотра результата сборка не нужна — открыть сохранённую сцену.

## Что открыто и откуда продолжать

**Сейчас остановка для одобрения checkpoint P.** Полноценная раздача историй всем дворам и другим районам не сделана. Занавески подготовлены в kit, но ещё не расставлены; огород/пугало, тёплые окна и больше дымящих труб — для полной v19. Нужны отдельные визуальные виды голубей, чаек, пчёл и дальнейшие животные, разнообразие повадок/посадок. Первая Rough стая и бабочки — лёгкая демонстрация механизма. Звуки из списка отсутствуют, загрузок не было.

После одобрения:

1. Взять Unity lock, открыть исходную `Map_Look_v18_Play` и **перезапустить все 15 маршрутов с label `before18_g18_v02`**.
2. Продолжить draft `ArtSource/References/Map/map_plan_v19.py`: компактность, улицы, более сильные овраги/впадины/холмы из обновлённого задания, дороги ≤8%, спокойные дворы и площадки. Пока новых full-v19 данных нет.
3. Перенести одобренную атмосферу и окончательные группы деталей в full v19 builders; запечь police/crowd/ambience/water по финальному плану. Перестроить Bounds/Volumes/field для изменённых границ.
4. Закончить районную жизнь и одобренное аудио; затем полный v19 Play, 15 after routes, проверки и трёхколоночные листы **v17 | v18 | v19**.

Play остановлен. Редактор возвращён в сохранённую `Map_Look_v18_Play`, `dirty=false`, без сохранения Play-изменений. Собственный Unity lock освобождён. Проверка `.meta` новых импортированных ассетов — PASS. Ни commit, ни stage, ни push не выполнялись; WORK_SYNC не редактировался.
