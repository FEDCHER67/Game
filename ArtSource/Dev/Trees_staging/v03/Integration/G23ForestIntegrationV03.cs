using System;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Trees.Editor
{
    // Explicit, revision-preserving integration. Never runs automatically or rebuilds a map.
    public static class G23ForestIntegrationV03
    {
        public const string Root = "Assets/OnlyVolunteers/Art/Trees/v03";
        public const string BaseScene = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play.unity";
        public const string Scene = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i01_trees.unity";
        public const string Data = Root + "/SceneData/Terrain_v19_i01_trees.asset";
        public const string Evidence = "Working/Reviews/Trees/i01";
        static readonly string[] Names = { "Spruce_A", "Spruce_B", "Fir", "Young" };
        static readonly float[] Heights = { 9, 8, 7.5f, 6 };
        static readonly float[] Widths = { 5.76f, 5.52f, 5.10f, 3.54f };
        static readonly float[] Radii = { .264f, .284f, .254f, .184f };
        static readonly float[] CapsuleHeights = { 3.2f, 3.2f, 3.15f, 2.52f };
        public static string Prefab(int i) => Root + "/Prefabs/Forest_" + Names[i] + "_v03_04.prefab";
        static void Folder(string path) { if (AssetDatabase.IsValidFolder(path)) return; Folder(Path.GetDirectoryName(path).Replace('\\','/')); AssetDatabase.CreateFolder(Path.GetDirectoryName(path).Replace('\\','/'), Path.GetFileName(path)); }
        static void Fresh(string path) { if (File.Exists(path)) throw new IOException("Preserve existing deliverable: " + path); }

        public static string BuildAssets()
        {
            foreach (string dir in new[] { "Materials", "Meshes", "Prefabs", "SceneData" }) Folder(Root + "/" + dir);
            string texPath = Root + "/Textures/Forest_NeedleFrond_v03_03.png";
            var ti = (TextureImporter)AssetImporter.GetAtPath(texPath);
            ti.sRGBTexture = true; ti.alphaSource = TextureImporterAlphaSource.FromInput;
            ti.alphaIsTransparency = true; ti.mipmapEnabled = true;
            ti.mipMapsPreserveCoverage = true; ti.alphaTestReferenceValue = .5f;
            ti.wrapMode = TextureWrapMode.Clamp; ti.filterMode = FilterMode.Trilinear;
            ti.anisoLevel = 4; ti.maxTextureSize = 2048;
            ti.textureCompression = TextureImporterCompression.Uncompressed; ti.SaveAndReimport();
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(texPath);
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(Root + "/Shaders/TreeSway_v03.shader");
            if (shader == null || ShaderUtil.ShaderHasError(shader)) throw new Exception("Wind shader is not ready");
            var result = new StringBuilder();
            for (int n = 0; n < Names.Length; n++)
            {
                Fresh(Prefab(n));
                string modelPath = Root + "/Models/Forest_" + Names[n] + "_v03_04.fbx";
                var importer = (ModelImporter)AssetImporter.GetAtPath(modelPath);
                importer.isReadable = true; importer.importAnimation = false; importer.importCameras = false;
                importer.importLights = false; importer.meshCompression = ModelImporterMeshCompression.Off;
                importer.importNormals = ModelImporterNormals.Import; importer.SaveAndReimport();
                var source = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
                var mats = new Material[4];
                for (int m = 0; m < 4; m++)
                {
                    mats[m] = new Material(shader) { name = "Forest_" + Names[n] + "_" + m + "_v03", enableInstancing = true };
                    mats[m].SetVector("_TreeShape", new Vector4(0, 1f / Heights[n], 2f / Widths[n], Heights[n] * .008f));
                    mats[m].SetVector("_WindSettings", new Vector4(.72f,.18f,.94f,.34f));
                    mats[m].SetFloat("_Smoothness", .08f); mats[m].SetFloat("_Cull", 2);
                    if (m == 0) { mats[m].SetColor("_BaseColor", new Color(104/255f,80/255f,60/255f)); mats[m].SetFloat("_AlphaClip", 0); mats[m].DisableKeyword("_ALPHATEST_ON"); mats[m].renderQueue = 2000; }
                    else { float tint = new[] { 0, .96f, 1f, 1.04f }[m]; mats[m].SetColor("_BaseColor", new Color(tint,tint,tint,1)); mats[m].SetTexture("_BaseMap", texture); mats[m].SetFloat("_AlphaClip",1); mats[m].SetFloat("_Cutoff",.5f); mats[m].EnableKeyword("_ALPHATEST_ON"); mats[m].renderQueue = 2450; mats[m].SetOverrideTag("RenderType","TransparentCutout"); }
                    string mp = Root + "/Materials/" + mats[m].name + ".mat"; Fresh(mp); AssetDatabase.CreateAsset(mats[m], mp);
                }
                var root = new GameObject("Forest_" + Names[n] + "_v03_04");
                try
                {
                    var lods = new LOD[3];
                    for (int l = 0; l < 3; l++)
                    {
                        var mf = source.GetComponentsInChildren<MeshFilter>(true).Single(f => f.name.EndsWith("_LOD" + l));
                        var mesh = Object.Instantiate(mf.sharedMesh); mesh.name = root.name + "_LOD" + l;
                        // Bake the FBX's axis conversion, keeping the authored UV tip mask and split normals.
                        Matrix4x4 matrix = source.transform.worldToLocalMatrix * mf.transform.localToWorldMatrix;
                        mesh.vertices = mesh.vertices.Select(matrix.MultiplyPoint3x4).ToArray();
                        Matrix4x4 normals = matrix.inverse.transpose;
                        mesh.normals = mesh.normals.Select(v => normals.MultiplyVector(v).normalized).ToArray();
                        mesh.RecalculateTangents(); mesh.RecalculateBounds();
                        if (Mathf.Abs(mesh.bounds.size.y - Heights[n]) > .01f || Mathf.Abs(mesh.bounds.min.y) > .01f) throw new Exception("FBX units/pivot mismatch: " + mesh.name + mesh.bounds);
                        result.AppendLine(mesh.name + " height=" + mesh.bounds.size.y + " triangles=" + mesh.triangles.Length / 3);
                        var bounds = mesh.bounds; bounds.Expand(new Vector3(.5f,.02f,.5f)); mesh.bounds = bounds;
                        string path = Root + "/Meshes/" + mesh.name + ".asset"; Fresh(path); AssetDatabase.CreateAsset(mesh,path);
                        var child = new GameObject("LOD" + l); child.transform.SetParent(root.transform,false);
                        child.AddComponent<MeshFilter>().sharedMesh = mesh;
                        var renderer = child.AddComponent<MeshRenderer>(); renderer.sharedMaterials = mats;
                        renderer.shadowCastingMode = ShadowCastingMode.On; renderer.receiveShadows = true;
                        lods[l] = new LOD(new[] { .18f,.065f,.005f }[l], new Renderer[] { renderer });
                    }
                    var group = root.AddComponent<LODGroup>(); group.fadeMode = LODFadeMode.None; group.SetLODs(lods); group.RecalculateBounds();
                    var capsule = root.AddComponent<CapsuleCollider>(); capsule.direction = 1;
                    capsule.radius = Radii[n]; capsule.height = CapsuleHeights[n]; capsule.center = Vector3.up * capsule.height * .5f;
                    PrefabUtility.SaveAsPrefabAsset(root,Prefab(n));
                }
                finally { Object.DestroyImmediate(root); }
            }
            AssetDatabase.SaveAssets();
            File.WriteAllText(Evidence + "/asset_validation.txt",result.ToString());
            return result.ToString();
        }

        public static bool Target(TreeInstance tree, TerrainData data, Vector3 origin)
        {
            Vector3 p = Vector3.Scale(tree.position,data.size) + origin;
            return p.x >= 127.4f && p.x <= 346 && p.z >= 81 && p.z <= 315.2f && data.treePrototypes[tree.prototypeIndex].prefab.name.Contains("tree_pine_");
        }
        public static string Integrate()
        {
            var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if (EditorApplication.isPlaying || scene.path != BaseScene || scene.isDirty) throw new Exception("Requires saved base scene in Edit mode");
            Fresh(Scene); Fresh(Data);
            var terrain = Terrain.activeTerrain; var old = terrain.terrainData;
            if (!EditorSceneManager.SaveScene(scene,Scene)) throw new Exception("SaveAs failed");
            if (!AssetDatabase.CopyAsset(AssetDatabase.GetAssetPath(old),Data)) throw new Exception("Terrain copy failed");
            var data = AssetDatabase.LoadAssetAtPath<TerrainData>(Data);
            var prototypes = data.treePrototypes.ToList(); int first = prototypes.Count;
            for (int i=0;i<4;i++) prototypes.Add(new TreePrototype { prefab=AssetDatabase.LoadAssetAtPath<GameObject>(Prefab(i)), bendFactor=0 });
            data.treePrototypes = prototypes.ToArray();
            var trees = old.treeInstances; var random = new System.Random(230304); int[] counts = new int[4];
            for(int i=0;i<trees.Length;i++) if(Target(trees[i],old,terrain.transform.position))
            {
                int variant = random.Next(4); float scale = .9f + .2f*(float)random.NextDouble();
                var tr = trees[i]; tr.prototypeIndex = first + variant; tr.heightScale=tr.widthScale=scale;
                tr.rotation = (float)random.NextDouble()*Mathf.PI*2; trees[i]=tr; counts[variant]++;
            }
            data.SetTreeInstances(trees,false); EditorUtility.SetDirty(data);
            terrain.terrainData=data; terrain.GetComponent<TerrainCollider>().terrainData=data; terrain.Flush();
            EditorSceneManager.MarkSceneDirty(scene); AssetDatabase.SaveAssets(); EditorSceneManager.SaveScene(scene);
            string result="Replaced="+counts.Sum()+"; variants="+string.Join(",",counts)+"; preserved positions/all non-target instances; seed=230304; native sizes with uniform 0.9–1.1 jitter.";
            File.WriteAllText(Evidence+"/integration.txt",result); return result;
        }
        public static string CaptureAfter()
        {
            if(UnityEngine.SceneManagement.SceneManager.GetActiveScene().path != Scene) throw new Exception("Wrong scene");
            var terrain=Terrain.activeTerrain;
            var views=new Vector4[]{new Vector4(260,202,60,-6),new Vector4(214,190,320,-4),new Vector4(300,280,210,-4)};
            var oldClock=Shader.GetGlobalVector("_TreesPreviewClock");
            try { Shader.SetGlobalVector("_TreesPreviewClock",new Vector4(12,0,0,1));
                for(int i=0;i<3;i++){ var v=views[i]; var p=new Vector3(v.x,0,v.y); p.y=terrain.SampleHeight(p)+terrain.transform.position.y+1.85f; string file=Evidence+"/after_0"+(i+1)+".png"; Fresh(file); OnlyVolunteers.Map.Look.V3.V19PilotTools.Render(file,p,Quaternion.Euler(v.w,v.z,0),75,460,1600,900,false,0,true); }
            } finally { Shader.SetGlobalVector("_TreesPreviewClock",oldClock); }
            return "Three matching forest captures saved";
        }
        public static string Validate()
        {
            var terrain=Terrain.activeTerrain; var data=terrain.terrainData;
            var old=AssetDatabase.LoadAssetAtPath<TerrainData>("Assets/OnlyVolunteers/Map/LookV3/Palette19/Full_v07/Finish_v03/Terrain_finish_v03.asset");
            var a=old.treeInstances; var b=data.treeInstances; int changed=0,invalid=0;
            if(a.Length!=b.Length) throw new Exception("Tree count changed");
            for(int i=0;i<a.Length;i++) { bool target=Target(a[i],old,terrain.transform.position); if(target){changed++; if(!b[i].position.Equals(a[i].position) || b[i].prototypeIndex<20 || b[i].prototypeIndex>23 || b[i].heightScale<.9f || b[i].heightScale>1.1f || b[i].widthScale!=b[i].heightScale || !b[i].color.Equals(a[i].color) || !b[i].lightmapColor.Equals(a[i].lightmapColor))invalid++; } else if(!a[i].position.Equals(b[i].position) || a[i].prototypeIndex!=b[i].prototypeIndex || a[i].rotation!=b[i].rotation || a[i].heightScale!=b[i].heightScale || a[i].widthScale!=b[i].widthScale || !a[i].color.Equals(b[i].color) || !a[i].lightmapColor.Equals(b[i].lightmapColor))invalid++; }
            int missing=0; foreach(var go in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())foreach(var t in go.GetComponentsInChildren<Transform>(true))missing+=GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject);
            var shader=AssetDatabase.LoadAssetAtPath<Shader>(Root+"/Shaders/TreeSway_v03.shader");
            string result="trees="+a.Length+" changed="+changed+" nonTargetUnchanged="+(a.Length-changed)+" invalid="+invalid+" missingScripts="+missing+" shaderErrors="+ShaderUtil.ShaderHasError(shader)+" colliderDataMatched="+(terrain.GetComponent<TerrainCollider>().terrainData==data);
            File.WriteAllText(Evidence+"/scene_validation.txt",result);
            if(invalid!=0 || missing!=0 || ShaderUtil.ShaderHasError(shader)) throw new Exception(result);
            return result;
        }
    }
}
