from pathlib import Path
import urllib.request,urllib.parse,http.cookiejar,re,json,io,zipfile,hashlib
root=Path(r'C:\Dev\Game\ArtSource\Vehicles_W86')
s=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
p=s.open('https://quaternius.itch.io/lowpoly-cars/purchase').read().decode(); csrf=re.search(r'name="csrf_token" value="([^"]+)',p).group(1)
u=json.loads(s.open('https://quaternius.itch.io/lowpoly-cars/download_url',urllib.parse.urlencode({'csrf_token':csrf}).encode()).read())['url']
t=s.open(u).read().decode(); csrf=re.search(r'name="csrf_token" value="([^"]+)',t).group(1)
u=json.loads(s.open('https://quaternius.itch.io/lowpoly-cars/file/1148381',urllib.parse.urlencode({'csrf_token':csrf}).encode()).read())['url']
qdata=s.open(u).read(); q=zipfile.ZipFile(io.BytesIO(qdata)); lic=q.read('Realistic Car Pack - Nov 2018/License.txt'); assert b'CC0 1.0' in lic
kurl='https://kenney.nl/media/pages/assets/car-kit/1a312ec241-1775131960/kenney_car-kit.zip';kdata=s.open(kurl).read();k=zipfile.ZipFile(io.BytesIO(kdata)); klic=k.read('License.txt');assert b'CC0' in klic
picks=[]
for name,slug,category,target,color in [('NormalCar1','SEDAN','car','car_sedan_*','#5A7FA6'),('NormalCar2','COMPACT','car','car_hatchback / old_soviet_car','#A8504A'),('SportsCar','DISPLAY_COUPE','display','Downtown parked-car proposal A','#C9B79A'),('SportsCar2','DISPLAY_GT','display','Downtown parked-car proposal B','#6F8F6A')]:
 d=root/slug/'source';d.mkdir(parents=True)
 for ext in ['obj','mtl']:(d/(name+'.'+ext)).write_bytes(q.read(f'Realistic Car Pack - Nov 2018/OBJ/{name}.{ext}'))
 (d/'License.txt').write_bytes(lic)
 picks.append(dict(name=slug,category=category,source=str(d/(name+'.obj')),author='Quaternius',licence='CC0-1.0',url='https://quaternius.itch.io/lowpoly-cars',color=color,target=target,archive_sha256=hashlib.sha256(qdata).hexdigest()))
for name,slug,category,target,color in [('van','PANEL_VAN','van','Additional static van; no generic parked van currently found','#C9B79A'),('truck-flat','FLATBED','truck','World flatbed candidate; no exact flatbed kind currently found','#6F8F6A'),('truck','BOX_TRUCK','truck','World delivery truck candidate; preserve dedicated M1 machinery','#5A7FA6')]:
 d=root/slug/'source';d.mkdir(parents=True)
 for ext in ['obj','mtl']:
  member=f'Models/OBJ format/{name}.{ext}';(d/(name+'.'+ext)).write_bytes(k.read(member))
 (d/'License.txt').write_bytes(klic)
 # referenced atlas, only if used by the selected material
 mtl=(d/(name+'.mtl')).read_text();print(name,mtl[:600])
 for member in k.namelist():
  if member.endswith('colormap.png') and 'OBJ' in member:
   (d/'Textures').mkdir(exist_ok=True);(d/'Textures/colormap.png').write_bytes(k.read(member));break
 picks.append(dict(name=slug,category=category,source=str(d/(name+'.obj')),author='Kenney',licence='CC0-1.0',url='https://kenney.nl/assets/car-kit',color=color,target=target,archive_sha256=hashlib.sha256(kdata).hexdigest()))
d=root/'ASTRA_STATIC_VAN'/'source';d.mkdir(parents=True)
ref=Path(r'C:\Dev\Game\ArtSource\Props\VAN-TIER0-ASTRA-001\VAN-TIER0-ASTRA-001_v02.blend')
(d/'LOCAL_REFERENCE.md').write_text('Approved project-owned model, reused read-only. Source: '+str(ref)+'\nNo CC0 claim. No controller/animation is copied.\n',encoding='utf-8')
picks.append(dict(name='ASTRA_STATIC_VAN',category='van',source=str(ref),author='Only Volunteers / Astra',licence='Project-owned (see original PRODUCTION_REPORT.md)',url='local project source',color='#C9B79A',target='Static world variant of approved Astra van; player van unchanged'))
(root/'picks_v01.json').write_text(json.dumps(picks,indent=2),encoding='utf-8')
print('Saved',len(picks),'picks. Kenney files', [n for n in k.namelist() if 'colormap' in n])
