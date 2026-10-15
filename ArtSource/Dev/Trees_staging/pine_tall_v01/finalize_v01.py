from pathlib import Path
import json,hashlib
r=Path('C:/Dev/Game');s=Path(__file__).parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((s/'validation_v01_02.json').read_text());bind=json.loads((s/'wind_bindings_v01.json').read_text())
recipe={'status':'STAGED ONLY, approval gate before Unity integration','sourceRevision':'v01_02','import':{'globalScale':1,'useFileUnits':True,'bakeAxisConversion':True,'importAnimation':False,'meshCompression':'Off'},'lodScreenHeights':[.23,.085,.008],'cullBelow':.008,'windBounds':'Apply conservative bounds padding on new imported meshes and compensate LOD thresholds as in i09. Do not modify the Blender render geometry.','shader':bind['shader'],'materials':bind['material_remaps'],'variants':[{k:v for k,v in spec.items() if k in ['id','height','width','colliders']} for spec in d['variants']]}
for spec in recipe['variants']:spec['fbx']='Models/'+spec['id']+'_v01_02.fbx'
(s/'prefab_recipe_v01.json').write_text(json.dumps(recipe,indent=2))
old=json.loads((s/'protected_before_v01.json').read_text());bad=[p for p,h in old.items() if sha(r/p)!=h]
unrelated='Assets/OnlyVolunteers/Inventory/Runtime/WorldItem.cs'
assert all(p.replace('\\','/')==unrelated for p in bad),bad
prior=json.loads((s/'internal_v01_preserved_v01_02.json').read_text());bad_internal=[]
for name,h in prior.items():
    found=list(s.rglob(name));assert len(found)==1,(name,len(found))
    if sha(found[0])!=h:bad_internal.append(name)
assert not bad_internal,bad_internal
(s/'preservation_final_v01.json').write_text(json.dumps({'status':'PASS tree/scene scope; unrelated workspace drift recorded','protectedProjectFiles':len(old),'unchangedFiles':len(old)-len(bad),'changed':bad,'note':'WorldItem.cs changed after successful FBX roundtrip checks. G23 made no writes to that inventory file; it was left untouched. All tree assets, scenes, i09 dependencies and ProjectSettings in the snapshot remain unchanged.','initialV01Files':len(prior),'initialChanged':bad_internal},indent=2))
files=[p for p in s.rglob('*') if p.is_file() and p.name!='delivery_manifest_v01.json']+[r/'Working/Reviews/Trees/pine_tall_v01.png']
(s/'delivery_manifest_v01.json').write_text(json.dumps({'finalCandidate':'PineTall A/B/C v01_02','files':{p.relative_to(r).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)} for p in files}},indent=2))
print('PASS scoped preservation;',len(old)-len(bad),'project files unchanged; unrelated drift:',bad,';',len(prior),'initial files unchanged;',len(files),'deliverables catalogued.')
