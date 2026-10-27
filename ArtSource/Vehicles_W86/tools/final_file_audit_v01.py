from pathlib import Path
import json,hashlib,re
B=Path(r'C:\Dev\Game').resolve();R=B/'ArtSource/Vehicles_W86';D=B/'Working/Reviews/W86Polish_2026-10-25';manifest=R/'file_manifest_v01.json';listing=R/'FILES_CREATED_OR_CHANGED.md'
manifest.touch(exist_ok=False);listing.touch(exist_ok=False)
files=sorted([p.resolve() for p in R.rglob('*') if p.is_file()]+[(D/'vehicles_v01.png').resolve(),(D/'G47_REPORT_RU.md').resolve()],key=lambda p:str(p).lower())
records=[]
for p in files:
 inside=p.is_relative_to(B);exists=p.is_file();assert inside and exists,p
 records.append({'path':str(p),'exists':exists,'inside_C_Dev_Game':inside,'sha256':None if p in [manifest,listing] else hashlib.sha256(p.read_bytes()).hexdigest()})
manifest.write_text(json.dumps({'file_count':len(records),'all_exist_under_C_Dev_Game':True,'note':'All files created or changed by G47. Includes retained numbered experiments, scripts, logs and Python cache files; only selected_models_v01.json defines integration candidates. The two self-referential inventory files have no hash.','files':records},indent=2),encoding='utf-8')
text=['# [G47] Полный список созданных / изменённых файлов','',f'Всего: **{len(records)}**. Каждый путь абсолютный; для каждого проверены существование и нахождение внутри **C:\\Dev\\Game**. Статус всех строк: **EXISTS / UNDER C:\\Dev\\Game — PASS**.','', 'Новая папка ArtSource/Vehicles_W86 отсутствовала до начала работы. В ней сохранены выбранные модели, исходники, номерные эксперименты, превью, скрипты, журналы и кэш Python. В Working созданы только указанные ниже vehicles_v01.png и G47_REPORT_RU.md. Существующие файлы проекта G47 не редактировал. Хеши содержимого: file_manifest_v01.json.','', '| Абсолютный путь | Существует | Внутри C:\\Dev\\Game |','|---|---|---|']
for q in records:text.append(f'| `{q["path"]}` | PASS | PASS |')
listing.write_text('\n'.join(text)+'\n',encoding='utf-8')
assert all(Path(q['path']).is_file() and Path(q['path']).is_relative_to(B) for q in records)
# Verify active package and local documentation references.
specs=json.loads((R/'selected_models_v01.json').read_text());roundtrip=json.loads((R/'roundtrip_validation_v01.json').read_text());assert len(specs)==7 and all(q['PASS'] for q in roundtrip)
for p in specs:
 for k,f in p['files'].items():assert Path(f).is_file() and Path(f).is_relative_to(R),(k,f)
for doc in [R/'README.md',R/'SOURCES.md',R/'CURRENT_VEHICLES.md',D/'G47_REPORT_RU.md']:
 for target in re.findall(r'\]\((C:/[^)]+)\)',doc.read_text(encoding='utf-8')):assert Path(target).is_file(),(doc,target)
print('FILES',len(records),'all exist and inside',str(B));print('SELECTED PACKAGE 7 / 7 roundtrip PASS; local document links PASS')
