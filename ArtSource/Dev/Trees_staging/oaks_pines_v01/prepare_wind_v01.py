from pathlib import Path
import json,re,uuid
root=Path(__file__).parent;game=root.parents[3]
template=(game/'Assets/OnlyVolunteers/Map/Wind/v01/Materials/GenericFoliageWind_v01.mat').read_text()
shader=(game/'Assets/OnlyVolunteers/Map/Wind/Trees_v01/Shaders/GenericFoliageWind_v02.shader.meta').read_text()
guid=re.search(r'guid: ([0-9a-f]+)',shader)[1]
data=json.loads((root/'validation_v01.json').read_text());palette=data['palette'];med=json.loads((root/'map_sizes_v01.json').read_text())['summary']
settings={'Oak':(.055,med['Oak']['heightMedian']*1.02,['Bark','LeafDark','Leaf','LeafLight']),
          'Pine':(.028,med['Pine']['heightMedian']*1.35,['Bark','LeafDark','LeafPine'])}
mapping={};profiles={}
for family,(response,height,slots) in settings.items():
    mapping[family]={};profiles[family]={'_WindResponse':response,'_FlexibleHeight':height,'_UseVertexMask':0,'_UseVertexTint':0,'_Cutoff':0,'_Cull':2,'_TipFlash':.025}
    for slot in slots:
        name=f'{family}_{slot}_Wind_v01';text=template.replace('m_Name: GenericFoliageWind_v01','m_Name: '+name)
        text=re.sub(r'm_Shader: \{fileID: 4800000, guid: [0-9a-f]+, type: 3\}',f'm_Shader: {{fileID: 4800000, guid: {guid}, type: 3}}',text)
        for key,val in profiles[family].items():text=re.sub(r'(- '+key+r': )[^\n]*',lambda m:m[1]+str(val),text)
        rgb=[int(palette[slot][i:i+2],16)/255 for i in (1,3,5)]
        text=re.sub(r'(- _BaseColor: ).*',lambda m:m[1]+f'{{r: {rgb[0]:.8f}, g: {rgb[1]:.8f}, b: {rgb[2]:.8f}, a: 1}}',text)
        p=root/'WindMaterials'/(name+'.mat');assert not p.exists();p.write_text(text)
        p.with_suffix('.mat.meta').write_text('fileFormatVersion: 2\nguid: '+uuid.uuid4().hex+'\nNativeFormatImporter:\n  externalObjects: {}\n  mainObjectFileID: 2100000\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n')
        mapping[family][f'MAT_{slot}_oaks_pines_v01']=str(p.relative_to(root))
(root/'wind_bindings_v01.json').write_text(json.dumps({'shader':'OnlyVolunteers/Wind/v02/GenericFoliage','shader_guid':guid,'shared_include':'Assets/OnlyVolunteers/Map/Wind/v01/Shaders/V19Wind.hlsl','profiles':profiles,'material_remaps':mapping,
 'status':'Staged only, not imported or tested in Unity. Lower response and high stiffness preserve the heavy trunk. Pine is stiffer than oak. At integration, stiffness must scale with world height as in i08; preserve the global gust field and use generic settings only.'},indent=2))
print('Staged',sum(len(m) for m in mapping.values()),'materials on existing generic shader')
