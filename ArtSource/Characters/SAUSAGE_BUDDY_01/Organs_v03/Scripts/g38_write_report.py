"""Assemble evidence-backed G38 report and a complete local file inventory."""
import json,hashlib
from pathlib import Path
ROOT=Path('C:/Dev/Game');O=ROOT/'ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v03'
R=ROOT/'Working/Reviews/Operations/organs_v03';W=R/'G38_work';REV='v03c'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
C=read(W/'construction_four.json');V=read(W/'validation_four_final.json');F=read(W/'fit_four_final.json')
A=read(W/'preservation_source.json');Z=read(W/'preservation_delivered_v03c.json')
E=read(W/'external_clearance_v03c.json');X=read(W/'fbx_roundtrip_v03c.json');XP=read(W/'fbx_nonrib_preservation_v03c.json')
B=read(W/'break_check_v03c.json');MAN=read(O/'G38_collisions_manifest_v03c.json')
old=read(O.parent/'Patient_v03/ORGANS_LAYOUT_v03.json');new=read(O.parent/'Patient_v03/ORGANS_LAYOUT_v03c.json')
used={m for o in A['objects'].values() for m in o.get('materials',[])}
nonribs={n:r for n,r in A['objects'].items() if not n.startswith('RIB_')}
assert all(Z['objects'][n]==r for n,r in nonribs.items())
assert all(A['materials'][n]==Z['materials'][n] for n in used)
assert all(r['pass'] for r in X.values()) and XP['all_unchanged_nonrib_exact']
assert {k:v for k,v in old.items() if k!='ribcage'}=={k:v for k,v in new.items() if k!='ribcage'}
fmt=lambda x:f'{x:.3f}'
vec=lambda v:', '.join(f'{x:.6f}' for x in v)
link=lambda p:f'[{p.name}]({p.as_posix()})'
text=[]
def p(s=''):text.append(s+'\n\n')
def table(head,rows):
    lines=['| '+' | '.join(head)+' |','| '+' | '.join('---' for _ in head)+' |']
    for row in rows:lines.append('| '+' | '.join(str(x).replace('|','/') for x in row)+' |')
    p('\n'.join(lines))
