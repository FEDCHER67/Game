using System;
using System.Linq;
using OnlyVolunteers.Characters.Npc;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.Editor
{
    /// <summary>Integrates approved source copies; preserves the existing patient prefab GUID, clips and 65-bone rig.</summary>
    public static class OperationStage1AnatomyV02
    {
        private const string Stage = "Assets/OnlyVolunteers/Operation/Stage1/";
        private const string Patient = "Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/";
        [MenuItem("OnlyVolunteers/Operation/Integrate approved anatomy v02")]
        public static string Apply()
        {
            if (EditorApplication.isPlaying || EditorApplication.isCompiling) throw new InvalidOperationException("Editor must be idle");
            string modelPath = Patient + "SAUSAGE_BUDDY_PATIENT_v02.fbx";
            var importer = (ModelImporter)AssetImporter.GetAtPath(modelPath);
            var oldImporter = (ModelImporter)AssetImporter.GetAtPath(Patient + "SAUSAGE_BUDDY_PATIENT_v01.fbx");
            importer.animationType = oldImporter.animationType;
            importer.avatarSetup = oldImporter.avatarSetup; importer.sourceAvatar = oldImporter.sourceAvatar;
            importer.importAnimation = false; importer.preserveHierarchy = true;
            importer.importNormals = ModelImporterNormals.Import; importer.SaveAndReimport();
            var tuning = AssetDatabase.LoadAssetAtPath<OperationTuning>(Stage + "Data/OperationStage1_v02.asset");
            tuning.anatomicalLayout = true;
            tuning.abdomenModel = AssetDatabase.LoadAssetAtPath<GameObject>(Stage + "Art/OperationAbdomen_v02.fbx");
            tuning.abdomenGradient = AssetDatabase.LoadAssetAtPath<Texture2D>(Stage + "Art/OperationAbdomen_v02_Gradient.png");
            tuning.skinStencilShader = AssetDatabase.LoadAssetAtPath<Shader>(Stage + "Art/Shaders/OperationSkinStencil_v02.shader");
            tuning.maskStencilShader = AssetDatabase.LoadAssetAtPath<Shader>(Stage + "Art/Shaders/OperationMaskStencil_v02.shader");
            if (tuning.skinStencilShader == null || tuning.maskStencilShader == null) throw new InvalidOperationException("Stencil shaders missing");
            tuning.abdomenOffset = Vector2.zero; tuning.abdomenCutLength = 0.242f; tuning.abdomenHalfSize = new Vector2(0.122f, 0.138f);
            tuning.liverLoopRadius = new Vector2(0.085f, 0.056f); tuning.organLift = 0f;
            tuning.organHalfSize = new[] { new Vector2(0.030f,0.050f), new Vector2(0.030f,0.050f), new Vector2(0.110f,0.068f) };
            tuning.cordHitRadius = 0.010f; tuning.organItemScale = 0.7f;
            EditorUtility.SetDirty(tuning); AssetDatabase.SaveAssetIfDirty(tuning);
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
                foreach (var mesh in model.GetComponentsInChildren<SkinnedMeshRenderer>()) if (materials.TryGetValue(mesh.name, out var mats)) mesh.sharedMaterials = mats;
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
                PrefabUtility.SaveAsPrefabAsset(patient, path);
            }
            finally { PrefabUtility.UnloadPrefabContents(patient); }
            foreach (var guid in AssetDatabase.FindAssets("t:ItemDefinition", new[] { "Assets/OnlyVolunteers/Inventory/Items" }))
            {
                var definition = AssetDatabase.LoadAssetAtPath<OnlyVolunteers.Inventory.ItemDefinition>(AssetDatabase.GUIDToAssetPath(guid));
                if (definition == null || definition.WorldModel == null) continue;
                string name = definition.WorldModel.name.ToUpperInvariant();
                if (!name.Contains("KIDNEY") && !name.Contains("LIVER")) continue;
                var so = new SerializedObject(definition); so.FindProperty("worldModelSize").floatValue = name.Contains("KIDNEY") ? 0.15f : 0.22f;
                so.ApplyModifiedPropertiesWithoutUndo(); AssetDatabase.SaveAssetIfDirty(definition);
            }
            return "Approved patient/opening v02 integrated; 65 bones, same clips/avatar; organ scales, guide/loop/cord data and stencil shaders assigned";
        }
    }
}
