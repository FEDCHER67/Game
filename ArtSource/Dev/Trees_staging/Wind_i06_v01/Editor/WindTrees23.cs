using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Wind.Editor
{
    public static class WindTrees23
    {
        public const string Root="Assets/OnlyVolunteers/Map/Wind/Trees_v01";
        public const string Base="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i05_wind_grass.unity";
        public const string Scene="Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i06_wind_trees.unity";
        public const string OriginalData="Assets/OnlyVolunteers/Art/Trees/v03/SceneData/Terrain_v19_i01_trees.asset";
        public const string Data=Root+"/Terrain_v19_i06_wind.asset";
        public const string Evidence="Working/Reviews/Wind/trees_i06";
        static readonly Dictionary<string,Material> materials=new();
        static readonly Dictionary<GameObject,GameObject> prefabs=new();
        [Serializable] public sealed class Mapping { public string before,after,kind;public float response,stiffness; }
        [Serializable] public sealed class Manifest { public Mapping[] materials;public string[] prefabs;public int treeInstances,sceneRenderers; }
        static readonly List<Mapping> mappings=new();
        static void Fresh(string path){if(File.Exists(path))throw new IOException("Preserve earlier deliverable: "+path);}
        static void Folder(string path){if(AssetDatabase.IsValidFolder(path))return;string p=Path.GetDirectoryName(path).Replace('\\','/');Folder(p);AssetDatabase.CreateFolder(p,Path.GetFileName(path));}
        public static string Kind(string name)
        {
            name=name.ToLowerInvariant();
            if(name.Contains("bare")||name.Contains("leafless"))return "Bare";
            if(name.Contains("forest_"))return "Forest";
            if(name.Contains("apple"))return "Apple";
            if(name.Contains("birch"))return "Birch";
            if(name.Contains("poplar"))return "Poplar";
            if(name.Contains("palm"))return "Palm";
            if(name.Contains("pine"))return "Pine";
            if(name.Contains("hedge")||name.Contains("bush")||name.Contains("shrub"))return "Bush";
            return "Broadleaf";
        }
        public static Vector2 Settings(string kind)
        {
            switch(kind){case "Apple":return new(.13f,2.5f);case "Birch":return new(.085f,4);case "Poplar":return new(.065f,5);case "Palm":return new(.18f,7);case "Bare":return new(.045f,14);case "Forest":return new(.16f,5);case "Pine":return new(.09f,5);case "Bush":return new(.22f,.7f);default:return new(.08f,4);}
        }
        static Material WindMaterial(Material source,string kind,Vector3 pivot)
        {
            string sourcePath=AssetDatabase.GetAssetPath(source);
            string key=sourcePath+"|"+kind+"|"+pivot.ToString("F4");
            if(materials.TryGetValue(key,out var cached))return cached;
            var settings=Settings(kind);
            var preset=AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Map/Wind/v01/Materials/Generic"+(kind=="Bush"?"Bush":"Foliage")+"Wind_v01.mat");
            var mat=new Material(preset){name=source.name+"_"+kind+"_Wind_v01",shader=Shader.Find("OnlyVolunteers/Wind/v02/GenericFoliage"),enableInstancing=true};
            mat.SetColor("_BaseColor",source.HasProperty("_BaseColor")?source.GetColor("_BaseColor"):source.color);
            if(source.HasProperty("_BaseMap")){mat.SetTexture("_BaseMap",source.GetTexture("_BaseMap"));mat.SetTextureScale("_BaseMap",source.GetTextureScale("_BaseMap"));mat.SetTextureOffset("_BaseMap",source.GetTextureOffset("_BaseMap"));}
            bool clip=source.IsKeywordEnabled("_ALPHATEST_ON")||(source.HasProperty("_AlphaClip")&&source.GetFloat("_AlphaClip")>.5f);
            mat.SetFloat("_Cutoff",clip?(source.HasProperty("_Cutoff")?source.GetFloat("_Cutoff"):.5f):0);
            mat.SetFloat("_WindResponse",settings.x);mat.SetFloat("_FlexibleHeight",settings.y);mat.SetVector("_WindPivotOS",pivot);
            mat.SetFloat("_Cull",source.HasProperty("_Cull")?source.GetFloat("_Cull"):2);
            mat.SetFloat("_UseVertexTint",0);mat.SetFloat("_UseVertexMask",0);mat.SetFloat("_TipFlash",.08f);
            string path=AssetDatabase.GenerateUniqueAssetPath(Root+"/Materials/"+mat.name+".mat");AssetDatabase.CreateAsset(mat,path);
            materials.Add(key,mat);mappings.Add(new Mapping{before=sourcePath,after=path,kind=kind,response=settings.x,stiffness=settings.y});return mat;
        }
        static void ConvertRenderer(MeshRenderer r,string kind)
        {
            var mf=r.GetComponent<MeshFilter>();if(!mf||!mf.sharedMesh)throw new Exception("Missing vegetation mesh: "+r.name);
            // All current tree meshes are upright and base-pivoted. A centred bush/hedge uses its base offset.
            float bottom=mf.sharedMesh.bounds.min.y;Vector3 pivot=new Vector3(0,Mathf.Abs(bottom)<.03f?0:bottom,0);
            r.sharedMaterials=r.sharedMaterials.Select(m=>WindMaterial(m,kind,pivot)).ToArray();
            GameObjectUtility.SetStaticEditorFlags(r.gameObject,GameObjectUtility.GetStaticEditorFlags(r.gameObject)&~StaticEditorFlags.BatchingStatic);
        }
        static GameObject WindPrefab(GameObject original)
        {
            if(prefabs.TryGetValue(original,out var found))return found;
            string path=Root+"/Prefabs/"+original.name+"_Wind_v01.prefab";Fresh(path);
            var copy=Object.Instantiate(original);copy.name=original.name+"_Wind_v01";
            try
            {
                foreach(var r in copy.GetComponentsInChildren<MeshRenderer>(true))ConvertRenderer(r,Kind(original.name));
                // Terrain native trees use their LOD-group sphere. Pad it automatically without modifying mesh data.
                var group=copy.GetComponent<LODGroup>();
                if(!group){group=copy.AddComponent<LODGroup>();group.SetLODs(new[]{new LOD(.005f,copy.GetComponentsInChildren<Renderer>(true))});group.RecalculateBounds();}
                float oldSize=Mathf.Max(.1f,group.size);group.size=oldSize*1.8f+.2f;
                var lods=group.GetLODs();float ratio=group.size/oldSize;
                for(int i=0;i<lods.Length;i++)lods[i].screenRelativeTransitionHeight=Mathf.Min(.95f,lods[i].screenRelativeTransitionHeight*ratio);
                group.SetLODs(lods);
                var saved=PrefabUtility.SaveAsPrefabAsset(copy,path);prefabs.Add(original,saved);return saved;
            }
            finally{Object.DestroyImmediate(copy);}
        }
        public static bool IsVegetation(MeshRenderer r)
        {
            var mf=r.GetComponent<MeshFilter>();string n=(mf&&mf.sharedMesh?mf.sharedMesh.name:"").ToLowerInvariant();
            if(n=="sm_tree_swing")return false; // swing prop is rigid, not vegetation
            return n.StartsWith("tree_")||n.StartsWith("forest_")||n.Contains("bush")||n.Contains("hedge")||n.Contains("shrub")||r.sharedMaterials.Any(m=>m&&(m.name.ToLowerInvariant().Contains("hedge")||m.name.ToLowerInvariant().Contains("leaf")));
        }
        public static string Install()
        {
            var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if(EditorApplication.isPlaying||scene.path!=Base||scene.isDirty)throw new Exception("Requires clean i05 Edit scene");Fresh(Scene);Fresh(Data);
            if(Object.FindObjectsByType<V19Wind>().Length!=1)throw new Exception("Expected exactly one shared wind");
            var shader=Shader.Find("OnlyVolunteers/Wind/v02/GenericFoliage");if(!shader||ShaderUtil.ShaderHasError(shader))throw new Exception("Shader not ready");
            Folder(Root+"/Materials");Folder(Root+"/Prefabs");
            materials.Clear();mappings.Clear();prefabs.Clear();
            var terrain=Terrain.activeTerrain;var old=terrain.terrainData;var prototypes=old.treePrototypes;
            if(prototypes.Any(p=>!p.prefab))throw new Exception("Unresolved tree prototype");
            foreach(var prototype in prototypes)prototype.prefab=WindPrefab(prototype.prefab);
            if(!EditorSceneManager.SaveScene(scene,Scene))throw new Exception("SaveAs failed");
            if(!AssetDatabase.CopyAsset(AssetDatabase.GetAssetPath(old),Data))throw new Exception("Terrain copy failed");
            var data=AssetDatabase.LoadAssetAtPath<TerrainData>(Data);data.treePrototypes=prototypes;EditorUtility.SetDirty(data);AssetDatabase.SaveAssetIfDirty(data);
            terrain.terrainData=data;terrain.GetComponent<TerrainCollider>().terrainData=data;terrain.Flush();
            int count=0;foreach(var renderer in Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Include))if(IsVegetation(renderer)){ConvertRenderer(renderer,Kind(renderer.GetComponent<MeshFilter>().sharedMesh.name));count++;}
            new GameObject("V19FoliageBounds_v02").AddComponent<FoliageBounds23>().Refresh();
            var manifest=new Manifest{materials=mappings.ToArray(),prefabs=prefabs.Values.Select(AssetDatabase.GetAssetPath).ToArray(),treeInstances=data.treeInstanceCount,sceneRenderers=count};
            File.WriteAllText(Evidence+"/installation.json",JsonUtility.ToJson(manifest,true));
            foreach(var mat in materials.Values)AssetDatabase.SaveAssetIfDirty(mat);
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);
            return "Saved i06; terrain instances="+data.treeInstanceCount+" unique prefabs="+prefabs.Count+" materials="+materials.Count+" ordinary renderers="+count;
        }
        public static string Validate()
        {
            var a=AssetDatabase.LoadAssetAtPath<TerrainData>(OriginalData);var b=Terrain.activeTerrain.terrainData;
            var x=a.treeInstances;var y=b.treeInstances;int invalid=0,materialsCount=0;
            if(x.Length!=y.Length)throw new Exception("Tree count changed");
            for(int i=0;i<x.Length;i++)if(!x[i].position.Equals(y[i].position)||x[i].prototypeIndex!=y[i].prototypeIndex||x[i].rotation!=y[i].rotation||x[i].widthScale!=y[i].widthScale||x[i].heightScale!=y[i].heightScale||!x[i].color.Equals(y[i].color)||!x[i].lightmapColor.Equals(y[i].lightmapColor))invalid++;
            foreach(var p in b.treePrototypes)foreach(var r in p.prefab.GetComponentsInChildren<MeshRenderer>(true))foreach(var m in r.sharedMaterials){materialsCount++;if(!m||m.shader.name!="OnlyVolunteers/Wind/v02/GenericFoliage"||!m.enableInstancing)invalid++;}
            int missing=0;foreach(var root in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())foreach(var tr in root.GetComponentsInChildren<Transform>(true))missing+=GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(tr.gameObject);
            string result="trees="+x.Length+" changed instance fields="+invalid+" inspected material slots="+materialsCount+" missingScripts="+missing+" windOwners="+Object.FindObjectsByType<V19Wind>().Length+" shaderErrors="+ShaderUtil.ShaderHasError(Shader.Find("OnlyVolunteers/Wind/v02/GenericFoliage"));
            File.WriteAllText(Evidence+"/validation.txt",result);if(invalid!=0||missing!=0)throw new Exception(result);return result;
        }
        [Serializable] public sealed class Replacement {public int index,prototype;public float rotation,scale;public string reason;public float x,z;}
        [Serializable] public sealed class Replacements {public Replacement[] rows;}
        public static string ApplyG23cScope()
        {
            var scene=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if(EditorApplication.isPlaying||scene.path!=Scene)throw new Exception("Requires i06 work-in-progress Edit scene");
            var original=AssetDatabase.LoadAssetAtPath<TerrainData>(OriginalData);var terrain=Terrain.activeTerrain;var current=terrain.terrainData;
            if(AssetDatabase.GetAssetPath(current)!=Data)throw new Exception("Must edit only owned i06 TerrainData");
            var oldProtos=original.treePrototypes;var now=current.treePrototypes;
            for(int i=0;i<oldProtos.Length;i++)if(i<16)now[i]=oldProtos[i];
            current.treePrototypes=now;
            var all=original.treeInstances;var remaining=(TreeInstance[])all.Clone();
            var replacements=JsonUtility.FromJson<Replacements>(File.ReadAllText(Evidence+"/birch_replacements_v02.json"));
            foreach(var r in replacements.rows){var tree=remaining[r.index];if(tree.prototypeIndex!=5&&tree.prototypeIndex!=6)throw new Exception("Manifest target is not a birch");tree.prototypeIndex=r.prototype;tree.rotation=r.rotation;tree.widthScale*=r.scale;tree.heightScale*=r.scale;remaining[r.index]=tree;}
            current.SetTreeInstances(remaining,false);EditorUtility.SetDirty(current);AssetDatabase.SaveAssetIfDirty(current);terrain.Flush();
            var manifest=JsonUtility.FromJson<Manifest>(File.ReadAllText(Evidence+"/installation.json"));
            var lookup=manifest.materials.ToDictionary(m=>m.after,m=>AssetDatabase.LoadAssetAtPath<Material>(m.before));
            int restored=0;foreach(var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Include))
            {
                var old=r.sharedMaterials;bool any=false;
                for(int i=0;i<old.Length;i++)if(old[i]&&lookup.TryGetValue(AssetDatabase.GetAssetPath(old[i]),out var material)){old[i]=material;any=true;}
                if(any){r.sharedMaterials=old;restored++;}
            }
            var bounds=Object.FindAnyObjectByType<FoliageBounds23>();if(bounds)Object.DestroyImmediate(bounds.gameObject);
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);
            string result="G23c corrected scope: replaced birches="+replacements.rows.Length+" poplars="+replacements.rows.Count(r=>r.prototype==3||r.prototype==4)+" apples="+replacements.rows.Count(r=>r.prototype==7||r.prototype==8)+" total trees="+remaining.Length+" restored ordinary apple renderers="+restored+"; shared wind only prototype slots 16–23 (bare + Forest). Retained instance fields from i05.";
            File.WriteAllText(Evidence+"/g23c_scope_v02.txt",result);return result;
        }
        public static string ValidateG23c()
        {
            var original=AssetDatabase.LoadAssetAtPath<TerrainData>(OriginalData);var data=Terrain.activeTerrain.terrainData;
            var expected=original.treeInstances;var actual=data.treeInstances;int invalid=0,replaced=0,apples=0,poplars=0;
            if(expected.Length!=actual.Length)throw new Exception("Tree count changed");
            for(int i=0;i<expected.Length;i++)
            {
                var a=expected[i];var b=actual[i];if(!a.position.Equals(b.position)||!a.color.Equals(b.color)||!a.lightmapColor.Equals(b.lightmapColor))invalid++;
                if(a.prototypeIndex==5||a.prototypeIndex==6){replaced++;bool apple=b.prototypeIndex==7||b.prototypeIndex==8;bool poplar=b.prototypeIndex==3||b.prototypeIndex==4;if(apple)apples++;if(poplar)poplars++;float k=b.heightScale/a.heightScale;if(!(apple||poplar)||k<.89999f||k>1.10001f||Mathf.Abs(k-b.widthScale/a.widthScale)>.00001f||b.rotation<0||b.rotation>=Mathf.PI*2)invalid++;}
                else if(a.prototypeIndex!=b.prototypeIndex||a.rotation!=b.rotation||a.widthScale!=b.widthScale||a.heightScale!=b.heightScale)invalid++;
            }
            for(int i=0;i<24;i++)
            {
                if(i<16){if(data.treePrototypes[i].prefab!=original.treePrototypes[i].prefab)invalid++;}
                else foreach(var r in data.treePrototypes[i].prefab.GetComponentsInChildren<Renderer>(true))foreach(var m in r.sharedMaterials)if(!m||m.shader.name!="OnlyVolunteers/Wind/v02/GenericFoliage"||!m.enableInstancing)invalid++;
                var old=original.treePrototypes[i].prefab.GetComponentsInChildren<Collider>(true);var now=data.treePrototypes[i].prefab.GetComponentsInChildren<Collider>(true);
                if(old.Length!=now.Length)invalid++;else for(int c=0;c<old.Length;c++)if(EditorJsonUtility.ToJson(old[c])!=EditorJsonUtility.ToJson(now[c]))
                {
                    // Unity object references differ between prefab copies; compare the collision geometry directly.
                    if(old[c].GetType()!=now[c].GetType()||old[c].isTrigger!=now[c].isTrigger||old[c].enabled!=now[c].enabled||old[c].transform.localPosition!=now[c].transform.localPosition||old[c].transform.localScale!=now[c].transform.localScale)invalid++;
                    if(old[c] is CapsuleCollider a&&now[c] is CapsuleCollider b&&(a.center!=b.center||a.radius!=b.radius||a.height!=b.height||a.direction!=b.direction))invalid++;
                    if(old[c] is BoxCollider x&&now[c] is BoxCollider y&&(x.center!=y.center||x.size!=y.size))invalid++;
                    if(old[c] is MeshCollider u&&now[c] is MeshCollider v&&(u.sharedMesh!=v.sharedMesh||u.convex!=v.convex))invalid++;
                }
            }
            int missing=0;foreach(var root in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())foreach(var tr in root.GetComponentsInChildren<Transform>(true))missing+=GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(tr.gameObject);
            string result="G23c corrected: total="+actual.Length+" birches="+actual.Count(t=>t.prototypeIndex==5||t.prototypeIndex==6)+" replaced="+replaced+" poplars="+poplars+" apples="+apples+" invalid="+invalid+" missingScripts="+missing+" windOwners="+Object.FindObjectsByType<V19Wind>().Length;
            File.WriteAllText(Evidence+"/g23c_validation_v02.txt",result);if(invalid!=0||missing!=0||actual.Any(t=>t.prototypeIndex==5||t.prototypeIndex==6))throw new Exception(result);return result;
        }
    }
}
