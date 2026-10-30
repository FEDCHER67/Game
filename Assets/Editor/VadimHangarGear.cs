using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>GEAR room of the base hangar (Vadim 30.10, V2): the armoury / outfitter where players buy uniforms and
    /// weapons. The room is made procedurally in Blender (ArtSource/Buildings/HANGAR_GEAR_V01/build_gear.py, revision Rev);
    /// this script copies its FBX and derived textures into Assets/VadimLocal/Hangar/Rooms/Gear, builds the URP Lit
    /// materials from the Blender material table (_materials.json: texture, metre tiling, sRGB tint, smoothness, metallic,
    /// emission), and saves the prefab HANGAR_GEAR_vNN.prefab:
    ///  - root at the room's floor centre; the hall (front, door, window counter) is +Z, the door on +X (the FBX
    ///    imports with the hall at -Z, so the Model child is turned 180 degrees about Y);
    ///    11 x 6 m on the wall centre lines, 4.2 m clear height, roof slab on top;
    ///  - meshes GEAR_&lt;group&gt;_&lt;zone&gt;: rendering layers like VadimHangarLab (bit 0 always; _Hall bit 1, _Room bit 2,
    ///    _Both bits 1+2); static; no shadow receiving (no flicker); only the shell casts shadows;
    ///  - GEAR_BackWall_Room is its own object (it stands where the hangar's back wall is: drop it there if they meet);
    ///  - GEAR_Floor_Room is inactive (the hangar's shared concrete slab is the floor; enable it for a stand-alone room);
    ///  - BoxColliders from the COL_* boxes of the FBX (walls, roof, counter, grille, gun wall, lockers, shelves, rails,
    ///    crates, sandbags, stool, door leaf, guards);
    ///  - three unshadowed warm 3000 K point lights (two strip lamps, the gun wall), lighting the hall and room layers;
    ///  - anchors: Anchor_Door (hall side of the door), Anchor_CounterHall (customer spot), Anchor_Clerk.
    /// Existing assets of another content are never overwritten: a changed room needs a new Blender revision.
    /// Batch: -executeMethod OnlyVolunteers.EditorTools.VadimHangarGear.BuildBatch (also renders a few check shots).</summary>
    public static class VadimHangarGear
    {
        const string Rev = "v01";
        const string Name = "HANGAR_GEAR_" + Rev;
        const string Art = "ArtSource/Buildings/HANGAR_GEAR_V01";
        const string Dir = "Assets/VadimLocal/Hangar/Rooms/Gear";
        const string Log = @"C:\Users\chern_0eqkb03\VolunteersBuilds\hangar_gear\gear_build_" + Rev + ".txt";
        const string ShotDir = @"C:\Users\chern_0eqkb03\VolunteersBuilds\hangar_gear\editor_shots_" + Rev;
        const uint L0 = 1u, HallBit = 1u << 1, RoomBit = 1u << 2;
        static readonly Color Warm3000K = new(1f, .706f, .42f);

        [Serializable]
        class MatInfo
        {
            public string name, texture;
            public float tileW, tileH, smoothness, metallic, emissionIntensity;
            public float[] color, emission;
        }

        [Serializable]
        class MatList { public MatInfo[] materials; }

        static string Root => Path.GetDirectoryName(Application.dataPath);

        [MenuItem("Tools/Vadim/Hangar/Build GEAR room prefab (v01)")]
        public static void BuildMenu() => Build(false);

        public static void BuildBatch()
        {
            try
            {
                Build(true);
                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                EditorApplication.Exit(1);
            }
        }

        static void Build(bool shots)
        {
            var log = new StringBuilder();
            void L(string s) { log.AppendLine(s); Debug.Log("[GEAR] " + s); }
            L($"build {Name} {DateTime.Now:yyyy-MM-dd HH:mm:ss}");

            foreach (var sub in new[] { "", "/Models", "/Materials", "/Textures" }) EnsureFolder(Dir + sub);
            string fbx = $"{Dir}/Models/{Name}.fbx";
            CopyIn($"{Art}/{Name}.fbx", fbx, L);
            var mats = JsonUtility.FromJson<MatList>(File.ReadAllText(Path.Combine(Root, $"{Art}/{Name}_materials.json"))).materials;
            foreach (var m in mats.Where(m => m.texture.StartsWith(Dir + "/Textures/")))
                CopyIn($"{Art}/Textures/{Path.GetFileName(m.texture)}", m.texture, L);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);

            // materials (URP Lit), named like the FBX materials
            var byName = new Dictionary<string, Material>();
            foreach (var m in mats) byName[m.name] = MakeMaterial(m, L);
            AssetDatabase.SaveAssets();

            // model import: Blender custom (weighted) normals, metres, our materials remapped by name
            var mi = (ModelImporter)AssetImporter.GetAtPath(fbx);
            mi.globalScale = 1f;
            mi.useFileScale = true;
            mi.bakeAxisConversion = true;
            mi.importNormals = ModelImporterNormals.Import;
            mi.meshCompression = ModelImporterMeshCompression.Off;
            mi.isReadable = false;
            mi.importAnimation = false;
            mi.animationType = ModelImporterAnimationType.None;
            mi.importCameras = false;
            mi.importLights = false;
            mi.importBlendShapes = false;
            mi.addCollider = false;
            mi.generateSecondaryUV = false;
            mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            mi.materialLocation = ModelImporterMaterialLocation.InPrefab;
            foreach (var kv in byName) mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), kv.Key), kv.Value);
            mi.SaveAndReimport();

            // prefab
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(fbx);
            if (!model) throw new FileNotFoundException("model import failed: " + fbx);
            var root = new GameObject(Name);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
            PrefabUtility.UnpackPrefabInstance(inst, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            inst.name = "Model";
            inst.transform.SetParent(root.transform, false);
            // the FBX imports as Unity (x, y, z) = (bx, bz, by): the hall side (Blender -Y) comes in at -Z; turn it to +Z
            inst.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);

            var cols = new GameObject("Colliders");
            cols.transform.SetParent(root.transform, false);
            int nCol = 0, tris = 0, nullSlots = 0;
            Vector3? doorLeaf = null;
            foreach (Transform t in inst.transform.Cast<Transform>().ToList())
            {
                var mf = t.GetComponent<MeshFilter>();
                if (!mf || !mf.sharedMesh) continue;
                if (t.name.StartsWith("COL_"))
                {
                    var b = RootBounds(root.transform, t, mf.sharedMesh.bounds);
                    var c = new GameObject(t.name.Substring(4));
                    c.transform.SetParent(cols.transform, false);
                    var bc = c.AddComponent<BoxCollider>();
                    bc.center = b.center;
                    bc.size = b.size;
                    GameObjectUtility.SetStaticEditorFlags(c, StaticEditorFlags.BatchingStatic);
                    if (t.name == "COL_door_leaf") doorLeaf = b.center;
                    nCol++;
                    UnityEngine.Object.DestroyImmediate(t.gameObject);
                    continue;
                }
                var r = t.GetComponent<MeshRenderer>();
                uint mask = t.name.EndsWith("_Hall") ? L0 | HallBit : t.name.EndsWith("_Room") ? L0 | RoomBit : L0 | HallBit | RoomBit;
                r.renderingLayerMask = mask;
                bool shell = !t.name.StartsWith("GEAR_Props");
                r.shadowCastingMode = shell ? ShadowCastingMode.On : ShadowCastingMode.Off;
                r.receiveShadows = false;
                r.reflectionProbeUsage = ReflectionProbeUsage.BlendProbes;
                GameObjectUtility.SetStaticEditorFlags(t.gameObject, shell
                    ? StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic
                    : StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
                nullSlots += r.sharedMaterials.Count(x => x == null || !byName.ContainsValue(x));
                int mt = 0;
                for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) mt += (int)mf.sharedMesh.GetIndexCount(s) / 3;
                if (t.name.StartsWith("GEAR_Floor"))
                {
                    t.gameObject.SetActive(false);
                    L($"  {t.name}: {mt} tris, INACTIVE (stand-alone floor; the hangar slab is the floor)");
                    continue;
                }
                tris += mt;
                var wb = r.bounds;
                L($"  {t.name}: {mt} tris, mask {mask}, mats [{string.Join(", ", r.sharedMaterials.Select(x => x ? x.name : "NULL"))}], bounds {wb.min:F2}..{wb.max:F2}");
            }

            // warm 3000 K lamps: the two ceiling strips and the gun wall (no shadows; hall + room layers like the hangar's)
            var lights = new GameObject("Lights");
            lights.transform.SetParent(root.transform, false);
            AddLight(lights.transform, "Lamp strip +X", new Vector3(2.75f, 3.5f, 0f), 4.0f, 7.5f);
            AddLight(lights.transform, "Lamp strip -X", new Vector3(-2.75f, 3.5f, 0f), 4.0f, 7.5f);
            AddLight(lights.transform, "Gun wall", new Vector3(-0.5f, 2.3f, -1.6f), 1.2f, 3.2f);

            // anchors for the integration (customer spot in the hall, clerk behind the counter, door on the hall side)
            Anchor(root.transform, "Anchor_Door", new Vector3(4.3f, 0f, 3.8f));
            Anchor(root.transform, "Anchor_CounterHall", new Vector3(-0.5f, 0f, 4.2f));
            Anchor(root.transform, "Anchor_Clerk", new Vector3(-0.5f, 0f, 1.8f));

            string prefabPath = $"{Dir}/{Name}.prefab";
            var pf = PrefabUtility.SaveAsPrefabAsset(root, prefabPath);
            UnityEngine.Object.DestroyImmediate(root);
            AssetDatabase.SaveAssets();

            L($"prefab {prefabPath}: {tris} triangles (without the inactive floor), {nCol} box colliders, {nullSlots} unmapped material slots");
            if (doorLeaf.HasValue)
            {
                var d = doorLeaf.Value;
                bool ok = Mathf.Abs(d.x - 4.865f) < .05f && Mathf.Abs(d.z - 2.25f) < .05f;
                L($"axis check: door leaf collider centre {d:F3} (expected x +4.865, z +2.25) {(ok ? "OK" : "WRONG AXES")}");
                if (!ok) throw new Exception("FBX axis conversion differs from the expected Unity = (-bx, bz, -by)");
            }
            if (nullSlots > 0) throw new Exception("unmapped material slots in the GEAR model");
            if (shots) Shots(pf, L);
            Directory.CreateDirectory(Path.GetDirectoryName(Log));
            File.WriteAllText(Log, log.ToString());
        }

        static Bounds RootBounds(Transform root, Transform t, Bounds local)
        {
            var b = new Bounds(root.InverseTransformPoint(t.TransformPoint(local.min)), Vector3.zero);
            for (int i = 0; i < 8; i++)
            {
                var c = new Vector3((i & 1) == 0 ? local.min.x : local.max.x, (i & 2) == 0 ? local.min.y : local.max.y, (i & 4) == 0 ? local.min.z : local.max.z);
                b.Encapsulate(root.InverseTransformPoint(t.TransformPoint(c)));
            }
            return b;
        }

        static void AddLight(Transform parent, string name, Vector3 pos, float intensity, float range)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = pos;
            var l = go.AddComponent<Light>();
            l.type = LightType.Point;
            l.color = Warm3000K;
            l.intensity = intensity;
            l.range = range;
            l.shadows = LightShadows.None;
            l.lightmapBakeType = LightmapBakeType.Realtime;
            var ld = l.GetUniversalAdditionalLightData();
            ld.renderingLayers = HallBit | RoomBit;
        }

        static void Anchor(Transform parent, string name, Vector3 pos)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = pos;
        }

        static Material MakeMaterial(MatInfo m, Action<string> L)
        {
            string path = $"{Dir}/Materials/{m.name}_{Rev}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!mat)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            var c = new Color(m.color[0], m.color[1], m.color[2], 1f);
            mat.SetColor("_BaseColor", c);
            mat.SetColor("_Color", c);
            mat.SetFloat("_Smoothness", m.smoothness);
            mat.SetFloat("_Metallic", m.metallic);
            mat.SetFloat("_EnvironmentReflections", 1f);
            mat.SetFloat("_SpecularHighlights", 1f);
            // interiors never receive shadows (CLAUDE.md "No flicker")
            mat.SetFloat("_ReceiveShadows", 0f);
            mat.EnableKeyword("_RECEIVE_SHADOWS_OFF");
            if (!string.IsNullOrEmpty(m.texture))
            {
                var tex = Texture(m.texture);
                var sc = new Vector2(1f / m.tileW, 1f / m.tileH);
                foreach (var p in new[] { "_BaseMap", "_MainTex" })
                {
                    mat.SetTexture(p, tex);
                    mat.SetTextureScale(p, sc);
                    mat.SetTextureOffset(p, Vector2.zero);
                }
            }
            if (m.emissionIntensity > 0f && m.emission != null && m.emission.Length >= 3)
            {
                mat.EnableKeyword("_EMISSION");
                mat.SetColor("_EmissionColor", new Color(m.emission[0], m.emission[1], m.emission[2]) * m.emissionIntensity);
                mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            }
            EditorUtility.SetDirty(mat);
            L($"  material {path}: tex {(string.IsNullOrEmpty(m.texture) ? "-" : Path.GetFileName(m.texture))}, tint {c}");
            return mat;
        }

        /// <summary>Game import settings (as VadimHangarLab.Tex): mipmaps, trilinear, anisotropic 8, BC7, 1024, repeat.
        /// Only the room's own textures are re-imported; the shared hangar textures are used as they are.</summary>
        static Texture2D Texture(string path)
        {
            if (path.StartsWith(Dir + "/") && AssetImporter.GetAtPath(path) is TextureImporter imp)
            {
                if (imp.textureType != TextureImporterType.Default || !imp.mipmapEnabled || !imp.sRGBTexture || imp.anisoLevel != 8 ||
                    imp.filterMode != FilterMode.Trilinear || imp.wrapMode != TextureWrapMode.Repeat ||
                    imp.textureCompression != TextureImporterCompression.CompressedHQ || imp.maxTextureSize != 1024 ||
                    imp.alphaSource != TextureImporterAlphaSource.None)
                {
                    imp.textureType = TextureImporterType.Default;
                    imp.mipmapEnabled = true;
                    imp.sRGBTexture = true;
                    imp.anisoLevel = 8;
                    imp.filterMode = FilterMode.Trilinear;
                    imp.wrapMode = TextureWrapMode.Repeat;
                    imp.textureCompression = TextureImporterCompression.CompressedHQ;
                    imp.maxTextureSize = 1024;
                    imp.alphaSource = TextureImporterAlphaSource.None;
                    imp.SaveAndReimport();
                }
            }
            var t = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (!t) throw new FileNotFoundException("texture missing: " + path);
            return t;
        }

        static void CopyIn(string srcRel, string dstAsset, Action<string> L)
        {
            string src = Path.Combine(Root, srcRel), dst = Path.Combine(Root, dstAsset);
            if (!File.Exists(src)) throw new FileNotFoundException("missing Blender output: " + src);
            if (File.Exists(dst))
            {
                if (!File.ReadAllBytes(dst).SequenceEqual(File.ReadAllBytes(src)))
                    throw new IOException($"{dstAsset} exists and differs from {srcRel}: make a new Blender revision instead of overwriting");
                return;
            }
            File.Copy(src, dst);
            L($"  copied {srcRel} -> {dstAsset}");
        }

        static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }

        // ------------------------------------------------------------------ check shots (temporary scene, never saved)
        static void Shots(GameObject prefab, Action<string> L)
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var room = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            var floor = room.transform.Find("Model/GEAR_Floor_Room");
            if (floor) floor.gameObject.SetActive(true);
            var hallFloor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            hallFloor.transform.position = new Vector3(0, -.004f, 0);
            hallFloor.transform.localScale = new Vector3(6, 1, 6);
            var hm = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            hm.SetColor("_BaseColor", new Color(.42f, .40f, .37f));
            hm.SetFloat("_Smoothness", .1f);
            hallFloor.GetComponent<MeshRenderer>().sharedMaterial = hm;
            hallFloor.GetComponent<MeshRenderer>().renderingLayerMask = L0 | HallBit;
            // the hangar's inside ambient (HangarLighting) and two warm hall pendants in front of the room
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(.075f, .07f, .065f);
            RenderSettings.ambientEquatorColor = new Color(.10f, .088f, .072f);
            RenderSettings.ambientGroundColor = new Color(.13f, .105f, .08f);
            RenderSettings.skybox = null;
            foreach (var (n, p) in new[] { ("Pendant A", new Vector3(3f, 7f, 8f)), ("Pendant B", new Vector3(-4f, 7f, 8f)) })
            {
                var go = new GameObject(n);
                go.transform.position = p;
                go.transform.rotation = Quaternion.Euler(90, 0, 0);
                var l = go.AddComponent<Light>();
                l.type = LightType.Spot;
                l.color = new Color(1f, .78f, .52f);
                l.intensity = 55f;
                l.range = 14f;
                l.spotAngle = 100f;
                l.innerSpotAngle = 40f;
                l.shadows = LightShadows.None;
                l.GetUniversalAdditionalLightData().renderingLayers = HallBit;
            }
            var camGo = new GameObject("ShotCam");
            var cam = camGo.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(.03f, .028f, .025f);
            cam.nearClipPlane = .05f;
            cam.farClipPlane = 200f;
            Directory.CreateDirectory(ShotDir);
            void View(string name, Vector3 pos, Vector3 target, float vfov, bool noCeiling = false)
            {
                foreach (var r in room.GetComponentsInChildren<MeshRenderer>(true))
                    if (r.name.StartsWith("GEAR_Ceiling")) r.enabled = !noCeiling;
                cam.transform.position = pos;
                cam.transform.rotation = Quaternion.LookRotation(target - pos, Vector3.up);
                cam.fieldOfView = vfov;
                var rt = new RenderTexture(1440, 1080, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4 };
                cam.targetTexture = rt;
                cam.Render();
                RenderTexture.active = rt;
                var tex = new Texture2D(1440, 1080, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, 1440, 1080), 0, 0);
                tex.Apply();
                File.WriteAllBytes(Path.Combine(ShotDir, name + ".png"), tex.EncodeToPNG());
                RenderTexture.active = null;
                cam.targetTexture = null;
                UnityEngine.Object.DestroyImmediate(rt);
                UnityEngine.Object.DestroyImmediate(tex);
                L($"  shot {Path.Combine(ShotDir, name + ".png")}");
            }
            View("u01_door_view_1m7", new Vector3(4.30f, 1.70f, 2.75f), new Vector3(-0.6f, 1.0f, -1.4f), 77f);
            View("u02_hall_view_1m7", new Vector3(0.6f, 1.70f, 10.5f), new Vector3(0.6f, 1.75f, 0f), 68f);
            View("u03_overview34_no_ceiling", new Vector3(6.8f, 10.5f, 8.2f), new Vector3(0f, .3f, -.6f), 63f, true);
            View("u05_gun_wall", new Vector3(-0.5f, 1.65f, 0.45f), new Vector3(-0.5f, 1.55f, -2.9f), 63f);
            View("u08_uniforms", new Vector3(3.55f, 1.65f, 1.55f), new Vector3(4.85f, 1.2f, -0.35f), 63f);
        }
    }
}
