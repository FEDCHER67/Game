from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,re,collections,hashlib
B=Path(r'C:\Dev\Game');R=B/'ArtSource/Vehicles_W86';P=R/'previews';specs=json.loads((R/'selected_models_v01.json').read_text());picks=json.loads((R/'picks_v01.json').read_text());m1=json.loads((B/'Assets/OnlyVolunteers/Map/W85Build/Editor/W86Data/MODELS_M1.json').read_text())
def link(p,label=None):return f'[{label or Path(p).name}]({Path(p).as_posix()})'
def fnt(n,b=False):return ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf' if b else r'C:\Windows\Fonts\arial.ttf',n)
# Inventory of builder-resolved models, rather than hypothetical prefab names.
rows=[];imgs=[]
for k,n,img in [('car_sedan_blue',1260,'01_VK_Car_Sedan_Blue.png'),('car_sedan_red',1260,'02_VK_Car_Sedan_Red.png'),('car_sedan_beige',1260,'03_VK_Car_Sedan_Beige.png'),('car_sedan_green',1260,'04_VK_Car_Sedan_Green.png'),('car_hatchback',952,'05_VK_Car_Hatchback.png')]:
 prefab=B/f'Assets/OnlyVolunteers/Art/Map/Prefabs/CARS/{k}.prefab';preview=B/f'ArtSource/Props/VEHICLES_KIT/CARS/Previews/v01/{img}';rows.append((k,str(prefab),n,str(preview)));imgs.append((k,preview))
rows.append(('rusted_car / rusty_car_body',str(B/'Assets/OnlyVolunteers/Art/Map/Prefabs/WRECKS/car_wrecked.prefab'),1128,str(R/'tools/current_previews_v01/car_wrecked.png')));imgs.append(('car_wrecked',R/'tools/current_previews_v01/car_wrecked.png'))
# Exact wreck count from serialized mesh indices.
w=(B/'Assets/OnlyVolunteers/Art/Map/Prefabs/Meshes/car_wrecked.asset').read_text();wrecktris=int(re.search(r'indexCount: (\d+)',w).group(1))//3;rows[-1]=(rows[-1][0],rows[-1][1],wrecktris,rows[-1][3])
for kind,name in [('dump_truck','MW86_DumpTruck'),('concrete_mixer_truck','MW86_MixerTruck'),('military_cargo_truck','MW86_MilTruck'),('truck_with_container','MW86_TruckContainer'),('food_truck','MW86_FoodTruck'),('van_on_jacks','MW86_VanOnJacks'),('black_suv','MW86_SUV_Black')]:
 model=m1['models'][name];preview=R/'tools/research_previews_v01'/(name+'.png')
 if name in ['MW86_FoodTruck','MW86_MixerTruck','MW86_SUV_Black']:preview=R/'tools/current_previews_v01'/(name+'.png')
 if name=='MW86_VanOnJacks':preview=R/'tools/review_cells_v01/PANEL_VAN_current.png'
 rows.append((kind,str(B/model['fbx']),model['lod']['LOD0_tris'],str(preview)));imgs.append((name,preview))
text=['# Current world vehicle inventory — G47 / 2026-10-25','', 'Read-only inventory from the W85/W86 source builders and Data/v02. M1 vehicles are instantiated from FBX by W86Models, not separate named prefab assets. No Unity editor was opened.','', '| Data kind | Current prefab / FBX (absolute) | LOD0 tris | Blender / existing preview |','|---|---|---:|---|']
for k,p,n,img in rows:
 assert Path(p).is_file() and Path(img).is_file(),(p,img)
 text.append(f'| {k} | {link(p)} | {n} | {link(img)} |')
text += ['', '## Resolution rules and source evidence','',f'- {link(B/"Assets/OnlyVolunteers/Map/W85Build/Editor/W85Builder.cs")}: PrefabOf at lines 2019–2021 maps four sedan colours and the hatchback; old_soviet_car also maps to car_hatchback; rusted_car and rusty_car_body map to car_wrecked. The blue-sedan black_suv fallback is overridden by the M1 instance mapping.',f'- {link(B/"Assets/OnlyVolunteers/Map/W85Build/Editor/W86Districts.cs")}: parked_car at line 210 selects the nearest of those same five passenger-car prefabs from tint.',f'- {link(B/"Assets/OnlyVolunteers/Map/W85Build/Editor/W86Models.cs")}: M1ById takes precedence before PrefabOf. The exact FBX, instances, LOD counts and rotations are in {link(B/"Assets/OnlyVolunteers/Map/W85Build/Editor/W86Data/MODELS_M1.json")}.','', '## Placement counts','']
allcounts={}
def walk(o,c):
 if isinstance(o,dict):
  k=o.get('kind','')
  if k in [r[0] for r in rows]+['old_soviet_car','rusted_car','rusty_car_body','parked_car']:c[k]+=1
  for v in o.values():walk(v,c)
 elif isinstance(o,list):
  for v in o:walk(v,c)
