from pathlib import Path
import json,re,uuid
root=Path(__file__).parent;game=root.parents[3]
template=(game/'Assets/OnlyVolunteers/Map/Wind/v01/Materials/GenericFoliageWind_v01.mat').read_text()
shader='aac623136e1cfca4ab5963b42075b32d'
palette={'Bark':'68503C','LeafDark':'3A6E38','Leaf':'5C9640','LeafLight':'86B04A','Apple':'CE342C','PalmBark':'967652','PalmLeaf':'589E46','WoodDark':'684A30'}
settings={'Apple':(.13,2.5,['Bark','LeafDark','Leaf','LeafLight','Apple']),'Poplar':(.075,8,['Bark','LeafDark','Leaf','LeafLight']),'Palm':(.18,6,['PalmBark','PalmLeaf','Leaf']),'Bush':(.22,.7,['Bark','LeafDark','Leaf','LeafLight'])}
out=root/'WindMaterials';out.mkdir(exist_ok=True);mapping={}
for family,(response,height,slots) in settings.items():
    mapping[family]={}
    for slot in slots:
        name=family+'_'+slot+'_Wind_v04_01';text=template.replace('m_Name: GenericFoliageWind_v01','m_Name: '+name).replace('99db1555bb7555e4e8a8f091c9b55e31',shader)
        for key,val in {'_Cull':2,'_WindResponse':response,'_FlexibleHeight':height,'_Cutoff':0,'_TipFlash':.04,'_UseVertexTint':0,'_UseVertexMask':0}.items():text=re.sub(r'(- '+key+r': )[^\n]*',lambda m:m[1]+str(val),text)
        r,g,b=(int(palette[slot][i:i+2],16)/255 for i in (0,2,4))
        text=re.sub(r'(- _BaseColor: ).*',lambda m:m[1]+f'{{r: {r:.8f}, g: {g:.8f}, b: {b:.8f}, a: 1}}',text)
        path=out/(name+'.mat')
        if path.exists():raise FileExistsError(path)
        path.write_text(text);(out/(name+'.mat.meta')).write_text('fileFormatVersion: 2\nguid: '+uuid.uuid4().hex+'\nNativeFormatImporter:\n  externalObjects: {}\n  mainObjectFileID: 2100000\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n')
        mapping[family]['MAT_'+slot+'_v04_01']=str(path.relative_to(root))
(root/'wind_bindings_v04_01.json').write_text(json.dumps({'shader':'OnlyVolunteers/Wind/v02/GenericFoliage','shared_deformation':'Assets/OnlyVolunteers/Map/Wind/v01/Shaders/V19Wind.hlsl','material_remaps':mapping,'status':'Staged only; import, material remap, collider and LOD setup after Fedya approves the sheet.'},indent=2))
print('Staged',sum(map(len,mapping.values())),'generic wind materials; nothing imported')
