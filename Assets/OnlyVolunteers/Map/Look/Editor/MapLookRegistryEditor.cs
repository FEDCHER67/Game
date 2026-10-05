using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    // Registry inspector: lists every key the look builder asks for and maps imported art under ArtRoot to keys by
    // file name ("lamp_street.fbx" -> prop/lamp_street, "tree_birch.prefab" -> tree/birch, "wall_panel.mat" ->
    // mat/wall/panel, "TL_meadow.terrainlayer" -> layer/meadow). Assigned slots are never overwritten.
    [CustomEditor(typeof(MapLookRegistry))]
    public sealed class MapLookRegistryEditor : UnityEditor.Editor
    {
        public override void OnInspectorGUI()
        {
            var reg = (MapLookRegistry)target;
            EditorGUILayout.HelpBox("Empty slots build with generated placeholders. Fill slots by hand or use Auto-assign after importing art under ArtRoot.", MessageType.Info);
            using (new EditorGUILayout.HorizontalScope())
            {
                if (GUILayout.Button("Add missing keys"))
                {
                    Undo.RecordObject(reg, "Add missing keys");
                    AddMissingKeys(reg);
                    EditorUtility.SetDirty(reg);
                }
                if (GUILayout.Button("Auto-assign from ArtRoot"))
                {
                    Undo.RecordObject(reg, "Auto-assign map art");
                    int n = AutoAssign(reg);
                    EditorUtility.SetDirty(reg);
                    Debug.Log($"[MapLook] Auto-assign: {n} slots filled from {reg.ArtRoot}");
                }
            }
            EditorGUILayout.Space();
            DrawDefaultInspector();
        }

        public static void AddMissingKeys(MapLookRegistry reg)
        {
            var have = new HashSet<string>();
            foreach (PrefabSlot s in reg.Prefabs) if (s != null) have.Add(s.key);
            foreach (MaterialSlot s in reg.Materials) if (s != null) have.Add(s.key);
            foreach (LayerSlot s in reg.Layers) if (s != null) have.Add(s.key);
            foreach (string key in MapLookRegistry.KnownKeys())
            {
                if (have.Contains(key)) continue;
                if (key.StartsWith("mat/")) reg.Materials.Add(new MaterialSlot { key = key, fallback = LookPalette.Default(key) });
                else reg.Prefabs.Add(new PrefabSlot { key = key });
            }
            foreach (KeyValuePair<string, string> layer in TerrainBaker.LayerColours)
                if (!have.Contains("layer/" + layer.Key))
                    reg.Layers.Add(new LayerSlot { key = "layer/" + layer.Key, fallback = LookConvert.Color(layer.Value) });
        }

        public static int AutoAssign(MapLookRegistry reg)
        {
            if (!AssetDatabase.IsValidFolder(reg.ArtRoot)) return 0;
            AddMissingKeys(reg);
            int filled = 0;
            var root = new[] { reg.ArtRoot };
            foreach (string guid in AssetDatabase.FindAssets("t:GameObject", root))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                string name = Clean(Path.GetFileNameWithoutExtension(path), "sm_", "pf_", "p_", "prop_");
                string key = name.StartsWith("tree_") ? "tree/" + name.Substring(5) : "prop/" + name;
                PrefabSlot slot = reg.Prefabs.Find(s => s != null && s.key == key);
                if (slot == null) reg.Prefabs.Add(slot = new PrefabSlot { key = key });
                if (slot.prefab != null) continue;
                slot.prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (slot.prefab != null) filled++;
            }
            var known = new HashSet<string>(LookPalette.MaterialKeys);
            foreach (string guid in AssetDatabase.FindAssets("t:Material", root))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                string name = Clean(Path.GetFileNameWithoutExtension(path), "m_", "mat_", "mi_");
                string key = null;
                foreach (string k in known)
                    if (k.Substring(4).Replace('/', '_') == name)
                        key = k;
                if (key == null)
                {
                    int us = name.IndexOf('_');
                    key = "mat/" + (us > 0 ? name.Substring(0, us) + "/" + name.Substring(us + 1) : name);
                }
                MaterialSlot slot = reg.Materials.Find(s => s != null && s.key == key);
                if (slot == null) reg.Materials.Add(slot = new MaterialSlot { key = key, fallback = LookPalette.Default(key) });
                if (slot.material != null) continue;
                slot.material = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (slot.material != null) filled++;
            }
            foreach (string guid in AssetDatabase.FindAssets("t:TerrainLayer", root))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                string key = "layer/" + Clean(Path.GetFileNameWithoutExtension(path), "tl_", "layer_");
                LayerSlot slot = reg.Layers.Find(s => s != null && s.key == key);
                if (slot == null) reg.Layers.Add(slot = new LayerSlot { key = key });
                if (slot.layer != null) continue;
                slot.layer = AssetDatabase.LoadAssetAtPath<TerrainLayer>(path);
                if (slot.layer != null) filled++;
            }
            return filled;
        }

        private static string Clean(string name, params string[] prefixes)
        {
            name = name.ToLowerInvariant().Replace(' ', '_').Replace('-', '_');
            foreach (string p in prefixes)
                if (name.StartsWith(p))
                {
                    name = name.Substring(p.Length);
                    break;
                }
            return name;
        }
    }
}
