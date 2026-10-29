using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using OnlyVolunteers.Economy;
using OnlyVolunteers.Economy.Pharmacy;
using OnlyVolunteers.Map.Crowd;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W85
{
    public static partial class W85PlayIntegrator
    {
        // ------------------------------------------------------------------ W86 city pharmacy (Pharmacy_W86_v01, Rough 04-H3)
        /// <summary>Fedya 28.10 (brief claude-city-pharmacy ... v02): the city pharmacy in the ground-floor WEST unit of the
        /// Rough khrushchevka 04-H3 (11.5 x 12.7 m, the whole depth of the house): storefront C on the south facade (street),
        /// sales floor / counter B, stockroom A with the rear door into the back yard between H3 and H2 (van stop there).
        /// Nothing pharmacy-related in Downtown, no Hamlet pharmacy (STORY spec: on hold, "the pharmacy will be in the city").</summary>
        public const string PharmacyArtDir = "Assets/OnlyVolunteers/Art/Buildings/Pharmacy_W86";
        public const string PharmacyPrefabPath = PharmacyArtDir + "/Pharmacy_W86_v01.prefab";
        public const string PharmacyBuildingName = "W86_Pharmacy_Building (Pharmacy_W86_v01, 04-H3 west unit)";
        public const string PharmacyAnchorsName = "W86_Pharmacy_Anchors";
        public const string PharmacySiteName = "W86_Pharmacy_Site (04-H3 cut, front path)";
        // art v02 (ArtSource/Buildings/Pharmacy_W86, build_pharmacy_w86_v02.py --width 10.25 --depth 12.74 --height 2.6
        // --rear-door-x 0.7): the real 04-H3 bay - three window bays from the west corner (the fourth window, next to the
        // entrance, stays an apartment window) and a 2.6 m ceiling so the storefront stays under the 2nd-floor balconies
        const string PhAnchorsJson = PharmacyArtDir + "/Pharmacy_W86_anchors_v02.json";
        const string PhMaterialsJson = PharmacyArtDir + "/Pharmacy_W86_materials_v02.json";
        // labels atlas v02 (Fedya 29.10): the shop-window information sheet reads "Open daily 8:00-20:00"; every other region as v01
        const string PhLabels = PharmacyArtDir + "/Pharmacy_labels_v02.png";
        /// <summary>The baked tall-grass blades the pharmacy step cleared (unit, rear ramp, street path) and their original
        /// values, beside the play scene: the next run restores exactly those first, then clears again on the current data.</summary>
        const string PhGrassBackup = "pharmacy_W86_grass_backup_v01.bytes";
        static readonly string[] PhFbx = { "Pharmacy_W86_unit_v02.fbx", "Pharmacy_W86_props_v02.fbx" };
        public const string PharmacyHostName = "B_04-H3";
        /// <summary>Unit root = floor level at the middle of the street front (outer storefront face); yaw 180: the unit's +Z
        /// (street) looks south. West wall on the house's west end (669.49), east wall at 679.74 (2 cm short of the fourth
        /// window), front = the south facade (793.56), back = the north facade (806.30). Floor 5.10: 2 cm under the asphalt of
        /// the west link (5.12), 10 cm over the back yard (5.00, the rear ramp takes it), and the storefront top (floor + 3.0)
        /// stays under the 2nd-floor balcony slabs (8.14).</summary>
        public static readonly Vector3 PharmacyPos = new(674.615f, 5.10f, 793.56f);
        public const float PharmacyYaw = 180f;
        /// <summary>The van in the back yard between H3 and H2: nose east (it leaves by T3 -> T0), the right-hand sliding door
        /// facing the rear door (PHARMACY_SITE_RU, shifted to the built rear door at x 675.3).</summary>
        public static readonly Vector2 PharmacyVanStop = new(675.6f, 810.6f);
        public const float PharmacyVanYaw = 90f;
        static readonly string[] PhDoors = { "Door_Street", "Door_Staff", "Door_Rear" };
        /// <summary>Light intensities (URP point lights, no shadows): warm B sales floor, neutral A stockroom, the rear
        /// bulkhead, the green cross. Emission multipliers of the lamp diffusers and the cross faces.</summary>
        const float PhSalesLight = 2.6f, PhStockLight = 2.8f, PhBulkheadLight = 1.6f, PhCrossLight = 0.45f, PhLampEmission = 1.8f, PhCrossEmission = 1.2f;

        static Dictionary<string, object> PharmacyAnchorsData() =>
            File.Exists(PhAnchorsJson) ? MiniJson.Parse(File.ReadAllText(PhAnchorsJson)) as Dictionary<string, object> : null;

        /// <summary>Imports the pharmacy art (FBX importer settings + material remap), builds the URP Lit materials from
        /// Pharmacy_W86_materials_v01.json (matte, glass transparent, the labels atlas clamped) and saves the prefab
        /// <see cref="PharmacyPrefabPath"/>: unit (LODGroup LOD0 / LOD1; the three doors in both levels) + props (per-prop
        /// LODGroup), UCX_ hulls as box / convex colliders without renderers, the door components (street + rear: players,
        /// staff: STAFF ONLY), the counter-line blocker, lights at the anchors JSON points, static flags (doors and lights
        /// not static).</summary>
        public static string BuildPharmacyPrefab()
        {
            var sb = new StringBuilder();
            if (EditorApplication.isPlaying) return "pharmacy prefab: leave Play mode first";
            var mats = PharmacyMaterials(sb);
            if (mats.Count == 0) return sb.Append("pharmacy prefab: no materials").ToString();
            foreach (string f in PhFbx)
            {
                string p = PharmacyArtDir + "/" + f;
                if (!(AssetImporter.GetAtPath(p) is ModelImporter mi)) { sb.AppendLine("missing: " + p); continue; }
                mi.globalScale = 1f; mi.useFileScale = true;
                mi.importAnimation = false; mi.animationType = ModelImporterAnimationType.None;
                mi.importCameras = false; mi.importLights = false; mi.importBlendShapes = false; mi.importVisibility = false;
                mi.isReadable = true; mi.addCollider = false; mi.generateSecondaryUV = false;
                mi.meshCompression = ModelImporterMeshCompression.Off;
                mi.importNormals = ModelImporterNormals.Import; mi.importTangents = ModelImporterTangents.CalculateMikk;
                mi.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
                mi.materialLocation = ModelImporterMaterialLocation.InPrefab;
                foreach (var kv in mats) mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), kv.Key), kv.Value);
                mi.SaveAndReimport();
            }
            var anchors = PharmacyAnchorsData();
            if (anchors == null) return sb.Append("pharmacy prefab: missing " + PhAnchorsJson).ToString();
            var stage = EditorSceneManager.NewPreviewScene();
            try
            {
                var root = new GameObject("Pharmacy_W86_v01");
                SceneManager.MoveGameObjectToScene(root, stage);
                GameObject Inst(string f)
                {
                    var src = AssetDatabase.LoadAssetAtPath<GameObject>(PharmacyArtDir + "/" + f);
                    if (!src) return null;
                    var g = (GameObject)PrefabUtility.InstantiatePrefab(src, stage);
                    PrefabUtility.UnpackPrefabInstance(g, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                    g.transform.SetParent(root.transform, false);
                    g.transform.localPosition = Vector3.zero; g.transform.localRotation = Quaternion.identity; g.transform.localScale = Vector3.one;
                    return g;
                }
                var unit = Inst(PhFbx[0]); var props = Inst(PhFbx[1]);
                if (!unit || !props) return sb.Append("pharmacy prefab: FBX missing").ToString();
                { var imp = props.GetComponent<LODGroup>(); if (imp) Object.DestroyImmediate(imp); }
                // the ANCHOR_ empties are data (the JSON carries the same points)
                foreach (var t in root.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("ANCHOR_")).ToList())
                    if (t && t.childCount == 0) Object.DestroyImmediate(t.gameObject);

                // UCX_ hulls -> colliders (box when the hull is an axis-aligned box, else a convex mesh); no renderers
                int boxes = 0, hulls = 0;
                foreach (var t in root.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("UCX_")).ToList())
                {
                    var mf = t.GetComponent<MeshFilter>(); var mesh = mf ? mf.sharedMesh : null;
                    var mr = t.GetComponent<MeshRenderer>(); if (mr) Object.DestroyImmediate(mr);
                    if (mesh)
                    {
                        if (IsBoxHull(mesh)) { var bc = t.gameObject.AddComponent<BoxCollider>(); bc.center = mesh.bounds.center; bc.size = mesh.bounds.size; boxes++; }
                        else { var mc = t.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mesh; mc.convex = true; hulls++; }
                    }
                    if (mf) Object.DestroyImmediate(mf);
                }

                // LODs: unit LOD0 / LOD1 (shell, ceiling, interior; the doors in both), props LOD0 / LOD1 or cull-only
                Renderer[] Rs(Transform p, string suffix) => p.GetComponentsInChildren<Renderer>(true).Where(r => r.name.EndsWith(suffix)).ToArray();
                var doorRs = PhDoors.Select(d => unit.transform.Find(d)).Where(d => d).SelectMany(d => d.GetComponentsInChildren<Renderer>(true)).ToArray();
                var lg = unit.GetComponent<LODGroup>(); if (!lg) lg = unit.AddComponent<LODGroup>();
                lg.SetLODs(new[] { new LOD(.1f, Rs(unit.transform, "_LOD0").Concat(doorRs).ToArray()), new LOD(.008f, Rs(unit.transform, "_LOD1").Concat(doorRs).ToArray()) });
                lg.RecalculateBounds();
                int propLods = 0, propCull = 0;
                foreach (Transform h in props.transform)
                {
                    var r0 = Rs(h, "_LOD0"); var r1 = Rs(h, "_LOD1");
                    var plg = h.GetComponent<LODGroup>(); if (!plg) plg = h.gameObject.AddComponent<LODGroup>();
                    if (r0.Length > 0 && r1.Length > 0) { plg.SetLODs(new[] { new LOD(.12f, r0), new LOD(.02f, r1) }); propLods++; }
                    else { plg.SetLODs(new[] { new LOD(.01f, h.GetComponentsInChildren<Renderer>(true)) }); propCull++; }
                    plg.RecalculateBounds();
                }

                // doors: hinge transforms (closed); every door opens towards unit -Z (street door into the shop, staff door
                // into the stockroom, rear door out into the yard): the sign of the open yaw is taken from the leaf itself
                var doorInfo = WsObj(anchors, "doors");
                int doors = 0;
                foreach (string d in PhDoors)
                {
                    Transform hinge = unit.transform.Find(d);
                    if (!hinge) { sb.AppendLine("missing door " + d); continue; }
                    var dj = WsObj(doorInfo, d);
                    float open = Mathf.Abs(WsNum(dj != null && dj.TryGetValue("open_local_yaw", out var oy) ? oy : null, 90f));
                    var door = hinge.GetComponent<PharmacyDoorV01>() ?? hinge.gameObject.AddComponent<PharmacyDoorV01>();
                    door.OpenYaw = OpenSign(hinge, root.transform) * open;
                    door.Mode = d == "Door_Staff" ? PharmacyDoorV01.Access.StaffOnly : PharmacyDoorV01.Access.Public;
                    door.Title = d == "Door_Street" ? "дверь аптеки" : d == "Door_Rear" ? "заднюю дверь склада" : "служебную дверь";
                    door.AutoClose = d == "Door_Street" ? 10f : d == "Door_Rear" ? 25f : 0f;
                    door.Reach = d == "Door_Staff" ? 3.4f : 2.0f;   // the staff door is behind the counter: its refusal answers at the gate too
                    doors++;
                }

                // counter line: the 1.0-1.05 m counter would let a jumping player into the staff zone; a blocker exactly over
                // the counter footprint (wall to wall, counter top up to 2.0 m) - it reads as the counter, not a room wall
                var zones = WsObj(anchors, "zones");
                float zFront = WsV3(WsObj(zones, "customer"), "min").z, zBack = WsV3(WsObj(zones, "staff"), "max").z;   // -5.02 / -5.64
                if (Mathf.Abs(zFront - zBack) < .2f) { zFront = -5.02f; zBack = -5.64f; }
                var blocker = new GameObject("CounterLineBlocker");
                blocker.transform.SetParent(root.transform, false);
                var bcol = blocker.AddComponent<BoxCollider>();
                var ix = WsObj(anchors, "footprint") is Dictionary<string, object> fpj && fpj.TryGetValue("interior_x", out var ixo) && ixo is List<object> ixl && ixl.Count == 2 ? ixl : null;
                float bx0 = ix != null ? WsNum(ix[0], -4.925f) : -4.925f, bx1 = ix != null ? WsNum(ix[1], 4.925f) : 4.925f;   // wall to wall
                bcol.center = new Vector3((bx0 + bx1) * .5f, 1.5f, (zFront + zBack) * .5f);
                bcol.size = new Vector3(bx1 - bx0, 1.0f, Mathf.Abs(zFront - zBack));

                // lights at the anchors JSON points: warm B sales floor, neutral A stockroom, bulkhead, the green cross
                var lightsRoot = new GameObject("Lights").transform;
                lightsRoot.SetParent(root.transform, false);
                int nl = 0;
                foreach (var o in List(anchors, "lights").OfType<Dictionary<string, object>>())
                {
                    string name = Str(o, "name");
                    // sales floor: the middle column carries the light (fewer per-object lights), the side fixtures glow
                    if (name.StartsWith("Light_Sales_") && !(name.EndsWith("_02") || name.EndsWith("_05") || name.EndsWith("_08") || name.EndsWith("_04") || name.EndsWith("_06"))) continue;
                    var go = new GameObject(name);
                    go.transform.SetParent(lightsRoot, false);
                    go.transform.localPosition = WsV3(o, "position") + (name.StartsWith("Light_Sales") || name.StartsWith("Light_Stock") ? Vector3.down * .12f : Vector3.zero);
                    var l = go.AddComponent<Light>();
                    l.type = LightType.Point;
                    l.color = ColorUtility.TryParseHtmlString(Str(o, "colour"), out Color col) ? col : Color.white;
                    l.shadows = LightShadows.None;
                    var sug = WsObj(o, "suggested");
                    float range = WsNum(sug != null && sug.TryGetValue("point_range_m", out var pr) ? pr : null, 6f);
                    bool middle = name.EndsWith("_02") || name.EndsWith("_05") || name.EndsWith("_08");
                    l.range = name.StartsWith("Light_Sales") ? (middle ? 7.5f : 5.5f) : name.Contains("Cross") ? 2.4f : range;
                    l.intensity = name.StartsWith("Light_Sales") ? (middle ? PhSalesLight : PhSalesLight * .6f) : name.StartsWith("Light_Stock") ? PhStockLight
                        : name.Contains("Bulkhead") ? PhBulkheadLight : PhCrossLight;
                    l.renderMode = name.Contains("Cross") || name.Contains("Bulkhead") ? LightRenderMode.Auto : LightRenderMode.ForcePixel;
                    nl++;
                }

                // static like the map buildings / props; doors (they move), the blocker and the lights stay dynamic
                const StaticEditorFlags flags = StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic;
                var doorRoots = PhDoors.Select(d => unit.transform.Find(d)).Where(d => d).ToArray();
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                {
                    bool moving = doorRoots.Any(d => t.IsChildOf(d));
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, moving || t.IsChildOf(lightsRoot) || t == root.transform ? 0 : flags);
                }

                PrefabUtility.SaveAsPrefabAsset(root, PharmacyPrefabPath, out bool ok);
                sb.AppendLine($"pharmacy prefab {(ok ? "saved" : "FAILED")}: {PharmacyPrefabPath}; colliders {boxes} box + {hulls} convex (UCX_, renderers off) + counter-line blocker " +
                              $"{bcol.size.x:0.0} x {bcol.size.z:0.00} m at {bcol.center.y - .5f:0.0}-{bcol.center.y + .5f:0.0} m; LODGroups: unit LOD0/LOD1, {propLods} props LOD0/LOD1, {propCull} props cull-only; " +
                              $"{doors} doors (street/rear public, staff STAFF ONLY), {nl} lights");
            }
            finally { EditorSceneManager.ClosePreviewScene(stage); }
            return sb.ToString();
        }

        /// <summary>+1 or -1: the yaw sign that swings this door's free end towards the unit's -Z.</summary>
        static float OpenSign(Transform hinge, Transform unitRoot)
        {
            var rs = hinge.GetComponentsInChildren<Renderer>(true);
            if (rs.Length == 0) return 1f;
            Bounds b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
            Vector3 freeLocal = hinge.InverseTransformPoint(b.center); freeLocal.y = 0f;
            float Z(float sign) => unitRoot.InverseTransformPoint(hinge.parent.TransformPoint(hinge.localPosition + hinge.localRotation * (Quaternion.Euler(0f, sign * 60f, 0f) * freeLocal))).z;
            return Z(1f) < Z(-1f) ? 1f : -1f;
        }

        static Dictionary<string, Material> PharmacyMaterials(StringBuilder sb)
        {
            var res = new Dictionary<string, Material>();
            if (!File.Exists(PhMaterialsJson)) { sb.AppendLine("missing: " + PhMaterialsJson); return res; }
            var all = WsObj(MiniJson.Parse(File.ReadAllText(PhMaterialsJson)) as Dictionary<string, object>, "materials");
            if (all == null) { sb.AppendLine("no materials in " + PhMaterialsJson); return res; }
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            Folder(PharmacyArtDir + "/Materials");
            // the labels atlas: colour, clamped, mip-mapped (price cards and STAFF ONLY must stay readable at an angle)
            if (AssetImporter.GetAtPath(PhLabels) is TextureImporter ti &&
                (ti.wrapMode != TextureWrapMode.Clamp || ti.anisoLevel != 8 || !ti.sRGBTexture || !ti.mipmapEnabled || ti.maxTextureSize != 2048))
            {
                ti.textureType = TextureImporterType.Default; ti.sRGBTexture = true; ti.wrapMode = TextureWrapMode.Clamp; ti.mipmapEnabled = true;
                ti.anisoLevel = 8; ti.maxTextureSize = 2048; ti.textureCompression = TextureImporterCompression.CompressedHQ; ti.SaveAndReimport();
            }
            foreach (var kv in all)
            {
                if (!(kv.Value is Dictionary<string, object> m)) continue;
                string key = kv.Key.StartsWith("MAT_PH_") ? kv.Key.Substring(7) : kv.Key;
                string path = $"{PharmacyArtDir}/Materials/PH86_{key}_v01.mat";
                var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (!mat) { mat = new Material(shader); AssetDatabase.CreateAsset(mat, path); }
                if (mat.shader != shader) mat.shader = shader;
                string alb = m.TryGetValue("albedo", out var av) ? av as string : null;
                if (alb != null && alb.StartsWith("ArtSource/")) alb = PharmacyArtDir + "/" + Path.GetFileName(alb);
                if (key == "labels") alb = PhLabels;   // the atlas revision is chosen here (v02: "Open daily 8:00-20:00")
                var albT = alb != null ? AssetDatabase.LoadAssetAtPath<Texture2D>(alb) : null;
                if (alb != null && !albT) sb.AppendLine("missing texture " + alb);
                mat.SetTexture("_BaseMap", albT);
                string nrm = m.TryGetValue("normal", out var nv) ? nv as string : null;
                var nrmT = nrm != null ? AssetDatabase.LoadAssetAtPath<Texture2D>(nrm) : null;
                if (nrmT && AssetImporter.GetAtPath(nrm) is TextureImporter nti && nti.textureType != TextureImporterType.NormalMap) { sb.AppendLine("normal map not imported as NormalMap, skipped: " + nrm); nrmT = null; }
                mat.SetTexture("_BumpMap", nrmT);
                if (nrmT) { mat.EnableKeyword("_NORMALMAP"); mat.SetFloat("_BumpScale", key == "offwhite" || key.StartsWith("wall_") ? .45f : .8f); } else mat.DisableKeyword("_NORMALMAP");   // plaster: no crater noise
                float tiling = WsNum(m.TryGetValue("unity_tiling", out var tv) ? tv : null, 1f);
                mat.SetTextureScale("_BaseMap", new Vector2(tiling, tiling));
                mat.SetTextureOffset("_BaseMap", Vector2.zero);
                Color tint = ColorUtility.TryParseHtmlString(Str(m, "tint"), out Color tc) ? tc : Color.white;
                float alpha = m.TryGetValue("alpha", out var al) && al != null ? WsNum(al, 1f) : 1f;
                tint.a = alpha;
                mat.SetColor("_BaseColor", tint);
                // matte (the workshop rule): smoothness capped; glass keeps its sheen, the sink ceramic and the steel a little
                float smooth = WsNum(m.TryGetValue("smoothness", out var sv) ? sv : null, .2f), metal = WsNum(m.TryGetValue("metallic", out var mv) ? mv : null);
                smooth = key == "glass" ? smooth : key == "ceramic" ? Mathf.Min(smooth, .55f) : key == "metal" || key == "laminate" ? Mathf.Min(smooth, .4f) : Mathf.Min(smooth, .32f);
                metal = Mathf.Min(metal, key == "metal" ? .4f : .12f);   // indoor steel must not mirror the sky cube
                mat.SetFloat("_Smoothness", smooth);
                mat.SetFloat("_Metallic", metal);
                mat.SetFloat("_SmoothnessTextureChannel", 0f);
                string em = m.TryGetValue("emission", out var ev) ? ev as string : null;
                if (em != null && ColorUtility.TryParseHtmlString(em, out Color ec))
                { mat.EnableKeyword("_EMISSION"); mat.SetColor("_EmissionColor", ec * (key == "cross_glow" ? PhCrossEmission : PhLampEmission)); mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive; }
                else
                { mat.DisableKeyword("_EMISSION"); mat.SetColor("_EmissionColor", Color.black); mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.EmissiveIsBlack; }
                if (alpha < .99f)
                {
                    mat.SetFloat("_Surface", 1f); mat.SetFloat("_Blend", 0f); mat.SetOverrideTag("RenderType", "Transparent");
                    mat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha); mat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                    mat.SetFloat("_SrcBlendAlpha", (float)UnityEngine.Rendering.BlendMode.One); mat.SetFloat("_DstBlendAlpha", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                    mat.SetFloat("_ZWrite", 0f); mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                    mat.SetFloat("_Cull", 2f);
                    mat.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
                }
                else
                {
                    mat.SetFloat("_Surface", 0f); mat.SetOverrideTag("RenderType", "Opaque");
                    mat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.One); mat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.Zero);
                    mat.SetFloat("_SrcBlendAlpha", (float)UnityEngine.Rendering.BlendMode.One); mat.SetFloat("_DstBlendAlpha", (float)UnityEngine.Rendering.BlendMode.Zero);
                    mat.SetFloat("_ZWrite", 1f); mat.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
                    mat.renderQueue = -1;
                }
                EditorUtility.SetDirty(mat);
                res[kv.Key] = mat;
            }
            AssetDatabase.SaveAssets();
            sb.AppendLine($"pharmacy materials: {res.Count} URP Lit in {PharmacyArtDir}/Materials");
            return res;
        }

        // ------------------------------------------------------------------ the pharmacy in the play scene (step 8b)

        /// <summary>The pharmacy step on the OPEN play scene (no full Make): building, site (04-H3 cut, colliders, front path),
        /// anchors (cash desk, staff route, van stop); the scene is saved. Rerunnable: everything is found by name, the
        /// previous cut / path / colliders are restored first.</summary>
        public static string PlacePharmacyInOpenScene()
        {
            Log.Clear();
            if (EditorApplication.isPlaying) return Fail("leave Play mode first");
            var scene = SceneManager.GetActiveScene();
            if (string.IsNullOrEmpty(scene.path)) return Fail("the open scene is not saved");
            string sideDir = scene.path.Substring(0, scene.path.Length - ".unity".Length);
            PlacePharmacy(scene, sideDir);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            Note("saved " + scene.path);
            return Log.ToString();
        }

        static void PlacePharmacy(Scene scene, string sideDir)
        {
            Physics.SyncTransforms();
            var A = PharmacyAnchorsData();
            if (A == null) { Note("missing: " + PhAnchorsJson + " (pharmacy not placed)"); return; }
            var msb = new StringBuilder();
            PharmacyMaterials(msb);
            Note(msb.ToString().TrimEnd() + " (labels atlas " + Path.GetFileName(PhLabels) + ")");
            var building = PlacePharmacyBuilding(scene);
            if (!building) return;
            Physics.SyncTransforms();
            Note(FitPharmacySite(scene, building, sideDir, A));
            Physics.SyncTransforms();
            SnapPharmacyStreetBin(scene, building);
            Note(PlacePharmacyAnchors(scene, building, A));
        }

        static GameObject PlacePharmacyBuilding(Scene scene)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PharmacyPrefabPath);
            if (!prefab) { Note(BuildPharmacyPrefab()); prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PharmacyPrefabPath); }
            if (!prefab) { Note("missing: " + PharmacyPrefabPath + " (pharmacy not placed)"); return null; }
            GameObject go = null;
            int removed = 0;
            foreach (var g in scene.GetRootGameObjects().Where(g => g.name == PharmacyBuildingName).ToList())
            {
                bool mine = go == null && PrefabUtility.IsOutermostPrefabInstanceRoot(g) && PrefabUtility.GetCorrespondingObjectFromSource(g) == prefab;
                if (mine) go = g; else { Object.DestroyImmediate(g); removed++; }
            }
            bool reused = go != null;
            if (go) PrefabUtility.RevertPrefabInstance(go, InteractionMode.AutomatedAction);
            else
            {
                go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                if (go.transform.parent) go.transform.SetParent(null, true);
            }
            go.name = PharmacyBuildingName;
            go.transform.SetPositionAndRotation(PharmacyPos, Quaternion.Euler(0f, PharmacyYaw, 0f));
            go.transform.localScale = Vector3.one;
            EditorUtility.SetDirty(go);
            Note($"pharmacy building: {(reused ? "kept and reverted" : "placed")} {PharmacyBuildingName} ({PharmacyPrefabPath}) at {F(PharmacyPos)} yaw {PharmacyYaw:0}" + (removed > 0 ? $"; {removed} stale copy(ies) removed" : ""));
            return go;
        }

        static Transform FindDeep(Scene scene, string name)
        {
            foreach (var r in scene.GetRootGameObjects())
                foreach (var t in r.GetComponentsInChildren<Transform>(true))
                    if (t.name == name) return t;
            return null;
        }

        static Bounds MinMax(Vector3 min, Vector3 max) { var b = new Bounds(); b.SetMinMax(min, max); return b; }

        /// <summary>The house 04-H3 opened for the unit: the parts of its combined body / detail meshes inside the unit's box
        /// (west wall, south + north facade, plinth, ground-floor windows of the three bays) are cut away exactly along the
        /// box (the floors above, the fourth window, the entrance, balconies, drainpipes untouched), its big box collider stops
        /// at the unit's east wall and a box over the unit keeps the floors above solid; a concrete path through the front
        /// garden from the asphalt to the street door. Restored from the record first on every run (a rerun cuts the
        /// originals again, never a cut mesh).</summary>
        static string FitPharmacySite(Scene scene, GameObject building, string sideDir, Dictionary<string, object> A)
        {
            var sb = new StringBuilder();
            Transform host = FindDeep(scene, PharmacyHostName);
            if (!host) return "missing: house " + PharmacyHostName + " (pharmacy site not fitted)";
            GameObject site = UniqueRoot(scene, PharmacySiteName);
            site.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            var rec = site.GetComponent<PharmacySiteRecordV01>();
            if (!rec) rec = site.AddComponent<PharmacySiteRecordV01>();
            // ---- 1. undo the previous run
            int restored = 0;
            for (int i = 0; i < rec.Filters.Length && i < rec.FilterOriginals.Length; i++)
                if (rec.Filters[i] && rec.FilterOriginals[i]) { rec.Filters[i].sharedMesh = rec.FilterOriginals[i]; EditorUtility.SetDirty(rec.Filters[i]); restored++; }
            for (int i = 0; i < rec.Colliders.Length && i < rec.ColliderOriginals.Length; i++)
                if (rec.Colliders[i] && rec.ColliderOriginals[i]) { rec.Colliders[i].sharedMesh = rec.ColliderOriginals[i]; EditorUtility.SetDirty(rec.Colliders[i]); }
            for (int i = 0; i < rec.Boxes.Length && i < rec.BoxCentres.Length && i < rec.BoxSizes.Length && i < rec.BoxEnabled.Length; i++)
                if (rec.Boxes[i]) { rec.Boxes[i].center = rec.BoxCentres[i]; rec.Boxes[i].size = rec.BoxSizes[i]; rec.Boxes[i].enabled = rec.BoxEnabled[i]; EditorUtility.SetDirty(rec.Boxes[i]); }
            foreach (var g in rec.Hidden) if (g) { g.SetActive(true); EditorUtility.SetDirty(g); }
            foreach (Transform c in site.transform.Cast<Transform>().ToList()) Object.DestroyImmediate(c.gameObject);
            Physics.SyncTransforms();

            // ---- 2. the unit's box in the world (yaw 180: axis-aligned)
            var fp = WsObj(A, "footprint");
            Vector3 size = WsV3(fp, "size_xyz");                         // W, slab top, D
            float front = WsNum(fp != null && fp.TryGetValue("storefront_top_y", out var st) ? st : null, size.y + .15f);
            float W = size.x, D = size.z, top = size.y, Fy = PharmacyPos.y;
            float x0 = PharmacyPos.x - W * .5f, x1 = PharmacyPos.x + W * .5f, z0 = PharmacyPos.z, z1 = PharmacyPos.z + D;
            var boxes = new List<Bounds>
            {
                MinMax(new Vector3(x0 - .35f, Fy - .45f, z0 - .02f), new Vector3(x1, Fy + top, z1 + .1f)),           // the bay, up to the unit's slab
                MinMax(new Vector3(x0 - .35f, Fy - .45f, z0 - .3f), new Vector3(x1, Fy + front, z0 + .35f)),        // the facade strip behind the storefront
            };
            // ---- 3. cut the house's combined body / detail meshes (kit pieces - balconies, pipes, entrance - are separate)
            string meshDir = sideDir + "/Pharmacy_W86";
            Folder(meshDir);
            var filters = new List<MeshFilter>(); var originals = new List<Mesh>();
            int dropped = 0, split = 0;
            foreach (var mf in host.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!mf.name.StartsWith(PharmacyHostName + "_") || !mf.sharedMesh) continue;
                var mr = mf.GetComponent<MeshRenderer>();
                if (!mr || !W86MeshCutV01.Touches(mr.bounds, boxes)) continue;
                var r = W86MeshCutV01.Cut(mf.sharedMesh, mf.transform.localToWorldMatrix, boxes);
                if (!r.Changed) { Object.DestroyImmediate(r.Mesh); continue; }
                filters.Add(mf); originals.Add(mf.sharedMesh);
                mf.sharedMesh = SaveMeshAsset(r.Mesh, $"{meshDir}/PH86cut_{mf.name}.asset");
                EditorUtility.SetDirty(mf);
                dropped += r.Dropped; split += r.Split;
            }
            rec.Filters = filters.ToArray(); rec.FilterOriginals = originals.ToArray();
            rec.Colliders = new MeshCollider[0]; rec.ColliderOriginals = new Mesh[0];
            rec.Hidden = new GameObject[0];
            var lod = host.GetComponent<LODGroup>(); if (lod) lod.RecalculateBounds();
            sb.AppendLine($"pharmacy site: {filters.Count} house meshes of {PharmacyHostName} cut along the unit box ({dropped} triangles removed, {split} split; {restored} restored first): {string.Join(", ", filters.Select(f => f.name))}");

            // ---- 4. colliders: the house box stops at the unit, a box keeps the floors above it solid
            var boxesChanged = new List<BoxCollider>(); var bc0 = new List<Vector3>(); var bs0 = new List<Vector3>(); var be0 = new List<bool>();
            int added = 0;
            foreach (var bc in host.GetComponentsInChildren<BoxCollider>(true))
            {
                Bounds b = bc.bounds;
                if (!bc.enabled || b.min.x > x1 - .05f || b.max.x < x0 + .05f || b.min.y > Fy + top - .05f || b.max.y < Fy + .3f || b.size.y < 3f) continue;
                if (Quaternion.Angle(bc.transform.rotation, Quaternion.identity) > .01f || (bc.transform.lossyScale - Vector3.one).sqrMagnitude > 1e-6f) { sb.AppendLine("WARNING: rotated/scaled house collider left as is: " + PathOf(bc.transform)); continue; }
                boxesChanged.Add(bc); bc0.Add(bc.center); bs0.Add(bc.size); be0.Add(bc.enabled);
                var above = new GameObject("H3 collider above the pharmacy (" + bc.name + ")");
                above.transform.SetParent(site.transform, false);
                above.layer = bc.gameObject.layer;
                GameObjectUtility.SetStaticEditorFlags(above, GameObjectUtility.GetStaticEditorFlags(bc.gameObject));
                var ab = above.AddComponent<BoxCollider>();
                var am = MinMax(new Vector3(Mathf.Max(b.min.x, x0), Fy + top, b.min.z), new Vector3(Mathf.Min(b.max.x, x1), b.max.y, b.max.z));
                ab.center = am.center; ab.size = am.size;
                added++;
                if (b.max.x > x1 + .05f)
                {
                    var keep = MinMax(new Vector3(Mathf.Max(b.min.x, x1), b.min.y, b.min.z), b.max);
                    if (b.min.x < x0 - .05f) sb.AppendLine("WARNING: a house collider also reaches west of the unit (kept only east of it): " + PathOf(bc.transform));
                    bc.center = bc.transform.InverseTransformPoint(keep.center); bc.size = keep.size;
                }
                else bc.enabled = false;
                EditorUtility.SetDirty(bc);
            }
            rec.Boxes = boxesChanged.ToArray(); rec.BoxCentres = bc0.ToArray(); rec.BoxSizes = bs0.ToArray(); rec.BoxEnabled = be0.ToArray();
            sb.AppendLine($"  colliders: {boxesChanged.Count} house box(es) cut back to the unit's east wall, {added} box(es) above the unit (floors 2-5)");

            // ---- 5. the street path through the front garden: asphalt edge -> street door step (concrete, flush)
            var sd = WsObj(A, "street_door");
            Vector3 doorC = building.transform.TransformPoint(WsV3(sd, "centre"));
            float roadZ = PhRoadEdge(scene, doorC.x, z0);
            float roadY = GroundRay(scene, doorC.x, roadZ - .3f, (x, z) => Fy);
            var path = PharmacyPath(new Vector2(doorC.x - 1.2f, roadZ - .05f), new Vector2(doorC.x + 1.2f, z0 - .085f), roadY, Fy, meshDir);
            path.transform.SetParent(site.transform, false);
            sb.AppendLine($"  street path: 2.4 x {z0 - .085f - roadZ + .05f:0.00} m concrete from the asphalt edge (z {roadZ:0.00}, y {roadY:0.00}) to the street door step (y {Fy:0.00}), door centre x {doorC.x:0.00}");

            // ---- 6. checks: the balcony slabs above, other things inside the unit, grass blades
            float balcony = float.MaxValue;
            foreach (var r in host.GetComponentsInChildren<Renderer>(true))
                if (r.name.Contains("Balcony") && r.bounds.max.x > x0 && r.bounds.min.x < x1 && r.bounds.min.z < z0 + .1f && r.bounds.min.y > Fy + 1f) balcony = Mathf.Min(balcony, r.bounds.min.y);
            sb.AppendLine(balcony < float.MaxValue ? $"  storefront top {Fy + front:0.00} m, 2nd-floor balcony slab underside {balcony:0.00} m: clearance {balcony - Fy - front:0.00} m{(balcony - Fy - front < .01f ? " WARNING" : "")}" : "  no balconies over the storefront");
            var inside = new List<string>();
            foreach (var r in scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Renderer>(false)))
            {
                if (!r.enabled || r.transform.IsChildOf(building.transform) || r.transform.IsChildOf(site.transform)) continue;
                Bounds b = r.bounds;
                bool inUnit = b.min.x > x0 + .05f && b.max.x < x1 - .05f && b.min.z > z0 + .35f && b.max.z < z1 - .35f && b.min.y < Fy + top - .05f && b.max.y > Fy + .05f;
                if (inUnit && b.size.x < 40f) inside.Add(PathOf(r.transform));
            }
            sb.AppendLine(inside.Count == 0 ? "  inside the unit: no other renderers" : "  WARNING inside the unit: " + string.Join(", ", inside.Distinct().Take(12)));
            // the baked grass data itself (Fedya 29.10: Vadim's grass file may be edited here): blades in the unit, under the rear
            // ramp and on the street path are cleared (height 0) in the file the renderer reads; the previous run is undone first
            Vector3 rearC = building.transform.TransformPoint(WsV3(WsObj(A, "rear_door"), "centre"));
            var grassAreas = new[]
            {
                Rect.MinMaxRect(x0 - .05f, z0 - .05f, x1 + .05f, z1 + .05f),                                // the unit
                Rect.MinMaxRect(rearC.x - 1.25f, z1, rearC.x + 1.25f, z1 + 1.55f),                          // the rear ramp
                Rect.MinMaxRect(doorC.x - 1.3f, roadZ - .15f, doorC.x + 1.3f, z0 + .05f),                   // the street path
            };
            sb.AppendLine("  " + PharmacyClearGrass(scene, sideDir, grassAreas, Fy));
            sb.AppendLine("  " + PharmacyGrassReport(scene, x0, x1, z0, z1, Fy));
            // the GPU-copy mask of the first integration is not needed any more (by name: its script may already be deleted)
            int masks = 0;
            foreach (var mb in site.GetComponents<MonoBehaviour>())
                if (mb != null && mb.GetType().Name == "PharmacyGrassMaskV01") { Object.DestroyImmediate(mb); masks++; }
            masks += GameObjectUtility.RemoveMonoBehavioursWithMissingScript(site);
            if (masks > 0) sb.AppendLine($"  removed the old runtime grass mask from {PharmacySiteName} ({masks})");
            rec.Notes = sb.ToString();
            EditorUtility.SetDirty(rec);
            return sb.ToString().TrimEnd();
        }

        /// <summary>North edge of the asphalt in front of the door (a downward ray walk from the facade southwards).</summary>
        static float PhRoadEdge(Scene scene, float x, float facadeZ)
        {
            for (float z = facadeZ - .3f; z > facadeZ - 8f; z -= .05f)
                foreach (var h in Physics.RaycastAll(new Vector3(x, 40f, z), Vector3.down, 60f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore))
                    if (h.collider.gameObject.scene == scene && h.collider.name.StartsWith("Road_")) return z + .05f;
            return facadeZ - 2.4f;
        }

        /// <summary>A concrete slab (metre UVs, a 22 cm edge into the garden soil) from the asphalt (yRoad) to the step (yDoor).</summary>
        static GameObject PharmacyPath(Vector2 min, Vector2 max, float yRoad, float yDoor, string meshDir)
        {
            var go = new GameObject("Pharmacy street path (front garden, concrete)");
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var tri = new List<int>();
            void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud)
            {
                int i = v.Count; v.Add(a); v.Add(b); v.Add(c); v.Add(d); uv.Add(ua); uv.Add(ub); uv.Add(uc); uv.Add(ud);
                tri.AddRange(new[] { i, i + 1, i + 2, i, i + 2, i + 3 });
            }
            float y0 = yRoad, y1 = yDoor, bot = Mathf.Min(y0, y1) - .22f;
            var p00 = new Vector3(min.x, y0, min.y); var p10 = new Vector3(max.x, y0, min.y);
            var p11 = new Vector3(max.x, y1, max.y); var p01 = new Vector3(min.x, y1, max.y);
            // top (+y), south edge (-z), west edge (-x), east edge (+x); clockwise seen from outside = Unity front faces
            Quad(p00, p01, p11, p10, new Vector2(min.x, min.y), new Vector2(min.x, max.y), new Vector2(max.x, max.y), new Vector2(max.x, min.y));
            Quad(new Vector3(min.x, bot, min.y), p00, p10, new Vector3(max.x, bot, min.y), new Vector2(min.x, bot), new Vector2(min.x, y0), new Vector2(max.x, y0), new Vector2(max.x, bot));
            Quad(new Vector3(min.x, bot, max.y), p01, p00, new Vector3(min.x, bot, min.y), new Vector2(max.y, bot), new Vector2(max.y, y1), new Vector2(min.y, y0), new Vector2(min.y, bot));
            Quad(new Vector3(max.x, bot, min.y), p10, p11, new Vector3(max.x, bot, max.y), new Vector2(min.y, bot), new Vector2(min.y, y0), new Vector2(max.y, y1), new Vector2(max.y, bot));
            var m = new Mesh { name = "PH86_street_path" };
            m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(tri, 0); m.RecalculateNormals(); m.RecalculateTangents(); m.RecalculateBounds();
            m = SaveMeshAsset(m, meshDir + "/PH86_street_path.asset");
            go.AddComponent<MeshFilter>().sharedMesh = m;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>(PharmacyArtDir + "/Materials/PH86_concrete_v01.mat");
            var mc = go.AddComponent<MeshCollider>(); mc.sharedMesh = m;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            return go;
        }

        static Mesh SaveMeshAsset(Mesh m, string path)
        {
            var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            string name = Path.GetFileNameWithoutExtension(path);
            if (existing)
            {
                existing.Clear();
                EditorUtility.CopySerialized(m, existing);
                existing.name = name;
                EditorUtility.SetDirty(existing);
                Object.DestroyImmediate(m);
                return existing;
            }
            m.name = name;
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        /// <summary>Clears the baked tall-grass blades (height 0, the workshop step's way) inside the given world rects in the
        /// grass file the play scene's W85GrassRenderer reads. Rerunnable: the blades the previous run cleared are restored
        /// first from <see cref="PhGrassBackup"/> beside the play scene - only those that still hold exactly what that run wrote
        /// (same x / z, height 0), so a grass file rebaked or replaced since is never touched by an old record - then the
        /// clearing is done again on the current data and the backup rewritten. Blades higher than floor + 1.2 m (none
        /// expected) are left alone.</summary>
        static string PharmacyClearGrass(Scene scene, string sideDir, Rect[] areas, float floor)
        {
            var grass = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<W85GrassRenderer>(true)).FirstOrDefault(g => g.data && g.data.instances);
            if (!grass) return "grass: no baked grass renderer (nothing cleared)";
            string grassPath = AssetDatabase.GetAssetPath(grass.data.instances);
            if (!File.Exists(grassPath)) return "grass: file not found " + grassPath;
            byte[] gb = File.ReadAllBytes(grassPath);
            int blades = gb.Length / 32;
            string backup = sideDir + "/" + PhGrassBackup;
            int restored = 0, staleRecords = 0;
            if (File.Exists(backup))
            {
                try
                {
                    using var r = new BinaryReader(File.OpenRead(backup));
                    if (r.ReadString() != "PHG1") throw new InvalidDataException("not a pharmacy grass backup");
                    string path = r.ReadString();
                    int n = r.ReadInt32();
                    for (int k = 0; k < n; k++)
                    {
                        int i = r.ReadInt32(); float bx = r.ReadSingle(), bz = r.ReadSingle(), oy = r.ReadSingle(), oh = r.ReadSingle();
                        int off = i * 32;
                        if (path != grassPath || i < 0 || i >= blades || BitConverter.ToSingle(gb, off) != bx || BitConverter.ToSingle(gb, off + 8) != bz || BitConverter.ToSingle(gb, off + 12) != 0f)
                        { staleRecords++; continue; }
                        Buffer.BlockCopy(BitConverter.GetBytes(oy), 0, gb, off + 4, 4);
                        Buffer.BlockCopy(BitConverter.GetBytes(oh), 0, gb, off + 12, 4);
                        restored++;
                    }
                }
                catch (Exception e) { return "grass: backup " + backup + " unreadable (" + e.Message + "); nothing changed"; }
            }
            Rect all = areas[0];
            foreach (var a in areas) all = Rect.MinMaxRect(Mathf.Min(all.xMin, a.xMin), Mathf.Min(all.yMin, a.yMin), Mathf.Max(all.xMax, a.xMax), Mathf.Max(all.yMax, a.yMax));
            var records = new List<(int i, float x, float z, float y, float h)>();
            foreach (var c in grass.data.chunks)
            {
                if (c.centre.x + c.extents.x < all.xMin || c.centre.x - c.extents.x > all.xMax || c.centre.z + c.extents.z < all.yMin || c.centre.z - c.extents.z > all.yMax) continue;
                for (uint k = c.start; k < c.start + c.count && (k + 1) * 32 <= gb.Length; k++)
                {
                    int off = (int)k * 32;
                    float x = BitConverter.ToSingle(gb, off), y = BitConverter.ToSingle(gb, off + 4), z = BitConverter.ToSingle(gb, off + 8), h = BitConverter.ToSingle(gb, off + 12);
                    if (h <= 0f || y > floor + 1.2f) continue;
                    var q = new Vector2(x, z);
                    if (!areas.Any(a => a.Contains(q))) continue;
                    records.Add(((int)k, x, z, y, h));
                    Buffer.BlockCopy(BitConverter.GetBytes(0f), 0, gb, off + 12, 4);
                }
            }
            if (restored > 0 || records.Count > 0)
            {
                File.WriteAllBytes(grassPath, gb);
                AssetDatabase.ImportAsset(grassPath, ImportAssetOptions.ForceUpdate);
            }
            Folder(sideDir);
            using (var w = new BinaryWriter(File.Create(backup)))
            {
                w.Write("PHG1"); w.Write(grassPath); w.Write(records.Count);
                foreach (var b in records) { w.Write(b.i); w.Write(b.x); w.Write(b.z); w.Write(b.y); w.Write(b.h); }
            }
            AssetDatabase.ImportAsset(backup);
            // the renderer keeps its GPU copy until it is rebuilt: rebuild it now so the edit shows in the editor at once
            if (grass.isActiveAndEnabled) { grass.enabled = false; grass.enabled = true; }
            return $"grass data: {records.Count} blade(s) cleared (unit, rear ramp, street path) in {grassPath}" +
                   $"; previous run: {restored} restored first{(staleRecords > 0 ? $", {staleRecords} stale record(s) ignored (file changed since)" : "")}; backup {backup}";
        }

        /// <summary>Counts the baked tall-grass blades standing inside the unit (the check after the clearing).</summary>
        static string PharmacyGrassReport(Scene scene, float x0, float x1, float z0, float z1, float floor)
        {
            var grass = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<W85GrassRenderer>(true)).FirstOrDefault(g => g.data && g.data.instances);
            if (!grass) return "grass: no baked grass renderer";
            byte[] bytes = grass.data.instances.bytes;
            int n = 0, above = 0;
            var area = MinMax(new Vector3(x0, -100f, z0), new Vector3(x1, 100f, z1));
            foreach (var c in grass.data.chunks)
            {
                if (!new Bounds(c.centre, c.extents * 2f).Intersects(area)) continue;
                for (uint i = c.start; i < c.start + c.count; i++)
                {
                    int o = (int)i * 32;
                    float x = BitConverter.ToSingle(bytes, o), y = BitConverter.ToSingle(bytes, o + 4), z = BitConverter.ToSingle(bytes, o + 8), h = BitConverter.ToSingle(bytes, o + 12);
                    if (x <= x0 || x >= x1 || z <= z0 || z >= z1) continue;
                    n++; if (y + h > floor + .01f) above++;
                }
            }
            return n == 0 ? $"grass check: no baked blades inside the unit ({grass.data.name})"
                : above == 0 ? $"grass check: {n} blade records inside the unit, all cleared (height 0) - none reaches the shop floor ({grass.data.name})"
                : $"WARNING grass: {n} baked blades of {grass.data.name} stand inside the unit footprint, {above} reach above the shop floor";
        }

        static void SnapPharmacyStreetBin(Scene scene, GameObject building)
        {
            var bin = building.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "PH_P_StreetBin");
            if (!bin) { Note("pharmacy: no PH_P_StreetBin to snap"); return; }
            Vector3 p = bin.position;
            float best = float.MinValue;
            foreach (var h in Physics.RaycastAll(new Vector3(p.x, p.y + 2f, p.z), Vector3.down, 4f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore))
                if (!h.collider.transform.IsChildOf(bin) && h.normal.y > .7f && h.collider.gameObject.scene == scene) best = Mathf.Max(best, h.point.y);
            if (best == float.MinValue) { Note("pharmacy: street bin - no ground under it"); return; }
            bin.position = new Vector3(p.x, best, p.z);
            EditorUtility.SetDirty(bin);
            Note($"pharmacy: street bin snapped {best - p.y:+0.00;-0.00} m onto the pavement at {F(bin.position)}");
        }

        /// <summary>The root <see cref="PharmacyAnchorsName"/> at the unit's pose, children at the unit-local points of the
        /// anchors JSON: the cash desk (PharmacyCounterV01 at the purchase point), the staff routine (PharmacyStaffV01 with
        /// the route counter -> staff door -> stockroom -> rear door -> yard and its two doors), the rear loading point and
        /// the van stop in the yard. Idempotent (found by name, every field re-set); then the clearance checks.</summary>
        static string PlacePharmacyAnchors(Scene scene, GameObject building, Dictionary<string, object> A)
        {
            var sb = new StringBuilder();
            GameObject root = UniqueRoot(scene, PharmacyAnchorsName);
            root.transform.SetPositionAndRotation(building.transform.position, building.transform.rotation);
            root.transform.localScale = Vector3.one;

            var pj = WsObj(A, "counter_purchase_point");
            var desk = UniqueChild(root.transform, "PurchasePoint (cash desk)");
            desk.transform.localPosition = WsV3(pj, "position");
            desk.transform.localRotation = Quaternion.Euler(0f, WsNum(pj != null && pj.TryGetValue("yaw", out var py) ? py : null), 0f);
            var counter = desk.GetComponent<PharmacyCounterV01>();
            if (!counter) counter = desk.AddComponent<PharmacyCounterV01>();
            counter.Radius = 1.35f;
            EditorUtility.SetDirty(counter);

            var staffGo = UniqueChild(root.transform, "StaffRoutine (pharmacist placeholder)");
            staffGo.transform.localPosition = Vector3.zero; staffGo.transform.localRotation = Quaternion.identity;
            var staff = staffGo.GetComponent<PharmacyStaffV01>();
            if (!staff) staff = staffGo.AddComponent<PharmacyStaffV01>();
            var route = List(A, "staff_npc_route").OfType<Dictionary<string, object>>().ToList();
            foreach (Transform c in staffGo.transform.Cast<Transform>().ToList()) Object.DestroyImmediate(c.gameObject);
            var nodes = new Transform[route.Count];
            for (int i = 0; i < route.Count; i++)
            {
                var n = new GameObject($"Node_{i}" + (i == 0 ? " (cash desk)" : i == route.Count - 1 ? " (service yard)" : ""));
                n.transform.SetParent(staffGo.transform, false);
                n.transform.localPosition = WsV3(route[i], "position");
                n.transform.localRotation = Quaternion.Euler(0f, i == 0 ? 0f : 180f, 0f);   // at the desk he faces the customers
                nodes[i] = n.transform;
            }
            var doors = building.GetComponentsInChildren<PharmacyDoorV01>(true);
            staff.Route = nodes;
            staff.Doors = new[] { doors.FirstOrDefault(d => d.name == "Door_Staff"), doors.FirstOrDefault(d => d.name == "Door_Rear") };
            staff.DoorFrom = new[] { 2, 5 };                                             // staff door: sales side .. past its sweep in the stockroom
            staff.DoorTo = new[] { Mathf.Min(4, nodes.Length - 1), nodes.Length - 1 };  // rear door: inside .. the yard spot
            EditorUtility.SetDirty(staff);

            // network (Fedya 29.10, co-op): the server-owned pharmacy state - doors, opening hours, the pharmacist, purchases
            var net = root.GetComponent<PharmacyNetV01>();
            if (!net) net = root.AddComponent<PharmacyNetV01>();
            var fpj = WsObj(A, "footprint");
            Vector3 fsize = WsV3(fpj, "size_xyz");
            Vector3 wc = new Vector3(PharmacyPos.x, PharmacyPos.y + fsize.y * .5f, PharmacyPos.z + fsize.z * .5f);   // the unit's box (yaw 180: north of the front)
            net.InsideCentre = root.transform.InverseTransformPoint(wc);
            net.InsideSize = new Vector3(fsize.x, fsize.y, fsize.z);
            net.Doors = PhDoors.Select(n => doors.FirstOrDefault(d => d.name == n)).Where(d => d).ToArray();
            net.Staff = staff;
            EditorUtility.SetDirty(net);

            var vl = WsObj(A, "rear_van_loading");
            var load = UniqueChild(root.transform, "LoadingPoint (rear door, yard)");
            load.transform.localPosition = WsV3(WsObj(vl, "loading_point"), "position");
            load.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);
            { var lp = load.transform.position; load.transform.position = new Vector3(lp.x, GroundRay(scene, lp.x, lp.z, (x, z) => lp.y), lp.z); }
            var van = UniqueChild(root.transform, "VanStop (yard H3-H2, nose east, sliding door to the rear door)");
            float vy = GroundRay(scene, PharmacyVanStop.x, PharmacyVanStop.y, (x, z) => PharmacyPos.y);
            van.transform.SetPositionAndRotation(new Vector3(PharmacyVanStop.x, vy, PharmacyVanStop.y), Quaternion.Euler(0f, PharmacyVanYaw, 0f));
            EditorUtility.SetDirty(root);

            // ---- checks (doors are left out: they open)
            Physics.SyncTransforms();
            string Blocked(Vector3 feet)
            {
                var hits = Physics.OverlapCapsule(feet + Vector3.up * .55f, feet + Vector3.up * 1.6f, .42f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore)
                    .Where(c => c.gameObject.scene == scene && !(c is TerrainCollider) && !c.GetComponentInParent<PharmacyDoorV01>() && c.transform.root.name != "Van")
                    .Select(c => PathOf(c.transform).Replace(PharmacyBuildingName + "/", "")).Distinct().ToList();
                return hits.Count == 0 ? "" : string.Join(", ", hits.Take(3));
            }
            string Walk(string label, List<Vector3> pts)
            {
                var bad = new List<string>();
                for (int i = 0; i + 1 < pts.Count; i++)
                {
                    float len = Vector3.Distance(pts[i], pts[i + 1]);
                    for (float d = 0f; d <= len; d += .25f)
                    {
                        Vector3 p = Vector3.Lerp(pts[i], pts[i + 1], d / Mathf.Max(len, .001f));
                        string b = Blocked(p);
                        if (b.Length > 0) { bad.Add($"{F(p)}: {b}"); break; }
                    }
                }
                return bad.Count == 0 ? $"  {label}: clear (capsule r 0.42)" : $"  WARNING {label} blocked at " + string.Join("; ", bad.Take(3));
            }
            Vector3 L(Vector3 local) => root.transform.TransformPoint(local);
            var sd = WsObj(A, "street_door");
            Vector3 outside = L(WsV3(WsObj(sd, "outside"), "position"));
            Vector3 street = outside + root.transform.forward * 1.0f;
            street.y = GroundRay(scene, street.x, street.z, (x, z) => PharmacyPos.y);
            sb.AppendLine(Walk("customer street -> cash desk", new List<Vector3> { street, outside, L(WsV3(WsObj(sd, "inside"), "position")), desk.transform.position }));
            sb.AppendLine(Walk("staff route cash desk -> yard", nodes.Select(n => n.position).ToList()));
            var rd = WsObj(A, "rear_door");
            var cs = WsObj(WsObj(A, "stockroom"), "capture_space");
            sb.AppendLine(Walk("carry stockroom -> rear door -> loading point", new List<Vector3> { L(WsV3(cs, "centre")), L(WsV3(WsObj(rd, "inside"), "position")), L(WsV3(WsObj(rd, "outside"), "position")), load.transform.position }));
            var vanHits = Physics.OverlapBox(van.transform.position + Vector3.up * 1.25f, new Vector3(1.0f, 1.1f, 2.6f), van.transform.rotation, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore)
                .Where(c => c.gameObject.scene == scene && !(c is TerrainCollider)).Select(c => PathOf(c.transform)).Distinct().ToList();
            sb.AppendLine(vanHits.Count == 0 ? $"  van stop {F(van.transform.position)} yaw {PharmacyVanYaw:0}: 5.2 x 2.0 m box clear" : "  WARNING van stop box hits: " + string.Join(", ", vanHits.Take(5)));
            var lane = Physics.OverlapBox(new Vector3(693f, vy + 1.25f, PharmacyVanStop.y), new Vector3(37f, 1.1f, 1.3f), Quaternion.identity, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore)
                .Where(c => c.gameObject.scene == scene && !(c is TerrainCollider)).Select(c => PathOf(c.transform)).Distinct().ToList();
            sb.AppendLine(lane.Count == 0 ? "  yard drive lane x 656-730 (2.6 m wide on the van line): clear" : "  yard drive lane x 656-730: " + string.Join(", ", lane.Take(6)));
            Vector3 rdOut = L(WsV3(WsObj(rd, "outside"), "position")), vanDoor = van.transform.position + van.transform.right * 1.0f;   // right-hand sliding door (yaw 90: south, towards the house)
            sb.AppendLine($"  walk rear door (outside) -> van sliding door: {Vector2.Distance(new Vector2(rdOut.x, rdOut.z), new Vector2(vanDoor.x, vanDoor.z)):0.0} m; loading point ground {GroundRay(scene, load.transform.position.x, load.transform.position.z, (x, z) => 0f) - load.transform.position.y:+0.00;-0.00} m");
            sb.Insert(0, $"pharmacy anchors: root {PharmacyAnchorsName} at {F(root.transform.position)}; cash desk {F(desk.transform.position)} (r {counter.Radius:0.00}), staff route {nodes.Length} nodes, doors {staff.Doors.Count(d => d)}/2, van stop {F(van.transform.position)}\n" +
                         $"pharmacy network: PharmacyNetV01 on {PharmacyAnchorsName}, {net.Doors.Length}/3 doors ({string.Join(", ", net.Doors.Select(d => d.name))}), inside box {F(wc)} size {F(net.InsideSize)}, hours {PharmacyHours.SignText}\n");
            return sb.ToString().TrimEnd();
        }
    }
}
