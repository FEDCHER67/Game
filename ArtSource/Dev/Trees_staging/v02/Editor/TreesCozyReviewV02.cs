using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    public static class TreesCozyReviewV02
    {
        [MenuItem("OnlyVolunteers/Trees G23/Create comparison scene")]
        public static void BuildScene()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Stop Play first");
            if (File.Exists(V19TreesCozyV02.ScenePath)) throw new IOException("Test scene already exists; do not overwrite a delivered scene");
            for (int i = 0; i < SceneManager.sceneCount; i++)
                if (SceneManager.GetSceneAt(i).isDirty) throw new InvalidOperationException("Preserve the current dirty scene before opening the isolated tree review");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            SceneManager.SetActiveScene(scene);
            var sources = TreesCozyAuthoringV02.Sources();
            AddPairs("BareComparison", sources.Where(s => s.name.StartsWith("TREE_BARE_")), Vector3.zero);
            AddPairs("ForestConifers", sources.Where(s => s.name.StartsWith("V19_tree_") && V19TreesCozyV02.IsConifer(s.name)), new Vector3(0, 0, 32));
            AddPairs("BetweenBroadleaf", sources.Where(s => s.name.StartsWith("V19_tree_") && V19TreesCozyV02.IsBroadleaf(s.name) && s.name.EndsWith("_a")), new Vector3(0, 0, 64));
            AddTerrainAndInstancingProbes(sources);
            var ground = GameObject.CreatePrimitive(PrimitiveType.Plane); ground.name = "ReviewGround";
            ground.transform.position = new Vector3(0, -.02f, 30); ground.transform.localScale = new Vector3(24, 1, 12);
            string groundPath = V19TreesCozyV02.Root + "/Materials/ReviewGround_v02.mat";
            var groundMat = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "ReviewGround_v02" };
            groundMat.SetColor("_BaseColor", new Color(.53f, .58f, .49f)); groundMat.SetFloat("_Smoothness", 0);
            AssetDatabase.CreateAsset(groundMat, groundPath); ground.GetComponent<Renderer>().sharedMaterial = groundMat;
            var light = new GameObject("ReviewSun").AddComponent<Light>(); light.type = LightType.Directional;
            light.transform.rotation = Quaternion.Euler(40, -32, 0); light.color = new Color(1, .91f, .77f); light.intensity = 1.8f; light.shadows = LightShadows.Soft;
            RenderSettings.sun = light; RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(.60f, .69f, .79f); RenderSettings.ambientEquatorColor = new Color(.43f, .46f, .44f);
            RenderSettings.ambientGroundColor = new Color(.25f, .25f, .20f); RenderSettings.fog = false;
            var camera = new GameObject("Trees_ComparisonCamera").AddComponent<Camera>(); camera.tag = "MainCamera";
            camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = new Color(.67f, .78f, .81f);
            camera.nearClipPlane = .1f; camera.farClipPlane = 300; camera.orthographic = true;
            camera.gameObject.AddComponent<UniversalAdditionalCameraData>().renderPostProcessing = false;
            Frame(camera, GameObject.Find("BareComparison"), 1920, 1080);
            LookAssetStore.EnsureFolder("Assets/OnlyVolunteers/Scenes/Dev");
            EditorSceneManager.SaveScene(scene, V19TreesCozyV02.ScenePath);
            Debug.Log("[G23] Saved " + V19TreesCozyV02.ScenePath);
        }

        static void AddTerrainAndInstancingProbes(GameObject[] sources)
        {
            var trees = sources.Where(s => s.name.StartsWith("TREE_BARE_")).Select(s => V19TreesCozyV02.Resolve(s, "v19")).ToArray();
            var data = new TerrainData { name = "Trees_TerrainProbe_v02", heightmapResolution = 33, size = new Vector3(32, 1, 32) };
            data.treePrototypes = sources.Where(s => s.name.StartsWith("TREE_BARE_")).Select(t => new TreePrototype { prefab = t }).ToArray();
            data.treeInstances = Enumerable.Range(0, 9).Select(i => new TreeInstance {
                position = new Vector3(.15f + (i % 3) * .34f, 0, .15f + (i / 3) * .34f), prototypeIndex = i % 3,
                heightScale = 1, widthScale = 1, rotation = i * .4f, color = Color.white, lightmapColor = Color.white }).ToArray();
            LookAssetStore.EnsureFolder(V19TreesCozyV02.Root + "/Test");
            AssetDatabase.CreateAsset(data, V19TreesCozyV02.Root + "/Test/Trees_TerrainProbe_v02.asset");
            var originalData = data;
            data = V19TreesCozyV02.ResolveTerrainCopy(data, Vector3.zero, "v19");
            if (data == originalData || originalData.treePrototypes.Any(p => AssetDatabase.GetAssetPath(p.prefab).StartsWith(V19TreesCozyV02.Root)))
                throw new InvalidDataException("Terrain copy isolation failed");
            var nativePrototypes=data.treePrototypes.ToList();
            nativePrototypes.Add(new TreePrototype {prefab=V19TreesCozyV02.Resolve(sources.First(s=>s.name=="V19_tree_pine_a"),"v19")});
            nativePrototypes.Add(new TreePrototype {prefab=V19TreesCozyV02.Resolve(sources.First(s=>s.name=="V19_tree_oak_a"),"v19")});
            var nativeInstances=data.treeInstances;
            nativeInstances[0].prototypeIndex=nativePrototypes.Count-2;
            nativeInstances[1].prototypeIndex=nativePrototypes.Count-1;
            data.treePrototypes=nativePrototypes.ToArray(); data.SetTreeInstances(nativeInstances,false);
            EditorUtility.SetDirty(data); AssetDatabase.SaveAssetIfDirty(data);
            var terrain = Terrain.CreateTerrainGameObject(data); terrain.name = "TerrainTreeProbe"; terrain.transform.position = new Vector3(-40, 0, 90);
            var t = terrain.GetComponent<Terrain>(); t.treeDistance = 200; t.treeBillboardDistance = 200; t.treeMaximumFullLODCount = 100; t.drawInstanced = true;
            var f = trees[0].GetComponentInChildren<MeshFilter>(); var m = f.GetComponent<Renderer>().sharedMaterial;
            var probe = new GameObject("ExplicitGPUInstancing_16Trees").AddComponent<OnlyVolunteers.Trees.TreesInstancingProbeV02>();
            probe.transform.position = new Vector3(15, 0, 90); probe.Configure(f.sharedMesh, m);
        }
        public static string ValidatePlay()
        {
            if(!EditorApplication.isPlaying || SceneManager.GetActiveScene().path!=V19TreesCozyV02.ScenePath)
                throw new InvalidOperationException("Run Trees_Test in Play first");
            var probe=Object.FindAnyObjectByType<OnlyVolunteers.Trees.TreesInstancingProbeV02>();
            if(!probe || probe.SubmittedInstances!=16) throw new InvalidDataException("Explicit GPU instancing submission did not run");
            var terrain=GameObject.Find("TerrainTreeProbe").GetComponent<Terrain>();
            Physics.SyncTransforms(); var messages=new List<string>{"GPU instancing PASS: 16 instances submitted via Graphics.RenderMeshInstanced; GPU="+SystemInfo.graphicsDeviceName};
            for(int i=0;i<2;i++)
            {
                var instance=terrain.terrainData.treeInstances[i];
                var centre=terrain.transform.position+Vector3.Scale(instance.position,terrain.terrainData.size);
                var prefab=terrain.terrainData.treePrototypes[instance.prototypeIndex].prefab;
                float radius=prefab.GetComponent<CapsuleCollider>().radius;
                var from=centre+new Vector3(-4,1,0);
                if(!Physics.Raycast(from,Vector3.right,out var hit,7) || Mathf.Abs(hit.point.x-(centre.x-radius))>.03f)
                    throw new InvalidDataException("Native Terrain trunk collision failed: "+prefab.name);
                messages.Add("Native Terrain collision PASS: "+prefab.name+"; radius="+radius+"; hit="+hit.point);
            }
            string result=string.Join("\n",messages);
            TreesCozyAuthoringV02.WriteNew(V19TreesCozyV02.Review+"/play_validation_v02.txt",result); return result;
        }

        static void AddPairs(string name, IEnumerable<GameObject> sources, Vector3 offset)
        {
            var root = new GameObject(name); root.transform.position = offset;
            float x = 0;
            foreach (var source in sources)
            {
                var b = TreesCozyAuthoringV02.VisualBounds(source);
                var revised = V19TreesCozyV02.Resolve(source, "v19");
                var afterBounds=TreesCozyAuthoringV02.VisualBounds(revised);
                float gap = Mathf.Max(3.6f, b.max.x-afterBounds.min.x+1.5f);
                var pair = new GameObject(source.name + "_Pair"); pair.transform.SetParent(root.transform, false); pair.transform.localPosition = new Vector3(x, 0, 0);
                var before = (GameObject)PrefabUtility.InstantiatePrefab(source); before.name = source.name + "_BEFORE_v01"; before.transform.SetParent(pair.transform, false);
                var after = (GameObject)PrefabUtility.InstantiatePrefab(revised); after.name = source.name + "_AFTER_v02"; after.transform.SetParent(pair.transform, false); after.transform.localPosition = new Vector3(gap, 0, 0);
                Label(pair.transform, "v01", new Vector3(0, .25f, -3));
                Label(pair.transform, "v02", new Vector3(gap, .25f, -3));
                Label(pair.transform, source.name.Replace("V19_tree_", "").Replace("TREE_BARE_", "T").Replace("_v19", ""), new Vector3(gap / 2, -.03f, -4));
                x += gap * 2 + 3;
            }
            root.transform.position -= new Vector3(x * .5f - 3, 0, 0);
        }
        static void Label(Transform parent, string text, Vector3 position)
        {
            var go = new GameObject("Label_" + text); go.transform.SetParent(parent, false); go.transform.localPosition = position;
            go.transform.rotation = Quaternion.Euler(18, 0, 0);
            var label = go.AddComponent<TextMesh>(); label.text = text; label.fontSize = 70; label.characterSize = .075f;
            label.font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            go.GetComponent<MeshRenderer>().sharedMaterial=label.font.material;
            label.anchor = TextAnchor.MiddleCenter; label.color = new Color(.11f, .16f, .16f);
        }
        static Bounds BoundsOf(GameObject group)
        {
            var list = group.GetComponentsInChildren<Renderer>(); var b = list[0].bounds;
            foreach (var r in list.Skip(1)) b.Encapsulate(r.bounds); return b;
        }
        static void Frame(Camera camera, GameObject group, int width, int height)
        {
            var b = BoundsOf(group); camera.aspect = width / (float)height;
            camera.transform.position = b.center + new Vector3(0, 6, -32);
            camera.transform.LookAt(b.center); camera.orthographicSize = Mathf.Max(b.extents.y + b.extents.z * .2f, b.extents.x / camera.aspect) + 1;
        }
        public static string CaptureAll(string take="v02")
        {
            if(take.Any(c=>!char.IsLetterOrDigit(c)&&c!='_')) throw new ArgumentException("Use a numbered capture label");
            if (SceneManager.GetActiveScene().path != V19TreesCozyV02.ScenePath) throw new InvalidOperationException("Open Trees_Test first");
            var camera = GameObject.Find("Trees_ComparisonCamera").GetComponent<Camera>();
            var groups = new[] { GameObject.Find("BareComparison"), GameObject.Find("ForestConifers"), GameObject.Find("BetweenBroadleaf") };
            var probes = new[] { GameObject.Find("TerrainTreeProbe"), GameObject.Find("ExplicitGPUInstancing_16Trees") };
            var probeStates = probes.Select(p=>p.activeSelf).ToArray();
            var activeStates=groups.SelectMany(g=>g.GetComponentsInChildren<Transform>(true)).ToDictionary(t=>t.gameObject,t=>t.gameObject.activeSelf);
            var oldClock = Shader.GetGlobalVector("_TreesPreviewClock");
            var position = camera.transform.position; var rotation = camera.transform.rotation; float size = camera.orthographicSize, aspect = camera.aspect;
            try
            {
                foreach(var probe in probes) probe.SetActive(false);
                Shader.SetGlobalVector("_TreesPreviewClock", new Vector4(0, 0, 0, 1));
                string[] names = { "comparison_bare_"+take, "comparison_forest_conifers_"+take, "comparison_between_broadleaf_"+take };
                for (int i = 0; i < groups.Length; i++)
                {
                    for (int j = 0; j < groups.Length; j++) groups[j].SetActive(j == i);
                    // Two representative broadleaf species keep the before/after silhouette readable.
                    // All four species remain side by side in the saved test scene.
                    if(i==2) foreach(Transform pair in groups[i].transform) pair.gameObject.SetActive(pair.name.Contains("oak_")||pair.name.Contains("poplar_"));
                    Frame(camera, groups[i], 1920, 1080);
                    Shot(camera, V19TreesCozyV02.Review + "/" + names[i] + ".png", 1920, 1080);
                    if(i==2) foreach(Transform pair in groups[i].transform) pair.gameObject.SetActive(true);
                }
                string[] windNames={"bare","forest_conifers","between_broadleaf"};
                for(int group=0;group<groups.Length;group++)
                {
                    for(int j=0;j<groups.Length;j++) groups[j].SetActive(j==group);
                    var pairs=groups[group].transform.Cast<Transform>().ToArray();
                    var hero=pairs.Last();
                    var states=groups[group].GetComponentsInChildren<Transform>(true).ToDictionary(t=>t.gameObject,t=>t.gameObject.activeSelf);
                    try
                    {
                        foreach(var p in pairs) p.gameObject.SetActive(p==hero);
                        var before=hero.Cast<Transform>().First(t=>t.name.Contains("BEFORE")); before.gameObject.SetActive(false);
                        var after=hero.Cast<Transform>().First(t=>t.name.Contains("AFTER"));
                        foreach(var label in hero.GetComponentsInChildren<TextMesh>()) label.gameObject.SetActive(false);
                        Frame(camera,after.gameObject,1080,1080);
                        for(int frame=0;frame<3;frame++)
                        {
                            Shader.SetGlobalVector("_TreesPreviewClock",new Vector4(1+frame*2,0,0,1));
                            Shot(camera,V19TreesCozyV02.Review+"/sway_"+windNames[group]+"_0"+(frame+1)+"_t"+(1+frame*2)+"s_"+take+".png",1080,1080);
                        }
                    }
                    finally { foreach(var state in states) state.Key.SetActive(state.Value); }
                }
                foreach(var group in groups) group.SetActive(false);
                probes[0].SetActive(true);
                var native=probes[0].GetComponent<Terrain>();
                var target=native.transform.position+new Vector3(16,4,16);
                camera.transform.position=target+new Vector3(0,20,-45); camera.transform.LookAt(target);
                camera.orthographicSize=17; camera.aspect=1920f/1080;
                for(int frame=0;frame<2;frame++)
                {
                    Shader.SetGlobalVector("_TreesPreviewClock",new Vector4(1+frame*2,0,0,1));
                    Shot(camera,V19TreesCozyV02.Review+"/terrain_native_sway_0"+(frame+1)+"_t"+(1+frame*2)+"s_"+take+".png",1920,1080);
                }
                return "Saved three group comparisons, three GPU-rendered wind frames per group (1, 3, 5 seconds), and two native Terrain wind frames.";
            }
            finally
            {
                foreach (var state in activeStates) state.Key.SetActive(state.Value);
                for(int i=0;i<probes.Length;i++) probes[i].SetActive(probeStates[i]);
                Shader.SetGlobalVector("_TreesPreviewClock", oldClock);
                camera.transform.SetPositionAndRotation(position, rotation); camera.orthographicSize = size; camera.aspect = aspect;
            }
        }
        public static void Shot(Camera camera, string path, int width, int height)
        {
            if (File.Exists(path)) throw new IOException("Capture exists: " + path);
            var rt = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
            var oldTarget = camera.targetTexture; var oldActive = RenderTexture.active;
            Texture2D image = null;
            try
            {
                rt.Create(); camera.targetTexture = rt; camera.Render(); camera.Render();
                RenderTexture.active = rt; image = new Texture2D(width, height, TextureFormat.RGB24, false);
                image.ReadPixels(new Rect(0, 0, width, height), 0, 0); image.Apply();
                Directory.CreateDirectory(Path.GetDirectoryName(path)); File.WriteAllBytes(path, image.EncodeToPNG());
            }
            finally
            {
                camera.targetTexture = oldTarget; RenderTexture.active = oldActive;
                if (image) Object.DestroyImmediate(image); rt.Release(); Object.DestroyImmediate(rt);
            }
        }

        public static string Validate(string take="v02")
        {
            var results = new List<string>();
            var shader = Shader.Find(V19TreesCozyV02.ShaderName);
            if (!shader || ShaderUtil.ShaderHasError(shader)) throw new InvalidDataException("Sway shader failed");
            foreach (var source in TreesCozyAuthoringV02.Sources())
            {
                var revised = V19TreesCozyV02.Resolve(source, "v19");
                if (revised == source) throw new InvalidDataException("v19 did not switch: " + source.name);
                foreach (string rev in new[] { "v12", "v16", "v17", "v18", "v20" })
                    if (V19TreesCozyV02.Resolve(source, rev) != source) throw new InvalidDataException("Revision isolation failed: " + rev);
                var before = TreesCozyAuthoringV02.VisualBounds(source); var after = TreesCozyAuthoringV02.VisualBounds(revised);
                var ratio = new Vector3(after.size.x / before.size.x, after.size.y / before.size.y, after.size.z / before.size.z);
                if (Mathf.Abs(ratio.y-.78f) > .00001f || (V19TreesCozyV02.IsBare(source.name) && (ratio-V19TreesCozyV02.Proportions).sqrMagnitude>.000001f)) throw new InvalidDataException("Bad proportions: " + source.name + " " + ratio);
                var a = source.GetComponentsInChildren<MeshFilter>(); var b = revised.GetComponentsInChildren<MeshFilter>();
                if (V19TreesCozyV02.IsBare(source.name) && a.Length != b.Length) throw new InvalidDataException("Mesh count changed");
                for (int i = 0; V19TreesCozyV02.IsBare(source.name) && i < a.Length; i++)
                {
                    var original = a[i].sharedMesh; var copy = b[i].sharedMesh;
                    if (!original.vertices.SequenceEqual(copy.vertices) || !original.triangles.SequenceEqual(copy.triangles)
                        || !original.normals.SequenceEqual(copy.normals) || !original.uv.SequenceEqual(copy.uv))
                        throw new InvalidDataException("Source geometry changed: " + source.name);
                }
                if(!V19TreesCozyV02.IsBare(source.name))
                {
                    float target=TreesCozyAuthoringV02.TrunkRadius(source)*1.25f;
                    float actual=TreesCozyAuthoringV02.TrunkRadius(revised);
                    // Polygon orientation causes at most 2% envelope variation versus circumradius.
                    if(Mathf.Abs(actual-target)>target*.025f) throw new InvalidDataException("Trunk ratio failure: "+source.name+" "+actual+" / "+target);
                    if(Mathf.Abs(revised.GetComponentInChildren<CapsuleCollider>().radius-target)>.00001f) throw new InvalidDataException("Trunk collider mismatch");
                }
                var oldProxies = source.GetComponentsInChildren<Collider>(); var newProxies = revised.GetComponentsInChildren<Collider>();
                if (oldProxies.Length != newProxies.Length) throw new InvalidDataException("Collider count changed");
                foreach (var c in newProxies) if (c.transform.lossyScale != Vector3.one) throw new InvalidDataException("Non-unit collider scaling");
                foreach (var r in revised.GetComponentsInChildren<Renderer>())
                    foreach (var m in r.sharedMaterials)
                        if (!m || m.shader != shader || !m.enableInstancing) throw new InvalidDataException("Material/instancing failure: " + revised.name);
                results.Add(source.name + " PASS height=0.78, trunk=1.25, bare mesh preserved / separate crown revision, colliders=" + newProxies.Length + ", instanced material, v19-only resolution");
            }
            results.Add(ValidateSelection());
            results.Add("Shader PASS: " + shader.name + "; GPU=" + SystemInfo.graphicsDeviceName + "; supportsInstancing=" + SystemInfo.supportsInstancing);
            string text = string.Join("\n", results);
            TreesCozyAuthoringV02.WriteNew(V19TreesCozyV02.Review + "/validation_"+take+".txt", text);
            return text;
        }
        static string ValidateSelection()
        {
            var sources=TreesCozyAuthoringV02.Sources();
            var pine=sources.First(p=>p.name=="V19_tree_pine_a");
            var broad=sources.First(p=>p.name=="V19_tree_oak_a");
            var bare=sources.First(p=>p.name.StartsWith("TREE_BARE_01"));
            var data=new TerrainData {heightmapResolution=33,size=new Vector3(1500,1,800)};
            var master=V19TreesCozyV02.V19Revision;
            bool forest=V19TreesCozyV02.ForestConifers, between=V19TreesCozyV02.BetweenDistrictBroadleafTrial, rough=V19TreesCozyV02.RoughBareTrees;
            try
            {
                data.treePrototypes=new[]{new TreePrototype{prefab=pine},new TreePrototype{prefab=broad},new TreePrototype{prefab=bare}};
                Vector3[] positions={new(200,0,200),new(600,0,100),new(600,0,100),new(200,0,450),new(650,0,620)};
                int[] types={0,0,1,1,2};
                var original=positions.Select((p,i)=>new TreeInstance {position=new Vector3(p.x/1500,0,p.z/800),prototypeIndex=types[i],heightScale=1,widthScale=1,rotation=i*.2f,color=Color.white,lightmapColor=Color.white}).ToArray();
                data.SetTreeInstances(original,false);
                if(V19TreesCozyV02.ApplyToTerrain(data,Vector3.zero,"v18")) throw new InvalidDataException("v18 changed");
                V19TreesCozyV02.ApplyToTerrain(data,Vector3.zero,"v19");
                bool[] expected={true,false,true,false,true};
                for(int i=0;i<expected.Length;i++)
                {
                    var t=data.treeInstances[i]; bool revised=AssetDatabase.GetAssetPath(data.treePrototypes[t.prototypeIndex].prefab).StartsWith(V19TreesCozyV02.Root);
                    if(revised!=expected[i] || t.position!=original[i].position || t.heightScale!=1 || t.widthScale!=1 || t.rotation!=original[i].rotation)
                        throw new InvalidDataException("Spatial selection/placement preservation failed at "+i);
                }
                V19TreesCozyV02.BetweenDistrictBroadleafTrial=false;
                V19TreesCozyV02.ApplyToTerrain(data,Vector3.zero,"v19");
                if(data.treePrototypes[data.treeInstances[2].prototypeIndex].prefab!=broad || data.treePrototypes[data.treeInstances[0].prototypeIndex].prefab==pine)
                    throw new InvalidDataException("Broadleaf independent rollback failed");
                V19TreesCozyV02.ForestConifers=false;
                V19TreesCozyV02.ApplyToTerrain(data,Vector3.zero,"v19");
                if(data.treePrototypes[data.treeInstances[0].prototypeIndex].prefab!=pine || data.treePrototypes[data.treeInstances[4].prototypeIndex].prefab==bare)
                    throw new InvalidDataException("Conifer independent rollback failed");
                V19TreesCozyV02.V19Revision=V19TreesCozyV02.TreeRevision.Original;
                V19TreesCozyV02.ApplyToTerrain(data,Vector3.zero,"v19");
                if(data.treeInstances.Any(t=>AssetDatabase.GetAssetPath(data.treePrototypes[t.prototypeIndex].prefab).StartsWith(V19TreesCozyV02.Root)))
                    throw new InvalidDataException("Master rollback failed");
                return "Selection PASS: forest conifer only; common-land broadleaf only; district broadleaf preserved; bare selected; independent switches and master rollback; position/rotation/scale unchanged; v18 untouched.";
            }
            finally
            {
                V19TreesCozyV02.V19Revision=master; V19TreesCozyV02.ForestConifers=forest; V19TreesCozyV02.BetweenDistrictBroadleafTrial=between; V19TreesCozyV02.RoughBareTrees=rough;
                Object.DestroyImmediate(data);
            }
        }
    }
}
