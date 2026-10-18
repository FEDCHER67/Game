"""Publish v03d evidence, manifest pointer and exhaustive file inventory."""
import json,hashlib
from pathlib import Path
ROOT=Path('C:/Dev/Game');O=ROOT/'ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v03'
R=ROOT/'Working/Reviews/Operations/organs_v03';W=R/'G38_work'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
V=read(W/'validation_v03d_01.json');F=read(W/'fit_v03d_final.json');E=read(W/'external_clearance_v03d.json')
A=read(W/'preservation_delivered_v03c.json');Z=read(W/'preservation_delivered_v03d.json');ORIG=read(W/'preservation_source.json')
X=read(W/'fbx_roundtrip_v03d.json');XP=read(W/'fbx_visual_preservation_v03d.json')
M=read(O/'G38_collisions_manifest_v03d.json');MC=read(O/'G38_collisions_manifest_v03c.json')
C=read(W/'colliders_v03d_01.json');protected=read(W/'v03d_sources_before.json')
fixed={n:r for n,r in A['objects'].items() if not n.startswith('UCX_')}
assert fixed=={n:r for n,r in Z['objects'].items() if not n.startswith('UCX_')}
assert A['materials']==Z['materials']
assert all(r['pass'] for r in X.values()) and all(r['all_non_ucx_exact'] for r in XP.values())
assert all(sha(Path(p))==v['sha256'] for p,v in protected.items())
assert F['summary']['outside_2mm_pass'] and F['summary']['coverage_1mm_pass']
assert M['status']=='BLENDER_COLLIDER_VALIDATION_PASS'
assert all(M['objects'][n][k]==MC['objects'][n][k] for n in M['objects'] for k in ('mass_kg','hinge_parent','break_empty','object_local_transform','object_rest_world_transform'))
layout_c=O.parent/'Patient_v03/ORGANS_LAYOUT_v03c.json';layout_d=O.parent/'Patient_v03/ORGANS_LAYOUT_v03d.json'
assert layout_c.read_bytes()==layout_d.read_bytes()
original_nonribs={n:r for n,r in ORIG['objects'].items() if not n.startswith('RIB_')}
assert all(Z['objects'][n]==r for n,r in original_nonribs.items())
text=[]
def p(s=''):text.append(s+'\n\n')
def table(head,rows):
    lines=['| '+' | '.join(head)+' |','| '+' | '.join('---' for _ in head)+' |']
    lines.extend('| '+' | '.join(str(x).replace('|','/') for x in row)+' |' for row in rows)
    p('\n'.join(lines))
link=lambda path:f'[{path.name}]({path.as_posix()})'
vec=lambda v:', '.join(f'{x:.9f}' for x in v)
f3=lambda v:f'{v:.3f}'
gap=min(g['clearance_mm'] for g in V['rib_gaps'])
vmin=min(c['vertices'] for c in V['colliders'].values());vmax=max(c['vertices'] for c in V['colliders'].values())
body_counts=[]
for pose in ('closed','open35'):
    for body in ('BODY_REST','BODY_TABLE_REST'):
        names=[n for n,r in V['colliders'].items() if body in r['poses'][pose]['surface_intersections']]
        body_counts.append([pose,body,len(names),', '.join(names)])
