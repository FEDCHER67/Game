using System;
using System.IO;
using OnlyVolunteers.Characters.Npc;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.Editor
{
    /// <summary>Only the feature data and patient components are upgraded. Never rebuilds the approved table,
    /// scene, controller, clips, model, tool assets or spawnable list.</summary>
    public static class OperationStage1UpgradeV04
    {
        public const string Root = "C:/Dev/Game/Working/Reviews/Operations/stage1_v4";
        private const string Stage = "Assets/OnlyVolunteers/Operation/Stage1/";
        public const string Scene = "Assets/OnlyVolunteers/Scenes/Dev/Operation_Net_Stage1_v02.unity";

        [MenuItem("OnlyVolunteers/Operation/Apply shared abdomen and carry v04")]
        public static void Apply()
        {
            if (EditorApplication.isPlaying || EditorApplication.isCompiling) throw new InvalidOperationException("Editor must be idle");
            var tuning = AssetDatabase.LoadAssetAtPath<OperationTuning>(Stage + "Data/OperationStage1_v02.asset");
            if (tuning == null) throw new InvalidOperationException("Approved v02 tuning is missing");
            tuning.sharedAbdomen = true;
            // One opening between the chest and the closed torso strap, just above the highest belly skin.
            tuning.abdomenCutLength = 0.26f;
            tuning.abdomenHalfSize = new Vector2(0.14f, 0.15f);
            tuning.abdomenOffset = new Vector2(0.074f, 0.014f);
            tuning.liverLoopRadius = new Vector2(0.06f, 0.052f);
            tuning.organLift = 0.028f;
            // Slightly larger kidneys for the top view (their cords hang from the lower end, inside the opening).
            tuning.organHalfSize = new[] { new Vector2(0.02f, 0.035f), new Vector2(0.02f, 0.035f), new Vector2(0.021f, 0.032f) };
            // Straight top-down: the head top near the top edge, the opening's end just above the hotbar, tray on the right.
            tuning.cameraPosition = new Vector3(0.14f, 2.03f, 0.425f);
            tuning.cameraLookAt = new Vector3(0.14f, 0.89f, 0.425f);
            // Wheel out: up and toward the feet, so the leg straps are on screen.
            tuning.minZoom = -1f;
            tuning.wideCameraOffset = new Vector3(0f, 1.2f, -0.5f);
            EditorUtility.SetDirty(tuning);
            AssetDatabase.SaveAssetIfDirty(tuning);

            string path = Stage + "Prefabs/Stage1_Patient_v02.prefab";
            var patient = PrefabUtility.LoadPrefabContents(path);
            try
            {
                var animator = patient.GetComponentInChildren<Animator>();
                var npcRig = animator.GetComponent<NpcRig>();
                if (npcRig == null) npcRig = animator.gameObject.AddComponent<NpcRig>();
                npcRig.Animator = animator;
                npcRig.Ragdoll = AssetDatabase.LoadAssetAtPath<NpcRagdollProfile>("Assets/OnlyVolunteers/Characters/Npc/Data/Buddy_RagdollProfile.asset");
                if (npcRig.Ragdoll == null || npcRig.Ragdoll.Parts.Length != 11) throw new InvalidOperationException("Approved 11-body profile is missing");
                if (patient.GetComponent<OperationPatientRagdoll>() == null) patient.AddComponent<OperationPatientRagdoll>();
                PrefabUtility.SaveAsPrefabAsset(patient, path);
            }
            finally { PrefabUtility.UnloadPrefabContents(patient); }
            Debug.Log("[OPS v04] updated shared opening/camera tuning and patient adapter only");
        }

        public static string BuildPlayer()
        {
            Directory.CreateDirectory(Root + "/build");
            var result = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { Scene }, target = BuildTarget.StandaloneWindows64,
                locationPathName = Root + "/build/OperationsStage1v04.exe", options = BuildOptions.Development
            });
            string report = result.summary.result + " errors=" + result.summary.totalErrors + " warnings=" + result.summary.totalWarnings;
            File.WriteAllText(Root + "/player-build.txt", report);
            if (result.summary.result != BuildResult.Succeeded) throw new InvalidOperationException(report);
            return report;
        }
    }
}
