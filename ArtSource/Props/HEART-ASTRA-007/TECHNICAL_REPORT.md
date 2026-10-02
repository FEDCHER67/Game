# Текущая автономная low-poly версия — 2026-10-01, TASK-000031

Геометрия до/после: **19,576 → 1,860 render triangles (-90.5%)**; 1,286 граней, 936 вершин, 13 mesh-объектов. Число граней не равно числу квадов; движок считает треугольники. Открытых рёбер 0, неманифолдных 0 по оценке Blender; допустимые визуальные поверхности отделены от физических коллайдеров.

Три основные формы сокращены до 940 tris; десять поверхностных сосудов пересобраны регулярными шестигранными трубками (920 tris), восемь мелких ветвей удалены. Все 13 мешей закрыты. Сохранены 19 костей, все шесть исторических Blender Actions и текущий игровой heartbeat. Проверены 85 кадров: матрицы костей/контроллеров неизменны, координаты конечны. FBX reimport: 1860 tris, один игровой heartbeat; максимум расхождения границ около 0.00042 мм. Существующие ограничения PROVENANCE сохранены; это авторский рабочий ассет, без новой Unity-интеграции или переоценки прав.

Федя разрешил автономно закончить существующие модели и переслать ракурсы в обычный «Федя чат». Внешний вид этой новой версии проверен ассистентом и сравнительно оценён обычным чатом; это не новая личная приёмка Феди. Платные генерации не запускались. Основные .blend/.fbx и текущие статичные Previews обновлены. Существующие .meta сохранены. Git add . разрешён, commit/push этой задачей не выполнялись.

Проверочные результаты: WORK_SYNC.md; подробные временные JSON/скрипты в C:\Users\Zeyo-ne\.codex\visualizations\2026\09\29\01a0eb71-d153-7041-8dba-611d2f91c52b\autonomous_lowpoly\HEART-ASTRA-007. Не переносить сырые журналы в сторонние сервисы.

## История предыдущего прототипа (старые числа/Working-пути ниже не актуальны)

# HEART-ASTRA-007 — lungs-led organ-family art pass

## Red correction after visual review (2026-09-29)

The approved lungs-led heart had a successful cartoon matte finish, but the main body read too pink. This focused correction starts from that existing heart, not from a rebuilt or historical source. The immediately preceding `.blend`, FBX, report, and six previews are preserved in `Working/BeforeRedCorrection/`. The original deeper-red appearance can still be viewed in `Working/BeforeFamilyPass/front_before.png`.

The myocardium changed from linear RGB `(0.660, 0.095, 0.115)` to **`(0.430, 0.032, 0.044)`**. The arterial trunks changed from `(0.720, 0.190, 0.205)` to `(0.540, 0.067, 0.076)`, so the large upper forms also read red instead of making the whole asset appear pink. The coronary artery and fine branch colours were deepened enough to remain visible on the redder body. Both blue materials were kept unchanged. This is a visual move toward the old red character, not a direct numerical mix of the old and new shaders.

Preview lighting is now closer to neutral white: the key is `(1.0, 1.0, 1.0)`, rim `(0.94, 0.96, 1.0)`, and fill `(1.0, 0.96, 0.93)`. Light energies, broad source sizes, zero light specular contribution, matte roughness, geometry, rig, and animation are unchanged. All six previews were refreshed and visually checked. The body now reads as a **red cartoon heart** while the burgundy and blue details remain separate; no wet or sharp highlights are visible.

Validation after this correction: the final `.blend` reopened in Blender 5.2.1 LTS. A fingerprint of every mesh's vertices, polygons, world transform, modifiers, armature bone geometry, six action names/ranges, and sampled poses at frames 1, 55, and 85 exactly matches the preceding saved heart (`Working/red_correction_validation.json`). The updated FBX reimported with 21 meshes, 19 bones, the active heartbeat, six materials, and unchanged evaluated bounds (`Working/family_pass_validation.json`). Final visual approval remains with the user.

## Source and result

The human-selected `Working/Heart_Astra_007_v6.blend` was edited in place. Its previous version is preserved in `Working/BeforeFamilyPass/Heart_Astra_007_v6.blend`; the original and backup share SHA-256 `2017E336992FD2D45427C7AD74688DB1515DD6106906AAC3A0EFE95E79BBB401`. The approved `../LUNGS-ASTRA-001/` asset and its previews were the colour and surface-finish benchmark. No other organ asset was changed.