p('# G38 — утверждённая визуальная модель v03c, коллайдеры v03d')
p('**PASS — проверки геометрии коллайдеров в Blender выполнены. Внешний вид v03c сохранён побитно. Unity / PhysX / игровой тест: NOT RUN.**')
p('Текущая ревизия — **v03d**. Пользователь принял четыре пары v03c без изменений рендерных мешей и разрешил 6–10 коротких частей на ребро. Это заменяет прежний лимит четыре части. Пересечения с телом/шеей и исходное перекрытие грудины с шеей приняты пользователем и исключены из критериев PASS; ниже они остаются информацией. Требования прилегания к кости, зазора до органов и прохода инструмента сохранены.')
p('Главные файлы: '+', '.join(link(x) for x in [O/'Organs_v03d.blend',O/'FBX/RIBCAGE_v03d.fbx',O/'Organs_InBody_v03d.fbx',O/'G38_collisions_manifest_v03d.json',layout_d,R/'organs_v03d_ribs_sheet.png'])+'.')
p(f'![Лист v03d]({(R/"organs_v03d_ribs_sheet_preview.png").as_posix()})')
p('## v03d colliders')
p('Изменена только геометрия UCX. Всего **96 выпуклых частей**: 8 рёбер × 10 и 2 половины грудины × 8. Каждый сегмент замкнут, триангулирован, содержит '+f'{vmin}–{vmax}'+' вершин и имеет единичную локальную матрицу и matrix_parent_inverse под своим rib/sternum. Декоративных cartilage коллайдеров и нового spine коллайдера нет.')
p('Для рёбер границы коротких частей выбраны по кривизне: минимизируется худший выступ выпуклой оболочки, затем суммарный квадрат выступов. В hull входят все кольца выбранного участка, включая промежуточные. Точки рендерного меша не менялись. Грудина разделена на восемь коротких срезов по высоте; сохранён зазор 0.4 мм между левыми/правыми UCX у midline.')
cuts=[(n,r) for n,entry in C['objects'].items() for r in entry['parts'] if r['cuts']]
p('Единственное подрезание около органов: '+(', '.join(r['name'] for n,r in cuts) if cuts else 'нет')+'. У нижнего правого ребра расстояние самого утверждённого render mesh до диафрагмы в open35 равно 2.949 мм. Подрезана только соответствующая часть UCX до целевого зазора 3.15 мм; фактический минимум 3.149244 мм после float32 сохранения. Покрытие видимой кости осталось в допуске 1 мм.')
table(['Проверка','Статус','Измеренный результат'],[
 ['Неизменность утверждённой визуальной модели','PASS','45 / 45 non-UCX объектов, все 17 материалов, все BREAK/pivots/mass hints точно равны v03c'],
 ['Четыре пары, render budget','PASS','RIB_L/R_01..04; 5 840 треугольников, без изменений'],
 ['Convex / ≤64 vertices / triangulated / closed','PASS',f'96 / 96; {vmin}–{vmax} вершин на часть'],
 ['Выступ UCX за кость ≤2 мм','PASS',f"Консервативная верхняя оценка {F['summary']['maximum_outside_bound_mm']:.6f} мм"],
 ['Непокрытая поверхность кости ≤1 мм','PASS',f"Консервативная верхняя оценка {F['summary']['maximum_uncovered_bound_mm']:.6f} мм"],
 ['Зазор до органов ≥3 мм, closed','PASS',f"Минимум {V['summary']['min_organ_clearance_closed_mm']:.6f} мм"],
 ['Зазор до органов ≥3 мм, open35','PASS',f"Минимум {V['summary']['min_organ_clearance_open_mm']:.6f} мм"],
 ['Проход инструмента 8 мм','PASS',f'Все 6 соседних пар; минимум {gap:.6f} мм'],
 ['20 проб сферы 8 мм с SurgicalBone mask','PASS','20 / 20: только rib/sternum UCX или ничего'],
 ['Пересечения с телом/шеей','INFO — ACCEPTED','Не участвуют в PASS по последнему указанию пользователя; полные значения ниже'],
 ['TABLE_REST + открытие 35°','PASS / INFO','Органы и UCX преобразуются общим torso transform; posed body проверен отдельно как информация'],
 ['Сохранённый .blend и оба FBX','PASS','Повторно открыты/импортированы; every non-UCX object совпадает с v03c'],
 ['Масштаб','PASS','scene unit scale=1 метр; export global_scale=1; local UCX transforms applied'],
 ['Unity / PhysX cooking / игровой тест','NOT RUN','По запрету пользователя Unity и Assets не трогались']])
