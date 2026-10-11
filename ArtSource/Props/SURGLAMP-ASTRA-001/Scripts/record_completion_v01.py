import hashlib, json
from pathlib import Path

ROOT = Path(r'C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001')
source = Path(r'C:\Dev\Game\Working\Tripo\surglamp_tripo_base.fbx')
download = Path(r'C:\Users\Zeyo-ne\Downloads\surglamp_astra_001_tripo_base.fbx')
assert source.read_bytes() == download.read_bytes()
sha = hashlib.sha256(source.read_bytes()).hexdigest()
mesh = json.loads((ROOT / 'Validation/mesh_v01.json').read_text(encoding='utf-8'))
interfaces = json.loads((ROOT / 'Validation/interfaces_v01.json').read_text(encoding='utf-8'))
export = json.loads((ROOT / 'Validation/fbx_roundtrip_v01.json').read_text(encoding='utf-8'))
assert mesh['pass'] and interfaces['pass'] and export['pass']
manifest_path = ROOT / 'Source/reference_manifest_Rev02.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
manifest.update({
    'generation_status': 'completed',
    'tripo_model_id': 'a99e975c-520d-4d22-9c06-b5b030ecb78b',
    'balance_before_generation': 180,
    'all_four_reference_slots_cleared': True,
    'source_fbx': {'file': str(source), 'original_download': str(download),
                   'bytes': source.stat().st_size, 'sha256': sha, 'byte_identical': True,
                   'triangles': 1926, 'vertices': 1011, 'polygons': 1119, 'nonmanifold_edges': 50},
    'tripo_proofs': ['Source/tripo_settings_create100.png', 'Source/tripo_result_balance80.png',
                     'Source/tripo_slots_cleared.png', 'Source/tripo_export_fbx.png'],
    'final_blender_revision': 'v01',
    'final_triangles': 1168,
    'mesh_validation_pass': True,
    'interface_validation_pass': True,
    'fbx_roundtrip_pass': True,
    'paid_extras': False,
    'final_acceptance': 'awaiting visual acceptance; reference Rev02 approved by Fedya',
    'review_scene': r'C:\Dev\Game\Working\Reviews\TRIPO_PARTY_2026-10-05_v01.blend',
})
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

readme = '''# SURGLAMP-ASTRA-001 — операционная лампа v01

Мобильная лампа в чистом мультяшном стиле: белый круглый плафон, голубой кант и кремовый рассеиватель, металлическая вертикальная стойка, белый гибкий кронштейн, четыре белые опоры и четыре чёрных колёсика.

## Готовые файлы

- `SURGLAMP_ASTRA_001_v01.blend` — финальный объект `Prop_SurgicalLamp`, упакованная текстура, свет и камера для просмотра; исходник сохранён в скрытой коллекции.
- `SURGLAMP_ASTRA_001_v01.fbx` — только финальный объект, текстура встроена.
- `Textures/SURGLAMP_basecolor_v01.png` — чистый атлас 1024×1024.
- `Previews/01_front_v01.png` … `07_hero_v01.png` — семь видов 800×800.
- `Validation/mesh_v01.json`, `interfaces_v01.json`, `fbx_roundtrip_v01.json` — PASS.

Финал: **1 168 треугольников**, 612 вершин, 14 замкнутых частей в одном объекте; бюджет 600–1200. Размеры около 0,647×0,805×1,700 м. Начало координат на земле у центра основания, FRONT = −Y. Сглаженные поверхности, резкие границы и взвешенные нормали. Стойка выровнена; опоры и колёсики перестроены локально, все соединения проверены.

## Генерация и приёмка

Точный комплект `TripoViews/Rev02/` утверждён Федей здесь 05.10.2026 ответом «ок». FRONT повторно использован из Rev01 без изменений; LEFT/RIGHT/BACK — исправленные Rev02. Отклонённый LEFT Rev01 сохранён.

Одна Tripo multi-view / Smart Mesh / quads / P2.0 генерация, целевое значение 1000 граней; Create ровно 100 кредитов, баланс **180 → 80**. Все четыре слота очищены. Исходный FBX без изменений: `C:/Dev/Game/Working/Tripo/surglamp_tripo_base.fbx`. Повторных генераций и платных операций не было.

Финальная модель v01 подготовлена для визуальной приёмки. Общая сцена только последней партии: `C:/Dev/Game/Working/Reviews/TRIPO_PARTY_2026-10-05_v01.blend` — дубинка v02, бита v01, сковородка v03, электрошокер v02, пистолет v01 и эта лампа v01. В общей сцене размеры нормализованы для удобного просмотра; производственные размеры находятся в исходных файлах.
'''
(ROOT / 'README.md').write_text(readme, encoding='utf-8')

