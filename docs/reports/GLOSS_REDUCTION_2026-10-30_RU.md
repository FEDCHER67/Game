# Блеск моделей −67 % (часть 1 брифа, 30.10.2026)

Федя: «все модели примерно на 67 % менее блестящие». Сделано для всех живых сцен сборки (MainMenu_v01, Map_W85_Play_v02, NetworkTest)
и всего, что они спаунят. Игрок (PlayerSausage_W86, материалы PLAYER_*) и Player/Hands не тронуты: их делает полностью матовыми другой
агент (SausageMatteV01). Часть 2 (швы одежды) не делалась.

## Правило

- Новое = база × **0.33** (`OvGlossV01.Factor`). Управляющий параметр везде `_Smoothness`: URP Lit и шейдеры проекта Palette19 / V3 Surface /
  T1_ChainLinkVeil / GlassAerial19V01 (с картой metallic/gloss или mask: smoothness = A-канал × скаляр, поэтому меняется только скаляр,
  текстуры не правились — ничего не уменьшено дважды).
- Стекло (имя содержит glass / window / windshield / lens, но не frame) × **0.55** (`OvGlossV01.GlassFactor`): при ×0.33 стекло башен
  (0.95 → 0.31) становится атласной синей облицовкой без неба; при ×0.55 (0.52) остаётся мягкое отражение неба и всё равно заметно меньше
  зеркальности. Сравнение: `compare_towers_glass_variants.png`.
- Глаза (Eye_White, Pupil, Eye_Shine) сохраняют влажный блик — как у игрока в SausageMatteV01.
- Не менялись: metallic, specular highlights, environment reflections, emission, прозрачность, шейдеры/ключевые слова, пресеты, отражения.
  Проверено диффом 1806 материалов до/после: ни одного изменения кроме `_Smoothness`, все отношения ровно 0.33 или 0.55.

## Семейства: было → стало, где

| Семейство | Было | Стало | Где применено |
|---|---|---|---|
| Фасады, правила W86LookV01 (runtime-копии) | камень .24±.06, штукатурка .20±.05, кирпич .16±.04, бетон .18±.03 | .079±.02, .066±.017, .053±.013, .059±.01 | `W86LookV01.DefaultRules` ×G |
| Даунтаун-«sheen» +0.14 | Downtown-кирпич/камень до .32 | снят (= обычные .04–.07) | `W86LookV01`: boost = 0, поле `DowntownBoost` оставлено только для загрузки сцены |
| Стекло (правило W86Look) | .95 | .52 | ×GG |
| Металлы (W86Look) | galv/chrome .55, Metal_Dark .42, Metal_Paint/Window_Frame/trapez .45, flat_gloss .70 | .18, .14, .15, .23 (metallic .7/.55/.15 без изм.) | ×G |
| Пластик, машины-реквизит, техника (W86Look) | white_plastic .50, SK_Palette-машины .62, MW86_Machines .45 | .165, .20, .15 | ×G |
| W86 машины (MAT_W86_VehiclePalette_v01) | скаляр .9 над картой v02: краска .31, хром .45, стекло .77, резина .14 | скаляр .297: .10, .15, .25, .04 | `W86VehiclesV01.EnsureMaterial` + манифест; карта v02 не менялась |
| Мастерская WS86_* (19 .mat) | ср. .28, стекло .92 | ср. .10, стекло .51 | `W85PlayIntegrator` (сборка материалов) + манифест |
| Аптека PH86_* (20 .mat) | ср. .29, стекло .90 | ср. .10, стекло .495 | `W85PlayIntegrator.Pharmacy` + манифест |
| Фургон игрока (Van/Materials 12, Paint/Generated 5) | ср. .30, VAN_Glass .85 | ср. .11, .47 | манифест. Кузов `OnlyVolunteers/Paint/Body` — ламберт без блика, снижать нечего |
| Толпа NPC (SausageBuddy, 976 встроенных в FBX материалов) | кожа .50, нос .55, одежда/аксессуары ср. .37, очки-линзы .94 | .165, .18, ср. .12, .52 | `GlossFbxPostprocessorV01` при импорте |
| Механик (FBX) | кожа .50, ткань .08, ключ .64, масло .55 | .165, .026, .21, .18 | то же |
| Пропы W86 (MapW86_v01, 103 FBX-материала) и прочие FBX (StyleKit, TextureTest, Vehicles, Operation, Scalpel, Table) | ср. .44–.50 | ср. .146–.165 | то же |
| .mat карты: MapTextures T1/T2 (104), TextureTest (97), W85Build/Generated (62), VadimLocal (66), Art/Map, GrandpaYard, StyleKit, органы, операция, тест/сеть | ср. .05–.45, маски-множители 1.0 | ×0.33 (маски 1.0 → .33), стекло ×0.55 | манифест (469 .mat) |
| Runtime-материалы кода | операция `OperationVisuals.Lit` (кожа .30, кровь .55, мешки .70…); каркас фургона: рейл .5, стропы .2, мягкая обивка .08; стяжка .55; запасной реквизит NPC .5 | ×0.33: .10, .18, .23…; .165, .066, .026; .18; .165 | `OperationVisuals`, `VanCargoFitoutV01.Tint`, `CaptureTieVisuals`, `NpcAnimDriver` |