p('У UCX_RIB_L_04_06 обычная сетка давала недостаточно точную верхнюю оценку 2.182 мм при измеренных отсчётах около 1.932 мм. Только этот участок проверен дополнительным адаптивным разбиением всех его треугольников: расстояние центра до тела кости + радиус охватывающей сферы + запас 0.01 мм. Полученная верхняя оценка 1.998829 мм проходит лимит. Это уточнение измерения на неизменной геометрии, а не замена FAIL на PASS без проверки. Исходное измерение сохранено внутри final fit JSON.')
p('### Каждый UCX: прилегание и ближайший орган / другой меш')
p('Все расстояния ниже — мм. Organ включает lungs, heart, liver, kidneys, vessels, diaphragm, airway и остальные органы. Other включает тело, abdomen, другие render bones и UCX других targets; собственный render mesh и части того же compound исключены. Ноль в Other возможен на принятом body/neck пересечении либо на соединении ребра с грудиной. Эти значения не подменяют отдельный обязательный минимум до органов.')
table(['UCX','V','Convex','Organ closed, мм / имя','Organ open35, мм / имя','Other closed, мм / имя','Other open35, мм / имя','Outside ≤, мм'],[
 [n,c['vertices'],'yes' if c['convex'] else 'NO',
  f"{c['poses']['closed']['organ_min_mm']:.6f} / {c['poses']['closed']['nearest_organ']}",
  f"{c['poses']['open35']['organ_min_mm']:.6f} / {c['poses']['open35']['nearest_organ']}",
  f"{E['closed'][n]['min_external_mesh_mm']:.6f} / {E['closed'][n]['nearest_external_mesh']}",
  f"{E['open35'][n]['min_external_mesh_mm']:.6f} / {E['open35'][n]['nearest_external_mesh']}",
  f"{F['outside'][n]['certified_upper_outside_mm']:.6f}"] for n,c in V['colliders'].items()])
p('### Покрытие каждой видимой кости и межрёберные промежутки')
table(['Render target','Непокрытое расстояние ≤, мм','≤1 мм'],[[n,f"{r['certified_upper_uncovered_mm']:.6f}",'PASS' if r['pass_1mm'] else 'FAIL'] for n,r in F['coverage'].items()])
table(['Соседние рёбра','Минимальный зазор, мм','8 мм'],[[g['a']+' / '+g['b'],f"{g['clearance_mm']:.6f}",'PASS' if g['pass_8mm'] else 'FAIL'] for g in V['rib_gaps']])
p('### Тело, шея, TABLE_REST и прочие крайние случаи')
table(['Положение рёбер','Меш тела','Число пересечённых UCX','Имена (INFO, принято)'],body_counts)
p('У грудины **нулевое изменение render mesh, pivots и transforms**. Ранее исследованный срез 84 мм не применён и больше не требуется по принятому критерию. Chin/neck контакты разрешены; они остаются в per-collider JSON как body_rest/body_table расстояния, surface_intersections и head containment samples. Нижние liver/kidney positions, лёгкие, сердце, сосуды, diaphragm и airway не изменялись.')
p('REST и TABLE_REST body проверялись как два отдельных меша. TABLE_REST body вычислен из исходного posed patient и переведён обратно точной матрицей torso; сама поза пациента не редактировалась. Для рёбер/органов TABLE_REST — одна общая жёсткая трансформация, поэтому относительные расстояния из closed/open35 сохраняются. Открытие выполнялось исходными RIBCAGE_HALF_L/R: +35° / −35° по локальной Y. UCX и BREAK следуют родителям; контроль исходных матриц и hierarchy приведён ниже.')
p('В Blender-источниках отсутствуют Unity body/organ Collider assets. Измерены имеющиеся meshes; отсутствие этих Collider assets не объявляется тестом Unity. SPINE_THORACIC не менялся, нового коллайдера позвоночника нет. OperationAbdomen_v03 использован только как read-only геометрия в одноразовой проверке; пересечений UCX с его поверхностями нет.')
p('### 20 непрерывных проб инструментом')
p('Seed 38; сфера диаметром 8 мм (радиус 4 мм). Двадцать origin равномерно по проекции грудной клетки в TABLE_REST, направление top game camera (0, 0, −1). Линии не перегенерировались по результатам. Conservative advancement использует 1-Lipschitz distance-to-triangle, допуск контакта 0.001 мм, лимит 5000 шагов; все пробы завершились. Колонка без фильтра намеренно показывает реальные органы через открытые промежутки, чтобы проверить необходимость SurgicalBone mask.')
table(['№','Origin TABLE_REST, м','Первый hit: SurgicalBone only','Путь, мм','Без bone-only mask'],[
 [r['id'],vec(r['origin_table_m']),r['filtered']['first_hit'] or 'ничего',f3(r['filtered']['travel_m']*1000) if r['filtered']['travel_m'] is not None else '—',r['unfiltered_bones_and_organs']['first_hit'] or 'ничего'] for r in V['probe_tests']])
