using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Operation.Stage1.EditorTools;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.Editor
{
    /// <summary>Integrates an approved anatomy revision into stage 1 from a small table of paths (Claude round 2,
    /// 2026-10-18): the next revision (v04: organ block lower, OperationAbdomen_v04 with a bigger opening) is one more
    /// <see cref="Revision"/> entry and a menu line, no new code.
    /// What it does, all idempotent:
    /// 1. copies the revision's files from ArtSource into Operation/Stage1/Art (ArtSource is only read; an existing copy
    ///    with other content is never overwritten: the run stops);
    /// 2. keeps Unity's default FBX import (as the v03 copies) and makes the ribcage readable (its UCX_* meshes become runtime
    ///    bone colliders, OperationSurgicalBones);
    /// 3. points the patient prefab at a new patient FBX when the revision has one (same 65-bone rig, avatar, NpcRig
    ///    profile, materials by slot; Patient_Skin_Closed never stencilled), checks the anchors and sockets;
    /// 4. reads the stage-1 tuning values from the revision's ORGANS_LAYOUT json (belly guide and cut length, opening half
    ///    size, kidney cords, organ half sizes; Blender X negated into Unity like the v03 tool did by hand) and sets the organ,
    ///    chest and abdomen models; 5. re-bakes the player-safe query meshes (the new ABDOMEN_MASK);
    /// 6. makes sure the layer SurgicalBone and the tags SurgicalRib / SurgicalSternum exist.</summary>
    public static class OperationStage1Anatomy
    {
        private const string Stage = "Assets/OnlyVolunteers/Operation/Stage1/";
        private const string Art = Stage + "Art/";
        private const string Source = "ArtSource/Characters/SAUSAGE_BUDDY_01/";
        private const string OldPatient = "Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/";

        public sealed class Revision
        {
            public string Label;
            /// <summary>ORGANS_LAYOUT json under ArtSource (read only).</summary>
            public string Layout;
            /// <summary>ArtSource file → Assets copy (made when missing; an identical copy is fine; a different one stops).</summary>
            public (string from, string to)[] Copies = new (string, string)[0];
            /// <summary>Patient FBX (Assets); null keeps the current patient model.</summary>
            public string Patient;
            /// <summary>Kidney L, kidney R, liver (Assets FBX).</summary>
            public string[] Organs;
            /// <summary>Heart, lung L, lung R, ribcage, chest vessels (Assets FBX).</summary>
            public string[] Chest;
            public string Abdomen, AbdomenGradient;
            /// <summary>Round 3: the sutured state of the opening (same INC_ABDOMEN frame); null keeps the current one.</summary>
            public string Sutured;
        }

        private static string O(string name) => Art + "Organs_v03/" + name + ".fbx";

        /// <summary>v03 with G38's v03d ribcage: four thick rib pairs (render v03c) and 96 convex UCX bone colliders.</summary>
        public static readonly Revision V03d = new Revision
        {
            Label = "v03d",
            Layout = Source + "Patient_v03/ORGANS_LAYOUT_v03d.json",
            Copies = new[] { (Source + "Organs_v03/FBX/RIBCAGE_v03d.fbx", O("RIBCAGE_v03d")) },
            Organs = new[] { O("ORGAN_KIDNEY_L_v03"), O("ORGAN_KIDNEY_R_v03"), O("ORGAN_LIVER_v03") },
            Chest = new[] { O("ORGAN_HEART_v03"), O("ORGAN_LUNG_L_v03"), O("ORGAN_LUNG_R_v03"), O("RIBCAGE_v03d"), O("CHEST_VESSELS_v03") },
            Abdomen = Art + "Abdomen_v03/OperationAbdomen_v03.fbx",
            AbdomenGradient = Art + "Abdomen_v03/OperationAbdomen_v03_Gradient.png",
        };
        private static string O4(string name) => Art + "Organs_v04/" + name + ".fbx";
        private static (string, string) Fbx4(string name) => (Source + "Organs_v04/FBX/" + name + ".fbx", O4(name));

        /// <summary>v04 (Fedya approved 2026-10-18): the whole organ block 4.5 cm lower, ribs v04 (back tips trimmed, 96 UCX,
        /// same SurgicalBone contract), the big chest+belly opening OperationAbdomen_v04, patient v04 (same rig and weights,
        /// markers/sockets moved).</summary>
        public static readonly Revision V04 = new Revision
        {
            Label = "v04",
            Layout = Source + "Patient_v04/ORGANS_LAYOUT_v04.json",
            Copies = new[]
            {
                (Source + "Patient_v04/SAUSAGE_BUDDY_PATIENT_v04.fbx", Art + "Patient_v04/SAUSAGE_BUDDY_PATIENT_v04.fbx"),
                Fbx4("ORGAN_KIDNEY_L_v04"), Fbx4("ORGAN_KIDNEY_R_v04"), Fbx4("ORGAN_LIVER_v04"),
                Fbx4("ORGAN_HEART_v04"), Fbx4("ORGAN_LUNG_L_v04"), Fbx4("ORGAN_LUNG_R_v04"), Fbx4("RIBCAGE_v04"), Fbx4("CHEST_VESSELS_v04"),
                ("ArtSource/Props/TABLE-ASTRA-001/v04/OperationAbdomen_v04.fbx", Art + "Abdomen_v04/OperationAbdomen_v04.fbx"),
                ("ArtSource/Props/TABLE-ASTRA-001/v04/OperationAbdomen_v04_Gradient.png", Art + "Abdomen_v04/OperationAbdomen_v04_Gradient.png"),
            },
            Patient = Art + "Patient_v04/SAUSAGE_BUDDY_PATIENT_v04.fbx",
            Organs = new[] { O4("ORGAN_KIDNEY_L_v04"), O4("ORGAN_KIDNEY_R_v04"), O4("ORGAN_LIVER_v04") },
            Chest = new[] { O4("ORGAN_HEART_v04"), O4("ORGAN_LUNG_L_v04"), O4("ORGAN_LUNG_R_v04"), O4("RIBCAGE_v04"), O4("CHEST_VESSELS_v04") },
            Abdomen = Art + "Abdomen_v04/OperationAbdomen_v04.fbx",
            AbdomenGradient = Art + "Abdomen_v04/OperationAbdomen_v04_Gradient.png",
        };
        private static string O5(string name) => Art + "Organs_v05/" + name + ".fbx";
        private static (string, string) Fbx5(string name) => (Source + "Organs_v05/FBX/" + name + ".fbx", O5(name));

        /// <summary>v05 (Fedya approved 2026-10-18): bigger and lower opening, chest block lower, kidneys moved, intestines
        /// back, low-rise trunks (stencil zone +7 faces), and the sutured state OperationSutured_v05 (20 ordered stitches).</summary>
        public static readonly Revision V05 = new Revision
        {
            Label = "v05",
            Layout = Source + "Patient_v05/ORGANS_LAYOUT_v05.json",
            Copies = new[]
            {
                (Source + "Patient_v05/SAUSAGE_BUDDY_PATIENT_v05.fbx", Art + "Patient_v05/SAUSAGE_BUDDY_PATIENT_v05.fbx"),
                Fbx5("ORGAN_KIDNEY_L_v05"), Fbx5("ORGAN_KIDNEY_R_v05"), Fbx5("ORGAN_LIVER_v05"),
                Fbx5("ORGAN_HEART_v05"), Fbx5("ORGAN_LUNG_L_v05"), Fbx5("ORGAN_LUNG_R_v05"), Fbx5("RIBCAGE_v05"), Fbx5("CHEST_VESSELS_v05"),
                ("ArtSource/Props/TABLE-ASTRA-001/v05/OperationAbdomen_v05.fbx", Art + "Abdomen_v05/OperationAbdomen_v05.fbx"),
                ("ArtSource/Props/TABLE-ASTRA-001/v05/OperationAbdomen_v05_Gradient.png", Art + "Abdomen_v05/OperationAbdomen_v05_Gradient.png"),
                ("ArtSource/Props/TABLE-ASTRA-001/v05/OperationSutured_v05.fbx", Art + "Abdomen_v05/OperationSutured_v05.fbx"),
            },
            Patient = Art + "Patient_v05/SAUSAGE_BUDDY_PATIENT_v05.fbx",
            Organs = new[] { O5("ORGAN_KIDNEY_L_v05"), O5("ORGAN_KIDNEY_R_v05"), O5("ORGAN_LIVER_v05") },
            Chest = new[] { O5("ORGAN_HEART_v05"), O5("ORGAN_LUNG_L_v05"), O5("ORGAN_LUNG_R_v05"), O5("RIBCAGE_v05"), O5("CHEST_VESSELS_v05") },
            Abdomen = Art + "Abdomen_v05/OperationAbdomen_v05.fbx",
            AbdomenGradient = Art + "Abdomen_v05/OperationAbdomen_v05_Gradient.png",
            Sutured = Art + "Abdomen_v05/OperationSutured_v05.fbx",
        };
        // The next revision: one more entry like V04 (its copies, patient, organs, chest, abdomen, ORGANS_LAYOUT json) and
        // a menu line; Apply does the rest.

        [MenuItem("OnlyVolunteers/Operation/Integrate anatomy v03d (4 rib pairs + bone colliders)")]
        public static void MenuV03d() => Debug.Log("[OPS] " + Apply(V03d));

        [MenuItem("OnlyVolunteers/Operation/Integrate anatomy v04 (organs 4.5 cm lower, big opening)")]
        public static void MenuV04() => Debug.Log("[OPS] " + Apply(V04));

        [MenuItem("OnlyVolunteers/Operation/Integrate anatomy v05 (lower opening, intestines, sutured state)")]
        public static void MenuV05() => Debug.Log("[OPS] " + Apply(V05));

        public static string Apply(Revision r)
        {
            if (EditorApplication.isPlaying || EditorApplication.isCompiling) throw new InvalidOperationException("Editor must be idle");
            var log = new System.Text.StringBuilder("anatomy " + r.Label + ": ");
            string project = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            // 1. copies
            foreach (var (from, to) in r.Copies)
            {
                string src = Path.Combine(project, from), dst = Path.Combine(project, to);
                if (!File.Exists(src)) throw new FileNotFoundException("ArtSource file missing", src);
                if (File.Exists(dst))
                {
                    if (!File.ReadAllBytes(src).SequenceEqual(File.ReadAllBytes(dst))) throw new InvalidOperationException("A different copy already exists (never overwritten): " + to);
                    continue;
                }
                Directory.CreateDirectory(Path.GetDirectoryName(dst));
                File.Copy(src, dst);
                log.Append("copied ").Append(Path.GetFileName(to)).Append("; ");
            }
            AssetDatabase.Refresh();
            // 2. import: default settings like the v03 copies; the ribcage readable (runtime bone colliders)
            for (int i = 0; i < r.Chest.Length; i++) MatchImport(r.Chest[i], i == 3, log);
            foreach (var organ in r.Organs) MatchImport(organ, false, log);
            // 3. patient
            if (!string.IsNullOrEmpty(r.Patient)) log.Append(SwapPatient(r.Patient)).Append("; ");
            // 4. tuning from the layout json
            var tuning = AssetDatabase.LoadAssetAtPath<OperationTuning>(Stage + "Data/OperationStage1_v02.asset");
            var layout = JObject.Parse(File.ReadAllText(Path.Combine(project, r.Layout)));
            tuning.anatomicalLayout = true; tuning.anatomyV03 = true;
            var belly = layout["guide_belly"];
            tuning.bellyStart = Unity(belly["abdomen_local_start"]); tuning.bellyEnd = Unity(belly["abdomen_local_end"]);
            tuning.abdomenCutLength = (float)belly["length_m"];
            var opening = layout["opening_abdomen"];
            tuning.abdomenHalfSize = new Vector2((float)opening["half_width"], ((float)opening["half_length_top"] + (float)opening["half_length_bottom"]) * 0.5f);
            Vector3 Cord(string organ, string cord, string end) => V(layout["organs"][organ]["cords"][cord]["marker_local_unity_" + end]);
            tuning.cordStarts = new[] { Cord("ORGAN_KIDNEY_L", "A_renal_artery", "start"), Cord("ORGAN_KIDNEY_L", "B_renal_vein", "start"), Cord("ORGAN_KIDNEY_R", "A_renal_artery", "start"), Cord("ORGAN_KIDNEY_R", "B_renal_vein", "start") };
            tuning.cordEnds = new[] { Cord("ORGAN_KIDNEY_L", "A_renal_artery", "end"), Cord("ORGAN_KIDNEY_L", "B_renal_vein", "end"), Cord("ORGAN_KIDNEY_R", "A_renal_artery", "end"), Cord("ORGAN_KIDNEY_R", "B_renal_vein", "end") };
            Vector2 Half(string organ) { var size = V(layout["organs"][organ]["size_m_xyz_local"]); return new Vector2(Round4(size.x * 0.5f), Round4(size.y * 0.5f)); }
            tuning.organHalfSize = new[] { Half("ORGAN_KIDNEY_L"), Half("ORGAN_KIDNEY_R"), Half("ORGAN_LIVER") };
            GameObject Load(string path) => AssetDatabase.LoadAssetAtPath<GameObject>(path);
            tuning.organModelsV03 = r.Organs.Select(Load).ToArray();
            tuning.chestModelsV03 = r.Chest.Select(Load).ToArray();
            tuning.abdomenModel = Load(r.Abdomen);
            tuning.abdomenGradient = AssetDatabase.LoadAssetAtPath<Texture2D>(r.AbdomenGradient);
            if (!string.IsNullOrEmpty(r.Sutured))
            {
                // The seam's progress lives in UV1 ("Progress"): no generated lightmap UVs over it.
                if (AssetImporter.GetAtPath(r.Sutured) is ModelImporter sutured && sutured.generateSecondaryUV) { sutured.generateSecondaryUV = false; sutured.SaveAndReimport(); }
                tuning.suturedModel = Load(r.Sutured);
                if (tuning.suturedModel == null) throw new InvalidOperationException("Sutured model missing: " + r.Sutured);
            }
            if (tuning.abdomenModel == null || tuning.organModelsV03.Any(x => x == null) || tuning.chestModelsV03.Any(x => x == null))
                throw new InvalidOperationException("A model of " + r.Label + " is missing");
            EditorUtility.SetDirty(tuning); AssetDatabase.SaveAssetIfDirty(tuning);
            log.Append($"tuning: belly {tuning.bellyStart:F4}->{tuning.bellyEnd:F4}, cut {tuning.abdomenCutLength:F4}, half {tuning.abdomenHalfSize:F4}, organ halves {string.Join(" ", tuning.organHalfSize.Select(h => h.ToString("F4")))}; ");
            // 5. query meshes
            log.Append(OperationQueryMeshBaker.Bake()).Append("; ");
            // 6. layer and tags
            log.Append(EnsureLayerAndTags());
            int ucx = tuning.chestModelsV03[3].GetComponentsInChildren<MeshFilter>(true).Count(f => f.name.StartsWith("UCX_"));
            log.Append($"; ribcage {Path.GetFileName(r.Chest[3])}: {ucx} UCX bone colliders at runtime");
            AssetDatabase.SaveAssets();
            return log.ToString();
        }

        private static float Round4(float v) => Mathf.Round(v * 10000f) / 10000f;
        private static Vector3 V(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        /// <summary>A Blender-frame marker-local point into Unity (X negated after the FBX import).</summary>
        private static Vector3 Unity(JToken t) { var v = V(t); return new Vector3(-v.x, v.y, v.z); }

        /// <summary>The v03 model copies use Unity's default FBX import settings (checked: their .meta files match a fresh
        /// import); only the ribcage must be readable for its runtime bone colliders.</summary>
        private static void MatchImport(string path, bool readable, System.Text.StringBuilder log)
        {
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer == null) throw new InvalidOperationException("Not a model: " + path);
            if (readable && !importer.isReadable) { importer.isReadable = true; importer.SaveAndReimport(); log.Append("import ").Append(Path.GetFileName(path)).Append(" readable; "); }
        }

        private static string EnsureLayerAndTags()
        {
            var manager = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
            var layers = manager.FindProperty("layers"); var tags = manager.FindProperty("tags");
            string result = "";
            bool hasLayer = false;
            for (int i = 0; i < layers.arraySize; i++) if (layers.GetArrayElementAtIndex(i).stringValue == OperationSurgicalBones.LayerName) hasLayer = true;
            if (!hasLayer)
                for (int i = 8; i < layers.arraySize; i++)
                    if (string.IsNullOrEmpty(layers.GetArrayElementAtIndex(i).stringValue)) { layers.GetArrayElementAtIndex(i).stringValue = OperationSurgicalBones.LayerName; result += "layer SurgicalBone = " + i + "; "; hasLayer = true; break; }
            foreach (var tag in new[] { OperationSurgicalBones.RibTag, OperationSurgicalBones.SternumTag })
            {
                bool has = false;
                for (int i = 0; i < tags.arraySize; i++) if (tags.GetArrayElementAtIndex(i).stringValue == tag) has = true;
                if (!has) { tags.InsertArrayElementAtIndex(tags.arraySize); tags.GetArrayElementAtIndex(tags.arraySize - 1).stringValue = tag; result += "tag " + tag + "; "; }
            }
            manager.ApplyModifiedPropertiesWithoutUndo();
            return result.Length == 0 ? "layer and tags present" : result;
        }

        /// <summary>The v03 tool's patient step for a new patient FBX (same rig, avatar, profile, slot materials).</summary>
        private static string SwapPatient(string modelPath)
        {
            string path = Stage + "Prefabs/Stage1_Patient_v02.prefab";
            var patient = PrefabUtility.LoadPrefabContents(path);
            try
            {
                var prior = patient.GetComponentInChildren<Animator>();
                if (prior != null && PrefabUtility.GetCorrespondingObjectFromSource(prior.gameObject) is GameObject current &&
                    AssetDatabase.GetAssetPath(current) == modelPath) return "patient already " + Path.GetFileName(modelPath);
                var importer = (ModelImporter)AssetImporter.GetAtPath(modelPath);
                var oldImporter = (ModelImporter)AssetImporter.GetAtPath(OldPatient + "SAUSAGE_BUDDY_PATIENT_v01.fbx");
                importer.animationType = oldImporter.animationType;
                importer.avatarSetup = oldImporter.avatarSetup; importer.sourceAvatar = oldImporter.sourceAvatar;
                importer.importAnimation = false; importer.preserveHierarchy = true;
                importer.importNormals = ModelImporterNormals.Import; importer.SaveAndReimport();
                var skin = AssetDatabase.LoadAllAssetsAtPath(OldPatient + "SAUSAGE_BUDDY_PATIENT_v01.fbx").OfType<Material>().First(m => m.name == "Buddy_Skin");
                var nose = AssetDatabase.LoadAllAssetsAtPath(OldPatient + "SAUSAGE_BUDDY_PATIENT_v01.fbx").OfType<Material>().First(m => m.name == "Buddy_Skin_Nose");
                var closed = AssetDatabase.LoadAssetAtPath<Material>(Art + "Patient_v03/Patient_Skin_Closed.mat");
                var controller = prior.runtimeAnimatorController; var avatar = prior.avatar;
                var priorRig = prior.GetComponent<NpcRig>(); var profile = priorRig != null ? priorRig.Ragdoll : null;
                var materials = prior.GetComponentsInChildren<SkinnedMeshRenderer>().ToDictionary(x => x.name, x => x.sharedMaterials);
                UnityEngine.Object.DestroyImmediate(prior.gameObject);
                var model = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(modelPath), patient.transform);
                model.name = "PATIENT model";
                var animator = model.GetComponent<Animator>(); if (animator == null) animator = model.AddComponent<Animator>();
                animator.avatar = avatar; animator.runtimeAnimatorController = controller; animator.applyRootMotion = false; animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                var rig = model.GetComponent<NpcRig>(); if (rig == null) rig = model.AddComponent<NpcRig>(); rig.Animator = animator; rig.Ragdoll = profile;
                foreach (var mesh in model.GetComponentsInChildren<SkinnedMeshRenderer>())
                {
                    if (mesh.name == "Body")
                    {
                        var slots = mesh.sharedMaterials;
                        for (int i = 0; i < slots.Length; i++)
                            slots[i] = slots[i] == null ? skin : slots[i].name == "Buddy_Skin" ? skin : slots[i].name == "Buddy_Skin_Nose" ? nose : slots[i].name.StartsWith("Patient_Skin_Closed") ? closed : slots[i];
                        mesh.sharedMaterials = slots;
                    }
                    else if (materials.TryGetValue(mesh.name, out var mats) && mats.Length == mesh.sharedMaterials.Length) mesh.sharedMaterials = mats;
                }
                var bodyRig = new SerializedObject(patient.GetComponent<OperationPatientRig>());
                bodyRig.FindProperty("animator").objectReferenceValue = animator;
                bodyRig.FindProperty("face").objectReferenceValue = model.GetComponentsInChildren<SkinnedMeshRenderer>().First(x => x.name == "Face");
                bodyRig.ApplyModifiedPropertiesWithoutUndo();
                var names = new[] { "INC_KIDNEY_L", "INC_KIDNEY_R", "INC_LIVER", "INC_ABDOMEN", "GUIDE_BELLY_START", "GUIDE_BELLY_END" };
                var anchors = new SerializedObject(patient.GetComponent<OperationPatientAnchors>()); var points = anchors.FindProperty("incisions"); points.arraySize = names.Length;
                var all = model.GetComponentsInChildren<Transform>(true);
                for (int i = 0; i < names.Length; i++) points.GetArrayElementAtIndex(i).objectReferenceValue = all.Single(x => x.name == names[i]);
                anchors.ApplyModifiedPropertiesWithoutUndo();
                if (all.Count(x => x.name.StartsWith("mixamorig:")) != 65) throw new InvalidOperationException("Expected unchanged 65-bone skeleton");
                foreach (var socket in new[] { "SOCKET_KIDNEY_L", "SOCKET_KIDNEY_R", "SOCKET_LIVER", "SOCKET_HEART", "SOCKET_LUNG_L", "SOCKET_LUNG_R", "SOCKET_THORAX" })
                    if (!all.Any(x => x.name == socket)) throw new InvalidOperationException("Missing " + socket);
                PrefabUtility.SaveAsPrefabAsset(patient, path);
                return "patient -> " + Path.GetFileName(modelPath);
            }
            finally { PrefabUtility.UnloadPrefabContents(patient); }
        }
    }
}
