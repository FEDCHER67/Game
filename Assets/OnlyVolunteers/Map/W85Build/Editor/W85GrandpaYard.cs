using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using OnlyVolunteers.Map.Crowd;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W85
{
    // Grandpa's yard props (ArtSource/Props/GRANDPA_YARD_v01, procedural bpy, metres, pivot = base centre on the ground, front +Z,
    // UCX_ convex hulls): imported into Art/Props/GrandpaYard_v01 (FBX copies, flat-colour URP Lit materials from the manifest,
    // one prefab per prop with convex colliders from the UCX hulls). Re-runnable: the folder is rebuilt from the source each time.
    public static class W85GrandpaYard
    {
        const string Src = "ArtSource/Props/GRANDPA_YARD_v01";
        public const string Dst = "Assets/OnlyVolunteers/Art/Props/GrandpaYard_v01";

        [MenuItem("OnlyVolunteers/Map/W85 Build/Import grandpa yard props (GRANDPA_YARD_v01)")]
        static void ImportMenu() => Debug.Log(Import());

        public static string Import()
        {
            var log = new StringBuilder("[GrandpaYard] import\n");
            string manifest = Src + "/GRANDPA_YARD_v01_manifest.json";
            if (!File.Exists(manifest)) return log.Append("missing " + manifest).ToString();
            var mj = MiniJson.Parse(File.ReadAllText(manifest)) as Dictionary<string, object>;
            foreach (string f in new[] { "Assets/OnlyVolunteers/Art/Props", Dst, Dst + "/FBX", Dst + "/Materials", Dst + "/Prefabs" })
                if (!AssetDatabase.IsValidFolder(f)) AssetDatabase.CreateFolder(Path.GetDirectoryName(f).Replace('\\', '/'), Path.GetFileName(f));
            // materials: flat painted colours (sRGB), smoothness = 1 - roughness
            var mats = new Dictionary<string, Material>();
            foreach (var kv in (mj["materials"] as Dictionary<string, object>) ?? new Dictionary<string, object>())
            {
                var rec = kv.Value as Dictionary<string, object>;
                string path = $"{Dst}/Materials/{kv.Key}.mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (!m) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { enableInstancing = true }; AssetDatabase.CreateAsset(m, path); }
                ColorUtility.TryParseHtmlString(rec["srgb"] as string, out Color c);
                m.SetColor("_BaseColor", c);
                m.SetFloat("_Smoothness", 1f - Num(rec["roughness"]));
                m.SetFloat("_Metallic", Num(rec["metallic"]));
                EditorUtility.SetDirty(m);
                mats[kv.Key] = m;
            }
            int n = 0;
            foreach (var p in ((mj["props"] as List<object>) ?? new List<object>()).OfType<Dictionary<string, object>>())
            {
                string name = p["name"] as string, src = Src + "/" + p["fbx"], fbx = $"{Dst}/FBX/{name}.fbx";
                if (!File.Exists(src)) { log.AppendLine("missing " + src); continue; }
                File.Copy(src, fbx, true);
                AssetDatabase.ImportAsset(fbx, ImportAssetOptions.ForceSynchronousImport);
                var mi = (ModelImporter)AssetImporter.GetAtPath(fbx);
                mi.globalScale = 1f; mi.importAnimation = false; mi.importCameras = false; mi.importLights = false;
                mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
                foreach (var em in AssetDatabase.LoadAllAssetsAtPath(fbx).OfType<Material>())
                {
                    string key = mats.Keys.Where(k => em.name.StartsWith(k)).OrderByDescending(k => k.Length).FirstOrDefault();
                    if (key != null) mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), em.name), mats[key]);
                }
                mi.SaveAndReimport();
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(fbx);
                var go = (GameObject)PrefabUtility.InstantiatePrefab(model);
                PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                go.name = name;
                int hulls = 0;
                foreach (var mf in go.GetComponentsInChildren<MeshFilter>(true).Where(m => m.name.StartsWith("UCX_")).ToList())
                {
                    var o = mf.gameObject; var mesh = mf.sharedMesh;
                    Object.DestroyImmediate(o.GetComponent<MeshRenderer>()); Object.DestroyImmediate(mf);
                    var mc = o.AddComponent<MeshCollider>(); mc.sharedMesh = mesh; mc.convex = true; hulls++;
                }
                foreach (Transform t in go.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic);
                PrefabUtility.SaveAsPrefabAsset(go, $"{Dst}/Prefabs/{name}.prefab");
                Object.DestroyImmediate(go);
                var rs = model.GetComponentsInChildren<Renderer>(true).Where(r => !r.name.StartsWith("UCX_")).ToArray();
                log.AppendLine($"{name}: prefab, {hulls} convex hull(s), materials {string.Join("/", rs.SelectMany(r => r.sharedMaterials).Where(x => x).Select(x => x.name).Distinct())}");
                n++;
            }
            AssetDatabase.SaveAssets();
            log.AppendLine($"{n} props in {Dst}/Prefabs");
            return log.ToString();
        }

        static float Num(object o) => o is double d ? (float)d : o is long l ? l : 0f;

        public static GameObject Prefab(string name) => AssetDatabase.LoadAssetAtPath<GameObject>($"{Dst}/Prefabs/{name}.prefab");
    }
}