provenance = f'''# SURGLAMP-ASTRA-001 — происхождение v01

## Изображения

05.10.2026, обычный ChatGPT в браузере, чат «Федя чат»:
https://chatgpt.com/g/g-p-6aadbaaa21c081918dcf9006013794cd-only-volunteers/c/6aadbae4-9db8-83eb-b549-cced1b1c33b2

FRONT создан новым запросом. Первый запрос завершился ошибкой; штатный повтор дал FRONT Rev01. LEFT Rev01 от этого FRONT отклонён из-за ракурса три четверти. LEFT Rev02 получен от FRONT, RIGHT Rev02 от LEFT Rev02, BACK Rev02 от FRONT. FRONT Rev01 перенесён в комплект Rev02 побайтно.

Четыре PNG 1254×1254 скачаны штатной кнопкой Download и сохранены без локального зеркалирования, обрезки, ретуши, масштабирования или изменения фона. Оригинальные имена, SHA256, размеры и снимки браузера — `Source/reference_manifest_Rev02.json`. LEFT Rev01 и его снимок сохранены как отклонённые. Проекции художественные, с небольшими различиями кадрирования.

## Tripo

Rev02 явно утверждён Федей здесь 05.10.2026: «ок». Одна multi-view / Smart Mesh / quads / P2.0 генерация, целевое значение 1000 граней, Create ровно 100; баланс 180 → 80. Model ID: `a99e975c-520d-4d22-9c06-b5b030ecb78b`. Результат в интерфейсе: 1119 граней, 1011 вершин, Quad. Все четыре слота очищены.

Экспорт FBX, пресет Blender: оригинальная загрузка `C:/Users/Zeyo-ne/Downloads/surglamp_astra_001_tripo_base.fbx`; побайтная копия `C:/Dev/Game/Working/Tripo/surglamp_tripo_base.fbx`.

- Размер: {source.stat().st_size} байт.
- SHA256: `{sha}`.
- Совпадение с загрузкой: подтверждено.
- Снимки настроек, результата, очищенных слотов и экспорта: `Source/tripo_*.png`.

## Локальная доводка

Blender 5.2.1 LTS. Сохранены исходный плафон и непрерывный кронштейн/стойка/ступица; границы замкнуты, источник сохранён в скрытой коллекции. Стойка выправлена, асимметричные опоры и парные висящие шины заменены четырьмя одинаковыми опорами с закреплёнными колёсиками. Снижение полигонов и ремонт выполнялись локально, без повторной генерации и платной ретопологии.

Чистые цвета и голубой кант восстановлены локальными материалами и запечены в атлас 1024×1024; атлас упакован в Blend и встроен в FBX. Финал 1168 треугольников. Семь превью, проверка сетки/соединений и повторного импорта FBX — PASS. Приёмка финальной модели ожидается; приёмка ракурсов подтверждена.
'''
(ROOT / 'PROVENANCE.md').write_text(provenance, encoding='utf-8')

