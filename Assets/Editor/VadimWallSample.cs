using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>The retaining wall on a white background in colour variants (for Vadim to pick).</summary>
    static class VadimWallSample
    {
        const string T = "Assets/OnlyVolunteers/Art/MapTextures_W86/T1/Textures/";
        const string Out = "C:/Users/chern_0eqkb03/VolunteersBuilds/";

        public static void Render()
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var baseMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/VadimLocal/Hill/Wall_retaining_concrete.mat");
            var variants = new (string tex, Color col)[]
            {
                ("T1_concrete_slabs_old_albedo.png", new Color(.80f, .80f, .78f)),   // А now
                ("T1_concrete_slabs_old_albedo.png", new Color(.95f, .94f, .91f)),   // Б light
                ("T1_concrete_slabs_old_albedo.png", new Color(.93f, .87f, .76f)),   // В warm sand
                ("T1_concrete_light_albedo.png", new Color(.86f, .86f, .84f)),       // Г smooth light, like the tunnel portal
                ("T1_concrete_slabs_old_albedo.png", new Color(.62f, .63f, .62f)),   // Д darker grey
                ("T1_concrete_bridge_albedo.png", new Color(.88f, .88f, .87f)),      // Е bridge concrete
            };
            RenderSettings.ambientMode = AmbientMode.Flat; RenderSettings.ambientLight = new Color(.62f, .62f, .64f);
            var sun = new GameObject("Sun").AddComponent<Light>(); sun.type = LightType.Directional; sun.intensity = 1.25f; sun.color = new Color(1f, .97f, .92f);
            sun.transform.rotation = Quaternion.Euler(40, 30, 0); sun.shadows = LightShadows.Soft;
            for (int i = 0; i < variants.Length; i++)
            {
                var m = baseMat ? new Material(baseMat) : new Material(Shader.Find("Universal Render Pipeline/Lit"));
                var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(T + variants[i].tex);
                foreach (var p in new[] { "_BaseMap", "_MainTex" }) if (m.HasProperty(p)) m.SetTexture(p, tex);
                foreach (var p in new[] { "_BaseColor", "_Color" }) if (m.HasProperty(p)) m.SetColor(p, variants[i].col);
                var go = new GameObject("Wall_" + i); go.transform.position = new Vector3(i * 60f, 0, 0);
                go.AddComponent<MeshFilter>().sharedMesh = WallPiece(10f, 4.25f, false);
                go.AddComponent<MeshRenderer>().sharedMaterial = m;
            }
            var ground = GameObject.CreatePrimitive(PrimitiveType.Plane); ground.transform.localScale = new Vector3(100, 1, 100); ground.transform.position = new Vector3(150, -.02f, 0);
            var gm = new Material(Shader.Find("Universal Render Pipeline/Lit")); gm.SetColor("_BaseColor", Color.white); gm.SetFloat("_Smoothness", 0f);
            ground.GetComponent<MeshRenderer>().sharedMaterial = gm;
            var cam = new GameObject("Cam").AddComponent<Camera>(); cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = Color.white; cam.fieldOfView = 32;
            float shadow0 = QualitySettings.shadowDistance; QualitySettings.shadowDistance = 80f; // restored at the end (Unity saves it into ProjectSettings)
            for (int i = 0; i < variants.Length; i++)
            {
                float cx = i * 60f + 5f;
                cam.transform.position = new Vector3(cx - 6.5f, 7.5f, -13.5f); cam.transform.LookAt(new Vector3(cx - .3f, 1.9f, 0));
                Shot(cam, 1100, 720, Out + $"wall_var_{i}.png");
            }
            cam.transform.position = new Vector3(5.4f, 2.2f, -4.2f); cam.transform.LookAt(new Vector3(8.5f, 2.6f, 0));
            Shot(cam, 1100, 720, Out + "wall_var_0_close.png");
            QualitySettings.shadowDistance = shadow0;
        }

        /// <summary>A straight piece of the route wall: face, cap, ends; optional panel joints (grooves) every 2.5 m.</summary>
        static Mesh WallPiece(float len, float h, bool joints)
        {
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            void Q(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud)
            { int i = v.Count; v.Add(a); v.Add(b); v.Add(c); v.Add(d); uv.Add(ua); uv.Add(ub); uv.Add(uc); uv.Add(ud); t.AddRange(new[] { i, i + 1, i + 2, i, i + 2, i + 3 }); }
            const float th = .5f, cap = .15f, tile = 4f;
            float step = joints ? 2.5f : len;
            for (float x = 0; x < len - .01f; x += step)
            {
                float x0 = x + (joints && x > 0 ? .04f : 0f), x1 = Mathf.Min(x + step, len) - (joints && x + step < len ? .04f : 0f);
                Q(new Vector3(x0, 0, 0), new Vector3(x0, h, 0), new Vector3(x1, h, 0), new Vector3(x1, 0, 0), new Vector2(x0 / tile, 0), new Vector2(x0 / tile, h / tile), new Vector2(x1 / tile, h / tile), new Vector2(x1 / tile, 0));
                if (joints && x1 < len - .01f) Q(new Vector3(x1, 0, .06f), new Vector3(x1, h, .06f), new Vector3(x1 + .08f, h, .06f), new Vector3(x1 + .08f, 0, .06f), Vector2.zero, Vector2.up * .1f, Vector2.one * .1f, Vector2.right * .1f);
            }
            Q(new Vector3(-.1f, h + cap, -.1f), new Vector3(-.1f, h + cap, th + .1f), new Vector3(len + .1f, h + cap, th + .1f), new Vector3(len + .1f, h + cap, -.1f), Vector2.zero, Vector2.up * .2f, new Vector2(len / tile, .2f), new Vector2(len / tile, 0));
            Q(new Vector3(-.1f, h, -.1f), new Vector3(-.1f, h + cap, -.1f), new Vector3(len + .1f, h + cap, -.1f), new Vector3(len + .1f, h, -.1f), Vector2.zero, Vector2.up * .05f, new Vector2(len / tile, .05f), new Vector2(len / tile, 0));
            Q(new Vector3(0, 0, 0), new Vector3(0, 0, th), new Vector3(0, h, th), new Vector3(0, h, 0), Vector2.zero, Vector2.right * .1f, Vector2.one * .1f, Vector2.up);
            Q(new Vector3(len, 0, 0), new Vector3(len, h, 0), new Vector3(len, h, th), new Vector3(len, 0, th), Vector2.zero, Vector2.up, Vector2.one * .1f, Vector2.right * .1f);
            var m = new Mesh(); m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(t, 0); m.RecalculateNormals(); m.RecalculateBounds();
            return m;
        }

        static void Shot(Camera cam, int w, int h, string file)
        {
            var rt = new RenderTexture(w, h, 24); cam.targetTexture = rt; cam.Render();
            RenderTexture.active = rt; var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0); tex.Apply(); File.WriteAllBytes(file, tex.EncodeToPNG());
            RenderTexture.active = null; cam.targetTexture = null;
        }
    }
}