The heart silhouette, 21 meshes, 19-bone armature, six Blender heartbeat actions, and camera composition were retained. This pass changes the six existing material slots, their procedural colour ramps, and preview lighting. Fine normal texture strengths were reduced; geometry and rigging were not remodeled. The saved heart remains recognizable as the selected v6 asset.

## Palette and matte response

Colours below are the **current red-corrected** linear RGB shader and FBX diffuse values. The heart has a richer red body than the lungs, warm red trunks, deeper berry coronary arteries, and a controlled blue vein accent. It uses the same clean, stylized colour separation as the lungs.

| Material | Use | Linear RGB | Roughness |
| --- | --- | --- | ---: |
| `01 | Cartoon coral myocardium` | main body and aorta | `(0.430, 0.032, 0.044)` | 0.86 |
| `02 | Soft coral arterial trunks` | separate upper arterial/caval forms | `(0.540, 0.067, 0.076)` | 0.86 |
| `03 | Muted blue great vessel` | large blue arch | `(0.045, 0.115, 0.255)` | 0.87 |
| `04 | Berry coronary arteries` | raised coronary arteries | `(0.205, 0.012, 0.029)` | 0.87 |
| `05 | Soft blue coronary veins` | raised coronary veins | `(0.040, 0.105, 0.230)` | 0.87 |
| `06 | Fine berry branches` | fine arterial branches | `(0.155, 0.008, 0.022)` | 0.87 |

All six Principled materials have metallic, coat, sheen, and Specular IOR Level set to **0**, and Diffuse Roughness set to **0.68**. Their prior roughness values of roughly 0.47–0.53 and coat values of roughly 0.066–0.075 were removed. The procedural roughness link was replaced by a stable 0.86–0.87 value, at least as matte as the approved lungs (0.84–0.86). Colour-ramp variation remains restrained at approximately 94–105% of the representative colour. Bump strengths are capped at 0.018, and the three broad preview lights have specular contribution 0. A front, rear, both three-quarter, side, and closeup render were checked visually: the colour is brighter than the original deep ruby, the raised vessels separate from the body, and there are no narrow wet or plastic highlights.

## Animation and export

The Blender file still contains the six original actions, including the active `Heartbeat | v5 regional amplitude and sculpted return`. The art pass does not alter any heartbeat keyframes or timings; the saved scene remains at 24 fps with frames 1–85. The FBX intentionally exports the active heartbeat clip only, rather than the historical action variants and source `ArmatureAction`.

`HEART-ASTRA-007.fbx` contains 21 evaluated mesh objects, a 19-bone rig, one active heartbeat action, and six materials. The hidden rig had to be made selectable during export; the saved Blender scene retains its previous rig visibility. Blender FBX reimport names the action `Corazon_SourceRig_Heartbeat|Scene` and shifts its frame labels to 2–86. Comparing source frames 1, 55, 85 against imported frames 2, 56, 86 gives matching evaluated bounds to within 0.000001 Blender units on each sorted axis. The animation and pose are therefore preserved despite the frame-label offset.

## Geometry and validation

| File/state | Meshes | Vertices | Triangles | Bones |
| --- | ---: | ---: | ---: | ---: |
| Saved `.blend`, base mesh | 21 | 6,048 | 11,606 | 19 |
| Saved `.blend`, evaluated at frame 55 | 21 | 9,990 | 19,576 | 19 |
| FBX after reimport | 21 | 9,990 | 19,576 | 19 |

The `.blend` reopened in Blender 5.2.1 LTS. The FBX reimported successfully with all 21 mesh names, the 19-bone armature, one heartbeat action, and all six material names, diffuse colours, roughness values, and zero specular values. The frame-1 and frame-85 source poses match; the matching imported frames 2 and 86 match them as well. Detailed counts and bounds are in `Working/family_pass_validation.json`.

Six 1000 × 1000 renders are in `Previews/`: front hero, rear, left three-quarter, right three-quarter, side, and closeup. The closeup deliberately crops the uppermost tube to emphasize the surface palette and coronary details. `Working/BeforeFamilyPass/front_before.png` preserves a visual comparison with the prior look.

**Visual pass:** technically complete and ready for the user's subjective approval. **Rights:** unchanged; see `PROVENANCE.md`. The older `REPORT.md` is the historical pre-pass audit and its statement that the file was not modified applies only to that audit.
