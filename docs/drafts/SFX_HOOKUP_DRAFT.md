# Звуковой слой SFX: подключение заглушек (черновик)

Статус: черновик, ветка `cloud/sfx-hookup`. Код написан в облачной сессии без Unity: компиляция, импорт и прослушивание в игре **не проверены**. Громкость, высота и дистанции — первые прикидки, их подбирают на слух в Play mode.

## Что сделано

- `Assets/OnlyVolunteers/Audio/Scripts/SfxLibrary.cs` — ScriptableObject: id события → список AudioClip, диапазон громкости и высоты, 3D (SpatialBlend, Min/MaxDistance), кулдаун на id, приоритет, флаг `Locked`.
- `Assets/OnlyVolunteers/Audio/Scripts/Sfx.cs` — статический помощник `Sfx.PlayAt(id, position, volumeScale, pitchScale)`. Пул AudioSource (по умолчанию 24) создаётся при первом звуке и живёт между сценами. Без аллокаций на вызов. Если голоса заняты, вытесняется самый неважный (по приоритету), при равенстве — самый старый. Один и тот же клип не играет два раза подряд.
- `Assets/OnlyVolunteers/Audio/Scripts/SfxIds.cs` — все id событий константами.
- `Assets/OnlyVolunteers/Audio/Scripts/SfxSurfaces.cs` — поверхность под ногой: фургон (слои Vehicle/VehicleInterior) — металл; Terrain — сильнейший слой splat-карты по имени слоя (`TL_meadow`, `TL_sand`…); остальное — по имени материала (`Look_mat_ground_asphalt__…`). Результат кэшируется на коллайдер/слой.
- `Assets/OnlyVolunteers/Audio/Editor/SfxLibraryImporter.cs` — меню редактора (см. ниже).
- Библиотека: `Assets/OnlyVolunteers/Audio/Resources/SfxLibrary.asset` (создаёт меню). `Sfx` сам загружает её из Resources.

**Каждый хук необязателен.** Нет библиотеки, нет id или у id нет клипов — `Sfx.PlayAt` просто возвращает false, игра идёт без звука. Звук локальный (каждая машина играет то, что видит), сеть не затронута.

Файлы Вадима (Player/, Network/, KCC, Inventory/) **не менялись**. Хуки только в коде карты и фургона: `GreyboxInteractor`, `GreyboxNpc`, `GreyboxNpcBody`, `GreyboxKccPawn` (обёртка над его префабом, сам префаб не тронут), `VanDoor`.

## Как включить (один раз, в Unity)

1. Убедиться, что WAV на месте: `git lfs pull` (в `ArtSource/Audio/SFX_GEN/Out/v01/` должны быть настоящие WAV, а не текстовые LFS-указатели; импортёр их распознаёт и пишет предупреждение).
2. Меню **OnlyVolunteers → Audio → Import SFX_GEN v01 + fill library**.
   - Копирует `ArtSource/Audio/SFX_GEN/Out/v01/*.wav` в `Assets/OnlyVolunteers/Audio/SFX_GEN/` (файл с тем же размером пропускается, .meta сохраняются).
   - Ставит настройки импорта для коротких звуков: моно, Decompress On Load, ADPCM, Preload.
   - Создаёт/заполняет `Audio/Resources/SfxLibrary.asset` по префиксу имени файла и пишет в консоль отчёт по каждому id.
3. Play mode, слушать. Крутить громкость/высоту/дистанции прямо в ассете библиотеки.

## События