p('# G38 — четыре пары рёбер по новому референсу, v03c')
p('**Статус: модель для визуального ревью сохранена; требования к игровым коллизиям НЕ выполнены. Задача целиком не закрыта.**')
p('Последнее указание пользователя: четыре пары по присланному изображению, все остальные органы по-прежнему менять нельзя. Это заменяет прежнее число пять. Итог текущей визуальной правки — **v03c**. Созданный ранее v03b с пятью парами оставлен отдельной промежуточной версией, не перезаписан и не является текущим вариантом по референсу.')
p('Главные файлы: '+', '.join(link(x) for x in [O/'Organs_v03c.blend',O/'FBX/RIBCAGE_v03c.fbx',O/'Organs_InBody_v03c.fbx',O/'G38_collisions_manifest_v03c.json',O.parent/'Patient_v03/ORGANS_LAYOUT_v03c.json',R/'organs_v03c_ribs_sheet.png'])+'.')
p(f'![Лист проверки]({(R/"organs_v03c_ribs_sheet_preview.png").as_posix()})')
p('## Что изменено')
p('- Только меши рёбер: RIB_L/R_01..04. Рёбра 05..09 отсутствуют в новой ревизии. Четыре пары имеют плавные дуги и соединения с двумя исходными половинами грудины; свободных передних концов нижней пары нет.')
p('- Основной профиль высотой 20 мм против примерно 8.5–9.5 мм исходного. Хрящ плавно сужается до 14 мм. Толщина в глубину обычно 8 мм; у боковых участков третьей/четвёртой пары локально до 3.2 мм для зазора с неподвижной анатомией. Это локальное сужение, а не равномерное удвоение во всех направлениях.')
p('- Исходные ivory bone / blue cartilage материалы и сглаживание сохранены. STERNUM_L/R и SPINE_THORACIC сохраняют исходную геометрию. Положение каждого сохранённого rib pivot и обоих RIBCAGE_HALF неизменно.')
p('- 8 рёбер × 636 треугольников + 2 половины грудины × 376 = **5 840 треугольников**. Каждый видимый сегмент замкнут, связен, без неманифолдных рёбер.')
p('- Добавлены mass_kg, 10 BREAK_ empties и 46 черновых UCX: по четыре на ребро и по семь на половину грудины. Отдельных декоративных cartilage/spine коллайдеров нет; в исходнике у позвоночника коллайдера не было.')
p('## Проверки и ограничения')
render_cross=[(pose,n,r['intersections']) for pose,rows in V['render_mesh_clearance'].items() for n,r in rows.items() if r['intersections']]
gapmin=min(g['clearance_mm'] for g in V['rib_gaps'])
rows=[['Четыре пары и бюджет ≤ 6 000 трис','PASS','8 рёбер, 2 sternum halves, 5 840 трис'],
 ['Геометрия / transforms всех non-rib объектов','PASS',f'{len(nonribs)} объектов; точное равенство снимков после повторного открытия .blend'],
 ['Материалы назначенных объектов','PASS',f'{len(used)} материалов: параметры и узлы совпадают'],
 ['Габариты rib+sternum','PASS','min/max совпадают с v03 по сохранённым float32 координатам'],
 ['Видимые рёбра / органы и живот, closed + open35','PASS' if not render_cross else 'FAIL','Пересечений с organ/vessel/airway/diaphragm/spine/abdomen мешами нет'],
 ['UCX: выпуклость / ≤64 vertices / замкнутые triangles','PASS','46 / 46; local scale=1, rotation=0, translation=0 под своим сегментом'],
 ['8 мм инструмент между соседними рёбрами','PASS' if V['summary']['all_rib_gaps_at_least_8mm'] else 'FAIL',f'Минимальный зазор {gapmin:.3f} мм'],
 ['UCX снаружи не более 2 мм','FAIL',f"Верхняя оценка максимума {F['summary']['maximum_outside_bound_mm']:.3f} мм"],
 ['Покрытие видимой поверхности: не глубже 1 мм','FAIL',f"Верхняя оценка непокрытого расстояния {F['summary']['maximum_uncovered_bound_mm']:.3f} мм"],
 ['UCX / органы ≥3 мм closed','FAIL',f"Минимум {V['summary']['min_organ_clearance_closed_mm']:.3f} мм; есть пересечения"],
 ['UCX / органы ≥3 мм open35','FAIL',f"Минимум {V['summary']['min_organ_clearance_open_mm']:.3f} мм"],
 ['UCX / тело и шея во всех позах','BLOCKED','Есть пересечения с фиксированными body meshes; см. таблицу ниже'],
 ['20 sphere sweeps с bone-only фильтром','PASS','20 из 20: rib/sternum или ничего; это проверка заданного фильтра, не готовности физических коллизий'],
 ['FBX повторный импорт и масштаб','PASS','Оба FBX проверены отдельным background Blender процессом'],
 ['Unity / PhysX / игровой тест','NOT RUN','По запрету пользователя Unity и Assets не трогались']]
