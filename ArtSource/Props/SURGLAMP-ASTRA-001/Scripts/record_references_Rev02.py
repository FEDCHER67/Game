from pathlib import Path
import hashlib,json,shutil,struct
root=Path(r'C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001')
downloads=Path(r'C:\Users\Zeyo-ne\Downloads')
entries=[('FRONT','01_front.png','Минималистичная хирургическая лампа на колёсах.png','Rev01','chatgpt_front_Rev01_proof.png'),('LEFT','02_left.png','Медицинская лампа на колёсной стойке.png','Rev02','chatgpt_left_Rev02_proof.png'),('RIGHT','03_right.png','Медицинский светильник на четырёх колёсах.png','Rev02','chatgpt_right_Rev02_proof.png'),('BACK','04_back.png','Медицинская лампа_ вид сзади.png','Rev02','chatgpt_back_Rev02_proof.png')]
views=[]
for view,filename,original,revision,proof in entries:
 src=downloads/original;dst=root/'TripoViews/Rev02'/filename
 if dst.exists():assert dst.read_bytes()==src.read_bytes()
 else:shutil.copyfile(src,dst)
 b=dst.read_bytes();assert b[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',b[16:24])
 assert w==h==1254 and (root/'Source'/proof).is_file()
 views.append({'view':view,'file':f'TripoViews/Rev02/{filename}','original_download':original,'generator_revision':revision,'width':w,'height':h,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'byte_identical':True,'browser_proof':f'Source/{proof}'})
rejected=root/'TripoViews/Rev01/02_left.png'
manifest={'asset':'SURGLAMP-ASTRA-001','reference_revision':'Rev02','date':'2026-10-05','approval':'awaiting explicit Claude/Fedya approval of this exact four-view pack','generator':'ordinary ChatGPT browser UI','conversation':'https://chatgpt.com/g/g-p-6aadbaaa21c081918dcf9006013794cd-only-volunteers/c/6aadbae4-9db8-83eb-b549-cced1b1c33b2','local_image_edits':False,'generation_chain':'FRONT new request; LEFT Rev01 from FRONT rejected; LEFT Rev02 from FRONT; RIGHT Rev02 from LEFT Rev02; BACK Rev02 from FRONT','front_revision_reused':'Rev01 FRONT copied byte-identically into exact Rev02 pack','views':views,'rejected_views':[{'file':'TripoViews/Rev01/02_left.png','reason':'three-quarter head angle shows too much diffuser; superseded by edge-on LEFT Rev02','sha256':hashlib.sha256(rejected.read_bytes()).hexdigest()}],'tripo_generations':0,'tripo_credits_spent':0,'last_confirmed_balance':180,'target_triangles':[600,1200],'nominal_height_m':1.7,'nominal_base_width_m':.65,'planned_create_credits':100,'planned_balance_after_generation':80,'notes':'Original PNGs are artistic orthographic approximations, with minor framing variations; no pixel-exact CAD equivalence claimed.'}
(root/'Source/reference_manifest_Rev02.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(root/'README.md').write_text('''# SURGLAMP-ASTRA-001 — комплект Rev02 на утверждение

Мобильная операционная лампа: круглый белый плафон с голубым кантом и кремовым рассеивателем, одна металлическая стойка, толстый гибкий белый кронштейн, белая крестовая база на четырёх чёрных колёсиках. Чистый мультяшный стиль со слегка пухлыми формами. Номинальная высота1.7м, ширина основания65см. Плановый бюджет Blender600–1200тр.

## Точный комплект

Все файлы `TripoViews/Rev02/`,1254×1254, исходники обычного ChatGPT без локальной правки:

| Слот | Файл | Содержание |
| --- | --- | --- |
| FRONT | `01_front.png` | Исходный FRONT Rev01: круглый рассеиватель, голубой кант. |
| LEFT | `02_left.png` | Исправленный LEFT Rev02: плафон слева от стойки, светящаяся поверхность ребром. |
| RIGHT | `03_right.png` | RIGHT Rev02: противоположный профиль, плафон справа. |
| BACK | `04_back.png` | BACK Rev02: белая закрытая крышка, стойка перед ней, рассеиватель скрыт. |

Первый LEFT Rev01 с лишней видимой плоскостью рассеивателя сохранён и исключён из комплекта. FRONT перенесён в папку Rev02 побайтно; LEFT/RIGHT/BACK сгенерированы отдельно. Все четыре PNG проверены на идентичность оригинальным Download. SHA256 и browser-proof — в `Source/reference_manifest_Rev02.json`.

Точный комплект показан здесь для явного «ок» Claude/Феди. **Tripo ещё не запускался, расход0, баланс180.** После утверждения разрешена одна генерация Create ровно100 с согласованными Smart Mesh/quads/P2.0; плановый остаток80. Полигональность снижать локально в Blender. Без повторов, платных опций, коммитов и правок WORK_SYNC.md.
''',encoding='utf-8')
(root/'PROVENANCE.md').write_text('''# SURGLAMP-ASTRA-001 — происхождение ракурсов Rev02

05.10.2026, обычный ChatGPT в браузере, чат «Федя чат»:
https://chatgpt.com/g/g-p-6aadbaaa21c081918dcf9006013794cd-only-volunteers/c/6aadbae4-9db8-83eb-b549-cced1b1c33b2

FRONT создан новым запросом. Первый запрос закончился ошибкой, штатный повтор дал FRONT Rev01. От выбранного FRONT создан LEFT Rev01; он отклонён локальным визуальным осмотром из-за ракурса три четверти. Новый LEFT Rev02 создан от FRONT, с видимым ребром плафона. От выбранного LEFT Rev02 создан противоположный RIGHT Rev02. BACK Rev02 создан от выбранного FRONT.

Каждый результат скачан штатной кнопкой Download. Все исходные PNG1254×1254 скопированы побайтно без локального зеркалирования, обрезки, масштабирования, ретуши или изменения фона. FRONT Rev01 повторно использован в папке точного комплекта Rev02 без изменений; не генерировался повторно. Имена скачиваний, SHA256 и размеры — `Source/reference_manifest_Rev02.json`. `Source/chatgpt_front_Rev01_proof.png`, `chatgpt_left_Rev02_proof.png`, `chatgpt_right_Rev02_proof.png`, `chatgpt_back_Rev02_proof.png` показывают эти изображения в просмотрщике браузера.

Отклонённый LEFT сохранён в `TripoViews/Rev01/02_left.png`, его снимок — `Source/chatgpt_left_rejected_Rev01_proof.png`; не загружать его в Tripo. Художественные проекции содержат небольшие различия кадрирования и не являются точными CAD-проекциями.

Точный комплект Rev02 ожидает явного утверждения Claude/Феди здесь. Генераций Tripo0, расход0, текущий подтверждённый баланс180. Одна дальнейшая генерация за100 разрешается только после «ок» на этот комплект. Бюджет600–1200тр., снижение полигонов только локальное. Коммитов/WORK_SYNC-правок нет.
''',encoding='utf-8')
(root/'REPORT.md').write_text('''# SURGLAMP-ASTRA-001 — ракурсы Rev02, 05.10.2026

Четыре отдельные исходные PNG1254×1254 готовы для приёмки. FRONT из Rev01, остальные из Rev02. Проверена побайтная идентичность каждого оригинальному Download; SHA256 и browser-proof сохранены.

Визуальный осмотр: круглый рассеиватель и голубой кант только спереди; в LEFT/RIGHT плафон виден ребром и меняет сторону относительно стойки, наклоны противоположны. BACK показывает закрытую белую крышку без света, стойка перекрывает нижнюю центральную часть. На всех видах одна стойка, один плафон, один гибкий кронштейн, четыре ноги и четыре колёсика; пропорции и стиль близки. Небольшие художественные различия кадрирования сохранены в исходниках. LEFT Rev01 был три четверти; сохранён как отклонённый, в текущий комплект не входит.

**Ожидается явное «ок» Claude/Феди на точный Rev02. Tripo не запускался, расход0, баланс180.** После приёмки: одна Create100, Smart Mesh/quads/P2.0, очистка слотов, неизменённый FBX в Working/Tripo, локальная доводка до600–1200тр. Плановый остаток80. Это последняя модель текущей партии; повторных генераций и платных опций нет. Без коммитов/WORK_SYNC.
''',encoding='utf-8')
p=root.parent/'TRIPO_BATCH_2026-10-05.md';s=p.read_text(encoding='utf-8')
old='| 6 | SURGLAMP-ASTRA-001 | 600–1200 | Not started. |'
new='| 6 | SURGLAMP-ASTRA-001 | 600–1200 | Exact four-view Rev02 pack ready in ordinary ChatGPT: unchanged FRONT Rev01 reused, corrected edge-on LEFT Rev02, opposite RIGHT Rev02, closed rear BACK Rev02; four1254px originals, hashes and browser-proof saved. First LEFT Rev01 preserved as rejected three-quarter view. Pack shown here; awaiting explicit Claude/Fedya approval. No Tripo generation or expenditure; balance180. |'
assert old in s;s=s.replace(old,new);p.write_text(s,encoding='utf-8')
print(json.dumps({'views':len(views),'dimensions':[1254,1254],'byte_identical':True,'balance':180,'tripo_generations':0,'approval':'pending'}))
