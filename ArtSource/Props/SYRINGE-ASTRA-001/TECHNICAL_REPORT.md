# Текущая автономная low-poly версия — 2026-10-01, TASK-000031

Геометрия до/после: **7,649 → 877 render triangles (-88.5%)**; 453 граней, 582 вершин, 21 mesh-объектов. Число граней не равно числу квадов; движок считает треугольники. Открытых рёбер 243, неманифолдных 247 по оценке Blender; допустимые визуальные поверхности отделены от физических коллайдеров.

Первый вариант 948 tris признан обычным чатом слишком ломаным на упорах/юбке/переходе к игле. Rev02 исправляет именно эти зоны: ровная простая призма, регулярные восьмигранные переходы, шестигранная игла; итог 877 tris. Сохранены имена/родители 21 меша, движущийся поршень и наполнение. Все 61 кадр проверены: позы контроллеров неизменны, координаты конечны; FBX reimport совпадает по границам примерно до 0.000056 мм. Исходная прозрачная оболочка, плоские деления и некоторые визуальные острова остаются открытыми, для коллайдеров не использовать. Обновлены PNG и sampled GIF/MP4: новая последовательность содержит 13 реальных состояний за ~2 секунды с фронтального ракурса; историческое описание 122 кадров/двух камер ниже больше не описывает текущий MP4. Проверки каждого кадра геометрии выполнены отдельно. Unity-интеграция не добавлена.

Федя разрешил автономно закончить существующие модели и переслать ракурсы в обычный «Федя чат». Внешний вид этой новой версии проверен ассистентом и сравнительно оценён обычным чатом; это не новая личная приёмка Феди. Платные генерации не запускались. Основные .blend/.fbx и текущие статичные Previews обновлены. Существующие .meta сохранены. Git add . разрешён, commit/push этой задачей не выполнялись.

Проверочные результаты: WORK_SYNC.md; подробные временные JSON/скрипты в C:\Users\Zeyo-ne\.codex\visualizations\2026\09\29\01a0eb71-d153-7041-8dba-611d2f91c52b\autonomous_lowpoly\SYRINGE-ASTRA-001. Не переносить сырые журналы в сторонние сервисы.

Итог обычного чата после просмотра трёх актуальных скринов: Rev02 соответствует общему стилю, случайные заломы ушли; увеличивать полигонаж не рекомендовано. Читаемость тонкой иглы в Unity остаётся будущей проверкой при отдельной интеграции. Это рекомендация, не личная приёмка Феди.

## История предыдущего прототипа (старые числа/Working-пути ниже не актуальны)

# SYRINGE-ASTRA-001 — stylized blood-draw syringe

## Deliverables

- Canonical Blender source: `SYRINGE-ASTRA-001.blend` (saved at frame 31, PARTIAL).
- Unity mesh/animation export: `SYRINGE-ASTRA-001.fbx` (game hierarchy only; no camera or lights).
- Six exterior review views, three state views, `Previews/10_draw_fill.gif`, and the complete two-angle `Previews/11_full_motion_review.mp4`.
- Individual sampled animation frames and side/three-quarter state checks in `Previews/Animation/`.
- Source, rebuild, preview, and validation scripts in `Working/`; untouched Tripo FBX in `Working/Tripo/`.
- Lineage and reference record: `PROVENANCE.md`.

## Shape and movable parts

The approved option A silhouette comes from the supplied uncolored Tripo FBX: broad finger flange, oversized thumb pad, short chamber, tapered hub, and fine needle. The FBX was split into disconnected islands. Useful flange, body collar, hub, thumb, plunger shaft, stopper, lip, and needle surfaces were retained and scaled to a 0.24 m overall length. Three overlapping/open generated chamber surfaces were replaced by a simple clear shell and two slender chamber guards. A central core was added so the thumb pad, shaft, and stopper have continuous geometry in EMPTY, PARTIAL, and FULL, including the section hidden by the finger flange.

The export root is `SYRINGE_ASTRA_001 | root`. `CTRL_PlungerTravel_Z` parents the thumb pad, shaft, connecting core, and four stopper pieces. `SM_BloodVolume_FILL_Z` is a separate bottom-anchored, closed cylinder. The barrel, grips, hub, needle, graduations, and guards remain fixed. The needle is cosmetic geometry; a future Unity pickup collider should be a simple separate compound collider.

## Fill control and animation

`DRAW_FILL` runs at 30 fps over frames **1–61** (2 seconds). Timeline markers: **EMPTY** frame 1, **PARTIAL** frame 31, **FULL** frame 61. The root has a named `fill` authoring property from 0 to 1. The renderable motion is baked onto the two transforms for FBX:

| Normalized fill | Plunger controller local Z | Blood mesh local Z scale | Visible state |
| ---: | ---: | ---: | --- |
| 0 | -0.048 m | 0.000001 m | Empty; blood hidden below the lower lip |
| 0.5 | -0.024 m | 0.02448 m | Half-filled |
| 1 | 0 m | 0.04896 m | Full to the underside of the stopper |

The blood base sits at local Z 0.0792 m and never moves. Its top rises as the plunger retracts. The stopper-to-blood gap is roughly 0.5–1.5 mm across the checked states, avoiding visible intersection. Future runtime code should derive both transforms from one server-authoritative normalized fill value; the FBX's clip is an authoring/example motion, not a network state implementation. At exact zero Unity may disable the blood renderer to avoid a collapsed-mesh edge.

## Materials and art family

The approved lungs, heart, kidney, and brain previews were compared before coloring. Six game materials are exported: cool pale matte plastic, deep slate plastic, charcoal stopper, saturated warm cartoon red blood, restrained tinted clear chamber, and satin needle metal. The opaque surfaces use roughness 0.69–0.90, broad lighting, and no coat. The blood has a modest emission contribution to keep its side readable through the barrel without wet highlights. The chamber uses a single transparent shell at alpha 0.08 in Blender; opaque lips and slim guards preserve its outline. No logo, cross, medical text, or borrowed texture is used.

Unity URP will need an explicit transparent material for the chamber. FBX does not guarantee Blender alpha blend mode, emission, or sorting behavior in URP; verify the chamber/blood overlap against bright and dark gameplay backgrounds after import. The exterior previews are Blender Eevee renders, not Unity shader proof.

## Geometry and validation

The final game hierarchy contains **21 meshes, 4,084 vertices, and 7,649 triangles**. Blender 5.2.1 reopened the saved .blend. The exported FBX reimported in a clean Blender scene with the same 21 mesh names, counts, and six material names; no review camera or lights were present. At frames 1, 31, and 61, reimported FBX motion still raises the blood and thumb pad monotonically. `Working/validation.json` records each pose's bounds and source hash. The original Tripo FBX SHA-256 remains `27730BC9042B9C8F48DBBD41AD2C288C270414C32A7C9820FFD284BAB1B8FF41`.

For the final visual review, the saved .blend was reopened in Blender and **every frame 1–61 was rendered from front and three-quarter cameras**. The resulting 122 frames were inspected as chronological contact sheets. The thumb pad, shaft, connecting core, and stopper remain continuous while the blood rises; the programmatic every-frame check found no backward motion or blood/stopper intersection and a maximum gap of 1.471 mm. The full two-angle sequence is in `Previews/11_full_motion_review.mp4`.

The simple new blood and plunger-core meshes are closed. Several retained Tripo visual islands have boundary and nonmanifold edges inherited from the generated source. They have no visible exterior hole in the reviewed views, but are unsuitable as physics colliders; author simple Unity colliders separately. No Unity prefab, scene, script, package, or project setting was edited, and Unity import/runtime appearance remains to be checked.
