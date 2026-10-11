# G14 — стилизованная вода для StyleKit v3

Дата: **11.10.2026**. Шейдер и материалы подготовлены без запуска Unity. Проверка компиляции шейдера, импорта материалов и вида карты остаётся за лидом.

## Выбор из трёх кандидатов

| Кандидат | Исходник / лицензия | Проверенный код и решение |
| --- | --- | --- |
| **MatrixRex — Uber Stylized Water** | [Репозиторий](https://github.com/MatrixRex/Uber-Stylized-Water/tree/1fdd16c6312611fef7fb248dee86cdd3fd456a1e), commit `1fdd16c6312611fef7fb248dee86cdd3fd456a1e`; [MIT](https://github.com/MatrixRex/Uber-Stylized-Water/blob/1fdd16c6312611fef7fb248dee86cdd3fd456a1e/LICENSE) | **Выбран.** В исходном проекте Unity `6000.0.72f1`, URP `17.0.4`. Есть shallow/deep, intersection foam, shoreline, два движущихся normal-сэмпла, мягкий specular, fresnel/reflection и refraction. В includes уже есть адаптация Forward+ / Cluster Light Loop для Unity 6.1+. Все необходимые package-includes найдены в локальном URP `17.5.0`; новые Unity-пакеты не нужны. |
| Opoi375 — Cartoon Water Advanced | [Репозиторий](https://github.com/opoi375/com.opoi375.cartoon-rendering/tree/fb4c23c0faf39028f8da7bd2078e84bd76d8b403), commit `fb4c23c0faf39028f8da7bd2078e84bd76d8b403`; [MIT](https://github.com/opoi375/com.opoi375.cartoon-rendering/blob/fb4c23c0faf39028f8da7bd2078e84bd76d8b403/LICENSE.md) | Кандидат точно под Unity `6000.5` / URP `17.5.0`: depth gradient, intersection foam, vertex waves, tessellation с fallback. Отклонён для G14: advanced fragment смешивает цвет и шум пены, но не использует animated normal map для lighting/specular; для полного набора G14 пришлось бы дописывать эффект. |
| bmjoy / tojynick — Stylized Water Shader Unity URP | [Репозиторий](https://github.com/bmjoy/Stylized-Water-Shader-Unity-URP/tree/f5e1fdf3ed710d06edb9e0317c33eed99eaef398), commit `f5e1fdf3ed710d06edb9e0317c33eed99eaef398`; [MIT](https://github.com/bmjoy/Stylized-Water-Shader-Unity-URP/blob/f5e1fdf3ed710d06edb9e0317c33eed99eaef398/LICENSE) | Shallow/deep, foam, distortion, vertex waves. Автор подтверждает только Unity 2021, отдельно предупреждает о depth-эффектах ортографической камеры. В главном graph нет exposed normal map. Отклонён: Unity 6 / URP 17 и обязательные animated normals не подтверждены. |

Все три репозитория доступны для чтения и скачивания без аккаунта. Только первый прошёл весь набор требований G14 по исходнику. Unity-компиляция в нашем проекте ещё не подтверждена. Дополнительно проверенный `billtruong003/stylized-toon-world-kit` отклонён по лицензии: README прямо указывает proprietary / no redistribution.

## Что импортировано и адаптировано

`Shader/UberStylizedWater.shader` — существующий опубликованный shader source, без генерации собственного water shader. Сохранены оригинальные эффекты и GUID `8097978abb0800149a7a110f04640a53`. Добавлен один переключатель `_OV_MeshFlow`: существующий normal sampler получает смещение `worldXZ - UV1.xy * time`, поэтому рябь идёт по направлению, записанному в mesh. Смещение защищено `VARYINGS_NEED_TEXCOORD1`; depth/lighting coordinates не изменены. Float добавлен одинаково во все шесть material constant buffers. Подключение авторского CustomEditor снято: используется стандартный inspector Unity.

Импортированы `SubGraphs/CubeMap.hlsl`, `Third Party/URP_ShaderGraphCustomLighting-main/CustomLighting.hlsl`, `Textures/Foam 1.png`, `Textures/Noise 2.png`, их `.meta` и лицензии. Два mask texture сохраняют авторские linear/repeat/mipmap settings. Normal map переиспользован из G13: `Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/8a_water/8a_water_v03_normal.png`, GUID `c0f8cb0ffd91f6d499d674e17656644f`.

`LICENSE` содержит MIT MatrixRex 2025. Вложенные MIT-файлы Cyanilux 2020 и 2021 сохранены для CustomLighting и уже встроенных в shader функций ShaderGraphVariables. `SOURCE_MANIFEST_v01.json` фиксирует commit, upstream Git blob и SHA-256 каждого импортированного исходника, SHA-256 адаптации и использованный normal map. Строка добавлена в `../PROVENANCE.md`.

В Unity import tree нет новых C#-скриптов, DLL, native plugins, development graphs, demo scenes, reflection manager или downloader. Используется готовый `.shader` и две его обязательные local includes. Материалы записаны в Unity YAML; редакторное меню для их создания не требуется.

## Три материала

Все пути начинаются с `Assets/OnlyVolunteers/Art/StyleKit_v3/Materials/`.

| Параметр | `M3_Water_Sea.mat` | `M3_Water_Lake.mat` | `M3_Water_River.mat` |
| --- | --- | --- | --- |
| Shallow | `#40ADE3` | `#40A6D0` | `#68BCE4` |
| Deep | `#3A7CB5` | `#3296C6` | `#40ADE3` |
| `_Water_Depth` | 2.5 | 1.2 | 0.85 |
| Tile основного normal-сэмпла, м | 4 | 5 | 1.5 |
| `_Normal_Scale` | 2.5 | 2 | 6.666667 |
| `_Normal_Strength` | 0.24 | 0.12 | 0.28 |
| `_Normal_Pan` | 0.30 | 0.10 | 0.35 |
| `_Normal_DistanceStrength` | 0.055 | 0.03 | 0.065 |
| `_InterSec_Width` | 0.10 | 0.05 | 0.085 |
| Foam alpha, цвет `chalk #F4EFE6` | 0.85 | 0.60 | 0.72 |
| Animated shoreline | Включён, alpha 0.42 | Выключен | Выключен |
| `_OV_MeshFlow` | 0 | 0 | 1 |
| `_Specular_Spread` | 0.55 | 0.65 | 0.50 |
| Specular intensity multiplier | 0.14 | 0.10 | 0.12 |
| `_Reflection_Strength` | 0.08 | 0.05 | 0.06 |

Основа палитры — `water #2E98D6` и его light/dark из STYLE_BIBLE_v2 §2. Море использует этот светлый/тёмный ramp. Озеро — смесь 75% water ramp и 25% `teal #3F9196`; река — water.light, shallow высветлен 22% chalk. Низкие specular/reflection значения сохраняют чистый цвет и мягкую читаемую поверхность.

Alpha обеих depth colors равна **1**, ShoreFade выключен. Вид воды непрозрачный; шейдер сохраняет авторскую Transparent queue `3000` / `ZWrite Off`, чтобы читать глубину непрозрачного дна до воды. Transparent sorting и объекты, рисуемые прозрачным проходом под водой, нужно проверить в карте. Refraction, caustics, underwater layer и Gerstner vertex displacement выключены. Волны создаёт animated normal map: крупные полигоны карты не требуют дополнительного подразделения.

## Настройки URP — действия лида

1. Выбрать pipeline asset, который реально назначен в **Project Settings → Graphics → Default Render Pipeline**, и проверить overrides в **Project Settings → Quality → Render Pipeline Asset**.
2. В inspector выбранного **Universal Render Pipeline Asset → Rendering → Depth Texture** поставить **On**. Это обязательный toggle для shallow/deep, shoreline и intersection foam.
3. **URP Asset → Rendering → Opaque Texture** нужен только при включении `_ENABLEREFRACTION`. У текущих трёх материалов refraction выключен; включать Opaque Texture ради G14 не требуется.
4. В **Camera → Rendering → Depth Texture** оставить **Use Pipeline Settings** или **On**, а не Off. Для refraction то же правило относится к **Camera → Rendering → Opaque Texture**.

На 11.10.2026 в `Assets/Settings/PC_RPAsset.asset` оба texture toggle уже **On** (`m_RequireDepthTexture: 1`, `m_RequireOpaqueTexture: 1`). В `Mobile_RPAsset.asset` оба Off: для использования G14 на этом quality asset лид включает Depth Texture. URP assets, renderer assets и camera settings в G14 не изменялись. Renderer Feature / planar reflection component для этих материалов не нужны.

Документация URP: [Depth/opaque options pipeline asset](https://docs.unity3d.com/6000.0/Documentation/Manual/urp/universalrp-asset.html), [camera options](https://docs.unity3d.com/6000.0/Documentation/Manual/urp/camera-component-reference.html).

## Подключение к map builder

`materials_v3.json` обновлён в том же schema `OnlyVolunteers.StyleKitV3/1`; изменения сделаны **и в `categories`, и в `entries`**, потому что entries имеют приоритет при чтении.

| Ключ | Материал | Потребитель |
| --- | --- | --- |
| `8a_water` | `M3_Water_Sea.mat` | sea / общий fallback |
| `8a_water_lake` | `M3_Water_Lake.mat` | lake, pond, bog; pool/fountain при отсутствии отдельного preset |
| `8a_water_river` | `M3_Water_River.mat` | river, canal |

Текущий `V3Materials.ReadKitTable()` выбирает наибольшее поле `revision` среди `materials_v3*.json`. Поэтому также добавлен **`materials_v3_v05.json`**, revision **5**, на основе v04. Все non-water categories и entries сохранены из v04; старые numbered manifests не перезаписаны. Base manifest сохраняет свою revision 2 и non-water записи; для builder активен v05. Будущие новые revisions следует наследовать от v05 или переносить эти три water entries.

После импорта G14 лид может вызвать существующий builder в своей editor-сессии с **новым, ещё не существующим именем сцены**, например:

```csharp
OnlyVolunteers.Map.Look.V3.MapLookBuilderV3.Build("Map_Look_v17_G14");
```

Это существующий API проекта. Builder перечитывает manifest и выбирает материалы через `V3Materials.Water(kind)`; менять builder source не требуется. Его обычное меню `OnlyVolunteers/Map/Style v3/Build Map Look v16 (style v3)` сохраняет фиксированную v16, поэтому для сохранения предыдущего deliverable нужен вызов с новым именем. Одна лишь команда `Refresh Style v3 Materials (data swap)` обновляет surface/fallback assets; уже существующим water MeshRenderer нужно явно назначить новые `.mat` или собрать новую сцену.

River ribbon в `V3Water.cs` уже записывает `UV1.xy = direction * speed` в world XZ: river `0.55`, canal `0.22`, mouth `0.30` м/с. С G14 normal-сэмплы перемещаются по этой скорости и направлению. На mesh без этого канала выключить `_OV_MeshFlow`, чтобы lightmap UV не были приняты за скорость. Water renderers должны оставаться без baked lightmap UV/Shadowmask: этот канал занят flow.

## Что делает каждый параметр материала

Это имена стандартного material inspector. World-space UV строится из `XZ * 0.1`; потому основной normal tile = `10 / _Normal_Scale` метров, а второй normal-сэмпл имеет удвоенный размер. `metres_per_tile` в manifest описывает основной tile; shader использует свой `_Normal_Scale`, поскольку `[NoScaleOffset]` maps не читают обычный texture scale.

| Параметр / группа | Действие |
| --- | --- |
| `_Color_Shallow`, `_Color_Deep` | Цвет мелководья / глубины; alpha задаёт видимость дна. В G14 alpha 1. |
| `_Water_Depth` | Характерная вертикальная глубина перехода при WorldSpaceDepth: shallow weight приблизительно `exp(-depth / Water_Depth)`. Не ширина береговой полосы в метрах. |
| `_WorldSpaceDepth` | World-space глубина, стабильная при повороте перспективной камеры; выключение переключает на camera depth. Ортографическую камеру отдельно проверить. |
| `_ShoreFade`, `_ShoreFade_Smoothness` | Прозрачное смягчение линии пересечения; в G14 выключено для сплошного цвета воды. |
| `_DistanceMask_Start`, `_DistanceMask_Fade` | Начало и длина перехода к дальним параметрам; G14 45 / 100 м. |
| `_ENABLENORMAL`, `_Normal_Map` | Включают два движущихся сэмпла normal map; влияют на свет, отражения, distortion. |
| `_Normal_Strength`, `_Normal_DistanceStrength` | Амплитуда normal perturbation вблизи / вдали; дальняя меньше, чтобы не мельтешить. |
| `_Normal_Scale`, `_Normal_Pan` | Размер ряби и скорость стандартных двух встречных diagonal panners. Pan — shader unit, не м/с. |
| `_OV_MeshFlow` | Добавленный G14 toggle: normal UV advected по UV1.xy mesh velocity. Включён только у river. |
| `_Enable_Intersection`, `_InterSec_Color` | Включение пены на берегах и у непрозрачных объектов; цвет и alpha пены. |
| `_InterSec_Width` | Расширение полосы intersection foam по depth mask; безразмерное, зависит от Water_Depth и склона берега. Не фиксированные 0.8 м. |
| `_InterSec_Foam_Mask`, `_InterSec_Foam_Invert` | Mask текстуры пены и инверсия; в G14 используется авторский Foam 1. |
| `_InterSec_Foam_Scale`, `_InterSec_Foam_Tile`, `_InterSec_Foam_Pan` | Масштаб, anisotropic tiling и скорость рисунка пены. |
| `_InterSec_Dissolve`, `_InterSec_Foam_Smooth` | Количество разрывов пены и мягкость их границы. Dissolve 0 даёт чистую полосу. |
| `_InterSec_Foam_Distortion` | Искривление рисунка пены SurfaceDistortion noise. |
| `_InterSec_GradientDissolve`, `_InterSec_Edge_Fade` | Сохраняют пену у пересечения, растворяют и смягчают её внешний край. |
| `_SurfaceDistortion_Map`, `_SurfaceDistortion_Scale`, `_SurfaceDistortion_Strength`, `_SurfaceDistortion_Pan` | Texture, размер, амплитуда и движение noise distortion для foam UV. |
| `_ENABLESHORELINE`, `_SL_Color` | Дополнительные бегущие береговые полосы и их цвет/alpha; только sea. |
| `_SL_WaterDepth`, `_SL_Speed`, `_SL_Ammount`, `_SL_Thickness` | Depth-зона, скорость, количество и толщина shoreline полос. |
| `_SL_CenterMask`, `_SL_CenterMaskFade` | Положение и мягкость ограничения береговых полос. |
| `_SL_Dissolve_Mask`, `_SL_Dissolve`, `_SL_GradientDissolve` | Noise texture, разрывы полос и зависимость dissolve от глубины. |
| `_SL_MaskPan`, `_SL_MaskScale`, `_SL_MaskTile` | Движение и размер shoreline noise. |
| `_SL_EnableTrail`, `_SL_Trail_Fade` | Пенный след после бегущей полосы и его затухание; trail выключен. |
| `_ShadowColor` | Цвет и интенсивность тени на воде; G14 использует мягкий water.dark с alpha 0.12. |
| `_Specular_Color` | Цвет/яркость блика. G14 — слабый chalk tint, без сильных HDR вспышек. |
| `_Specular_Spread`, `_Specular_Hardness`, `_Specular_Size` | Ширина мягкого блика, переход к резкой границе и размер резкого блика. |
| `_Reflection_Strength`, `_Reflection_Fresnel`, `_Reflection_Distortion` | Сила обычного reflection probe/sky, усиление к скользящему углу и normal distortion. |
| `_ENABLEPLANERREFLECTION` | Включает авторский planar reflection branch; выключен, его runtime manager не импортирован. |
| `_ENABLEREFRACTION`, `_Refraction_Strength`, `_Refraction_Distance_Strength`, `_Refraction_Distance_Fade` | Scene-color distortion, near/far intensity и переход; выключено. Включение требует Opaque Texture и alpha ниже 1 для видимого дна. |
| `_Enable_SurfaceFoam`, `_SurfFoam_Color`, `_SurfFoam_Map` | Рисунок пены по всей поверхности и его цвет/mask; в G14 выключен. |
| `_SurfFoam_AlphaBlend`, `_Invert_SurfFoam` | Поведение alpha поверхностной пены и инверсия её mask. |
| `_SurfFoam_Pan`, `_SurfFoam_Scale`, `_SurfFoam_Tile` | Движение и размер поверхностной пены. |
| `_SurfFoam_Edge`, `_SurfFoam_EdgeSmooth` | Толщина и мягкость края её рисунка. |
| `_ENABLE_UNDERWATERLAYER`, `_Underwater_Color`, `_UnderWater_Depth` | Дополнительный слой рисунка под водой, его цвет и offset; выключен. |
| `_ConformToGeometry`, `_UnderWater_ScaleModifier`, `_UnderWater_Start`, `_Underwater_Fade` | Подгонка этого слоя под дно, scale и near/far fade. |
| `_ENABLECAUSTICS`, `_Caustics_Map`, `_Caustics_Strength`, `_Caustics_Depth` | Подводные световые узоры, texture, яркость и depth projection; выключены, caustics textures не импортированы. |
| `_Caustics_Pan`, `_Caustics_Scale`, `_Caustics_Start`, `_Caustics_Fade` | Скорость, размер и distance fade caustics. |
| `_Caustics_Distortion_Map`, `_Caustics_Distortion_Strength`, `_Caustics_Distortion_Scale` | Noise distortion caustics; требуется собственная texture при включении. |
| `_ENABLEWAVE`, `_Wave_Top_Color` | Gerstner vertex displacement и цвет гребня; выключен на текущих крупных map polygons. |
| `_1st_Wave_Length`, `_1st_Wave_Height`, `_1st_Wave_Speed`, `_1st_Wave_Direction`, `_1st_Wave_Sharpness` | Длина, высота, скорость, world XYZ направление и острота первой геометрической волны. |
| `_2nd_Wave_Length`, `_2nd_Wave_Height`, `_2nd_Wave_Speed`, `_2nd_Wave_Direction`, `_2nd_Wave_Sharpness` | Те же параметры второй геометрической волны. |
| `_QueueOffset`, `_QueueControl`, `unity_Lightmaps`, `unity_LightmapsInd`, `unity_ShadowMasks`, `_ParallaxMapping_ca6a44575e7e4a939c2f1426afff27a2_Heightmap_1_Texture2D` | Скрытые служебные поля Unity / сгенерированного shader; вручную не настраивать. |

## Превью и приёмка

[Пример автора](https://raw.githubusercontent.com/MatrixRex/Uber-Stylized-Water/1fdd16c6312611fef7fb248dee86cdd3fd456a1e/docs/assets/images/showcase5.webp). Это существующий upstream showcase, с авторским preset; собственный кадр G14 ещё не снят.

![Upstream showcase](https://raw.githubusercontent.com/MatrixRex/Uber-Stylized-Water/1fdd16c6312611fef7fb248dee86cdd3fd456a1e/docs/assets/images/showcase5.webp)

Лид проверяет импорт без розового error shader; shallow/deep на наклонном берегу, пену у opaque камня/пирса, мягкую animated рябь и движение river → canal → mouth. На текущем mesh flow меняется вдоль русла: у поворотов проверить растяжение UV при длительной работе. Числа берега из STYLE_BIBLE_v2 §3.4 (8 м shallow / 0.8 м foam) должны быть проверены по фактическому склону: depth-based shader не задаёт одинаковую горизонтальную ширину для любого берега.

Проверки G14 пройдены: JSON schema и reader selection, сохранение всех 22 non-water categories/entries из v04, YAML syntax трёх материалов, shader/texture GUID resolution, 23 новых уникальных meta GUID, property/keyword соответствие, шесть одинаковых material constant buffers, guarded flow, 26 локальных HLSL include paths, upstream hashes и полные тексты лицензий. Parameter guide покрывает все exposed/служебные shader properties. Unity compile/render/play-test по условию задачи не запускались.