p('### Контракт Unity / Claude')
p('UCX — соглашение имён; Unity автоматически не превращает эти meshes в коллайдеры. Для каждой части из манифеста нужен отдельный **MeshCollider(convex=true)** под указанным target, с local identity; UCX MeshRenderer отключить. Layer: **SurgicalBone**. Tags: **SurgicalRib** / **SurgicalSternum**. Числовой индекс слоя не назначался. Все mallet/osteotome raycast/sphere sweep queries и соответствующие физические контакты должны включать только SurgicalBone и исключать organ/vessel/diaphragm/lung/heart/body. Межрёберные просветы остаются открытыми.')
p('В манифесте `ready_for_unity_integration=true`, `ready_for_runtime=false`: геометрия прошла измерения Blender, но импорт, PhysX cooking и проверка реального инструмента остаются работой Unity. Никаких настроек Unity, Assets, layers или tags в проекте эта задача не меняла.')
p('### Mass, BREAK и hinges')
p('mass_kg, существующие BREAK позиции и hinge parents сохранены точно из v03c; новых оценок массы не выполнялось. Значения — прежние игровые hints, volume × 1100 кг/м³. Полные local/world matrices, bounds и vertex counts каждого UCX находятся в манифесте.')
table(['Target','Частей','mass_kg','BREAK world/rest, м','Hinge parent'],[[n,len(r['ucx_parts']),r['mass_kg'],vec(r['break_empty']['position_rest_world_m']),r['hinge_parent']] for n,r in M['objects'].items()])
p('## Доказательство неизменности v03c → v03d')
p('После повторного открытия сохранённого v03d сравнены все 45 объектов вне UCX и все 17 материалов. SHA256 transforms включает location, rotation Euler/quaternion, scale, delta transforms, parent/type/bone, matrix_basis, matrix_parent_inverse, matrix_world. Mesh SHA256 включает float32 vertices, topology, polygon material/smooth flags, material slots, UV и weights. Колонки получены из двух независимо открытых .blend. Полные снимки: '+link(W/'preservation_delivered_v03c.json')+', '+link(W/'preservation_delivered_v03d.json')+'.')
table(['Объект','Transform SHA256 v03c','Transform SHA256 v03d','Mesh SHA256 v03c','Mesh SHA256 v03d'],[
 [n,r['transform_sha256'],Z['objects'][n]['transform_sha256'],r.get('mesh_sha256','—'),Z['objects'][n].get('mesh_sha256','—')] for n,r in fixed.items()])
table(['Объект','World location до / после, м','Local scale до / после','Parent до / после'],[
 [n,vec([r['transform']['matrix_world'][i][3] for i in range(3)])+' / '+vec([Z['objects'][n]['transform']['matrix_world'][i][3] for i in range(3)]),
  str(r['transform']['scale'])+' / '+str(Z['objects'][n]['transform']['scale']),
  (r['transform']['parent'] or '—')+' / '+(Z['objects'][n]['transform']['parent'] or '—')] for n,r in fixed.items()])