table(['Проверка','Статус','Факт'],rows)
p('Плавный изгиб нельзя заменять одной большой выпуклой оболочкой без перемычки внутри дуги. Текущее разбиение на четыре части на ребро такие перемычки создаёт и не проходит fit/clearance. Разрешение на 6–8 меньших частей запрошено; на момент сборки этого отчёта ответа нет. Эксперимент с восемью равномерными частями сохранён только в G38_work: он также не прошёл все допуски и не выдаётся за готовое решение. Потребуется подбор границ частей и повторная проверка, а не просто увеличение числа.')
p('**Не включать черновые UCX v03c в gameplay.** В манифесте стоит `BLOCKED_REVIEW_CANDIDATE`, `ready_for_runtime=false` и перечислены проваленные проверки. Внешний вид и неизменность анатомии не являются доказательством готовности коллизий.')
p('### Габариты и масштаб')
table(['Ось','До min, м','После min, м','До max, м','После max, м'],[[axis,C['before_bounds'][0][i],C['after_bounds'][0][i],C['before_bounds'][1][i],C['after_bounds'][1][i]] for i,axis in enumerate('XYZ')])
p('Scene unit scale = 1 метр; экспорт global_scale=1, apply_unit_scale, FBX_SCALE_UNITS, -Z forward / Y up. Все новые UCX имеют единичную локальную матрицу под своим rib/sternum. Существующие float32 остатки scale у некоторых органов (например 1.0000001192) сохранены бит-в-бит, не нормализованы. Максимальная ошибка габаритов после FBX roundtrip: '+f"{max(r['bounds_error_mm'] for data in X.values() for r in data['objects'].values()):.6f}"+' мм.')
p('### Шея, TABLE_REST и раскрытие')
p('Исходная грудина пересекает фиксированную геометрию головы/шеи. Исследован только разрешённый верхний срез внутри прежних границ: для прохождения выбранной проверки обоих head meshes closed/open требуется верх z=1.094 м вместо 1.178 м, то есть удаление 84 мм из 120 мм (70%). Это сильно меняет общий вид, поэтому такой вариант не применён. Нельзя считать этот один вид среза доказательством невозможности всех допустимых фасок; это документированный неудачный вариант, а не разрешение менять тело или pivots.')
p('В конечном v03c у STERNUM_L/R **нулевое изменение геометрии и transforms**; добавлены только разрешённые mass_kg и BREAK/UCX дети. На листе исходная и сохранённая форма обозначены как одинаковые, отдельно показан неприменённый trim study спереди и сбоку. Пивоты/тело/шея не изменялись.')
bodyrows=[]
for pose in ('closed','open35'):
    for body in ('BODY_REST','BODY_TABLE_REST'):
        names=[n for n,r in V['colliders'].items() if body in r['poses'][pose]['surface_intersections']]
        bodyrows.append([pose,body,len(names),', '.join(names)])
table(['Rib pose','Фиксированный body mesh','Пересечённых UCX','Имена'],bodyrows)
p('TABLE_REST проверен с вычисленным posed body, переведённым обратно в rest frame точным torso transform. Для top-camera sweep использована матрица из исходного ORGANS_LAYOUT_v03.json. При общей жёсткой трансформации organs/ribs их относительные зазоры сохраняются. Открытие: локальная Y шарниров +35° L / −35° R; UCX и BREAK следуют своими родителями. Body-контакты отмечены как провал, включая open35 + TABLE_REST. В источнике нет Unity body/organ collider assets; их отсутствие не объявляется успешным тестом.')
p('Liver, обе kidneys, lungs, heart, vessels, diaphragm, airway и их lowered layout positions не двигались. OperationAbdomen_v03 проверялся в отдельном процессе как read-only reference. Рендерные окна/прозрачность тела сделаны только в одноразовых review-сценах и в .blend/FBX результата не сохранены.')
p('## Каждый коллайдер')
p('Расстояния — мм. «Other» включает остальные видимые кости, органы, тело, abdomen и UCX других targets; собственный render mesh и части того же compound исключены. Ноль означает пересечение/контакт. Все части замкнуты и триангулированы. Convex проверяется по supporting planes в локальных координатах, допуск 0.005 мм. Outside — консервативная верхняя оценка по сетке, не округлённое до PASS измерение.')
table(['UCX','V','Convex','Орган closed, мм / имя','Орган open35, мм / имя','Other closed, мм / имя','Other open35, мм / имя','Outside ≤, мм'],[
 [n,r['vertices'],'yes' if r['convex'] else 'NO',f"{r['poses']['closed']['organ_min_mm']:.3f} / {r['poses']['closed']['nearest_organ']}",
 f"{r['poses']['open35']['organ_min_mm']:.3f} / {r['poses']['open35']['nearest_organ']}",
 f"{E['closed'][n]['min_external_mesh_mm']:.3f} / {E['closed'][n]['nearest_external_mesh']}",
 f"{E['open35'][n]['min_external_mesh_mm']:.3f} / {E['open35'][n]['nearest_external_mesh']}",fmt(F['outside'][n]['certified_upper_outside_mm'])]
 for n,r in V['colliders'].items()])