| id | Файлы (префикс) | Где срабатывает | Условие |
|---|---|---|---|
| `hit_head` | `punch_bonk_*` (выше тон) | `GreyboxInteractor` (Q) | удар кулаком попал, зона «голова» |
| `hit_torso` | `punch_bonk_*` (ниже тон) | `GreyboxInteractor` (Q) | зона «торс» (и удар от третьего лица) |
| `hit_limb` | `slap_*` | `GreyboxInteractor` (Q) | зона «конечности» |
| `thud_ground` | `body_thud_ground_*` | `GreyboxNpcBody.OnCollisionEnter` | тело упало на что угодно, кроме фургона; громкость по скорости удара: от 1.2 м/с тихо, от 6 м/с в полную (`ThudMinSpeed`, `ThudFullSpeed`); сидящие в кузове не стучат |
| `thud_van_floor` | `body_thud_van_floor_*` | там же | то же, но коллайдер на слое Vehicle (пол, бампер, арки) |
| `door_front_open` | `van_door_open` | `VanDoor.Request` | передняя распашная дверь начала открываться из закрытого положения |
| `door_front_close` | `van_door_close` | `VanDoor.Step` | дверь защёлкнулась, закрывалась с открытости меньше `SlamFrom` (0.6) |
| `door_front_slam` | `van_door_slam` | `VanDoor.Step` | защёлкнулась после полного взмаха (≥ `SlamFrom`) |
| `door_rear_open` / `door_rear_close` | `rear_door_open` / `rear_door_close` | `VanDoor` | то же для задних створок |
| `door_rear_slam` | `van_door_slam` (ниже тон) | `VanDoor` | задняя створка, полный взмах |
| `door_slide_open` / `door_slide_close` | `slide_door_open` / `slide_door_close` | `VanDoor.Request` | сдвижная: звук длиной во весь ход (0.9 с), поэтому играет в начале движения |
| `step_asphalt` / `step_grass` / `step_sand` / `step_metal` | `footstep_asphalt_*` / `footstep_grass_*` / `footstep_sand_*` / `footstep_metal_floor_*` | `GreyboxKccPawn.Update` | шаг по пройденной дистанции на устойчивой земле: ~2.4 шага/с при ходьбе 4.7 м/с, ~3 при спринте; присед тише (`CrouchVolume` 0.4); приземление — один шаг, громкость по скорости падения |
| `npc_scream` | `npc_scream_*` | `GreyboxNpc` | NPC начинает убегать (испугался игрока/фургона), встал после оглушения и бежит, рванул к двери из кузова; не чаще раза в 6 с на NPC (`ScreamCooldown`) |
| `npc_mumble` | `npc_mumble_gibberish_*` | `GreyboxNpc.UpdateDown` | фаза Groggy (вторая часть оглушения), каждые 2.5–5 с (`MumbleInterval`) |
| `npc_whimper` | `npc_whimper_*` | `GreyboxNpc.UpdateSeated` | сидит в кузове, каждые 4–9 с (`WhimperInterval`) |
| `organ_squish` | `organ_squish_*` | `GreyboxInteractor` (E) | подобран предмет с `ItemKind.Organ` (офлайн-подбор) |
| `npc_gasp`, `police_siren`, `phone_buzz`, `cash_register` | `npc_gasp_*`, `police_siren_short`, `phone_buzz`, `cash_register` | — | лежат в библиотеке, ни к чему не подключены |

Правило префикса: имя файла (без расширения) равно префиксу или «префикс_цифры». `footstep_sand_03` попадает в `footstep_sand`; `van_door_open_slow` в `van_door_open` уже не попадёт.

Поверхность шага по ключевым словам в имени (первая подходящая группа побеждает, иначе асфальт):
- металл: metal, iron, steel, rust, van, rail, corrugated, cargo;
- песок: sand, beach, gravel, ballast;
- трава: grass, meadow, lawn, field, forest, hedge, leaves, dirt, moss, soil, mud.

## Как заменить заглушки настоящими звуками

1. Положить WAV/OGG в `Assets/OnlyVolunteers/Audio/Final/` (можно в подпапки) с теми же префиксами, например `punch_bonk_01.wav`, `footstep_grass_01.wav` … `footstep_grass_06.wav`. Количество вариантов любое.
2. Меню **OnlyVolunteers → Audio → Refill library from Audio folders**. Для каждого id, у которого нашлись файлы в `Final/`, они **заменяют** заглушки SFX_GEN; где в `Final/` ничего нет, остаются заглушки.
3. Настройки, подобранные вручную в ассете (громкость, высота, дистанции, кулдаун, приоритет), при перезаполнении сохраняются — меняются только клипы.
4. Нужен особый набор, не по префиксу: перетащить клипы в запись руками и поставить `Locked` — перезаполнение её не тронет.
5. Новая версия заглушек (v02) — по правилу проекта новым номером: `Out/v02/`, а в импортёре поменять `SourceDir`. Старое не перезаписывать.

Новое событие в коде: константа в `SfxIds`, строка в таблице `Events` у `SfxLibraryImporter` (id, префикс, громкость, высота, дистанция, кулдаун, приоритет), вызов `Sfx.PlayAt(SfxIds.X, позиция)` в нужном месте.

## Что проверить в игре

- Всё компилируется; меню создаёт библиотеку, в отчёте у каждого подключённого id есть клипы.
- Удары по голове/торсу/ногам звучат по-разному; падение тела на землю и на пол фургона отличается; прыгающее тело не строчит пулемётом.
- Двери: открытие, мягкое закрытие, хлопок после полного взмаха; сдвижная звучит в такт движению; «нога в двери» (откат после упора) не хлопает.
- Шаги: темп совпадает с ходьбой/спринтом, асфальт/трава/песок/металл фургона различаются на карте; если на Terrain всё звучит одинаково — проверить имена слоёв террейна.
- Толпа: крики при наезде фургона не сливаются в кашу (кулдаун id 0.3 с, 24 голоса).
- Баланс громкости между группами — на слух.

## Ограничения

- На Terrain каждый шаг читает 1×1 пиксель splat-карты (`GetAlphamaps`), это единственная мелкая аллокация на шаг.
- Звук органа привязан к офлайн-подбору (`OfflineWorldItem`) через `GreyboxInteractor`; сетевой подбор (`NetworkInventory`) пока без звука.
- Шаги только у KCC-игрока карты; шагов NPC и других игроков нет.
- Микшера нет: поле `Output` в библиотеке пустое, можно назначить AudioMixerGroup позже.