Без контроля блеска (проверены, не менялись): листва/трава (GenericFoliage, FoliageNearFade, IndirectGrass), вода, небо, туман/дымка,
террейн (слои уже smoothness 0), частицы/unlit, `Standard` (KCC ExampleCharacter, не рендерится в URP), пакетный Lit.mat (read-only).
Дым механика (MechanicPuff, .12 → .04) попал в манифест как обычный Lit.

## Почему не накапливается

- **.mat — манифест** `Assets/OnlyVolunteers/Art/Gloss/gloss_manifest_v01.json`: путь → baseline + target (абсолютный). Применение:
  значение = target → пропуск; = baseline → ставится target; иное → «drift», не трогается. Повторный прогон: «0 set, 469 already on target»;
  повторный capture: «+0».
- **Страж импорта** `GlossMatGuardV01` (OnPostprocessAllAssets, синхронно): если билдер карты/пропов перезапишет материал из списка старой
  константой, сразу возвращает target. Тест: WS86_concrete записан 0.22 и сохранён → тут же 0.0726 (в файле тоже).
- **FBX** — `GlossFbxPostprocessorV01` в `OnPreprocessMaterialDescription` после URP (порядок 1000): каждый импорт начинается с FBX, ×0.33
  ровно один раз. Двойной реимпорт: кожа 0.165 → 0.165. Legacy ImportStandard — через OnPostprocessMaterial, для режима description он
  пропускается (без двойного применения).
- **Билдеры** W86VehiclesV01 / мастерская / аптека умножают сами → пересобранный материал = target манифеста; их новые материалы capture
  больше не берёт (`BuilderRoots`), чтобы не уменьшить дважды.
- **W86LookV01** пишет абсолютные значения в свежие копии исходных материалов — повтор не накапливается; копий стало 62 вместо 64
  (ушли отдельные Даунтаун-копии), без копии на объект.
- Смена коэффициента: меню «Gloss v01: re-target from baselines» — пересчёт от baseline, не от текущего (так ставилось стекло 0.55).
- Меню: `OnlyVolunteers/Art/Gloss v01: capture new live materials + apply` — только для НОВЫХ живых материалов (вручную, осознанно).

## Изменённые файлы

Новые: `Assets/OnlyVolunteers/Art/Gloss/OvGlossV01.cs`, `Art/Gloss/Editor/GlossReductionV01.cs`, `Art/Gloss/gloss_manifest_v01.json`.
Правки: `Map/W85Build/Runtime/W86LookV01.cs`, `Map/W85Build/Editor/W86VehiclesV01.cs`, `W85PlayIntegrator.cs`, `W85PlayIntegrator.Pharmacy.cs`,
`Operation/Stage1/Scripts/OperationVisuals.cs`, `Vehicles/Van/Scripts/VanCargoFitoutV01.cs`, `Characters/Npc/Scripts/NpcAnimDriver.cs`,
`Capture/Scripts/CaptureTieVisuals.cs`; 469 .mat (только `_Smoothness`); реимпорт ~1200 FBX (встроенные материалы, .meta не менялись).

## Сравнение (одинаковые камера, 13:30 по часам неба, экспозиция, качество; Play)

`Working/Reviews/Gloss_2026-10-30/`: `compare_downtown.png` (улица с башнями), `compare_towers.png`, `compare_facades.png`,
`compare_car.png`, `compare_npc.png` (4 типа толпы крупно), `compare_workshop.png` (интерьер + механик), `compare_towers_glass_variants.png`;
исходники `before_*.png` / `after_*.png`, `variant_*_all_x033.png`.

## Открыто

- Стекло W86 машин в одной упакованной карте под одним скаляром → ×0.33 (0.25), а не 0.52 как у зданий. Если нужно одинаково — новая
  ревизия карты `W86_VehicleSurface_v03` с пер-ячеечными множителями.
- «67 %» — по параметру; визуально NPC на дистанции меняются мягко, стены почти не менялись (они и были матовые), главное — стекло,
  металл, пол мастерской, кожа/костюмы вблизи. Приёмка глазами Феди в игре не проводилась.
- Полная пересборка карты (MakeV02 / BuildV02Silent) не запускалась: устойчивость проверена тестом стража и кодом билдеров.
- FBX-постпроцессор действует на все FBX в Assets (кроме игрока/рук/глаз) — одна политика и для неживых моделей. Любое изменение его
  версии вызывает реимпорт всех ~1200 FBX (~30 с). Новые живые .mat в манифест сами не попадают — после добавления запустить capture.
- Сохранения: папка LocalLow скопирована, автосейв 0, слот тестовый; хэши всех файлов до/после трёх Play-сессий совпали.
