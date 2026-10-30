using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Small shared presentation helpers: runtime materials, primitives without colliders, hover tint.</summary>
    public static class OperationVisuals
    {
        private static readonly Dictionary<string, Material> Cache = new();
        private static Shader lit, unlit;
        private static readonly int BaseColor = Shader.PropertyToID("_BaseColor");
        private static readonly int Color = Shader.PropertyToID("_Color");

        /// <summary>Material assets referenced by the presentation so their shaders are included in player builds
        /// (Shader.Find only sees shaders some build material uses).</summary>
        public static Material LitTemplate, UnlitTemplate;

        public static Material Lit(string key, Color color, float smoothness = 0.35f)
        {
            if (Cache.TryGetValue("L" + key, out var m) && m != null) return m;
            if (LitTemplate != null) m = new Material(LitTemplate);
            else { lit ??= Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard"); m = new Material(lit); }
            m.name = "Ops_" + key; m.hideFlags = HideFlags.DontSave;
            m.SetColor(BaseColor, color); m.color = color; m.SetFloat("_Smoothness", smoothness * OnlyVolunteers.Art.OvGlossV01.Factor); // Fedya 30.10: ~67 % less gloss, once per cached material
            Cache["L" + key] = m; return m;
        }
        /// <summary>Unlit, optionally transparent (guides, glows, hover discs).</summary>
        public static Material Unlit(string key, Color color, bool transparent = false)
        {
            if (Cache.TryGetValue("U" + key, out var m) && m != null) return m;
            if (UnlitTemplate != null) m = new Material(UnlitTemplate);
            else
            {
                unlit ??= Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Universal Render Pipeline/Lit");
                m = new Material(unlit);
            }
            m.name = "OpsU_" + key; m.hideFlags = HideFlags.DontSave;
            m.SetColor(BaseColor, color); m.color = color;
            if (transparent)
            {
                m.SetFloat("_Surface", 1f); m.SetFloat("_Blend", 0f);
                m.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
                m.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                m.SetFloat("_ZWrite", 0f);
                m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                m.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent + 10;
            }
            Cache["U" + key] = m; return m;
        }

        public static GameObject Primitive(PrimitiveType type, string name, Transform parent, Material material)
        {
            var go = GameObject.CreatePrimitive(type);
            go.name = name;
            var c = go.GetComponent<Collider>(); c.enabled = false; Object.Destroy(c);
            go.GetComponent<Renderer>().sharedMaterial = material;
            go.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            if (parent != null) go.transform.SetParent(parent, false);
            return go;
        }

        /// <summary>Places a cylinder (height along local Y) between two local points of its parent.</summary>
        public static void Between(Transform t, Vector3 from, Vector3 to, float width)
        {
            Vector3 d = to - from;
            t.localPosition = (from + to) * 0.5f;
            t.localRotation = Quaternion.FromToRotation(Vector3.up, d.sqrMagnitude > 1e-8f ? d.normalized : Vector3.up);
            t.localScale = new Vector3(width, d.magnitude * 0.5f, width);
        }

        public static LineRenderer Line(string name, Transform parent, Material material, float width, int points)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var line = go.AddComponent<LineRenderer>();
            line.useWorldSpace = false; line.sharedMaterial = material; line.widthMultiplier = width;
            line.positionCount = points; line.numCapVertices = 4; line.numCornerVertices = 2;
            line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; line.receiveShadows = false;
            line.alignment = LineAlignment.TransformZ;
            return line;
        }

        // ---------- hover tint ----------
        private static readonly MaterialPropertyBlock Block = new();
        private static readonly Dictionary<Renderer, bool> Tinted = new();

        public static void Tint(Renderer[] renderers, Color tint, float amount)
        {
            if (renderers == null) return;
            foreach (var r in renderers)
            {
                if (r == null) continue;
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++)
                {
                    if (mats[i] == null) continue;
                    Color baseColor = mats[i].HasProperty(BaseColor) ? mats[i].GetColor(BaseColor) : mats[i].HasProperty(Color) ? mats[i].color : UnityEngine.Color.white;
                    r.GetPropertyBlock(Block, i);
                    Block.SetColor(BaseColor, UnityEngine.Color.Lerp(baseColor, tint, amount));
                    r.SetPropertyBlock(Block, i);
                }
                Tinted[r] = true;
            }
        }
        public static void Untint(Renderer[] renderers)
        {
            if (renderers == null) return;
            foreach (var r in renderers)
            {
                if (r == null || !Tinted.Remove(r)) continue;
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++) { r.GetPropertyBlock(Block, i); Block.Clear(); r.SetPropertyBlock(Block, i); }
            }
        }

        public static Color PlayerColor(int clientId)
        {
            Color[] palette = { new(1f, 0.62f, 0.15f), new(0.2f, 0.85f, 1f), new(0.55f, 1f, 0.3f), new(1f, 0.35f, 0.85f) };
            return palette[Mathf.Abs(clientId) % palette.Length];
        }

        /// <summary>Little cartoon droplets (no gore): bouncy blobs that shrink away.</summary>
        public static void Splash(Vector3 world, int count, Color color, float size = 0.025f)
        {
            var mat = Lit("drop" + ColorUtility.ToHtmlStringRGB(color), color, 0.6f);
            for (int i = 0; i < count; i++)
            {
                var drop = Primitive(PrimitiveType.Sphere, "Droplet", null, mat);
                drop.transform.position = world;
                drop.transform.localScale = Vector3.one * Random.Range(size * 0.7f, size * 1.3f);
                drop.AddComponent<OnlyVolunteers.Operation.OrganDroplet>().Launch(new Vector3(Random.Range(-0.9f, 0.9f), Random.Range(1.2f, 2.2f), Random.Range(-0.9f, 0.9f)));
            }
        }
    }
}
