from pathlib import Path
import json,hashlib
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\PISTOL-ASTRA-001')
source=Path(r'C:\Dev\Game\Working\Tripo\pistol_tripo_base.fbx')
download=Path(r'C:\Users\Zeyo-ne\Downloads\pistol_astra_001_tripo_base.fbx')
assert source.read_bytes()==download.read_bytes()
sha=hashlib.sha256(source.read_bytes()).hexdigest()
mesh=json.loads((ROOT/'Validation/mesh_v01.json').read_text(encoding='utf-8'))
fbx=json.loads((ROOT/'Validation/fbx_roundtrip_v01.json').read_text(encoding='utf-8'))
assert mesh['pass'] and fbx['pass'] and mesh['trigger_guard_open']
manifest_path=ROOT/'Source/reference_manifest_Rev01.json'
m=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
m.update(generation_status='completed',slots_cleared=True,source_fbx=str(source),source_fbx_bytes=source.stat().st_size,source_fbx_sha256=sha,source_fbx_byte_identical_to_download=True,final_blend='PISTOL_ASTRA_001_v01.blend',final_fbx='PISTOL_ASTRA_001_v01.fbx',final_triangles=760,mesh_validation='PASS',fbx_validation='PASS',trigger_guard_open=True,final_acceptance='awaiting Claude/Fedya review of v01 previews',paid_extras=False)
manifest_path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'README.md').write_text('''# PISTOL-ASTRA-001 — v01 готов к приёмке

Мультяшный компактный пистолет: чёрный корпус, коричневые накладки с обеих сторон, без надписей и логотипов. Чистые цвета, слегка пухлые формы. **760 треугольников**, бюджет 400–800. Спусковая скоба имеет физическое сквозное отверстие; крючок расположен внутри.

## Готовые файлы

- `PISTOL_ASTRA_001_v01.blend` — редактируемый источник; исходная сетка Tripo сохранена в скрытой коллекции.
- `PISTOL_ASTRA_001_v01.fbx` — один объект `Item_Pistol`, семь замкнутых частей, текстура включена.
- `Textures/PISTOL_basecolor_v01.png` — чистый локальный атлас 1024×1024, упакован в blend.
- `Previews/01_front_v01.png` … `07_hero_v01.png` — шесть ортографических видов и общий ракурс.
- `Validation/mesh_v01.json`, `fbx_roundtrip_v01.json` — обе проверки PASS, включая открытое отверстие скобы.

Размеры: 19 × 3.872 × 13.753 см (X/Y/Z), origin снизу по центру; FRONT = −Y, дуло = −X. Smooth shading, резкие переходы и weighted normals.

Rev01 утверждён Claude от имени Феди 05.10.2026. Выполнена одна генерация Tripo за ровно 100 кредитов: **280 → 180**. Smart Mesh, quads, P2.0, target500; все четыре слота очищены. Исходный FBX сохранён без изменений в `C:/Dev/Game/Working/Tripo/pistol_tripo_base.fbx`. Локальная доводка и снижение полигонов в Blender; повторных генераций или платных опций нет.

V01 показан для приёмки; окончательное принятие модели ещё ожидается. Коммитов и правок WORK_SYNC.md нет.
''',encoding='utf-8')
(ROOT/'PROVENANCE.md').write_text(f'''# PISTOL-ASTRA-001 — происхождение Rev01 / v01

05.10.2026. Четыре отдельных PNG 1254×1254 созданы в обычном ChatGPT, чат «Федя чат»: {m['conversation']}. FRONT — новый запрос; LEFT от выбранного FRONT; RIGHT от LEFT; BACK от FRONT. Все Download сохранены побайтно, без отражения, обрезки, масштабирования или ретуши. Имена, размеры и SHA256 — в `Source/reference_manifest_Rev01.json`; четыре `Source/chatgpt_*_Rev01_proof.png` подтверждают изображения в браузере.

Конвенция: FRONT широкая сторона, дуло влево; LEFT дульный торец; RIGHT закрытый задний торец; BACK противоположная широкая сторона, дуло вправо. Небольшая вариация кадрирования торцов сохранена в исходниках и была раскрыта до утверждения. Точный Rev01 явно утверждён здесь Claude от имени Феди 05.10.2026.

## Tripo

- Модель: `2892f17d-81c7-4952-948d-ae52cae4c02c`.
- Multi-view / Smart Mesh / quads / P2.0, target500. Кнопка Create ровно100; одна генерация, баланс280→180.
- Результат интерфейса:693 faces /583 vertices, экспорт FBX без исходной текстуры; фактический FBX содержит1118 треугольников.
- Все четыре входных слота очищены. Снимки настройки, результата, очистки и экспорта находятся в `Source/`.
- Исходное скачивание: `{download}`; неизменённая копия: `{source}`.
- Размер {source.stat().st_size} байт, SHA256 `{sha}`. Побайтная идентичность проверена.

## Локальный Blender

Исходная форма корпуса, скобы, двух накладок, двух прицелов, крючка и дульного элемента сохранена. Закрыты открытые торцы отдельных исходных деталей; скоба до обработки уже была замкнутой поверхностью со сквозным отверстием и не заполнялась. После закрытия торцов1142тр.; локальное снижение до760тр. Чистые чёрно-коричневые материалы, Smart UV, локальная запечённая текстура1024, smooth/sharp/weighted normals. Экспортируется только итоговый объект; неизменённая исходная геометрия также оставлена скрытой в blend.

Процедура: `Scripts/polish_v01.py`. Валидация: `Scripts/validate_export_v01.py`; повторный импорт FBX подтвердил760тр., UV/текстуру, замкнутость и открытое отверстие скобы. Платной ретопологии, новых генераций или дорогих опций не было. V01 ожидает приёмки Claude/Феди. Без коммитов/WORK_SYNC.
''',encoding='utf-8')
(ROOT/'REPORT.md').write_text('''# PISTOL-ASTRA-001 — отчёт v01, 05.10.2026

## Итог

**760 треугольников — PASS**, бюджет400–800. Один объект,392 вершины,503 полигона,7 частей. Нулевые nonmanifold/boundary edges и нулевые вырожденные грани. Координаты и UV конечны, положительный объём. Размеры19×3.872×13.753см, origin снизу по центру, FRONT−Y. Чистый атлас1024 упакован в blend и экспорт FBX.

## Спусковая скоба

Отверстие оставлено физически сквозным. Девять лучей через свободную часть скобы проходят без попаданий, как в итоговой сетке, так и после повторного импорта FBX. Характеристика Эйлера основного корпуса0 подтверждает отверстие; остальные шесть частей имеют2. На широких видах и общем ракурсе просвет виден вокруг спускового крючка.

## Доводка и осмотр

Исходная форма Tripo сохранена: корпус, накладки с двух сторон, крючок, дуло и прицелы. Закрыты32 исходные граничные кромки отдельных деталей (скоба исходно замкнута), затем локальное снижение1118→1142→760тр. Чистые материалы и локальный атлас, сглаживание с контролируемыми резкими переходами. Все7 превью просмотрены: противоположные широкие стороны согласованы, передний торец с дулом, задний закрыт, коричневые накладки с двух сторон; сверху корпус ровный, мелкие низкополигональные грани намеренно сохранены.

`Validation/mesh_v01.json`: PASS. `Validation/fbx_roundtrip_v01.json`: PASS —760тр.,7 замкнутых частей, UV,1024px текстура, размер19см и открытая скоба. Unity-импорт в этой задаче не выполнялся.

## Расход и статус

Rev01 явно утверждён Claude/Федей. Одна генерация Tripo Smart Mesh/quads/P2.0 target500, Create100:280→**180**. Слоты очищены, исходный FBX сохранён побайтно в Working/Tripo. Платных опций, повторов и платной ретопологии нет. V01 готов и показан на приёмку; финальное принятие ожидается.

Файлы: `PISTOL_ASTRA_001_v01.blend`, одноимённый FBX; `Previews/01_front_v01.png` … `07_hero_v01.png`. Коммитов/правок WORK_SYNC.md нет.
''',encoding='utf-8')
batch_path=ROOT.parent/'TRIPO_BATCH_2026-10-05.md'
b=batch_path.read_text(encoding='utf-8-sig')
b=b.replace('| 5 | PISTOL-ASTRA-001 | 400–800 | Four separate Rev01 views ready in ordinary ChatGPT:1254×1254 unchanged PNGs, original-download hashes verified, four browser-proof screenshots. FRONT/BACK wide opposite sides; LEFT muzzle, RIGHT closed rear. Exact images shown here, awaiting explicit pack approval. No Tripo generation or expenditure; balance280. |','| 5 | PISTOL-ASTRA-001 | 400–800 | Rev01 explicitly approved05.10 by Claude on behalf of Fedya. One Smart Mesh/quads/P2.0 generation, target500, Create100:280→180; model2892f17d-81c7-4952-948d-ae52cae4c02c. Four slots cleared; unchanged FBX in Working/Tripo. Proposed PISTOL_ASTRA_001_v01.blend/FBX760 triangles: original frame/grips/trigger/muzzle/sights retained, clean1024px atlas, seven closed parts, smooth/sharp/weighted normals. Physical trigger-guard opening preserved; nine clear rays and genus check, mesh/FBX roundtrip PASS. Seven previews inspected; v01 awaits final acceptance. |')
b=b.replace('New-party expenditure **400**, current balance **280** (confirmed at completed TASER generation). Two remaining planned generations cost200; planned balance80.','New-party expenditure **500**, current balance **180** (confirmed at completed PISTOL generation). One remaining planned SURGLAMP generation costs100; planned balance80.')
batch_path.write_text(b,encoding='utf-8')
print(json.dumps({'source_hash':sha,'source_bytes':source.stat().st_size,'triangles':760,'mesh_pass':mesh['pass'],'fbx_pass':fbx['pass'],'balance':180}))
