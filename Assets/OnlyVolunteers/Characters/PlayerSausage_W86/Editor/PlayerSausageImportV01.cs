using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using OnlyVolunteers.Characters.Player;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Characters.Player.EditorTools
{
    /// <summary>
    /// Imports PLAYER_SAUSAGE_W86 v01 (29.10, made in Blender: ArtSource/Characters/PLAYER_SAUSAGE_W86) into
    /// Characters/PlayerSausage_W86: the base and parts FBX into Models (copied, never over an existing file), imported like
    /// the NPC types (Generic, Copy From Other Avatar = Buddy A's, so every shared Sausage Buddy clip plays; no clip import;
    /// blend shapes; materials in the model), the parts manifest into Resources, and the prefab
    /// Prefabs/PLAYER_SAUSAGE_W86_v01.prefab: the base model with every option mesh of the parts FBX re-bound to the base
    /// skeleton by bone name (the parts' own skeleton removed), Animator with SausageBuddy_Greybox and Buddy A's avatar (no
    /// root motion), Face blend shapes at 0, a LODGroup (LOD0/1/2 at 15 / 40 / 150 m like the crowd) and
    /// PlayerSausageAvatarV01 dressing it with the default look.
    /// </summary>
    public static class PlayerSausageImportV01
    {
        public const string Root = "Assets/OnlyVolunteers/Characters/PlayerSausage_W86";
        public const string PrefabPath = Root + "/Prefabs/PLAYER_SAUSAGE_W86_v01.prefab";
        const string Source = "ArtSource/Characters/PLAYER_SAUSAGE_W86";
        const string BaseFbx = "PLAYER_SAUSAGE_W86_v01_base.fbx", PartsFbx = "PLAYER_SAUSAGE_W86_v01_parts.fbx", ManifestJson = "PLAYER_SAUSAGE_W86_v01_manifest.json";
        const string BuddyAFbx = "Assets/OnlyVolunteers/Characters/SausageBuddy/SAUSAGE_BUDDY_A_v04.fbx";
        const string ControllerPath = "Assets/OnlyVolunteers/Characters/SausageBuddy/SausageBuddy_Greybox.controller";
        const float LodFigureM = 1.8f, GameFov = 75f;
        static readonly float[] LodDistancesM = { 15f, 40f, 150f };

        [MenuItem("OnlyVolunteers/Characters/Import PLAYER_SAUSAGE_W86 v01")]
        public static void ImportMenu() => Debug.Log(Import());

        public static string Import()
        {
            var log = new StringBuilder();
            string project = Path.GetDirectoryName(Application.dataPath) ?? "";
            Directory.CreateDirectory(Path.Combine(project, Root, "Models"));
            Directory.CreateDirectory(Path.Combine(project, Root, "Prefabs"));
            Directory.CreateDirectory(Path.Combine(project, Root, "Resources"));
            Copy(project, BaseFbx, Root + "/Models/" + BaseFbx, log);
            Copy(project, PartsFbx, Root + "/Models/" + PartsFbx, log);
            Copy(project, ManifestJson, Root + "/Resources/" + ManifestJson, log);
            AssetDatabase.Refresh();

            Avatar avatar = null;
            foreach (Object o in AssetDatabase.LoadAllAssetsAtPath(BuddyAFbx)) if (o is Avatar a) avatar = a;
            if (avatar == null) return log.Append("FAILED: no Buddy A avatar at " + BuddyAFbx).ToString();
            Configure(Root + "/Models/" + BaseFbx, avatar, log);
            Configure(Root + "/Models/" + PartsFbx, avatar, log);
            var baseModel = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Models/" + BaseFbx);
            var partsModel = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Models/" + PartsFbx);
            var manifest = AssetDatabase.LoadAssetAtPath<TextAsset>(Root + "/Resources/" + ManifestJson);
            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(ControllerPath);
            if (baseModel == null || partsModel == null || manifest == null) return log.Append("FAILED: model or manifest missing after import").ToString();

            var root = (GameObject)PrefabUtility.InstantiatePrefab(baseModel);
            PrefabUtility.UnpackPrefabInstance(root, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            root.name = "PLAYER_SAUSAGE_W86_v01";
            var parts = (GameObject)PrefabUtility.InstantiatePrefab(partsModel);
            PrefabUtility.UnpackPrefabInstance(parts, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            try
            {
                var bones = new Dictionary<string, Transform>(StringComparer.Ordinal);
                foreach (Transform t in root.GetComponentsInChildren<Transform>(true)) if (!bones.ContainsKey(t.name)) bones[t.name] = t;
                int moved = 0, missing = 0;
                foreach (SkinnedMeshRenderer smr in parts.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                {
                    var mapped = new Transform[smr.bones.Length];
                    for (int i = 0; i < mapped.Length; i++)
                    {
                        Transform b = smr.bones[i];
                        if (b != null && bones.TryGetValue(b.name, out Transform to)) mapped[i] = to; else { mapped[i] = null; missing++; }
                    }
                    Transform rootBone = smr.rootBone != null && bones.TryGetValue(smr.rootBone.name, out Transform rb) ? rb : null;
                    smr.transform.SetParent(root.transform, false);
                    smr.bones = mapped;
                    if (rootBone != null) smr.rootBone = rootBone;
                    moved++;
                }
                log.AppendLine($"parts: {moved} meshes re-bound to the base skeleton ({missing} unmatched bone slots)");
                // the base may already carry an Animator from its FBX
                if (!root.TryGetComponent(out Animator animator)) animator = root.AddComponent<Animator>();
                animator.runtimeAnimatorController = controller;
                animator.avatar = avatar;
                animator.applyRootMotion = false;
                animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                int shapes = 0;
                foreach (SkinnedMeshRenderer smr in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                    if (smr.sharedMesh != null && smr.sharedMesh.blendShapeCount > 0 && smr.name.StartsWith("Face", StringComparison.Ordinal))
                        for (int i = 0; i < smr.sharedMesh.blendShapeCount; i++) { smr.SetBlendShapeWeight(i, 0f); shapes++; }
                log.AppendLine($"face blend shapes zeroed: {shapes}");
                SetupLods(root);
                if (!root.TryGetComponent(out PlayerSausageAvatarV01 dress)) dress = root.AddComponent<PlayerSausageAvatarV01>();
                dress.Manifest = manifest;
                dress.Apply(OnlyVolunteers.Session.AppearanceRules.Default());
                int smrs = root.GetComponentsInChildren<SkinnedMeshRenderer>(true).Length, on = 0;
                foreach (var smr in root.GetComponentsInChildren<SkinnedMeshRenderer>(false)) on++;
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath, out bool ok);
                log.AppendLine($"prefab {PrefabPath}: {(ok ? "saved" : "FAILED")} ({smrs} skinned meshes, {on} on with the default look)");
            }
            finally
            {
                Object.DestroyImmediate(parts);
                Object.DestroyImmediate(root);
            }
            AssetDatabase.SaveAssets();
            return log.ToString();
        }

        static void Copy(string project, string file, string target, StringBuilder log)
        {
            string from = Path.Combine(project, Source, file), to = Path.Combine(project, target);
            if (File.Exists(to)) { log.AppendLine("kept " + target); return; }
            if (!File.Exists(from)) { log.AppendLine("MISSING source " + from); return; }
            File.Copy(from, to);
            log.AppendLine("copied " + target);
        }

        static void Configure(string path, Avatar avatar, StringBuilder log)
        {
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer == null) { log.AppendLine("no ModelImporter for " + path); return; }
            importer.animationType = ModelImporterAnimationType.Generic;
            importer.avatarSetup = ModelImporterAvatarSetup.CopyFromOther;
            importer.sourceAvatar = avatar;
            importer.importAnimation = false;
            importer.importBlendShapes = true;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
            importer.materialLocation = ModelImporterMaterialLocation.InPrefab;
            importer.SaveAndReimport();
            log.AppendLine("imported " + path + " (Generic, Buddy A avatar)");
        }

        static int LodOf(string name, out string part)
        {
            int i = name.LastIndexOf("_LOD", StringComparison.Ordinal);
            if (i > 0 && int.TryParse(name.Substring(i + 4), out int lod)) { part = name.Substring(0, i); return lod; }
            part = name;
            return 0;
        }

        // as NpcTypesImportV01.SetupLods: level n = each part's _LODn (or its next finer one), switches at 15 / 40 / 150 m
        static void SetupLods(GameObject root)
        {
            var parts = new Dictionary<string, SortedDictionary<int, Renderer>>();
            int maxLod = 0;
            foreach (SkinnedMeshRenderer smr in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                int lod = LodOf(smr.name, out string part);
                if (!parts.TryGetValue(part, out var p)) parts[part] = p = new SortedDictionary<int, Renderer>();
                p[lod] = smr;
                maxLod = Math.Max(maxLod, lod);
            }
            root.TryGetComponent(out LODGroup group);
            if (maxLod == 0) { if (group != null) Object.DestroyImmediate(group); return; }
            var levels = new List<Renderer>[maxLod + 1];
            for (int l = 0; l <= maxLod; l++) levels[l] = new List<Renderer>();
            foreach (var p in parts.Values)
            {
                if (!p.ContainsKey(0)) continue;
                Renderer last = null;
                for (int l = 0; l <= maxLod; l++) { if (p.TryGetValue(l, out Renderer r)) last = r; levels[l].Add(last); }
            }
            if (group == null) group = root.AddComponent<LODGroup>();
            float k = Mathf.Max(0.1f, QualitySettings.lodBias) * LodFigureM / (2f * Mathf.Tan(GameFov * 0.5f * Mathf.Deg2Rad));
            var lods = new LOD[maxLod + 1];
            float previous = 1f;
            for (int l = 0; l <= maxLod; l++)
            {
                float d = l == maxLod ? LodDistancesM[LodDistancesM.Length - 1] : LodDistancesM[Math.Min(l, LodDistancesM.Length - 2)];
                previous = Mathf.Min(previous * 0.999f, Mathf.Clamp(k / d, 0.001f, 0.99f));
                lods[l] = new LOD(previous, levels[l].ToArray());
            }
            group.fadeMode = LODFadeMode.None;
            group.SetLODs(lods);
            group.localReferencePoint = new Vector3(0f, LodFigureM * 0.5f, 0f);
            group.size = LodFigureM;
        }
    }
}
