using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // One kit module ready to be merged into a building: triangles grouped by role slot (plaster, brick, concrete,
    // metal_painted, metal_dark, wood, glass, roof), vertex normals as authored (weighted), the palette colour of every
    // vertex read from its UV cell. Frame = the module's Unity import frame: X along the wall (to the right seen from
    // outside), Y up, outward -Z, origin on the wall plane at the bottom centre (G12 README).
    public sealed class V3Module
    {
        public string Role;
        public Vector3[] V, N;
        public Color[] C;
        public readonly List<(string slot, int[] tris)> Parts = new();
        public Bounds Bounds;
        public int Triangles;
    }

    public sealed class V3Kit
    {
        public const string KitAsset = V3KitPostprocessor.KitDir + "/FacadeKit_PostSoviet_v01.asset";
        public const string SetAsset = V3KitPostprocessor.KitDir + "/FacadeKitSet_StyleV3.asset";
        public static readonly string[] Slots = { "plaster", "brick", "concrete", "metal_painted", "metal_dark", "wood", "glass", "roof" };

        private readonly FacadeKitSet set;
        private readonly Dictionary<(FacadeKit, string), V3Module> modules = new();
        private readonly Dictionary<string, Texture2D> palettes = new();

        private V3Kit(FacadeKitSet set)
        {
            this.set = set;
        }

        // The kit set (made on first use: every imported module under its role id, one default kit for all districts;
        // a district kit, e.g. the American Downtown kit, is added to FacadeKitSet.Districts later).
        public static V3Kit Load()
        {
            var set = AssetDatabase.LoadAssetAtPath<FacadeKitSet>(SetAsset);
            if (set == null || set.Default == null) set = Create();
            return new V3Kit(set);
        }

        private static FacadeKitSet Create()
        {
            var kit = AssetDatabase.LoadAssetAtPath<FacadeKit>(KitAsset);
            if (kit == null)
            {
                kit = ScriptableObject.CreateInstance<FacadeKit>();
                kit.KitId = "post_soviet_v01";
                AssetDatabase.CreateAsset(kit, KitAsset);
            }
            kit.Modules.Clear();
            foreach (string guid in AssetDatabase.FindAssets("t:Model", new[] { V3KitPostprocessor.KitDir }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                string role = Path.GetFileNameWithoutExtension(path);
                if (role.EndsWith("_v01")) role = role.Substring(0, role.Length - 4);
                kit.Modules.Add(new FacadeModule { Role = role, Model = AssetDatabase.LoadAssetAtPath<GameObject>(path) });
            }
            kit.Modules.Sort((a, b) => string.CompareOrdinal(a.Role, b.Role));
            EditorUtility.SetDirty(kit);
            var set = AssetDatabase.LoadAssetAtPath<FacadeKitSet>(SetAsset);
            if (set == null)
            {
                set = ScriptableObject.CreateInstance<FacadeKitSet>();
                AssetDatabase.CreateAsset(set, SetAsset);
            }
            set.Default = kit;
            EditorUtility.SetDirty(set);
            AssetDatabase.SaveAssets();
            return set;
        }

        public V3Module Get(string district, string role)
        {
            FacadeKit kit = set.For(district);
            V3Module m = Get(kit, role);
            if (m == null && kit != set.Default) m = Get(set.Default, role);
            return m;
        }

        private V3Module Get(FacadeKit kit, string role)
        {
            if (kit == null) return null;
            if (modules.TryGetValue((kit, role), out V3Module m)) return m;
            GameObject model = kit.Model(role);
            m = model != null ? Extract(model, role, Palette(kit.PalettePath)) : null;
            modules[(kit, role)] = m;
            return m;
        }

        private Texture2D Palette(string path)
        {
            if (string.IsNullOrEmpty(path)) return null;
            if (palettes.TryGetValue(path, out Texture2D t)) return t;
            string full = Path.Combine(Application.dataPath, "..", path);
            t = null;
            if (File.Exists(full))
            {
                t = new Texture2D(2, 2, TextureFormat.RGBA32, false, false) { filterMode = FilterMode.Point };
                t.LoadImage(File.ReadAllBytes(full));
            }
            palettes[path] = t;
            return t;
        }

        private static V3Module Extract(GameObject model, string role, Texture2D palette)
        {
            MeshFilter mf = model.GetComponentInChildren<MeshFilter>();
            MeshRenderer mr = model.GetComponentInChildren<MeshRenderer>();
            if (mf == null || mf.sharedMesh == null) return null;
            Mesh mesh = mf.sharedMesh;
            // The FBX root keeps Blender's export transform (90 deg about X, x100) and is often the mesh object itself: the
            // asset's localToWorld is the frame the kit contract describes (metres, Y up, outward -Z).
            Matrix4x4 toRoot = mf.transform.localToWorldMatrix;
            Matrix4x4 nm = toRoot.inverse.transpose;
            Vector3[] v = mesh.vertices, n = mesh.normals;
            Vector2[] uv = mesh.uv;
            var mod = new V3Module { Role = role, V = new Vector3[v.Length], N = new Vector3[v.Length], C = new Color[v.Length] };
            var b = new Bounds();
            for (int i = 0; i < v.Length; i++)
            {
                mod.V[i] = toRoot.MultiplyPoint3x4(v[i]);
                mod.N[i] = n != null && n.Length == v.Length ? nm.MultiplyVector(n[i]).normalized : Vector3.up;
                mod.C[i] = Sample(palette, uv != null && uv.Length == v.Length ? uv[i] : Vector2.zero);
                if (i == 0) b = new Bounds(mod.V[i], Vector3.zero);
                else b.Encapsulate(mod.V[i]);
            }
            mod.Bounds = b;
            Material[] mats = mr != null ? mr.sharedMaterials : new Material[0];
            for (int s = 0; s < mesh.subMeshCount; s++)
            {
                string name = s < mats.Length && mats[s] != null ? mats[s].name.ToLowerInvariant() : "plaster";
                string slot = "plaster";
                foreach (string k in Slots)
                    if (name.Contains(k)) slot = k;
                if (name.Contains("metal_dark")) slot = "metal_dark";
                else if (name.Contains("metal_painted")) slot = "metal_painted";
                int[] tris = mesh.GetTriangles(s);
                mod.Parts.Add((slot, tris));
                mod.Triangles += tris.Length / 3;
            }
            return mod;
        }

        private static Color Sample(Texture2D palette, Vector2 uv)
        {
            if (palette == null) return Color.white;
            int x = Mathf.Clamp(Mathf.FloorToInt(Mathf.Repeat(uv.x, 1f) * palette.width), 0, palette.width - 1);
            int y = Mathf.Clamp(Mathf.FloorToInt(Mathf.Repeat(uv.y, 1f) * palette.height), 0, palette.height - 1);
            Color c = palette.GetPixel(x, y);
            c.a = 1f;
            return c;
        }

        // Role slot -> surface category (the building's own wall / roof category where the slot is the building's).
        public static string SlotCategory(string slot, string wallCat, string roofCat) => slot switch
        {
            "plaster" => "3b_plaster_stucco",
            "brick" => "3a_brick",
            "concrete" => "3c_concrete_panels",
            "metal_painted" => "6a_painted_metal_panels",
            "metal_dark" => "6b_lightly_weathered_metal",
            "wood" => "5a_wood_planks_fences",
            "glass" => "glass",
            "roof" => "4c_corrugated_metal",
            _ => wallCat,
        };
    }
}
