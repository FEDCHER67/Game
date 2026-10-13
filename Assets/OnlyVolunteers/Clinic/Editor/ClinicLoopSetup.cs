using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.Clinic
{
    // OnlyVolunteers/Clinic/Add Patient Loop To Open Map Scene: puts the Field Clinic loop's one object (FC_ClinicLoop with
    // ClinicLoop, base B01 by default) into the open map Play scene and marks the scene dirty; save it yourself. Needed
    // again after a map rebuild (the map builders do not know about the loop). Does nothing if the object is there.
    public static class ClinicLoopSetup
    {
        private const string ObjectName = "FC_ClinicLoop";
        private const string KidneyItemPath = "Assets/OnlyVolunteers/Inventory/Items/Item_Kidney.asset";

        [MenuItem("OnlyVolunteers/Clinic/Add Patient Loop To Open Map Scene")]
        private static void Add()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
            {
                Debug.LogWarning("[Clinic] stop Play mode first: scene changes made in Play mode are lost.");
                return;
            }
            if (Object.FindAnyObjectByType<GreyboxPawn>(FindObjectsInactive.Include) == null)
            {
                Debug.LogWarning("[Clinic] the open scene has no map pawn (GreyboxPawn): open Map_Look_v17_Play first.");
                return;
            }
            ClinicLoop existing = Object.FindAnyObjectByType<ClinicLoop>(FindObjectsInactive.Include);
            if (existing != null)
            {
                Selection.activeObject = existing.gameObject;
                Debug.Log($"[Clinic] {existing.name} is already in the scene.", existing);
                return;
            }
            var go = new GameObject(ObjectName);
            Undo.RegisterCreatedObjectUndo(go, "Add Patient Loop");
            var loop = go.AddComponent<ClinicLoop>();
            loop.KidneyItem = AssetDatabase.LoadAssetAtPath<ItemDefinition>(KidneyItemPath);
            if (loop.KidneyItem == null) Debug.LogWarning($"[Clinic] {KidneyItemPath} not found: the operation pays from a base value of 250.");
            EditorSceneManager.MarkSceneDirty(go.scene);
            Selection.activeObject = go;
            Debug.Log($"[Clinic] added {ObjectName} to {go.scene.path}; save the scene to keep it.", go);
        }
    }
}