for path in (B/'Assets/OnlyVolunteers/Map/W85Build/Data/v02').rglob('*.json'):
 c=collections.Counter();walk(json.loads(path.read_text(encoding='utf-8-sig')),c)
 if c:allcounts[str(path)]=dict(c);text.append('- '+link(path)+': '+', '.join(f'{k} = {v}' for k,v in c.items()))
text += ['', '## Downtown and vans: explicit integration limits','', 'No distinct display_car / parked_van placement kind was found in the searched builders and data. There are ordinary Downtown parked cars in details_v85.json. Proposed display bases are props[10] car_sedan_beige at [1011, 514.8] and props[12] car_sedan_green at [1068, 514.8], both on 05-street-N0c. These are proposals, not existing showroom instances. The selected static Astra van is a world-ready reusable candidate; its eventual placement is not yet assigned. The existing van_on_jacks and food trucks retain their workshop/food-service roles.', '', 'Reuse unchanged for now: military truck, mixer, food trucks, SUV and wrecks. Selected replacements: the two ordinary-car families, the dump truck and container truck. All swaps remain subject to Fedya approval and Step 2.','',link(P/'current_vehicles_v01.png','Contact sheet of all inventoried current models')]
(R/'CURRENT_VEHICLES.md').write_text('\n'.join(text)+'\n',encoding='utf-8');(R/'current_vehicle_counts_v01.json').write_text(json.dumps(allcounts,indent=2),encoding='utf-8')
# One current-model contact sheet including unchanged specialised vehicles.
canvas=Image.new('RGB',(1800,80+460*math.ceil(len(imgs)/3)),'#202A33') if False else Image.new('RGB',(1800,80+460*((len(imgs)+2)//3)),'#202A33');d=ImageDraw.Draw(canvas);d.text((20,20),'[G47] Текущие модели сборщиков W85/W86 · без изменений',font=fnt(29,True),fill='white')
for i,(name,path) in enumerate(imgs):
 x=(i%3)*600;y=80+(i//3)*460;im=Image.open(path).convert('RGB');im.thumbnail((600,400));canvas.paste(im,(x+(600-im.width)//2,y+45));d.text((x+15,y+8),name,font=fnt(23,True),fill='white')
canvas.save(P/'current_vehicles_v01.png')
# Current six-side/LOD inspection of the selected revisions only.
raw=Image.open(R/'tools/technical_views_raw_v03.png').convert('RGB');out=Image.new('RGB',(raw.width+270,raw.height+100),'#202A33');out.paste(raw,(270,100));d=ImageDraw.Draw(out)
for i,n in enumerate(['ФРОНТ','СЗАДИ','СБОКУ +X','СБОКУ -X','СВЕРХУ','СНИЗУ','LOD1','LOD2']):d.text((280+i*360,25),n,font=fnt(21),fill='white')
for i,p in enumerate(specs):d.text((10,110+i*240),p['name']+f" v{p['revision']:02}",font=fnt(20),fill='white')
out.save(P/'technical_views_v02.png')
# Sources and licences, including measured counts rather than advertised face counts.
source=['# G47 / W86 vehicle provenance','', 'Checked 2026-10-25. Zero payments, credits, AI generation or paid assets. External models were obtained only from the author download pages below. ZIP archives were inspected in memory; only the initially picked OBJ/MTL files, their needed atlas and licence files were saved. Kenney van was subsequently rejected after visual comparison; its working revisions are retained but excluded from selected_models_v01.json.','', '| Source model / candidate | Author | Asset-specific licence | Source triangles (Blender) | Use / decision | Source |','|---|---|---|---:|---|---|']
rawcounts={'SEDAN':2954,'COMPACT':3124,'DISPLAY_COUPE':3078,'DISPLAY_GT':3148,'PANEL_VAN':2082,'FLATBED':2487,'BOX_TRUCK':2082,'ASTRA_STATIC_VAN':2514}
for p in picks:
 decision='Body selected' if p['author']=='Quaternius' else 'Wheel donor only; preserve the W86 specialised body' if 'reuse_source' in p else 'Approved local body reused as a static world copy' if p['name']=='ASTRA_STATIC_VAN' else 'Rejected after render; prefer approved Astra van'
 source.append(f'| {Path(p["source"]).stem} / {p["name"]} | {p["author"]} | {p["licence"]} | {rawcounts[p["name"]]} | {decision} | '+(f'[{p["url"]}]({p["url"]})' if p['url'].startswith('http') else link(p['source']))+' |')
 if 'reuse_source' in p:
  dest=R/p['name']/'source/LOCAL_REFERENCE.md';dest.write_text('Local project body reused read-only: '+p['reuse_source']+'\nAuthoring source: C:\\Dev\\Game\\ArtSource\\Props\\MAP_W86_v01\\vehicles\\build_machines.py\nProject asset; no CC0 claim for the body. Kenney wheel donor is CC0-1.0.\n',encoding='utf-8')
source += ['', '## Licence evidence','', '- [Kenney Car Kit official page](https://kenney.nl/assets/car-kit): Creative Commons CC0. Author: Kenney. Included License.txt files are kept with the picked sources.', '- [Quaternius LowPoly Cars author download](https://quaternius.itch.io/lowpoly-cars): explicit CC0-1.0; itch upload 1148381, Realistic Car Pack – Nov 2018. The archive License.txt explicitly states CC0-1.0 and is stored separately for each selected car. The broader current Quaternius site licence is not used to make a library-wide claim.', '- [Quaternius Cars pack page](https://quaternius.com/packs/cars.html) also identifies this pack as CC0.', '- [CC0-1.0 legal instrument](https://creativecommons.org/publicdomain/zero/1.0/) permits the selected intended reuse and modification. Attribution is not required; author credits are retained in THIRD_PARTY_NOTICES.md.', '', '## Local bodies and style references','', '- Dump truck body: '+link(B/'ArtSource/Props/MAP_W86_v01/vehicles/dump_truck/MW86_DumpTruck_v01.blend')+' — 1380 original triangles; rebuilt wheel assemblies use Kenney geometry.', '- Container truck body: '+link(B/'ArtSource/Props/MAP_W86_v01/vehicles/truck_container/MW86_TruckContainer_v01.blend')+' — 3492 original triangles; cab/chassis/container roles and measured axle bounds retained.', '- Approved van: '+link(B/'ArtSource/Props/VAN-TIER0-ASTRA-001/VAN-TIER0-ASTRA-001_v02.blend')+'; ownership/approval context: '+link(B/'ArtSource/Props/VAN-TIER0-ASTRA-001/PRODUCTION_REPORT.md')+'. No controller, handling, door script, cargo or upgrade changes.', '- Approved scale/style prop: '+link(B/'ArtSource/Props/FRIDGE-ASTRA-001/G34_v02/FRIDGE_ASTRA_001_v02.blend')+'. Existing Astra files are read-only.', '', '## Archive integrity','']
for author in ['Quaternius','Kenney']:
 p=next(p for p in picks if p['author']==author);source.append(f'- {author} downloaded ZIP SHA-256: `{p["archive_sha256"]}`.')
source += ['', 'Original source hashes and the complete absolute output list are in FILES_CREATED_OR_CHANGED.md / file_manifest_v01.json. No unknown-licence model was imported.']
(R/'SOURCES.md').write_text('\n'.join(source)+'\n',encoding='utf-8')
(R/'THIRD_PARTY_NOTICES.md').write_text('''# Third-party notices — W86 vehicles / G47

Quaternius — LowPoly Cars / Realistic Car Pack, Nov 2018.
Source: https://quaternius.itch.io/lowpoly-cars
Selected bodies: NormalCar1, NormalCar2, SportsCar, SportsCar2.
Asset-specific licence: CC0 1.0 Universal.
https://creativecommons.org/publicdomain/zero/1.0/
Original author licence files: each selected source/License.txt.

Kenney — Car Kit.
Source: https://kenney.nl/assets/car-kit
Selected donor geometry: wheel-front-right from truck-flat and truck, adapted to the original W86 truck axle positions/bounds and mirrored for the other side.
Asset-specific licence: Creative Commons Zero / CC0 1.0 Universal.
https://creativecommons.org/publicdomain/zero/1.0/
Original author licence files: FLATBED/source/License.txt and BOX_TRUCK/source/License.txt.
The van source and experimental adaptations remain only as rejected research, under the same CC0 licence.

Both authors label the downloaded assets CC0. Credits are retained voluntarily; no external model in this delivery has a share-alike or attribution obligation. No payment was made. No branded names, logos or number-plate text were added.

Existing Only Volunteers / Astra bodies, the W86 specialised truck bodies, project palette and local adaptations remain internal project assets. Their reuse does not dedicate them to CC0. The original approved project sources were not modified. The CC0 statements above apply only to the named third-party sources.
''',encoding='utf-8')
# Only the current seven selected revisions form the reviewable package.
readme=['# G47 W86 world vehicles — Step 1 review package','', '**STOP: no Unity import or map changes until Fedya sends go.**','', 'Integration allowlist: selected_models_v01.json. Earlier numbered revisions and PANEL_VAN are working history, not integration candidates. The v01 sources/exports are preserved; technical and visual repairs use distinct numbered revisions. Never import whole directories blindly.','', '| Selected asset | LOD0 / LOD1 / LOD2 triangles | Blender | Visual FBX | Collision FBX | Collision JSON |','|---|---|---|---|---|---|']
for p in specs:
 root=Path(p['folder']);n=p['name'];v=f'v{p["revision"]:02}';readme.append(f'| {n} | '+ ' / '.join(map(str,p['lod_triangles']))+' | '+' | '.join(link(root/f'{n}{s}_{v}.{e}') for s,e in [('', 'blend'),('', 'fbx'),('_collisions','fbx'),('_collisions','json')])+' |')
readme += ['', '## Material and geometry conventions','', 'One shared material MAT_W86_VehiclePalette_v01; shared/W86_VehiclePalette_v01.png is sRGB BaseMap; shared/W86_VehicleSurface_v01.png is linear packed R=metallic, G=roughness, A=smoothness. Both are 128×64. Use Point, Clamp and mipmaps off for this face-centred palette. Bind both maps explicitly in the existing URP Lit workflow at Step 2: FBX does not reproduce the Blender node graph automatically. Glass is opaque dark blue with controlled highlights for static props.', '', 'Metres; Blender Z-up, nose -Y; origin at the visual footprint base centre; visual object transforms applied. Export: axis_forward=-Z, axis_up=Y, FBX_SCALE_ALL, apply units, bake_space_transform, no animation. There are three independent LOD meshes per visual FBX; Step 2 must create/configure LODGroup explicitly (suggested initial screen heights 0.35 / 0.12 / 0.035; tune in scene).', '', 'Collision FBXs are separate. UCX objects are convex boxes, all checked closed and convex; each JSON contains Blender and proposed Unity-local centres/sizes. UCX names alone do not create Unity colliders. Use the JSON to add BoxColliders, or explicitly instantiate convex MeshColliders and disable UCX rendering. Never render/import collision files as visible vehicles.', '', 'Static render surfaces retain a few source contact edges: COMPACT and DISPLAY_COUPE have two four-face contacts each; Astra retains source part-contact edges. These are separate from the validated closed convex collision meshes. Render meshes have no open boundary or degenerate triangles in the selected LOD0s. Strict watertight render-topology approval is not claimed.', '', 'The approved Astra body remains 2554 triangles after closing the original glass panes, below the approximate 3k target; it was deliberately reused rather than padded. Other selected LOD0s are approximately 3k–6.7k. Materials and LOD appearance still need Unity verification after approval.', '', '## Review and evidence','',link(B/'Working/Reviews/W86Polish_2026-10-25/vehicles_v01.png','Approval comparison sheet')+' · '+link(P/'current_vehicles_v01.png','Current builder vehicles')+' · '+link(P/'technical_views_v02.png','Six-side / LOD inspection'),'',link(R/'roundtrip_validation_v01.json','FBX roundtrip check')+' · '+link(R/'CURRENT_VEHICLES.md','Builder inventory')+' · '+link(R/'SOURCES.md','Sources')+' · '+link(R/'THIRD_PARTY_NOTICES.md','Notices'),'', 'Verification command (read-only Blender FBX reimport):', '', '"C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" -b --factory-startup --python "C:\\Dev\\Game\\ArtSource\\Vehicles_W86\\tools\\verify_roundtrip_v01.py"','', 'NOT RUN: Unity import, live shader/material binding, culling/LOD transitions, driving or performance tests. These belong to Step 2 after explicit go and unity_lock.ps1 -Id G47.']
(R/'README.md').write_text('\n'.join(readme)+'\n',encoding='utf-8')
print('Inventory:',len(rows),'current model entries. Selected:',len(specs))
