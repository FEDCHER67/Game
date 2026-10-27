from pathlib import Path
import urllib.request,urllib.parse,http.cookiejar,re,json,io,zipfile,hashlib,subprocess
base=Path(r'C:\Dev\Game'); root=base/'ArtSource/Vehicles_W86'; out=root/'tools'
# Preserve read-only evidence of existing local edits and approved reference assets.
status=subprocess.check_output(['git','-C',str(base),'status','--porcelain=v1','-z']).decode()
paths=[]
for ent in status.split('\0'):
 if len(ent)>3:
  p=base/ent[3:]
  if p.is_file():paths.append(p)
for p in (base/'ArtSource/Props').glob('*ASTRA*'):
 paths += [f for f in p.rglob('*') if f.is_file()]
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
(out/'baseline_v01.json').write_text(json.dumps({'git_status':status,'files_sha256':hashes},indent=2),encoding='utf-8')
s=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
p=s.open('https://quaternius.itch.io/lowpoly-cars/purchase').read().decode(); csrf=re.search(r'name="csrf_token" value="([^"]+)',p).group(1)
u=json.loads(s.open('https://quaternius.itch.io/lowpoly-cars/download_url',urllib.parse.urlencode({'csrf_token':csrf}).encode()).read())['url']
t=s.open(u).read().decode()
print('download links',re.findall(r'href="([^"]+)"[^>]*>Download',t));print('upload ids',re.findall(r'data-upload_id="([^"]+)',t)); print(re.findall(r'.{0,100}1148381.{0,100}',t))
# Store only source-page HTML evidence, no purchase token or signed URLs.
(out/'source_research_v01.json').write_text(json.dumps({'checked':'2026-10-25','Kenney':'https://kenney.nl/assets/car-kit','Quaternius':'https://quaternius.itch.io/lowpoly-cars','licences':'Both asset-specific pages explicitly label CC0; verify included licence before extracting.'},indent=2),encoding='utf-8')
ids=re.findall(r'data-upload_id="([^"]+)',t)
for id in ids[:1]:
 csrf2=re.search(r'name="csrf_token" value="([^"]+)',t).group(1)
 ans=s.open('https://quaternius.itch.io/lowpoly-cars/file/'+id,urllib.parse.urlencode({'csrf_token':csrf2}).encode()).read()
 dl=json.loads(ans)['url']; data=s.open(dl).read(); z=zipfile.ZipFile(io.BytesIO(data))
 print('\n'.join(z.namelist()))
 # Select only 4 picks from this pack after confirming licence. Kept in memory at this stage.
 for n in z.namelist():
  if 'license' in n.lower():print('LICENSE',z.read(n).decode(errors='replace'))
