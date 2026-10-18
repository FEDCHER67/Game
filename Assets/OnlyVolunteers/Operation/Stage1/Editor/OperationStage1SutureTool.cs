using System;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.Editor
{
    /// <summary>Round 3 (Fedya: "every operation ends with suturing"): the table's fifth tool, the needle holder with a curved
    /// needle and thread (иглодержатель / нить), as a networked OperationTool of kind Suture. Built from the scalpel tool
    /// prefab (same NetworkObject/OperationTool setup, colliders and dock frame: the tip at the root, the handle along -X)
    /// with a procedural placeholder model until the art lands; registered in both spawnable lists (appended, so existing
    /// prefab ids stay) and in the tables' tool lists. Idempotent; never overwrites an existing tool prefab's model.</summary>
    public static class OperationStage1SutureTool
    {
        private const string Prefabs = "Assets/OnlyVolunteers/Operation/Stage1/Prefabs/";
        public const string ToolPath = Prefabs + "Stage1_Tool_Suture_v01.prefab";

        [MenuItem("OnlyVolunteers/Operation/Build suture tool (needle holder v01)")]
        public static void Menu() => Debug.Log("[OPS] " + Build());

        public static string Build()
        {
            if (EditorApplication.isPlaying || EditorApplication.isCompiling) throw new InvalidOperationException("Editor must be idle");
            var log = new System.Text.StringBuilder();
            if (AssetDatabase.LoadAssetAtPath<GameObject>(ToolPath) == null)
            {
                if (!AssetDatabase.CopyAsset(Prefabs + "Stage1_Tool_Scalpel_v02.prefab", ToolPath)) throw new InvalidOperationException("copy failed");
                var root = PrefabUtility.LoadPrefabContents(ToolPath);
                try
                {
                    root.name = "Stage1_Tool_Suture_v01";
                    var tool = root.GetComponent<OperationTool>();
                    var so = new SerializedObject(tool);
                    so.FindProperty("kind").intValue = (int)OperationToolKind.Suture;
                    var visual = (Transform)so.FindProperty("visual").objectReferenceValue;
                    so.ApplyModifiedPropertiesWithoutUndo();
                    foreach (Transform child in visual) child.gameObject.SetActive(false); // the scalpel model
                    Model(visual);
                    PrefabUtility.SaveAsPrefabAsset(root, ToolPath);
                    log.Append("tool prefab built; ");
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(ToolPath);
            var toolPrefab = prefab.GetComponent<OperationTool>();
            var network = prefab.GetComponent<FishNet.Object.NetworkObject>();
            foreach (var list in new[] { "Assets/DefaultPrefabObjects.asset", "Assets/OnlyVolunteers/Operation/Stage1/Data/OperationSpawnables_v02.asset" })
            {
                var asset = AssetDatabase.LoadMainAssetAtPath(list);
                if (asset == null) continue;
                var so = new SerializedObject(asset); var items = so.FindProperty("_prefabs");
                if (items == null) continue;
                bool has = false; for (int i = 0; i < items.arraySize; i++) if (items.GetArrayElementAtIndex(i).objectReferenceValue == network) has = true;
                if (has) continue;
                items.InsertArrayElementAtIndex(items.arraySize); items.GetArrayElementAtIndex(items.arraySize - 1).objectReferenceValue = network;
                so.ApplyModifiedPropertiesWithoutUndo(); EditorUtility.SetDirty(asset);
                log.Append("spawnable in ").Append(System.IO.Path.GetFileNameWithoutExtension(list)).Append("; ");
            }
            foreach (var table in new[] { Prefabs + "OperatingTableAstra_v02.prefab", Prefabs + "Stage1_Table_Placeholder_v02.prefab" })
            {
                var root = PrefabUtility.LoadPrefabContents(table);
                try
                {
                    var t = root.GetComponent<NetworkOperationTable>(); if (t == null) continue;
                    var so = new SerializedObject(t); var tools = so.FindProperty("toolPrefabs");
                    bool has = false; for (int i = 0; i < tools.arraySize; i++) if (tools.GetArrayElementAtIndex(i).objectReferenceValue == toolPrefab) has = true;
                    if (has) continue;
                    tools.InsertArrayElementAtIndex(tools.arraySize); tools.GetArrayElementAtIndex(tools.arraySize - 1).objectReferenceValue = toolPrefab;
                    so.ApplyModifiedPropertiesWithoutUndo();
                    PrefabUtility.SaveAsPrefabAsset(root, table);
                    log.Append("tool on ").Append(System.IO.Path.GetFileNameWithoutExtension(table)).Append("; ");
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            AssetDatabase.SaveAssets();
            return log.Length == 0 ? "suture tool already in place" : log.ToString();
        }

        /// <summary>Placeholder needle holder: steel jaws at the tip (root), shanks to two finger rings along -X, a curved
        /// needle in the jaws and a dark blue thread trailing from it (~15 cm, like the scalpel).</summary>
        private static void Model(Transform visual)
        {
            var steel = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "NeedleHolder steel" };
            steel.SetColor("_BaseColor", new Color(0.72f, 0.75f, 0.8f)); steel.SetFloat("_Metallic", 0.8f); steel.SetFloat("_Smoothness", 0.7f);
            var thread = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "Suture thread" };
            thread.SetColor("_BaseColor", new Color(0.12f, 0.15f, 0.34f)); thread.SetFloat("_Smoothness", 0.3f);
            string folder = "Assets/OnlyVolunteers/Operation/Stage1/Art/SutureTool_v01";
            if (!AssetDatabase.IsValidFolder(folder)) AssetDatabase.CreateFolder("Assets/OnlyVolunteers/Operation/Stage1/Art", "SutureTool_v01");
            AssetDatabase.CreateAsset(steel, folder + "/NeedleHolder_Steel_v01.mat");
            AssetDatabase.CreateAsset(thread, folder + "/Suture_Thread_v01.mat");
            var model = new GameObject("NEEDLE_HOLDER_v01").transform; model.SetParent(visual, false);
            GameObject Part(PrimitiveType type, string name, Vector3 position, Vector3 euler, Vector3 scale, Material material)
            {
                var go = GameObject.CreatePrimitive(type); go.name = name;
                UnityEngine.Object.DestroyImmediate(go.GetComponent<Collider>());
                go.transform.SetParent(model, false);
                go.transform.localPosition = position; go.transform.localEulerAngles = euler; go.transform.localScale = scale;
                go.GetComponent<Renderer>().sharedMaterial = material;
                return go;
            }
            // jaws (tip), two shanks crossing at the box joint, finger rings at the end
            Part(PrimitiveType.Cube, "Jaws", new Vector3(-0.012f, 0f, 0f), Vector3.zero, new Vector3(0.026f, 0.004f, 0.005f), steel);
            Part(PrimitiveType.Cylinder, "BoxJoint", new Vector3(-0.028f, 0f, 0f), new Vector3(90f, 0f, 0f), new Vector3(0.009f, 0.004f, 0.009f), steel);
            Part(PrimitiveType.Cube, "ShankA", new Vector3(-0.075f, 0f, 0.006f), new Vector3(0f, -7f, 0f), new Vector3(0.095f, 0.004f, 0.0045f), steel);
            Part(PrimitiveType.Cube, "ShankB", new Vector3(-0.075f, 0f, -0.006f), new Vector3(0f, 7f, 0f), new Vector3(0.095f, 0.004f, 0.0045f), steel);
            for (int side = -1; side <= 1; side += 2)
            {
                // a finger ring from short cylinders round a circle
                for (int k = 0; k < 10; k++)
                {
                    float a = k * Mathf.PI * 2f / 10f;
                    var c = new Vector3(-0.128f + Mathf.Cos(a) * 0.011f, 0f, side * 0.016f + Mathf.Sin(a) * 0.011f);
                    Part(PrimitiveType.Cube, "Ring" + (side < 0 ? "B" : "A") + k, c, new Vector3(0f, -a * Mathf.Rad2Deg, 0f), new Vector3(0.0035f, 0.0035f, 0.0075f), steel);
                }
            }
            // curved needle held in the jaws (half circle, 9 mm radius) and the thread trailing back
            for (int k = 0; k < 8; k++)
            {
                float a = Mathf.PI * (k + 0.5f) / 8f;
                var c = new Vector3(0.002f, -Mathf.Sin(a) * 0.009f, Mathf.Cos(a) * 0.009f);
                Part(PrimitiveType.Cube, "Needle" + k, c, new Vector3(-a * Mathf.Rad2Deg, 0f, 0f), new Vector3(0.0012f, 0.0012f, 0.0042f), steel);
            }
            Part(PrimitiveType.Cylinder, "Thread", new Vector3(-0.03f, -0.006f, -0.012f), new Vector3(0f, 0f, 90f), new Vector3(0.0016f, 0.03f, 0.0016f), thread);
        }
    }
}
