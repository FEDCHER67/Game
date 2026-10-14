using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    public static class TreesCozyAuthoringV02
    {
        public static readonly string[] SourceFolders = {
            "Assets/OnlyVolunteers/Art/Map/Prefabs/TREES",
            "Assets/OnlyVolunteers/Map/LookV3/Palette19/Test_v02/Vegetation",
            "Assets/OnlyVolunteers/ThirdParty/happykeys_rocks_dead_trees/v01/Prefabs"
        };
        const string Legacy = "Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v02/Prefabs/LEAFLESS_TERRAIN_v03.prefab";
        static readonly Dictionary<string, Mesh> meshes = new();
        static readonly Dictionary<string, Material> materials = new();
        static Vector3 D(Vector3 p) => Vector3.Scale(p, V19TreesCozyV02.Proportions);

        public static GameObject[] Sources() => SourceFolders.SelectMany(d => AssetDatabase.FindAssets("t:Prefab", new[] { d }))
            .Select(g => AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(g)))
            .Where(p => p && V19TreesCozyV02.IsTree(p.name))
            .Concat(new[] { AssetDatabase.LoadAssetAtPath<GameObject>(Legacy) }).Where(p => p).OrderBy(p => p.name).ToArray();

        [MenuItem("OnlyVolunteers/Trees G23/Create v02 assets (no map rebuild)")]
        public static void BuildAssets()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Stop Play first");
            var shader = Shader.Find(V19TreesCozyV02.ShaderName);
            if (!shader || ShaderUtil.ShaderHasError(shader)) throw new InvalidOperationException("Tree shader missing or has compiler errors");
            meshes.Clear(); materials.Clear();
            foreach (var dir in new[] { "Prefabs", "Meshes", "Materials" }) LookAssetStore.EnsureFolder(V19TreesCozyV02.Root + "/" + dir);
            Directory.CreateDirectory(V19TreesCozyV02.Review);
            var rows = new List<string> { "source,prefab_v02,height_before,height_after,height_ratio,width_ratio,trunk_ratio,colliders,source_mesh_geometry_preserved" };
            foreach (var source in Sources())
            {
                string destination = V19TreesCozyV02.RevisionPath(source);
                if (File.Exists(destination)) throw new IOException("Refusing to overwrite tree revision: " + destination);
                var go = PrefabUtility.LoadPrefabContents(AssetDatabase.GetAssetPath(source)); go.name = source.name + "_Cozy_v02";
                try
                {
                    if (go.transform.localScale != Vector3.one) throw new InvalidDataException("Expected unit root: " + source.name);
                    var originalBounds = VisualBounds(go);
                    var oldColliders = go.GetComponentsInChildren<Collider>(true);
                    // Capture before the visual hierarchy receives its affine proportion transform.
                    var proxies = oldColliders.Select(c => Proxy.From(c, go.transform)).ToArray();
                    foreach (var c in oldColliders) Object.DestroyImmediate(c);
                    var geometry = new GameObject("Proportions_v02").transform;
                    geometry.SetParent(go.transform, false);
                    foreach (var child in go.transform.Cast<Transform>().Where(t => t != geometry).ToArray()) child.SetParent(geometry, false);
                    // happykeys and the legacy leafless tree have a renderer on the prefab root.
                    var rootFilter = go.GetComponent<MeshFilter>();
                    if (rootFilter)
                    {
                        var visual = new GameObject("Mesh_v02"); visual.transform.SetParent(geometry, false);
                        visual.AddComponent<MeshFilter>().sharedMesh = rootFilter.sharedMesh;
                        var rootRenderer = go.GetComponent<MeshRenderer>();
                        var copyRenderer = visual.AddComponent<MeshRenderer>();
                        EditorUtility.CopySerialized(rootRenderer, copyRenderer);
                        foreach (var lod in go.GetComponentsInChildren<LODGroup>())
                        {
                            var levels = lod.GetLODs();
                            for (int i = 0; i < levels.Length; i++) levels[i].renderers = levels[i].renderers.Select(r => r == rootRenderer ? copyRenderer : r).ToArray();
                            lod.SetLODs(levels);
                        }
                        Object.DestroyImmediate(rootRenderer); Object.DestroyImmediate(rootFilter);
                    }
                    bool newCrown = !V19TreesCozyV02.IsBare(source.name);
                    if (newCrown)
                    {
                        ReplaceCrown(go, geometry, source, originalBounds);
                        float trunkRadius=TrunkRadius(source)*1.25f;
                        foreach(var proxy in proxies.Where(p=>p.capsule)) { proxy.radius=trunkRadius; proxy.height=Mathf.Max(proxy.height,2*trunkRadius); }
                    }
                    geometry.localScale = V19TreesCozyV02.Proportions;
                    // Pad the newly authored mesh bounds. Bare trees use bounds-only copies
                    // whose vertices, triangles, normals and UVs remain identical to v01.
                    foreach (var f in go.GetComponentsInChildren<MeshFilter>(true))
                    {
                        if (!f.sharedMesh) continue;
                        var m = f.sharedMesh;
                        AssetDatabase.TryGetGUIDAndLocalFileIdentifier(m, out string guid, out long fileId);
                        string key = guid + "_" + fileId;
                        Mesh padded;
                        if(newCrown)
                        {
                            padded=m; var b=m.bounds; b.Expand(.8f); padded.bounds=b;
                            EditorUtility.SetDirty(padded); AssetDatabase.SaveAssetIfDirty(padded);
                        }
                        else if (!meshes.TryGetValue(key, out padded))
                        {
                            string path = V19TreesCozyV02.Root + "/Meshes/" + key + "_Bounds_v02.asset";
                            padded = AssetDatabase.LoadAssetAtPath<Mesh>(path);
                            if (!padded)
                            {
                                padded = Object.Instantiate(m); padded.name = m.name + "_Bounds_v02";
                                var b = m.bounds; b.Expand(0.8f); padded.bounds = b;
                                AssetDatabase.CreateAsset(padded, path);
                            }
                            meshes[key] = padded;
                        }
                        f.sharedMesh = padded;
                        var r = f.GetComponent<Renderer>();
                        if (!r) continue;
                        var mats = r.sharedMaterials;
                        // Source trees have shared local base origins across LODs.
                        Vector3 baseLocal = f.transform.InverseTransformPoint(go.transform.TransformPoint(D(new Vector3(0, originalBounds.min.y, 0))));
                        float localHeight = originalBounds.size.y * 0.78f / f.transform.lossyScale.y;
                        float localRadius = f.sharedMesh.vertices.Max(v=>new Vector2(v.x,v.z).magnitude);
                        Vector4 shape = new(baseLocal.y, 1 / Mathf.Max(localHeight, 0.1f), 1 / Mathf.Max(localRadius, 0.1f), originalBounds.size.y * 0.78f * 0.011f);
                        for (int j = 0; j < mats.Length; j++) mats[j] = SwayMaterial(mats[j], shader, source.name, shape);
                        r.sharedMaterials = mats;
                        r.motionVectorGenerationMode = MotionVectorGenerationMode.Camera;
                    }
                    foreach (var t in go.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, 0);
                    foreach (var proxy in proxies) proxy.AddTo(go.transform,newCrown);
                    // Terrain discovers nested renderers through a root LODGroup.
                    if (!go.GetComponent<LODGroup>())
                        go.AddComponent<LODGroup>().SetLODs(new[] { new LOD(.01f, go.GetComponentsInChildren<Renderer>()) });
                    foreach (var lod in go.GetComponentsInChildren<LODGroup>()) lod.RecalculateBounds();
                    PrefabUtility.SaveAsPrefabAsset(go, destination);
                    var measured=VisualBounds(go);
                    rows.Add(FormattableString.Invariant($"{AssetDatabase.GetAssetPath(source)},{destination},{originalBounds.size.y:F6},{measured.size.y:F6},0.78,{measured.size.x/originalBounds.size.x:F6},1.25,{proxies.Length},{!newCrown}"));
                }
                finally { PrefabUtility.UnloadPrefabContents(go); }
            }
            WriteNew(V19TreesCozyV02.Review + "/proportions_v02.csv", string.Join("\n", rows));
            Debug.Log("[G23] Created " + (rows.Count - 1) + " tree prefab revisions. No map scene rebuilt.");
        }

        static void ReplaceCrown(GameObject go, Transform geometry, GameObject source, Bounds original)
        {
            foreach (Transform t in geometry.Cast<Transform>().ToArray()) Object.DestroyImmediate(t.gameObject);
            var lodGroup=go.GetComponent<LODGroup>(); if(!lodGroup) lodGroup=go.AddComponent<LODGroup>();
            string kind=V19TreesCozyV02.IsConifer(source.name)?"Conifer":"BroadleafTrial";
            string variant=source.name.EndsWith("_b")?"B":"A";
            string modelPath=V19TreesCozyV02.Root+"/Models/Cozy_"+kind+"_"+variant+"_v02.fbx";
            var importer=(ModelImporter)AssetImporter.GetAtPath(modelPath);
            if (!importer.isReadable || !importer.bakeAxisConversion)
            {
                importer.isReadable=true; importer.bakeAxisConversion=true; importer.globalScale=1;
                importer.useFileScale=true; importer.importAnimation=false; importer.importCameras=false; importer.importLights=false;
                importer.importNormals=ModelImporterNormals.Import; importer.SaveAndReimport();
            }
            var model=AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            if(!model) throw new FileNotFoundException(modelPath);
            var filters=model.GetComponentsInChildren<MeshFilter>(); var lods=new LOD[2];
            float trunk=TrunkRadius(source);
            for(int level=0;level<2;level++)
            {
                var f=filters.First(t=>t.name.EndsWith("LOD"+level)); var mesh=Object.Instantiate(f.sharedMesh);
                var vertices=mesh.vertices; var matrix=f.transform.localToWorldMatrix;
                for(int i=0;i<vertices.Length;i++) vertices[i]=matrix.MultiplyPoint3x4(vertices[i]);
                var bounds=new Bounds(vertices[0],Vector3.zero); foreach(var v in vertices) bounds.Encapsulate(v);
                float h=bounds.size.y; if(h<.5f || h>2) throw new InvalidDataException("FBX metre/axis round-trip failed: "+h);
                // Preserve the reference-driven crown silhouette rather than stretching a
                // rounded trial crown into the old poplar's tall narrow envelope.
                float aspect=kind=="Conifer"?(variant=="A"?.52f:.47f):(variant=="A"?.72f:.68f);
                float radial=original.size.y*.78f*aspect/(1.25f*2*Mathf.Max(bounds.extents.x,bounds.extents.z));
                var barkVertices=new HashSet<int>(mesh.GetTriangles(0));
                float baseRadius=barkVertices.Where(i=>(vertices[i].y-bounds.min.y)/h<.01f)
                    .Max(i=>new Vector2(vertices[i].x,vertices[i].z).magnitude);
                for(int i=0;i<vertices.Length;i++)
                {
                    var v=vertices[i]; float y=(v.y-bounds.min.y)/h;
                    float radiusScale=radial;
                    if(barkVertices.Contains(i)) radiusScale=Mathf.Lerp(trunk/baseRadius,radial,Mathf.SmoothStep(0,1,Mathf.Clamp01((y-.15f)/.35f)));
                    vertices[i]=new Vector3(v.x*radiusScale,original.min.y+y*original.size.y,v.z*radiusScale);
                }
                mesh.vertices=vertices; mesh.RecalculateNormals(); mesh.RecalculateBounds(); mesh.name=source.name+"_Crown_LOD"+level+"_v02";
                AssetDatabase.CreateAsset(mesh,V19TreesCozyV02.Root+"/Meshes/"+mesh.name+".asset");
                var child=new GameObject("Cozy_"+kind+"_LOD"+level); child.transform.SetParent(geometry,false);
                child.AddComponent<MeshFilter>().sharedMesh=mesh;
                var renderer=child.AddComponent<MeshRenderer>();
                // FBX colour slots are deterministic; create Unity Lit palette sources explicitly.
                Color[] colors=kind=="Conifer"?new[]{new Color(.29f,.16f,.075f),new Color(.045f,.18f,.17f),new Color(.10f,.29f,.24f)}
                    :new[]{new Color(.29f,.16f,.075f),new Color(.72f,.38f,.06f),new Color(.94f,.66f,.12f)};
                renderer.sharedMaterials=colors.Select((c,i)=>Palette(kind,i,c)).ToArray();
                lods[level]=new LOD(level==0?.12f:.012f,new Renderer[]{renderer});
            }
            lodGroup.SetLODs(lods); lodGroup.fadeMode=LODFadeMode.None;
        }
        static Material Palette(string kind,int slot,Color color)
        {
            string path=V19TreesCozyV02.Root+"/Materials/Palette_"+kind+"_"+slot+".mat";
            var mat=AssetDatabase.LoadAssetAtPath<Material>(path); if(mat) return mat;
            mat=new Material(Shader.Find("Universal Render Pipeline/Lit")){name="Palette_"+kind+"_"+slot};
            mat.SetColor("_BaseColor",color); mat.SetFloat("_Smoothness",0); AssetDatabase.CreateAsset(mat,path); return mat;
        }
        public static float TrunkRadius(GameObject tree)
        {
            var f=tree.GetComponentsInChildren<MeshFilter>(true).First(); var mesh=f.sharedMesh;
            var vertices=mesh.vertices;
            var points=mesh.GetTriangles(0).Distinct().Select(i=>tree.transform.InverseTransformPoint(f.transform.TransformPoint(vertices[i]))).ToArray();
            float bottom=points.Min(p=>p.y), top=points.Max(p=>p.y);
            var ring=points.Where(p=>p.y<=bottom+Mathf.Max(.001f,(top-bottom)*.01f)).ToArray();
            float x=(ring.Max(p=>p.x)-ring.Min(p=>p.x))*.5f, z=(ring.Max(p=>p.z)-ring.Min(p=>p.z))*.5f;
            return Mathf.Max(x,z,.025f);
        }

        static Material SwayMaterial(Material source, Shader shader, string treeName, Vector4 shape)
        {
            if (!source) throw new InvalidDataException("Missing source tree material");
            string key = treeName + "_" + source.name;
            if (materials.TryGetValue(key, out var mat)) return mat;
            string path = V19TreesCozyV02.Root + "/Materials/" + key + "_Sway_v02.mat";
            mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!mat)
            {
                mat = new Material(source) { name = key + "_Sway_v02", shader = shader, enableInstancing = true };
                mat.SetVector("_TreeShape", shape);
                mat.SetVector("_WindSettings", new Vector4(.72f, .18f, .94f, .34f));
                AssetDatabase.CreateAsset(mat, path);
            }
            materials[key] = mat; return mat;
        }

        public static Bounds VisualBounds(GameObject go)
        {
            bool any = false; Bounds result = default;
            foreach (var f in go.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!f.sharedMesh) continue;
                // Actual vertices, so padded culling bounds cannot distort measured proportions.
                foreach (var p in f.sharedMesh.vertices)
                {
                    Vector3 v = go.transform.InverseTransformPoint(f.transform.TransformPoint(p));
                    if (!any) { result = new Bounds(v, Vector3.zero); any = true; } else result.Encapsulate(v);
                }
            }
            if (!any) throw new InvalidDataException("No tree geometry: " + go.name);
            return result;
        }

        class Proxy
        {
            public string name; public bool capsule; public Vector3 centre, axis, size; public float radius, height;
            public Quaternion rotation; public PhysicsMaterial material; public bool trigger;
            public static Proxy From(Collider collider, Transform root)
            {
                var c = new Proxy { name = collider.name, material = collider.sharedMaterial, trigger = collider.isTrigger };
                if (collider is CapsuleCollider cap)
                {
                    c.capsule = true;
                    Vector3 localAxis = cap.direction == 0 ? Vector3.right : cap.direction == 1 ? Vector3.up : Vector3.forward;
                    c.centre = D(root.InverseTransformPoint(cap.transform.TransformPoint(cap.center)));
                    var axis = D(root.InverseTransformVector(cap.transform.TransformVector(localAxis)));
                    c.axis = axis.normalized;
                    c.height = cap.height * axis.magnitude;
                    var scale = cap.transform.lossyScale;
                    float radialScale = cap.direction == 0 ? Mathf.Max(scale.y * .78f, scale.z * 1.25f)
                        : cap.direction == 1 ? Mathf.Max(scale.x, scale.z) * 1.25f : Mathf.Max(scale.x * 1.25f, scale.y * .78f);
                    c.radius = cap.radius * radialScale;
                    c.height = Mathf.Max(c.height, c.radius * 2);
                }
                else if (collider is BoxCollider box)
                {
                    c.centre = D(root.InverseTransformPoint(box.transform.TransformPoint(box.center)));
                    var x = D(root.InverseTransformVector(box.transform.TransformVector(Vector3.right)));
                    var y = D(root.InverseTransformVector(box.transform.TransformVector(Vector3.up)));
                    var z = D(root.InverseTransformVector(box.transform.TransformVector(Vector3.forward)));
                    c.rotation = Quaternion.LookRotation(z, y);
                    // Conservative OBB of the transformed original box, including affine shear.
                    Quaternion inv = Quaternion.Inverse(c.rotation);
                    x = inv * x * box.size.x; y = inv * y * box.size.y; z = inv * z * box.size.z;
                    c.size = new Vector3(Mathf.Abs(x.x)+Mathf.Abs(y.x)+Mathf.Abs(z.x), Mathf.Abs(x.y)+Mathf.Abs(y.y)+Mathf.Abs(z.y), Mathf.Abs(x.z)+Mathf.Abs(y.z)+Mathf.Abs(z.z));
                }
                else throw new InvalidDataException("Unsupported tree collider: " + collider.GetType().Name);
                return c;
            }
            public void AddTo(Transform parent,bool rootCapsule)
            {
                if(rootCapsule && capsule && Vector3.Dot(axis,Vector3.up)>.9999f)
                {
                    // Preserve the native Terrain-tree root-capsule layout of leafy sources.
                    var root=parent.gameObject.AddComponent<CapsuleCollider>(); root.direction=1;
                    root.center=centre; root.radius=radius; root.height=height;
                    root.sharedMaterial=material; root.isTrigger=trigger; return;
                }
                var go = new GameObject(name + "_Collider_v02"); go.transform.SetParent(parent, false); go.transform.localPosition = centre;
                Collider c;
                if (capsule)
                {
                    go.transform.localRotation = Quaternion.FromToRotation(Vector3.up, axis);
                    var cap = go.AddComponent<CapsuleCollider>(); cap.direction = 1; cap.radius = radius; cap.height = height; c = cap;
                }
                else { go.transform.localRotation = rotation; var box = go.AddComponent<BoxCollider>(); box.size = size; c = box; }
                c.sharedMaterial = material; c.isTrigger = trigger;
            }
        }
        public static void WriteNew(string path, string text)
        {
            if (File.Exists(path)) throw new IOException("Refusing to overwrite " + path);
            Directory.CreateDirectory(Path.GetDirectoryName(path)); File.WriteAllText(path, text);
        }
    }
}