table(['Материал','SHA256 v03c','SHA256 v03d'],[[n,r['sha256'],Z['materials'][n]['sha256']] for n,r in A['materials'].items()])
p('Дополнительно все 27 исходных non-rib объектов из v03 совпадают с v03d. Это включает обе грудины, spine и hinge empties; изменения v03c затрагивали только ребра. Исходные float32 остатки масштаба некоторых органов (например 1.0000001192) сохранены бит-в-бит, а не нормализованы.')
table(['Исходный non-rib объект','Transform SHA256 v03','Transform SHA256 v03d','Mesh SHA256 v03','Mesh SHA256 v03d'],[
 [n,r['transform_sha256'],Z['objects'][n]['transform_sha256'],r.get('mesh_sha256','—'),Z['objects'][n].get('mesh_sha256','—')] for n,r in original_nonribs.items()])
p('### Layout, exports и масштаб')
p('ORGANS_LAYOUT_v03d.json **побайтно равен v03c**: ни одна запись не изменена. SHA256: `'+sha(layout_d)+'`. Разница с исходным v03 по-прежнему только в rib entries: '+link(R/'G38_LAYOUT_DIFF_v03c.patch')+'. Число пар/новая ревизия указаны в manifest; прежние version/date/legacy layout notes сохранены ради требования не редактировать остальные записи.')
p('Scene unit scale = 1 метр; FBX global_scale=1, apply_unit_scale, FBX_SCALE_UNITS, −Z forward / Y up. Повторный импорт обоих FBX подтвердил hierarchy, bounds, triangle counts, 96 UCX, 10 BREAK и mass hints. Максимальная ошибка bounds: '+f"{max(r['bounds_error_mm'] for result in X.values() for r in result['objects'].values()):.9f}"+' мм. Сравнение импортов v03c/v03d также подтвердило точное равенство каждого non-UCX объекта, включая ribs и BREAK: '+link(W/'fbx_visual_preservation_v03d.json')+'. Исходная особенность right lung — 1188 tris в .blend / 1187 в FBX import — сохранена, не является новой потерей.')
p('## Метод и воспроизводимость')
p('Blender 5.2.1 LTS, Python 3.13.13, NumPy 2.3.4. Только отдельные background процессы; открытый Blender пользователя не управлялся. Unity/Assets/rig/weights/OperationAbdomen/blood bag/syringe не редактировались. Commits/staging/push не выполнялись. Source v03 и все v03b/v03c deliverables сохранены; SHA256 '+str(len(protected))+' исходных/предыдущих файлов повторно проверены.')
p('Минимум между мешами: triangle intersection + vertex–face / edge–edge с консервативным AABB отсевом. Проверена также anatomical containment. Outside/coverage: barycentric grids, distance-to-solid / distance-to-compound и Lipschitz верхние оценки; для одного пограничного участка выполнено адаптивное уточнение, описанное выше. Convexity: supporting planes в локальных координатах с численным допуском 0.005 мм. Для parity containment применяется несколько лучей с шагом 0.01 мм против повторного счёта одной грани. Это численная геометрическая проверка, не PhysX runtime test.')
p('Все изображения — реальные Blender renders. Новые wireframe tiles сняты из доставленного Organs_v03d.blend в одноразовом процессе. Прозрачность костей используется только для просмотра и не сохранена в deliverables. Принятые визуальные tiles повторно использованы из v03c с явной подписью: render meshes не менялись. Исторические девять пар на листе — исходный v03 review.')
p('SciPy 1.17.0 / BSD-3-Clause использован из уже установленного G38_work/python_deps для float64 ConvexHull/Qhull. Новых зависимостей в v03d не устанавливалось. Provenance/licence/rollback: '+link(W/'dependency_notes.md')+'. Deliverables не требуют SciPy для использования.')
p('Команды относительно C:/Dev/Game; OUT = ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v03, WORK = Working/Reviews/Operations/organs_v03/G38_work. Генераторы новых model/export revisions отказываются перезаписывать существующие deliverables.')
p('```text\nblender --background OUT/Organs_v03c.blend --python OUT/Scripts/g38_build_colliders_v03d.py\nblender --background WORK/colliders_v03d_01.blend --python OUT/Scripts/g38_fit_v03b.py -- --out WORK/fit_v03d_01.json\nblender --background WORK/colliders_v03d_01.blend --python OUT/Scripts/g38_refine_fit_v03d.py\nblender --background WORK/colliders_v03d_01.blend --python OUT/Scripts/g38_validate_v03b.py -- --out WORK/validation_v03d_01.json\nblender --background WORK/colliders_v03d_01.blend --python OUT/Scripts/g38_package_v03d.py\nblender --background OUT/Organs_v03d.blend --python OUT/Scripts/g38_preservation_audit.py -- --out WORK/preservation_delivered_v03d.json\nblender --background OUT/Organs_v03d.blend --python OUT/Scripts/g38_external_v03d.py\nblender --background --factory-startup --python OUT/Scripts/g38_fbx_roundtrip.py -- --revision v03d\nblender --background --factory-startup --python OUT/Scripts/g38_fbx_visual_preservation_v03d.py\nblender --background OUT/Organs_v03d.blend --python OUT/Scripts/g38_render_colliders_v03d.py\npython OUT/Scripts/g38_compose_sheet_v03d.py\npython OUT/Scripts/g38_write_report_v03d.py\n```')
p('## Файлы')
primary=[O/'Organs_v03d.blend',O/'Organs_InBody_v03d.fbx',O/'FBX/RIBCAGE_v03d.fbx',O/'G38_collisions_manifest_v03d.json',layout_d,O/'G38_CURRENT.json',R/'organs_v03d_ribs_sheet.png',R/'organs_v03d_ribs_sheet_preview.png',R/'G38_REPORT.md',R/'G38_FILES_v03d.txt',R/'G38_FILES.txt',R/'G38_OUTPUT_HASHES.json']
for path in primary:p('- '+link(path))
p('G38_FILES_v03d.txt перечисляет все созданные/изменённые файлы именно этой правки, включая проверки, промежуточный candidate, логи и renders. G38_FILES.txt — полный список всей работы G38 с прежними ревизиями и изолированной зависимостью. v03b/v03c не перезаписаны. Текущий указатель G38_CURRENT.json ведёт на v03d.')
(R/'G38_REPORT.md').write_text(''.join(text),encoding='utf-8')
(O/'G38_CURRENT.json').write_text(json.dumps({'current_revision':'v03d','visual_source_revision':'v03c','rib_pairs':4,'status':'BLENDER_COLLIDER_VALIDATION_PASS','blend':str(O/'Organs_v03d.blend'),'manifest':str(O/'G38_collisions_manifest_v03d.json'),'report':str(R/'G38_REPORT.md'),'supersedes_collision_revision':'v03c','parts_per_rib':10,'render_meshes_changed':False,'body_neck_overlap_accepted':True,'ready_for_unity_integration':True,'unity_runtime_test':'NOT RUN'},indent=2),encoding='utf-8')
files=set(primary)
for folder in (O,O/'FBX',O/'Scripts',O.parent/'Patient_v03',R,W):files.update(p for p in folder.glob('*v03d*') if p.is_file())
files.update(p for p in (R/'G38_v03d_tiles').rglob('*') if p.is_file())
(R/'G38_FILES_v03d.txt').write_text('G38 v03d: created/modified files. No source v03/v03b/v03c or Unity/Assets files changed.\n\n'+'\n'.join(p.as_posix() for p in sorted(files))+'\n',encoding='utf-8')
allfiles=set(files)
for line in (R/'G38_FILES.txt').read_text(encoding='utf-8').splitlines():
    if line.startswith('C:/Dev/Game/'):allfiles.add(Path(line))
(R/'G38_FILES.txt').write_text('G38: created/edited files, including superseded drafts, logs, caches and dependency.\nOnly C:/Dev/Game. Original v03 sources are not modified.\n\n'+'\n'.join(p.as_posix() for p in sorted(allfiles))+'\n',encoding='utf-8')
hashes={'revision':'v03d','outputs':{p.as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)} for p in files if p.exists() and p.name!='G38_OUTPUT_HASHES.json'},'protected_sources_identity':protected,'protected_sources_still_identical':True}
(R/'G38_OUTPUT_HASHES.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
print('V03D_REPORT_DONE',len(files),'revision files;',len(allfiles),'total files;',len(fixed),'exact non-UCX objects',flush=True)
