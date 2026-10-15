from pathlib import Path
import json,hashlib,shutil
r=Path('C:/Dev/Game');s=r/'ArtSource/Dev/Trees_staging/i09_v01';e=r/'Working/Reviews/Trees/i09';e.mkdir(parents=True,exist_ok=True)
dst=r/'Assets/OnlyVolunteers/Art/Trees/OaksPines_i09'
def write(p,t):
    assert not p.exists(),p
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t,encoding='utf-8')
def copy(a,b):
    assert not b.exists(),b
    b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
paths=set(json.loads((r/'ArtSource/Dev/Trees_staging/pines_v04/protected_before_v04.json').read_text()))
for folder in ['ArtSource/Dev/Trees_staging/pines_v04','Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08','ProjectSettings']:
    paths.update(p.relative_to(r).as_posix() for p in (r/folder).rglob('*') if p.is_file())
for p in (r/'Assets/OnlyVolunteers/Scenes/Map').glob('*'): 
    if p.is_file():paths.add(p.relative_to(r).as_posix())
hashes={p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in sorted(paths)}
write(e/'protected_before.json',json.dumps(hashes,indent=2))
spec=[]
for fam,folder,rev,val in [('Oak','oaks_pines_v01','v01_02','validation_candidates_v01_02.json'),('Pine','pines_v04','v04','validation_v04.json')]:
    src=r/'ArtSource/Dev/Trees_staging'/folder
    spec.extend(v for v in json.loads((src/val).read_text())['variants'] if v['family']==fam)
    for v in 'ABC':copy(src/'Models'/f'{fam}_{v}_{rev}.fbx',dst/'Models'/f'{fam}_{v}_{rev}.fbx')
write(s/'approved_specs.json',json.dumps(spec,indent=2))
for p in (r/'ArtSource/Dev/Trees_staging/oaks_pines_v01/WindMaterials').glob('*.mat'):copy(p,dst/'Materials'/p.name)
text=(r/'Assets/OnlyVolunteers/Art/Trees/Leafy_v04/Editor/G23LeafyIntegration.cs').read_text()
build=text[text.index('        public static string BuildAssets()'):text.index('        public static string AuditTerrain')]
build=build.replace('var specs=(JArray)JObject.Parse(File.ReadAllText(Staging+"/validation_v04_03.json"))["variants"];','var specs=JArray.Parse(File.ReadAllText(Staging+"/approved_specs.json"));')
build=build.replace('Staging+"/wind_bindings_v04_03.json"','"ArtSource/Dev/Trees_staging/oaks_pines_v01/wind_bindings_v01.json"')
build=build.replace('foreach(var folder in new[]{"Meshes","Prefabs","SceneData"})Folder(Root+"/"+folder);','''foreach(var folder in new[]{"Meshes","Prefabs","SceneData"})Folder(Root+"/"+folder);
            var shader=Shader.Find("OnlyVolunteers/Wind/v03/GenericFoliageScaled");
            foreach(var guid in AssetDatabase.FindAssets("t:Material",new[]{Root+"/Materials"})){
                var mat=AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(guid));mat.shader=shader;mat.enableInstancing=true;EditorUtility.SetDirty(mat);
            }
            AssetDatabase.SaveAssets();''')
build=build.replace('family=="Apple"?.13f:family=="Poplar"?.075f:family=="Palm"?.18f:.22f','family=="Oak"?.055f:.028f')
build=build.replace('OnlyVolunteers/Wind/v02/GenericFoliage','OnlyVolunteers/Wind/v03/GenericFoliageScaled')
build=build.replace('spec["collider"]','spec["colliders"]').replace('-center[2]','center[2]').replace('-axis[2]','axis[2]')
build=build.replace('// Imported FBX handedness maps Blender Y to Unity +Z;\n                        // staged capsule recipes used -Z, so convert that axis here.','// These approved capsule recipes already use Blender Y -> Unity +Z.')
build=build.replace('Built 12 approved prefabs and 36 LODs; shared wind materials; 18 trunk capsules; bushes have no collider.','Built 6 approved prefabs and 18 LODs; shared scaled wind; 12 trunk capsules.')
header='''using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using OnlyVolunteers.Map.Wind;
using Object=UnityEngine.Object;
namespace OnlyVolunteers.Trees.Editor {
public static class G23OaksPinesI09 {
public const string Root="Assets/OnlyVolunteers/Art/Trees/OaksPines_i09";
public const string Base=G23MassI08.Scene;
public const string Scene="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i09_oaks_pines.unity";
public const string Data=Root+"/SceneData/Terrain_v19_i09_oaks_pines.asset";
public const string Evidence="Working/Reviews/Trees/i09";
const string Staging="ArtSource/Dev/Trees_staging/i09_v01";
static readonly string[] Families={"Oak","Pine"};
static string Revision(string f)=>f=="Oak"?"v01_02":"v04";
static string Prefab(string f,int v)=>Root+"/Prefabs/"+f+"_"+(char)('A'+v)+"_"+Revision(f)+".prefab";
static string Kind(int i)=>i==0||i==1||i==2?"Oak":i==12||i==13||i==15?"Pine":null;
static void Fresh(string p){if(File.Exists(p))throw new Exception("Preserve existing: "+p);}
static void Folder(string p){if(AssetDatabase.IsValidFolder(p))return;var a=Path.GetDirectoryName(p).Replace('\\\\','/');Folder(a);AssetDatabase.CreateFolder(a,Path.GetFileName(p));}
static float[] XYZ(Vector3 p)=>new[]{p.x,p.y,p.z};
static void Write(string p,object o)=>File.WriteAllText(Evidence+"/"+p,JsonConvert.SerializeObject(o,Formatting.Indented));
'''
write(s/'G23OaksPinesI09.build.cs.txt',header+build)
routes=json.loads((r/'Working/Reviews/Trees/i08/routes_input_v01.json').read_text())
for route in routes['routes']:route['name']=route['name'].replace('i08','i09')
write(e/'routes_input_v01.json',json.dumps(routes,indent=2))
print('Protected',len(hashes),'files. Six FBX + seven materials staged under lock.')
