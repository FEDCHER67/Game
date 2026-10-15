from pathlib import Path
import json,hashlib,re,uuid
r=Path('C:/Dev/Game');s=Path(__file__).parent
for name in ['Models','Preview','WindMaterials']:(s/name).mkdir(parents=True,exist_ok=True)
paths=set(json.loads((r/'Working/Reviews/Trees/i09/protected_before.json').read_text()))
for folder in ['Assets/OnlyVolunteers/Art/Trees/OaksPines_i09','ArtSource/Dev/Trees_staging/i09_v01']:
    paths.update(p.relative_to(r).as_posix() for p in (r/folder).rglob('*') if p.is_file())
for p in (r/'Assets/OnlyVolunteers/Scenes/Map').glob('*'):
    if p.is_file():paths.add(p.relative_to(r).as_posix())
p=s/'protected_before_v01.json';assert not p.exists();p.write_text(json.dumps({p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in sorted(paths)},indent=2))
palette={'Bark':'#76503E','LeafDark':'#3A6E38','LeafPine':'#2C6042'}
shader='Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Shaders/GenericFoliageWind_v03.shader'
guid=re.search(r'guid: (\w+)',(r/(shader+'.meta')).read_text())[1]
profile={'_WindResponse':.028,'_FlexibleHeight':24.3,'_UseVertexMask':0,'_UseVertexTint':0,'_Cutoff':0,'_Cull':2,'_TipFlash':.025}
remaps={}
template=(r/'ArtSource/Dev/Trees_staging/oaks_pines_v01/WindMaterials/Pine_LeafPine_Wind_v01.mat').read_text()
for slot,color in palette.items():
    name=f'PineTall_{slot}_Wind_v01';text=re.sub(r'm_Name: .*','m_Name: '+name,template)
    text=re.sub(r'm_Shader: .*',f'm_Shader: {{fileID: 4800000, guid: {guid}, type: 3}}',text)
    for key,value in profile.items():text=re.sub(r'(- '+key+r': )[^\n]*',lambda m:m[1]+str(value),text)
    rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    text=re.sub(r'(- _BaseColor: ).*',lambda m:m[1]+f'{{r: {rgb[0]}, g: {rgb[1]}, b: {rgb[2]}, a: 1}}',text)
    p=s/'WindMaterials'/(name+'.mat');assert not p.exists();p.write_text(text)
    p.with_suffix('.mat.meta').write_text('fileFormatVersion: 2\nguid: '+uuid.uuid4().hex+'\nNativeFormatImporter:\n  externalObjects: {}\n  mainObjectFileID: 2100000\n')
    remaps['MAT_'+slot+'_pine_tall_v01']='WindMaterials/'+p.name
(s/'wind_bindings_v01.json').write_text(json.dumps({'shader':'OnlyVolunteers/Wind/v03/GenericFoliageScaled','shader_guid':guid,'shared_include':'Assets/OnlyVolunteers/Map/Wind/v01/Shaders/V19Wind.hlsl','profiles':{'PineTall':profile},'material_remaps':{'PineTall':remaps},'status':'STAGED ONLY. No Unity import or scene placement. Uses existing shared gust field, stiff material profile and instance-height scaling.'},indent=2))
print('Protected',len(paths),'files; three stiff shared-wind materials staged outside Assets.')