p('Расстояние между мешами: тест пересечения треугольников и минимумы vertex–face / edge–edge с консервативным AABB отсевом. Fit: barycentric grids и расстояние до замкнутого тела/compound; максимум отсчётов плюс диаметр клетки даёт верхнюю оценку. Для inside применяется голосование нескольких лучей с шагом 0.01 мм против повторного попадания в ту же грань; это численная, не символическая геометрия. Все исходные отсчёты/границы/худшие позиции находятся в JSON проверки.')
table(['Render mesh','Непокрытое расстояние ≤, мм','≤1 мм'],[[n,fmt(r['certified_upper_uncovered_mm']),'PASS' if r['pass_1mm'] else 'FAIL'] for n,r in F['coverage'].items()])
table(['Пара соседних сегментов','Минимальный зазор, мм','8 мм'],[[f"{g['a']} / {g['b']}",fmt(g['clearance_mm']),'PASS' if g['pass_8mm'] else 'FAIL'] for g in V['rib_gaps']])
p('## 20 непрерывных проб инструментом')
p('Seed 38, без перегенерации неудачных линий. Сфера диаметром 8 мм (радиус 4 мм), origins равномерно по проекции грудной клетки TABLE_REST; направление (0,0,-1), как у top game camera. Conservative advancement по distance-to-triangle, допуск контакта 0.001 мм, максимум 5000 шагов. Столбец без фильтра — диагностический, включает кости и органы. Он показывает, почему открытые межрёберные промежутки требуют layer mask; физически закрывать их запрещено самим требованием прохода инструмента.')
table(['№','Origin TABLE_REST, м','Первый hit: SurgicalBone only','Путь до hit, мм','Без bone-only фильтра'],[[r['id'],vec(r['origin_table_m']),r['filtered']['first_hit'] or 'ничего',fmt(r['filtered']['travel_m']*1000) if r['filtered']['travel_m'] is not None else '—',r['unfiltered_bones_and_organs']['first_hit'] or 'ничего'] for r in V['probe_tests']])
p('### Контракт для Claude / Unity')
p('UCX — соглашение имён, Unity не создаёт по нему MeshCollider автоматически. Для каждой перечисленной части нужен отдельный `MeshCollider(convex=true)` под её target с local identity, а MeshRenderer UCX должен быть отключён. Layer: **SurgicalBone**; tags: **SurgicalRib** / **SurgicalSternum**. Индекс слоя намеренно не назначен. Все запросы mallet/osteotome и соответствующая фильтрация физических контактов должны включать только SurgicalBone, исключая органы/сосуды/диафрагму/тело. Прочие хирургические инструменты используют собственные masks. Это описание для последующей интеграции, не выполненная настройка Unity. Сначала исправить FAIL коллизий.')
p('## Mass и BREAK')
p('mass_kg = приблизительный объём замкнутого render mesh × 1100 кг/м³; игровой hint, не медицинская оценка. BREAK рёбер находится на видимой границе bone/cartilage; sternum BREAK — на midline поверхности. На сохранённом v03c максимальное расстояние BREAK от поверхности родителя: '+fmt(max(r['surface_distance_mm'] for r in B.values()))+' мм. Полные local/world positions и bounds каждой UCX части находятся в манифесте.')
table(['Target','mass_kg','BREAK world/rest, м','Hinge parent'],[[n,r['mass_kg'],vec(r['break_empty']['position_rest_world_m']),r['hinge_parent']] for n,r in MAN['objects'].items()])
p('## Побитовое сохранение всех non-rib объектов')
p('Ниже каждый исходный non-rib объект, включая обе грудины и hinge empties. Transform SHA256 включает location, rotation Euler/quaternion, scale, delta transforms, parent/type/bone, matrix_basis, matrix_parent_inverse и matrix_world. Mesh SHA256 включает float32 vertices, topology, polygon material/smooth flags, material slot names, UV и weights. Одинаковые строки здесь получены из двух независимо открытых .blend, а не скопированы в колонку «после». Полные числа матриц: '+link(W/'preservation_source.json')+' и '+link(W/'preservation_delivered_v03c.json')+'.')
table(['Объект','Transform SHA256 до','Transform SHA256 после','Mesh SHA256 до','Mesh SHA256 после'],[[n,r['transform_sha256'],Z['objects'][n]['transform_sha256'],r.get('mesh_sha256','—'),Z['objects'][n].get('mesh_sha256','—')] for n,r in nonribs.items()])
table(['Объект','World location до, м','World location после, м','Local scale до / после','Parent до / после'],[[n,vec([r['transform']['matrix_world'][i][3] for i in range(3)]),vec([Z['objects'][n]['transform']['matrix_world'][i][3] for i in range(3)]),str(r['transform']['scale'])+' / '+str(Z['objects'][n]['transform']['scale']),(r['transform']['parent'] or '—')+' / '+(Z['objects'][n]['transform']['parent'] or '—')] for n,r in nonribs.items()])
p('У сохранённых RIB_L/R_01..04 отдельно сравнены transform SHA256: '+('PASS' if all(A['objects'][n]['transform_sha256']==Z['objects'][n]['transform_sha256'] for n in MAN['objects'] if n.startswith('RIB_')) else 'FAIL')+'.')
table(['Назначенный материал','SHA256 до','SHA256 после'],[[n,A['materials'][n]['sha256'],Z['materials'][n]['sha256']] for n in sorted(used)])
p('## ORGANS_LAYOUT: только rib entries')
p('Все top-level поля вне ribcage и все non-RIB записи внутри ribcage равны исходному JSON. Сохранены даже исходные version/date/legacy notes: они не переписаны ради требования «только rib entries». Текущий состав модели задан в манифесте и этом отчёте. Полный unified diff: '+link(R/'G38_LAYOUT_DIFF_v03c.patch')+'.')
table(['Rib entry','До tris','После tris','Изменение'],[[n,r.get('tris','—'),new['ribcage'].get(n,{}).get('tris','—'),'удалён в v03c' if n not in new['ribcage'] else 'tris + local bounds + size; pivot/parent/materials неизменны'] for n,r in old['ribcage'].items() if n.startswith('RIB_')])
p('## Воспроизводимость и фактические команды')
p('Blender 5.2.1 LTS, Python 3.13.13, NumPy 2.3.4. Все действия — отдельные background процессы. Открытая сессия Blender пользователя не управлялась. Unity/Assets/rig/weights/OperationAbdomen/blood bag/syringe не редактировались. Никаких commits/staging/push. Исходные v03 и прежний PROGRESS.md не перезаписаны.')
p('Команды ниже приведены относительно C:/Dev/Game; OUT обозначает ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v03, WORK — Working/Reviews/Operations/organs_v03/G38_work. Существующие numbered .blend/FBX/JSON генераторы отказываются перезаписывать.')
p('```text\nblender --background OUT/Organs_v03.blend --python OUT/Scripts/g38_build_four_ribs.py\nblender --background WORK/ribcage_four04.blend --python OUT/Scripts/g38_validate_v03b.py -- --out WORK/validation_four_final.json\nblender --background WORK/ribcage_four04.blend --python OUT/Scripts/g38_fit_v03b.py -- --out WORK/fit_four_final.json\nblender --background WORK/ribcage_four04.blend --python OUT/Scripts/g38_package_v03b.py -- --revision v03c --draft-collisions\nblender --background --factory-startup --python OUT/Scripts/g38_fbx_roundtrip.py -- --revision v03c\nblender --background --factory-startup --python OUT/Scripts/g38_fbx_preservation.py -- --revision v03c\nblender --background OUT/Organs_v03c.blend --python OUT/Scripts/g38_preservation_audit.py -- --out WORK/preservation_delivered_v03c.json\nblender --background OUT/Organs_v03c.blend --python OUT/Scripts/g38_external_clearance.py -- --revision v03c\nblender --background OUT/Organs_v03c.blend --python OUT/Scripts/g38_break_check.py -- --out WORK/break_check_v03c.json\npython OUT/Scripts/g38_compose_sheet.py --revision v03c\n```')
p('`--draft-collisions` допускает запись маркированного review-экспорта при провале коллизий; он не меняет результаты тестов на PASS. Проверены оба FBX: geometry bounds, triangle counts с исходным FBX baseline, hierarchy, 10 BREAK и mass hints, 46 UCX. В исходном right lung уже есть различие tessellation 1188 tris в .blend / 1187 после FBX import; новый FBX повторяет v03 точно. '+link(W/'fbx_nonrib_preservation_v03c.json')+' подтверждает совпадение всех non-rib импортированных объектов.')
p('SciPy 1.17.0 / BSD-3-Clause установлен только в G38_work/python_deps для float64 ConvexHull/Qhull, без изменения Unity/system packages. [Документация ConvexHull](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.spatial.ConvexHull.html), [лицензия версии](https://github.com/scipy/scipy/blob/v1.17.0/LICENSE.txt). '+link(W/'dependency_notes.md')+' содержит provenance и rollback. Готовые .blend/FBX/JSON не требуют SciPy для использования.')
p('## Файлы')
p('Все созданные/изменённые этой работой пути, включая промежуточные варианты, логи, рендеры, Python caches и изолированную зависимость: '+link(R/'G38_FILES.txt')+'. SHA256 основных outputs и проверенных исходников: '+link(R/'G38_OUTPUT_HASHES.json')+'.')
primary=[O/'Organs_v03c.blend',O/'Organs_InBody_v03c.fbx',O/'FBX/RIBCAGE_v03c.fbx',O/'G38_collisions_manifest_v03c.json',O/'G38_CURRENT.json',O.parent/'Patient_v03/ORGANS_LAYOUT_v03c.json',R/'organs_v03c_ribs_sheet.png',R/'organs_v03c_ribs_sheet_preview.png',R/'G38_REPORT.md',R/'G38_LAYOUT_DIFF_v03c.patch',R/'G38_FILES.txt',R/'G38_OUTPUT_HASHES.json']
for path in primary:p('- '+link(path))
p('Предыдущие v03b outputs и G38_work кандидаты оставлены как промежуточные результаты. В текущую ревизию не переносились экспериментальные восемь частей на ребро. До ответа на вопрос о числе частей и устранения body/neck конфликтов готовность игровых коллизий остаётся BLOCKED.')
(R/'G38_REPORT.md').write_text(''.join(text),encoding='utf-8')
(O/'G38_CURRENT.json').write_text(json.dumps({'current_revision':'v03c','rib_pairs':4,'status':'VISUAL_REVIEW_COLLISIONS_BLOCKED','blend':str(O/'Organs_v03c.blend'),'manifest':str(O/'G38_collisions_manifest_v03c.json'),'report':str(R/'G38_REPORT.md'),'supersedes_visual_revision':'v03b','collider_count_override_approved':False},indent=2),encoding='utf-8')
files=set(primary)
files.update((O/'Scripts').glob('g38_*.py'))
files.update((O/'Scripts/__pycache__').glob('*.pyc'))
files.update(p for p in W.rglob('*') if p.is_file())
for folder in (R/'G38_tiles',R/'G38_v03c_tiles'):files.update(p for p in folder.rglob('*') if p.is_file())
files.update(O.glob('*v03b*'));files.update((O/'FBX').glob('*v03b*'))
files.add(O.parent/'Patient_v03/ORGANS_LAYOUT_v03b.json')
files.update(R.glob('*v03b*'));files.add(R/'G38_LAYOUT_DIFF.patch')
files={p for p in files if p.is_file() or p in primary}
(R/'G38_FILES.txt').write_text('G38: created/edited files, including superseded draft outputs and generated runtime caches.\nOnly C:/Dev/Game. No source v03 files are listed as modified.\n\n'+'\n'.join(p.as_posix() for p in sorted(files))+'\n',encoding='utf-8')
protected=[O/'Organs_v03.blend',O/'Organs_InBody_v03.fbx',O/'FBX/RIBCAGE_v03.fbx',O.parent/'Patient_v03/ORGANS_LAYOUT_v03.json',O.parent/'Patient_v03/SAUSAGE_BUDDY_PATIENT_v03.blend',ROOT/'ArtSource/Props/TABLE-ASTRA-001/v03/OperationAbdomen_v03.blend',ROOT/'ArtSource/Props/TABLE-ASTRA-001/v02/Patient_TableRest_v01.blend']
hashes={}
for group,paths in [('outputs',primary[:-1]),('protected_sources_identity',protected)]:
    hashes[group]={p.as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths if p.exists()}
(R/'G38_OUTPUT_HASHES.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
print('REPORT_WRITTEN',len(text),'blocks;',len(files),'files inventoried',flush=True)