report = '''# SURGLAMP-ASTRA-001 — отчёт v01, 05.10.2026

## Выполнено

Rev02 утверждён Федей. Одна обычная multi-view генерация Smart Mesh / quads / P2.0, Create 100; баланс 180 → **80**. Четыре слота очищены; FBX сохранён без изменений. Повторных генераций и платных опций нет.

В исходнике 1926 треугольников, 1011 вершин, 1119 полигонов и 50 незамкнутых рёбер. Исходная стойка наклонена, основание асимметрично, восемь шин отделены от опор. Локально выправлена стойка, сохранён плафон и непрерывный кронштейн, закрыты границы, основание перестроено с четырьмя закреплёнными колёсиками. Выполнено снижение полигонов, сглаживание и запекание чистого атласа.

## Итог

| Параметр | Результат |
| --- | --- |
| Треугольники | **1168**, бюджет 600–1200 |
| Вершины / полигоны | 612 / 640 |
| Объект / замкнутые части | 1 / 14 |
| Незамкнутые или неманифолдные рёбра | 0 |
| Грани нулевой площади | 0 |
| Размеры | 0,647 × 0,805 × 1,700 м |
| UV / атлас | 1 UV, 1024×1024, упакован и встроен |
| Затенение | Smooth, sharp edges, weighted normals |
| Колёса | 4, на земле, с креплениями к опорам |

## Проверки

- `Validation/mesh_v01.json`: PASS — бюджет, конечные координаты, ненулевая площадь, положительный объём, замкнутая сетка, высота.
- `Validation/interfaces_v01.json`: PASS — корни четырёх опор внутри ступицы, перекрытие опора/крепление около 13,6 мм, крепление/шина около 20,4 мм, зазор колёс до земли 0; точки кронштейна входят в плафон.
- `Validation/fbx_roundtrip_v01.json`: PASS — после повторного импорта 1168 тр., 14 замкнутых частей, корректные UV, конечные координаты и атлас 1024×1024.
- Семь превью осмотрены: front/back/left/right/top/bottom/hero. Стойка вертикальна, четыре одинаковые опоры, замкнутый задник плафона, кремовый рассеиватель и голубой кант спереди.

## Передача

`SURGLAMP_ASTRA_001_v01.blend`, `.fbx`, `Textures/`, `Previews/`, отчёты и происхождение готовы. Финальная v01 ожидает визуальной приёмки; автоматические проверки пройдены. Импорт в Unity в эту задачу не входил и не проверялся.

Обзор последней партии: `C:/Dev/Game/Working/Reviews/TRIPO_PARTY_2026-10-05_v01.blend`. В нём ровно шесть финальных сеток, 4016 треугольников суммарно. Масштаб отдельных экспонатов изменён только в обзорной сцене для читаемого просмотра; исходные модели сохранены.
'''
(ROOT / 'REPORT.md').write_text(report, encoding='utf-8')

batch_path = ROOT.parent / 'TRIPO_BATCH_2026-10-05.md'
batch = batch_path.read_text(encoding='utf-8-sig')
lines = batch.splitlines()
for index, line in enumerate(lines):
    if line.startswith('| 6 | SURGLAMP-ASTRA-001'):
        lines[index] = '| 6 | SURGLAMP-ASTRA-001 | 600–1200 | Rev02 explicitly approved05.10 by Fedya: «ок». One Smart Mesh/multi-view/quads/P2.0 generation, target1000, Create100:180→80; model a99e975c-520d-4d22-9c06-b5b030ecb78b. Four slots cleared; unchanged source FBX in Working/Tripo. SURGLAMP_ASTRA_001_v01.blend/FBX1168 triangles: retained source head and continuous gooseneck/stand/hub, straightened shaft, four identical feet and seated casters, clean packed1024px atlas, smooth/sharp/weighted normals. Mesh/interface/FBX roundtrip PASS, seven previews inspected. Final v01 awaits visual acceptance. |'
    elif line.startswith('New-party expenditure **500**'):
        lines[index] = 'New-party generation complete: six single100-credit generations, total **600**, balance **680 → 80**. No repeats or paid options. BATON494 + BAT476 + PAN558 + TASER560 + PISTOL760 + SURGLAMP1168 = **4016 triangles**. First five models accepted; SURGLAMPv01 ready for final visual acceptance. Fedya requested only this six-model party for Blender review: `C:/Dev/Game/Working/Reviews/TRIPO_PARTY_2026-10-05_v01.blend` (six final meshes, normalized display scales; original production sources unchanged).'
batch_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

review_readme = '''# Обзор последней партии Tripo — 05.10.2026

Откройте `TRIPO_PARTY_2026-10-05_v01.blend`: только последние версии дубинки v02 (494 тр.), биты v01 (476), сковородки v03 (558), электрошокера v02 (560), пистолета v01 (760), лампы v01 (1168). Ровно шесть сеток, суммарно 4016 треугольников. Каждая модель в отдельной именованной коллекции; камера, свет и подписи в коллекции «Обзор».

Для удобного осмотра размеры экспонатов нормализованы. Это обзорная сцена: производственные размеры и исходные файлы моделей сохранены, их пути и точные версии перечислены в `TRIPO_PARTY_2026-10-05_v01.json`. Все текстуры и шрифт упакованы. `TRIPO_PARTY_2026-10-05_v01.png` показывает всю шестёрку.
'''
(Path(r'C:\Dev\Game\Working\Reviews') / 'TRIPO_PARTY_2026-10-05_v01_README.md').write_text(review_readme, encoding='utf-8')
print(json.dumps({'source_sha256': sha, 'source_byte_identical': True, 'final_triangles': 1168, 'all_checks_pass': True, 'balance': 80}))
