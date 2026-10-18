using System;
using System.Linq;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Operation.Stage1.EditorTools;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.Editor
{
    /// <summary>Integrates the approved v03 art (Fedya 2026-10-18; ORGANS_LAYOUT_v03.json → unity_integration) from imported
    /// copies under Operation/Stage1/Art (ArtSource stays untouched): Patient_v03 (closed back: Body slot
    /// Patient_Skin_Closed is never stencilled), Organs_v03 at their SOCKET_* frames 1:1 (the same meshes on the tray),
    /// heart/lungs/ribcage/chest vessels as visuals, OperationAbdomen_v03 with its guide/cord data, BLOOD-BAG v05 and
    /// SYRINGE v02 for the blood draw and transfer. Keeps the patient prefab GUID, its controller/avatar, NpcRig profile
    /// and the 65-bone rig, like the v02 integration.</summary>
    public static class OperationStage1AnatomyV03
    {
        private const string Stage = "Assets/OnlyVolunteers/Operation/Stage1/";
        private const string Art = Stage + "Art/";
        private const string OldPatient = "Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/";

        [MenuItem("OnlyVolunteers/Operation/Integrate approved anatomy v03")]
        public static void Menu() => Debug.Log("[OPS] " + Apply());

        public static string Apply()
        {
            if (EditorApplication.isPlaying || EditorApplication.isCompiling) throw new InvalidOperationException("Editor must be idle");
            var log = new System.Text.StringBuilder();
            // 1. Patient v03 import: the v02/v01 rig settings (same 65 bones, avatar copied from v01).
            string modelPath = Art + "Patient_v03/SAUSAGE_BUDDY_PATIENT_v03.fbx";
            var importer = (ModelImporter)AssetImporter.GetAtPath(modelPath);
            var oldImporter = (ModelImporter)AssetImporter.GetAtPath(OldPatient + "SAUSAGE_BUDDY_PATIENT_v01.fbx");
            importer.animationType = oldImporter.animationType;
            importer.avatarSetup = oldImporter.avatarSetup; importer.sourceAvatar = oldImporter.sourceAvatar;
            importer.importAnimation = false; importer.preserveHierarchy = true;
            importer.importNormals = ModelImporterNormals.Import; importer.SaveAndReimport();

            // 2. Patient_Skin_Closed: a copy of the patient skin under a name the opening stencil never takes.
            var skin = AssetDatabase.LoadAllAssetsAtPath(OldPatient + "SAUSAGE_BUDDY_PATIENT_v01.fbx").OfType<Material>().First(m => m.name == "Buddy_Skin");
            var nose = AssetDatabase.LoadAllAssetsAtPath(OldPatient + "SAUSAGE_BUDDY_PATIENT_v01.fbx").OfType<Material>().First(m => m.name == "Buddy_Skin_Nose");
            string closedPath = Art + "Patient_v03/Patient_Skin_Closed.mat";
            var closed = AssetDatabase.LoadAssetAtPath<Material>(closedPath);
            if (closed == null) { closed = new Material(skin) { name = "Patient_Skin_Closed" }; AssetDatabase.CreateAsset(closed, closedPath); }

            // 3. Patient prefab: v03 model, same animator/avatar/profile, materials by slot name.
            string path = Stage + "Prefabs/Stage1_Patient_v02.prefab";
            var patient = PrefabUtility.LoadPrefabContents(path);
            try
            {
                var prior = patient.GetComponentInChildren<Animator>();
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
                        log.Append("Body slots: ").Append(string.Join(", ", slots.Select(m => m.name))).Append("; ");
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
            }
            finally { PrefabUtility.UnloadPrefabContents(patient); }

            // 4. Tuning (in place, like v02): v03 opening, guide, cords, organ meshes/sizes, chest visuals, blood bag.
            var tuning = AssetDatabase.LoadAssetAtPath<OperationTuning>(Stage + "Data/OperationStage1_v02.asset");
            tuning.anatomicalLayout = true; tuning.anatomyV03 = true;
            tuning.abdomenModel = AssetDatabase.LoadAssetAtPath<GameObject>(Art + "Abdomen_v03/OperationAbdomen_v03.fbx");
            tuning.abdomenGradient = AssetDatabase.LoadAssetAtPath<Texture2D>(Art + "Abdomen_v03/OperationAbdomen_v03_Gradient.png");
            // guide_belly (INC_ABDOMEN-local; x negated into Unity), length 0.1981; opening half-width 0.12, mean half-length.
            tuning.bellyStart = new Vector3(0.0002f, 0.0879f, -0.0064f); tuning.bellyEnd = new Vector3(0.0003f, -0.1101f, -0.0087f);
            tuning.abdomenCutLength = 0.1981f; tuning.abdomenHalfSize = new Vector2(0.12f, (0.095f + 0.128f) * 0.5f);
            // Kidney cords, marker_local_unity: L artery, L vein, R artery, R vein.
            tuning.cordStarts = new[] { new Vector3(0.0227f, 0.006f, 0.0056f), new Vector3(0.0227f, -0.0093f, 0.0104f), new Vector3(-0.0228f, 0.006f, 0.0052f), new Vector3(-0.0228f, -0.0091f, 0.0104f) };
            tuning.cordEnds = new[] { new Vector3(0.0569f, 0.0194f, -0.0144f), new Vector3(0.0623f, -0.008f, -0.0124f), new Vector3(-0.0515f, 0.0172f, -0.0227f), new Vector3(-0.0567f, -0.0102f, -0.0201f) };
            // Organ half sizes from size_m_xyz_local (hit capsules in the marker frame).
            tuning.organHalfSize = new[] { new Vector2(0.0363f, 0.0733f), new Vector2(0.0362f, 0.0730f), new Vector2(0.1105f, 0.0673f) };
            GameObject Load(string name) => AssetDatabase.LoadAssetAtPath<GameObject>(Art + "Organs_v03/" + name + ".fbx");
            tuning.organModelsV03 = new[] { Load("ORGAN_KIDNEY_L_v03"), Load("ORGAN_KIDNEY_R_v03"), Load("ORGAN_LIVER_v03") };
            tuning.chestModelsV03 = new[] { Load("ORGAN_HEART_v03"), Load("ORGAN_LUNG_L_v03"), Load("ORGAN_LUNG_R_v03"), Load("RIBCAGE_v03"), Load("CHEST_VESSELS_v03") };
            tuning.bloodBagModel = AssetDatabase.LoadAssetAtPath<GameObject>(Art + "BloodBag_v05/BLOOD_BAG_ASTRA_001_v05.fbx");
            if (tuning.abdomenModel == null || tuning.organModelsV03.Any(x => x == null) || tuning.chestModelsV03.Any(x => x == null) || tuning.bloodBagModel == null)
                throw new InvalidOperationException("A v03 art copy is missing");
            EditorUtility.SetDirty(tuning); AssetDatabase.SaveAssetIfDirty(tuning);
            log.Append(OperationQueryMeshBaker.Bake()).Append("; ");

            // 5. Blood syringe: SYRINGE v02 (plunger + blood column) in place of the old model on the existing tool prefab.
            string toolPath = Stage + "Prefabs/Stage1_Tool_Blood_v02.prefab";
            var tool = PrefabUtility.LoadPrefabContents(toolPath);
            try
            {
                var op = tool.GetComponent<OperationTool>();
                var so = new SerializedObject(op);
                var visual = (Transform)so.FindProperty("visual").objectReferenceValue;
                foreach (Transform child in visual)
                    if (child.name == "SYRINGE-ASTRA-001" || child.name == "Liquid" || child.name == "Marking" || child.name == "MarkingDot") child.gameObject.SetActive(false);
                var old = visual.Find("SYRINGE_ASTRA_001_v02"); if (old != null) UnityEngine.Object.DestroyImmediate(old.gameObject);
                var syringe = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(Art + "Syringe_v02/SYRINGE_ASTRA_001_v02.fbx"), visual);
                syringe.name = "SYRINGE_ASTRA_001_v02";
                syringe.transform.localPosition = Vector3.zero; syringe.transform.localScale = Vector3.one / Mathf.Max(0.0001f, visual.localScale.x);
                so.FindProperty("plungerV02").objectReferenceValue = syringe.transform.Find("PLUNGER");
                so.FindProperty("bloodV02").objectReferenceValue = syringe.transform.Find("BLOOD");
                so.ApplyModifiedPropertiesWithoutUndo();
                if (syringe.transform.Find("PLUNGER") == null || syringe.transform.Find("BLOOD") == null) throw new InvalidOperationException("Syringe v02 parts missing");
                PrefabUtility.SaveAsPrefabAsset(tool, toolPath);
            }
            finally { PrefabUtility.UnloadPrefabContents(tool); }
            AssetDatabase.SaveAssets();
            return log.Append("patient v03 (65 bones, closed back), organs v03 1:1 at sockets, chest visuals, abdomen v03, blood bag v05, syringe v02 integrated").ToString();
        }
    }
}
