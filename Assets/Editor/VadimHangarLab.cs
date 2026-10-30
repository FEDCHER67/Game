using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>HangarLab (Vadim 30.10, V2 base = one very big military hangar; reference GPT 42 "02_B_Обжитой"): a playable
    /// GREYBOX of the base for testing NPC catching and stuffing them into the van. A copy of the VanOnly scene (van v05,
    /// player, capture/network systems, the 1 km grey floor and the sky) with the hangar built around the van: 50 x 34 m
    /// inside, 9 m walls, a low gable roof (+2.5 m), steel trusses, three rooms along the back wall (VAN UPGRADES bay with a
    /// lift, PHARMACY and GEAR with door and window counter), a 14 x 7.5 m gate in the right gable wall, yellow floor
    /// markings, a lounge corner, crates, string lights and pendant lamps. One matte material per surface type, textured with
    /// GPT package 45 (approved 30.10; Textures/). Meshes are generated here (world-scale UVs, 1 UV = 1 m) and saved to
    /// Assets/VadimLocal/Hangar. Lighting: see HangarLighting (rendering layers keep the sun outside). Re-run = rebuilt.</summary>
    public static class VadimHangarLab
    {
        const string Src = VadimVanLab.VanOnlyDst;
        public const string Dst = "Assets/OnlyVolunteers/Scenes/Dev/HangarLab_v01.unity";
        const string Dir = "Assets/VadimLocal/Hangar";
        const string MatDir = Dir + "/Materials";
        const string MeshAsset = Dir + "/HangarLab_Meshes_v01.asset";
        const string LogFile = @"C:\Users\chern_0eqkb03\VolunteersBuilds\hangar_build.txt";
        const string ShotDir = @"C:\Users\chern_0eqkb03\VolunteersBuilds\hangar_v01\editor_shots";
        public const string RootName = "Hangar_Base_v01";

        // hangar-local metres: origin = centre of the floor, floor top y = 0, x along the long side, gate at +x
        const float HX = 25f, HZ = 17f, T = 0.4f, Eave = 9f, Rise = 2.5f, Overhang = 0.5f;
        const float GateHalf = 7f, GateH = 7.5f;
        const uint L0 = 1u, Hall = 1u << 1, Room = 1u << 2, Sun = 1u << 3;
        const uint MHall = L0 | Hall, MRoom = L0 | Room, MSun = L0 | Sun, MBoth = L0 | Hall | Room;

        static float RoofUnder(float z) => Eave + Rise * (1f - Mathf.Min(Mathf.Abs(z), 99f) / HZ);

        // ------------------------------------------------------------------ mesh accumulation
        sealed class Acc
        {
            public readonly List<Vector3> V = new();
            public readonly List<Vector3> N = new();
            public readonly List<Vector2> U = new();
            public readonly List<int> T = new();
        }

        static Dictionary<(string g, Material m, uint mask), Acc> _acc;
        static Transform _cols;
        static StringBuilder _log;
        static int _colCount;

        static Acc A(string group, Material m, uint mask)
        {
            var k = (group, m, mask);
            if (!_acc.TryGetValue(k, out var a)) _acc[k] = a = new Acc();
            return a;
        }

        static Vector2 Planar(Vector3 p, Vector3 n)
        {
            float ax = Mathf.Abs(n.x), ay = Mathf.Abs(n.y), az = Mathf.Abs(n.z);
            if (ay >= ax && ay >= az) return new Vector2(p.x, p.z);
            return ax >= az ? new Vector2(p.z, p.y) : new Vector2(p.x, p.y);
        }

        static void Quad(Acc a, Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3, Vector3 n, Vector2[] uv = null)
        {
            int b = a.V.Count;
            Vector3[] ps = { p0, p1, p2, p3 };
            for (int i = 0; i < 4; i++) { a.V.Add(ps[i]); a.N.Add(n); a.U.Add(uv != null ? uv[i] : Planar(ps[i], n)); }
            if (Vector3.Dot(Vector3.Cross(p1 - p0, p2 - p0), n) > 0f) a.T.AddRange(new[] { b, b + 1, b + 2, b, b + 2, b + 3 });
            else a.T.AddRange(new[] { b, b + 2, b + 1, b, b + 3, b + 2 });
        }

        static void Tri(Acc a, Vector3 p0, Vector3 p1, Vector3 p2, Vector3 n)
        {
            int b = a.V.Count;
            a.V.Add(p0); a.V.Add(p1); a.V.Add(p2);
            for (int i = 0; i < 3; i++) a.N.Add(n);
            a.U.Add(Planar(p0, n)); a.U.Add(Planar(p1, n)); a.U.Add(Planar(p2, n));
            if (Vector3.Dot(Vector3.Cross(p1 - p0, p2 - p0), n) > 0f) a.T.AddRange(new[] { b, b + 1, b + 2 });
            else a.T.AddRange(new[] { b, b + 2, b + 1 });
        }

        const int PX = 1, NX = 2, PY = 4, NY = 8, PZ = 16, NZ = 32, All = 63;

        /// <summary>Oriented box: centre, full size, rotation; faces = which sides to emit. UVs per face in the face's own frame
        /// (u to the right seen from outside, v up; top and bottom: u along the box x, v along z): metric (1 UV = 1 m, continuous
        /// across coplanar boxes, never stretched however the box is turned) or, with a Cell, one picture per face.</summary>
        static void Box(Acc a, Vector3 c, Vector3 s, Quaternion r, int faces = All, Cell? cell = null)
        {
            void F(int bit, Vector3 ln, Vector3 lu)
            {
                if ((faces & bit) == 0) return;
                Vector3 lr = Vector3.Cross(ln, lu);
                float hw = Mathf.Abs(Vector3.Dot(lr, s)) * .5f, hh = Mathf.Abs(Vector3.Dot(lu, s)) * .5f, hd = Mathf.Abs(Vector3.Dot(ln, s)) * .5f;
                Vector3 n = r * ln, rd = r * lr, ud = r * lu, fc = c + n * hd;
                Vector3[] p = { fc - rd * hw - ud * hh, fc + rd * hw - ud * hh, fc + rd * hw + ud * hh, fc - rd * hw + ud * hh };
                var uv = new Vector2[4];
                if (cell is Cell cl)
                {
                    float fa = hw / Mathf.Max(hh, 1e-4f), uw = cl.R.width * .98f, vh = cl.R.height * .98f;
                    if (fa < cl.Aspect) uw *= fa / cl.Aspect; else vh *= cl.Aspect / fa;
                    Vector2 m = cl.R.center;
                    uv[0] = m + new Vector2(-uw, -vh) * .5f; uv[1] = m + new Vector2(uw, -vh) * .5f;
                    uv[2] = m + new Vector2(uw, vh) * .5f; uv[3] = m + new Vector2(-uw, vh) * .5f;
                }
                else
                    for (int i = 0; i < 4; i++) uv[i] = new Vector2(Vector3.Dot(p[i], rd), Vector3.Dot(p[i], ud));
                Quad(a, p[0], p[1], p[2], p[3], n, uv);
            }
            F(PX, Vector3.right, Vector3.up); F(NX, Vector3.left, Vector3.up);
            F(PZ, Vector3.forward, Vector3.up); F(NZ, Vector3.back, Vector3.up);
            F(PY, Vector3.up, Vector3.forward); F(NY, Vector3.down, Vector3.forward);
        }

        static void BoxMM(Acc a, Vector3 min, Vector3 max, int faces = All, Cell? cell = null) =>
            Box(a, (min + max) * .5f, max - min, Quaternion.identity, faces, cell);

        static void Col(string name, Vector3 c, Vector3 s, Quaternion r)
        {
            var g = new GameObject("C_" + name);
            g.transform.SetParent(_cols, false);
            g.transform.localPosition = c;
            g.transform.localRotation = r;
            g.AddComponent<BoxCollider>().size = s;
            g.isStatic = true;
            _colCount++;
        }

        static void ColMM(string name, Vector3 min, Vector3 max) => Col(name, (min + max) * .5f, max - min, Quaternion.identity);

        /// <summary>A solid axis-aligned box with its collider.</summary>
        static void Solid(Acc a, string name, Vector3 min, Vector3 max, int faces = All, Cell? cell = null)
        {
            BoxMM(a, min, max, faces, cell);
            ColMM(name, min, max);
        }

        static void Beam(Acc a, Vector3 p, Vector3 q, float w, float h)
        {
            Vector3 d = q - p;
            Quaternion r = Quaternion.LookRotation(d, Mathf.Abs(d.normalized.y) > .99f ? Vector3.forward : Vector3.up);
            Box(a, (p + q) * .5f, new Vector3(w, h, d.magnitude), r);
        }

        /// <summary>Vertical frustum (r0 at the base, r1 at the top). inner: also the inside faces (lamp shades).</summary>
        static void Cyl(Acc a, Vector3 b, float r0, float r1, float h, int sides, bool top, bool bottom, bool inner = false)
        {
            for (int i = 0; i < sides; i++)
            {
                float a0 = i * Mathf.PI * 2f / sides, a1 = (i + 1) * Mathf.PI * 2f / sides, am = (a0 + a1) * .5f;
                Vector3 d0 = new(Mathf.Cos(a0), 0, Mathf.Sin(a0)), d1 = new(Mathf.Cos(a1), 0, Mathf.Sin(a1)), dm = new(Mathf.Cos(am), 0, Mathf.Sin(am));
                Vector3 p0 = b + d0 * r0, p1 = b + d1 * r0, p2 = b + d1 * r1 + Vector3.up * h, p3 = b + d0 * r1 + Vector3.up * h;
                Vector3 n = (dm * h + Vector3.up * (r0 - r1)).normalized;
                float sl = Mathf.Sqrt(h * h + (r0 - r1) * (r0 - r1));
                var uv = new[] { new Vector2(a0 * r0, b.y), new Vector2(a1 * r0, b.y), new Vector2(a1 * r1, b.y + sl), new Vector2(a0 * r1, b.y + sl) };
                Quad(a, p0, p1, p2, p3, n, uv);
                if (inner) Quad(a, p0, p3, p2, p1, -n, new[] { uv[0], uv[3], uv[2], uv[1] });
                if (top) Tri(a, b + Vector3.up * h, p3, p2, Vector3.up);
                if (bottom) Tri(a, b, p1, p0, Vector3.down);
            }
        }

        static void Bulb(Acc a, Vector3 c, float r)
        {
            Vector3[] d = { Vector3.right, Vector3.forward, Vector3.left, Vector3.back };
            for (int i = 0; i < 4; i++)
            {
                Vector3 p = c + d[i] * r, q = c + d[(i + 1) % 4] * r;
                Tri(a, c + Vector3.up * r, p, q, ((d[i] + d[(i + 1) % 4]).normalized + Vector3.up).normalized);
                Tri(a, c - Vector3.up * r, q, p, ((d[i] + d[(i + 1) % 4]).normalized - Vector3.up).normalized);
            }
        }

        /// <summary>Corrugated sheet in a wall frame: local x = u along the wall, y up, z into the wall (the visible side
        /// faces -z). Trapezoid ribs every 0.1875 m (as the v1 workshop), 3 cm deep, phase from the absolute u, so pieces join
        /// seamlessly; texture 03's ribs are aligned to them (colour only).</summary>
        static void Sheet(Acc a, Vector3 origin, Quaternion rot, float u0, float u1, float y0, Func<Vector3, float> yTop)
        {
            const float P = .1875f, D = .03f;
            float[] o = { 0f, .0625f, .09375f, .15625f, .1875f };
            float[] dd = { 0f, 0f, D, D, 0f };
            Vector3 W(float u, float y, float d) => origin + rot * new Vector3(u, y, -d);
            for (int k = Mathf.FloorToInt(u0 / P) - 1; k <= Mathf.CeilToInt(u1 / P); k++)
                for (int i = 0; i < 4; i++)
                {
                    float ua = k * P + o[i], ub = k * P + o[i + 1];
                    float ca = Mathf.Max(ua, u0), cb = Mathf.Min(ub, u1);
                    if (cb - ca < 1e-4f) continue;
                    float da = Mathf.Lerp(dd[i], dd[i + 1], (ca - ua) / (ub - ua)), db = Mathf.Lerp(dd[i], dd[i + 1], (cb - ua) / (ub - ua));
                    float ta = yTop(W(ca, 0, da)), tb = yTop(W(cb, 0, db));
                    if (ta <= y0 + 1e-3f && tb <= y0 + 1e-3f) continue;
                    Vector3 n = rot * new Vector3(da - db, 0, -(cb - ca)).normalized;
                    Quad(a, W(ca, y0, da), W(cb, y0, db), W(cb, tb, db), W(ca, ta, da), n,
                        new[] { new Vector2(ca, y0), new Vector2(cb, y0), new Vector2(cb, tb), new Vector2(ca, ta) });
                }
        }

        // ------------------------------------------------------------------ materials
        static Material Mat(string name, Color c, float smooth = .15f, float metal = 0f)
        {
            string path = $"{MatDir}/Hangar_{name}_v01.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(m, path); }
            m.SetColor("_BaseColor", c);
            m.SetFloat("_Smoothness", smooth);
            m.SetFloat("_Metallic", metal);
            m.SetFloat("_EnvironmentReflections", 1f);
            EditorUtility.SetDirty(m);
            return m;
        }

        static Material Emissive(string name, Color baseC, Color emit)
        {
            var m = Mat(name, baseC, .3f);
            m.EnableKeyword("_EMISSION");
            m.SetColor("_EmissionColor", emit);
            // URP keeps _EMISSION only while the GI flags say emissive (BaseShaderGUI.SetMaterialKeywords on import)
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            return m;
        }

        static Material Transparent(string name, Color c, float smooth)
        {
            var m = Mat(name, c, smooth);
            m.SetFloat("_Surface", 1f);
            m.SetFloat("_Blend", 0f);
            m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
            m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
            m.SetFloat("_SrcBlendAlpha", (float)BlendMode.One);
            m.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
            m.SetFloat("_ZWrite", 0f);
            m.SetFloat("_ReceiveShadows", 1f);
            m.SetOverrideTag("RenderType", "Transparent");
            m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            m.DisableKeyword("_ALPHATEST_ON");
            m.renderQueue = (int)RenderQueue.Transparent;
            m.SetShaderPassEnabled("DepthOnly", false);
            m.SetShaderPassEnabled("ShadowCaster", false);
            return m;
        }

        static Material mFloor, mMark, mWall, mSteel, mRoofIn, mRoofOut, mWood, mRoller, mGate, mCrate, mPallet, mRug, mSofa, mSign,
            mBulb, mGlass, mYellow, mRed, mCloth, mWhite, mTire, mLampPanel, mPeg, mShelf;

        static void Materials()
        {
            if (!AssetDatabase.IsValidFolder(Dir)) AssetDatabase.CreateFolder("Assets/VadimLocal", "Hangar");
            if (!AssetDatabase.IsValidFolder(MatDir)) AssetDatabase.CreateFolder(Dir, "Materials");
            // palette from the reference (02_B): warm grey concrete, taupe corrugated walls, graphite steel, olive crates.
            // Material slots follow GPT texture package 45 (NN = its texture number); the rest stay flat colours.
            // textures: GPT package 45 (approved 30.10), tileable copies in Textures/ (made from the originals by prep_textures.py:
            // cropped to whole plates / ribs / slats / boards, hazard repainted tileable, medical crosses recoloured green).
            // World-scale tiling (the meshes carry 1 UV = 1 m); a grey tint keeps each surface as bright as its old flat colour.
            mFloor = Mat("01_Floor_Concrete", new Color(.46f, .44f, .41f), .15f);
            Textured(mFloor, Tex("01_Concrete"), 6f, 6f, 1f / 6f, 1f / 6f, .75f); // 3 x 3 plates of 2 m, joints on the walls (x 25, z 17)
            mWall = Mat("03_Wall_Corrugated", new Color(.42f, .38f, .33f), .2f, .1f);
            Textured(mWall, Tex("03_Corrugated"), 1.3125f, 1.5f, -.171875f / 1.3125f, 0f, .68f); // its 7 ribs = 7 mesh ribs of 0.1875 m
            mSteel = Mat("04_Truss_Graphite", new Color(.17f, .17f, .17f), .25f, .3f);
            Textured(mSteel, Tex("04_Graphite"), 2f, 2f, 0f, 0f, .71f);
            mRoofIn = Mat("04_Roof_Inside", new Color(.26f, .24f, .22f), .12f);
            Textured(mRoofIn, Tex("04_Graphite"), 3f, 3f, 0f, 0f, 1f);
            mRoofOut = Mat("Roof_Outside", new Color(.36f, .35f, .34f), .2f, .1f);
            mRoller = Mat("05_RollerDoor_Gate", new Color(.42f, .42f, .40f), .25f, .2f);
            Textured(mRoller, Tex("05_Roller"), 1.036f, 1f, 0f, 0f, .95f); // 10 slats of 10 cm
            mGate = mRoller;
            mYellow = Mat("06_Hazard_Stripe", new Color(.86f, .62f, .12f), .25f);
            Textured(mYellow, Tex("06_Hazard"), 1f, 1f, 0f, 0f, 1f); // stripes 12.5 cm
            mWood = Mat("07_Room_WoodPanel", new Color(.46f, .36f, .26f), .15f);
            Textured(mWood, Tex("07_WoodCladding"), 1.05f, 1.378f, 0f, 0f, .84f); // 6 boards of 17.5 cm
            mPeg = Mat("08_Tool_Pegboard", new Color(.36f, .31f, .25f), .12f);
            // the pegboard is a plain board now: its tools are modelled (PegTools); texture 08's painted tools would fake shapes
            foreach (var p in new[] { "_BaseMap", "_MainTex" }) { mPeg.SetTexture(p, null); mPeg.SetTextureScale(p, Vector2.one); mPeg.SetTextureOffset(p, Vector2.zero); }
            mPeg.SetColor("_BaseColor", new Color(.42f, .36f, .28f));
            mShelf = Mat("09_Shelf_Locker", new Color(.30f, .34f, .31f), .25f, .2f);
            Textured(mShelf, Tex("09_OliveMetal"), 1.5f, 1.5f, 0f, 0f, .87f);
            mCloth = Mat("10_Uniform_Camo", new Color(.31f, .33f, .19f), .05f);
            Textured(mCloth, Tex("10_Camo"), 1f, 1f, 0f, 0f, .94f);
            mCrate = Mat("11_Crate_Military", new Color(.27f, .30f, .17f), .15f);
            // crates are modelled (rims, latches, handles): plain olive metal (09) tinted to the crate olive of texture 11
            Textured(mCrate, Tex("09_OliveMetal"), 1f, 1f, 0f, 0f, new Color(.78f, .80f, .67f));
            mPallet = Mat("12_Pallet_Wood", new Color(.58f, .45f, .29f), .1f);
            Textured(mPallet, Tex("12_LightWood"), 1f, 1f, 0f, 0f, .72f); // planks are modelled: each shows one board (Cell UVs)
            mWhite = Mat("13_Medicine_Boxes", new Color(.82f, .82f, .80f), .2f);
            Textured(mWhite, Tex("13_MedicalBoxes", true), 1f, 1f, 0f, 0f, 1f); // one label per box face (Cell UVs)
            mRug = Mat("Rug", new Color(.50f, .24f, .12f), .05f);
            mSofa = Mat("Sofa", new Color(.38f, .20f, .11f), .25f);
            mRed = Mat("Tool_Red", new Color(.58f, .12f, .08f), .3f, .2f);
            mTire = Mat("Rubber_Black", new Color(.06f, .06f, .06f), .2f);
            mBulb = Emissive("Bulb_Warm", new Color(1f, .85f, .6f), new Color(1f, .72f, .42f) * 4.0f);
            mLampPanel = Emissive("LampPanel_Warm", new Color(1f, .9f, .75f), new Color(1f, .82f, .6f) * 3.0f);
            mGlass = Transparent("Glass", new Color(.55f, .65f, .7f, .22f), .8f);
            mMark = Transparent("02_Marking_Decals", Color.white, .25f);
            mMark.SetTexture("_BaseMap", MarkingTexture());
            // signs: GPT boards 14a-c cropped 3:1 and stacked in one atlas; only the lettering glows (emission mask), warm and dim
            mSign = Emissive("14_Signs", new Color(.85f, .85f, .85f), new Color(1f, .66f, .36f) * 1.1f);
            mSign.SetFloat("_Smoothness", .15f);
            Textured(mSign, Tex("14_SignAtlas", true), 1f, 1f, 0f, 0f, .85f);
            mSign.SetTexture("_EmissionMap", Tex("14_SignEmission", true));
            AssetDatabase.SaveAssets();
        }

        const string TexDir = Dir + "/Textures";

        /// <summary>A package-45 texture with game import settings: mipmaps, trilinear, anisotropic 8, BC7 (no moire or crawl).</summary>
        static Texture2D Tex(string name, bool clamp = false)
        {
            string path = $"{TexDir}/Hangar_Tex_{name}_v01.png";
            if (!(AssetImporter.GetAtPath(path) is TextureImporter imp))
            {
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                imp = AssetImporter.GetAtPath(path) as TextureImporter;
                if (imp == null) throw new FileNotFoundException("hangar texture missing: " + path);
            }
            var wrap = clamp ? TextureWrapMode.Clamp : TextureWrapMode.Repeat;
            if (imp.textureType != TextureImporterType.Default || !imp.mipmapEnabled || !imp.sRGBTexture || imp.anisoLevel != 8 ||
                imp.filterMode != FilterMode.Trilinear || imp.wrapMode != wrap || imp.textureCompression != TextureImporterCompression.CompressedHQ ||
                imp.maxTextureSize != 1024 || imp.alphaSource != TextureImporterAlphaSource.None)
            {
                imp.textureType = TextureImporterType.Default;
                imp.mipmapEnabled = true;
                imp.sRGBTexture = true;
                imp.anisoLevel = 8;
                imp.filterMode = FilterMode.Trilinear;
                imp.wrapMode = wrap;
                imp.textureCompression = TextureImporterCompression.CompressedHQ;
                imp.maxTextureSize = 1024;
                imp.alphaSource = TextureImporterAlphaSource.None;
                imp.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        /// <summary>Base map tiled at world scale (one texture = worldW x worldH metres), offset in texture units, grey tint.</summary>
        static void Textured(Material m, Texture2D t, float worldW, float worldH, float offU, float offV, float tint) =>
            Textured(m, t, worldW, worldH, offU, offV, new Color(tint, tint, tint, 1f));

        static void Textured(Material m, Texture2D t, float worldW, float worldH, float offU, float offV, Color tint)
        {
            var sc = new Vector2(1f / worldW, 1f / worldH);
            var of = new Vector2(offU - Mathf.Floor(offU), offV - Mathf.Floor(offV));
            foreach (var p in new[] { "_BaseMap", "_MainTex" })
            {
                m.SetTexture(p, t);
                m.SetTextureScale(p, sc);
                m.SetTextureOffset(p, of);
            }
            var c = new Color(tint.r, tint.g, tint.b, 1f);
            m.SetColor("_BaseColor", c);
            m.SetColor("_Color", c);
            EditorUtility.SetDirty(m);
        }

        /// <summary>A picture cell of a texture (UV rect, its pixel aspect w / h): a Box face given a Cell shows the centre crop
        /// of the cell that fits the face's own aspect, so nothing is stretched.</summary>
        readonly struct Cell
        {
            public readonly Rect R;
            public readonly float Aspect;
            public Cell(Rect r, float aspect) { R = r; Aspect = aspect; }
        }

        static int _label;

        /// <summary>The next label of the medical boxes texture: 2 columns x 3 rows (image rows 0-343, 343-683, 683-1024).</summary>
        static Cell NextMedLabel()
        {
            int i = _label++ * 5 % 6, col = i % 2, row = i / 2;
            float[] y = { 0f, 343f, 683f, 1024f };
            return new Cell(new Rect(col * .5f, 1f - y[row + 1] / 1024f, .5f, (y[row + 1] - y[row]) / 1024f), 512f / (y[row + 1] - y[row]));
        }

        // ------------------------------------------------------------------ stroke font (block capitals, 4 x 6 units)
        static readonly Dictionary<char, float[][]> Glyphs = new()
        {
            ['A'] = new[] { new float[] { 0, 0, 0, 4.4f, 1.5f, 6, 2.5f, 6, 4, 4.4f, 4, 0 }, new float[] { 0, 2.8f, 4, 2.8f } },
            ['C'] = new[] { new float[] { 4, 4.9f, 3, 6, 1, 6, 0, 5, 0, 1, 1, 0, 3, 0, 4, 1.1f } },
            ['D'] = new[] { new float[] { 0, 0, 0, 6, 2.6f, 6, 4, 4.6f, 4, 1.4f, 2.6f, 0, 0, 0 } },
            ['E'] = new[] { new float[] { 4, 6, 0, 6, 0, 0, 4, 0 }, new float[] { 0, 3, 3, 3 } },
            ['G'] = new[] { new float[] { 4, 4.9f, 3, 6, 1, 6, 0, 5, 0, 1, 1, 0, 3, 0, 4, 1, 4, 2.8f, 2.2f, 2.8f } },
            ['H'] = new[] { new float[] { 0, 0, 0, 6 }, new float[] { 4, 0, 4, 6 }, new float[] { 0, 3, 4, 3 } },
            ['M'] = new[] { new float[] { 0, 0, 0, 6, 2, 2.8f, 4, 6, 4, 0 } },
            ['N'] = new[] { new float[] { 0, 0, 0, 6, 4, 0, 4, 6 } },
            ['P'] = new[] { new float[] { 0, 0, 0, 6, 3, 6, 4, 5, 4, 3.8f, 3, 2.8f, 0, 2.8f } },
            ['R'] = new[] { new float[] { 0, 0, 0, 6, 3, 6, 4, 5, 4, 3.8f, 3, 2.8f, 0, 2.8f }, new float[] { 2, 2.8f, 4, 0 } },
            ['S'] = new[] { new float[] { 4, 5, 3, 6, 1, 6, 0, 5, 0, 4, 1, 3, 3, 3, 4, 2, 4, 1, 3, 0, 1, 0, 0, 1 } },
            ['U'] = new[] { new float[] { 0, 6, 0, 1, 1, 0, 3, 0, 4, 1, 4, 6 } },
            ['V'] = new[] { new float[] { 0, 6, 2, 0, 4, 6 } },
            ['W'] = new[] { new float[] { 0, 6, 1, 0, 2, 4, 3, 0, 4, 6 } },
            ['Y'] = new[] { new float[] { 0, 6, 2, 3, 4, 6 }, new float[] { 2, 3, 2, 0 } },
        };
        const float GlyphAdvance = 5.6f, SpaceAdvance = 3.4f, Stroke = 0.95f;

        static float TextWidth(string s) => s.Sum(ch => ch == ' ' ? SpaceAdvance : GlyphAdvance) - (GlyphAdvance - 4f) + Stroke;

        /// <summary>Segments of 's' in glyph units, starting at x = Stroke/2 (baseline y = 0).</summary>
        static IEnumerable<(Vector2 a, Vector2 b)> TextSegments(string s)
        {
            float x = Stroke * .5f;
            foreach (char ch in s)
            {
                if (ch == ' ') { x += SpaceAdvance; continue; }
                foreach (var line in Glyphs[ch])
                    for (int i = 0; i + 3 < line.Length; i += 2)
                        yield return (new Vector2(x + line[i], line[i + 1]), new Vector2(x + line[i + 2], line[i + 3]));
                x += GlyphAdvance;
            }
        }

        // ------------------------------------------------------------------ raster canvas (straight alpha, analytic AA)
        sealed class Canvas
        {
            public readonly int W, H;
            public readonly Color[] Px;
            readonly Func<Vector2, Vector2> _toPx; // metres -> pixels
            readonly float _ppm;
            public Canvas(int w, int h, Func<Vector2, Vector2> toPx, float pixelsPerUnit) { W = w; H = h; Px = new Color[w * h]; _toPx = toPx; _ppm = pixelsPerUnit; }

            void Put(int x, int y, Color c, float cov)
            {
                if (cov <= 0f) return;
                cov = Mathf.Clamp01(cov) * c.a;
                ref Color d = ref Px[y * W + x];
                float a = cov + d.a * (1f - cov);
                if (a <= 1e-5f) return;
                Color rgb = (c * cov + d * d.a * (1f - cov)) / a;
                d = new Color(rgb.r, rgb.g, rgb.b, a);
            }

            static float SegDist(Vector2 p, Vector2 a, Vector2 b)
            {
                Vector2 ab = b - a;
                float t = ab.sqrMagnitude > 1e-8f ? Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude) : 0f;
                return (p - (a + ab * t)).magnitude;
            }

            /// <summary>Round-capped line, 'width' in units.</summary>
            public void Line(Vector2 a, Vector2 b, float width, Color c)
            {
                Vector2 pa = _toPx(a), pb = _toPx(b);
                float hw = width * .5f * _ppm;
                int x0 = Mathf.Max(0, Mathf.FloorToInt(Mathf.Min(pa.x, pb.x) - hw - 2)), x1 = Mathf.Min(W - 1, Mathf.CeilToInt(Mathf.Max(pa.x, pb.x) + hw + 2));
                int y0 = Mathf.Max(0, Mathf.FloorToInt(Mathf.Min(pa.y, pb.y) - hw - 2)), y1 = Mathf.Min(H - 1, Mathf.CeilToInt(Mathf.Max(pa.y, pb.y) + hw + 2));
                for (int y = y0; y <= y1; y++)
                    for (int x = x0; x <= x1; x++)
                        Put(x, y, c, hw - SegDist(new Vector2(x + .5f, y + .5f), pa, pb) + .5f);
            }

            /// <summary>Convex polygon (units), counter-clockwise or clockwise.</summary>
            public void Poly(Vector2[] pts, Color c)
            {
                var p = pts.Select(_toPx).ToArray();
                float area = 0; for (int i = 0; i < p.Length; i++) { var q = p[(i + 1) % p.Length]; area += p[i].x * q.y - q.x * p[i].y; }
                float s = area > 0 ? 1f : -1f;
                int x0 = Mathf.Max(0, Mathf.FloorToInt(p.Min(v => v.x)) - 2), x1 = Mathf.Min(W - 1, Mathf.CeilToInt(p.Max(v => v.x)) + 2);
                int y0 = Mathf.Max(0, Mathf.FloorToInt(p.Min(v => v.y)) - 2), y1 = Mathf.Min(H - 1, Mathf.CeilToInt(p.Max(v => v.y)) + 2);
                for (int y = y0; y <= y1; y++)
                    for (int x = x0; x <= x1; x++)
                    {
                        Vector2 pt = new(x + .5f, y + .5f);
                        float sd = float.MinValue;
                        for (int i = 0; i < p.Length; i++)
                        {
                            Vector2 e = p[(i + 1) % p.Length] - p[i];
                            Vector2 n = new Vector2(e.y, -e.x).normalized * s; // outward
                            sd = Mathf.Max(sd, Vector2.Dot(pt - p[i], n));
                        }
                        Put(x, y, c, .5f - sd);
                    }
            }

            public void Text(string s, Vector2 origin, float height, Color c)
            {
                float k = height / 6f;
                foreach (var (a, b) in TextSegments(s)) Line(origin + a * k, origin + b * k, Stroke * k, c);
            }

            public Texture2D Save(string path, bool alphaIsTransparency)
            {
                var tex = new Texture2D(W, H, TextureFormat.RGBA32, false);
                tex.SetPixels(Px);
                tex.Apply();
                File.WriteAllBytes(path, tex.EncodeToPNG());
                Object.DestroyImmediate(tex);
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                var imp = (TextureImporter)AssetImporter.GetAtPath(path);
                imp.textureType = TextureImporterType.Default;
                imp.mipmapEnabled = true;
                imp.alphaIsTransparency = alphaIsTransparency;
                imp.anisoLevel = 16;
                imp.filterMode = FilterMode.Trilinear;
                imp.wrapMode = TextureWrapMode.Clamp;
                imp.textureCompression = TextureImporterCompression.CompressedHQ;
                imp.maxTextureSize = 4096;
                imp.SaveAndReimport();
                return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            }
        }

        // floor markings over the whole hangar floor (x -25..25, z -17..17), 2.44 cm a pixel; mipmapped, so thin lines far
        // away fade instead of crawling (no shimmer)
        const int MarkW = 2048, MarkH = 1393;

        static Texture2D MarkingTexture()
        {
            var cv = new Canvas(MarkW, MarkH, p => new Vector2((p.x + HX) / (2 * HX) * MarkW, (p.y + HZ) / (2 * HZ) * MarkH), MarkW / (2 * HX));
            Color y = new(.86f, .62f, .12f, .95f), k = new(.07f, .07f, .07f, .95f);
            // lane loop: rounded rectangle, dashed, centre (0, -2), half 13 x 6.5, corner radius 3.5
            var path = new List<Vector2>();
            Vector2 c0 = new(0, -2); float hx = 13f, hz = 6.5f, rr = 3.5f;
            void Arc(Vector2 cc, float a0, float a1) { for (int i = 0; i <= 12; i++) { float a = Mathf.Lerp(a0, a1, i / 12f) * Mathf.Deg2Rad; path.Add(cc + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * rr); } }
            Arc(c0 + new Vector2(hx - rr, -hz + rr), -90, 0);
            Arc(c0 + new Vector2(hx - rr, hz - rr), 0, 90);
            Arc(c0 + new Vector2(-hx + rr, hz - rr), 90, 180);
            Arc(c0 + new Vector2(-hx + rr, -hz + rr), 180, 270);
            path.Add(path[0]);
            Dashed(cv, path, 1.1f, .7f, .22f, y);
            // direction arrows on the loop (counter-clockwise seen from above) and the exit lane to the gate
            Arrow(cv, new Vector2(-3, -8.5f), Vector2.right, y);
            Arrow(cv, new Vector2(4, 4.5f), Vector2.left, y);
            Arrow(cv, new Vector2(-13, -1), Vector2.down, y);
            Dashed(cv, new List<Vector2> { new(13.3f, 0), new(23.2f, 0) }, 1.1f, .7f, .22f, y);
            Arrow(cv, new Vector2(16.5f, -2.2f), Vector2.right, y);
            Arrow(cv, new Vector2(16.5f, 2.2f), Vector2.left, y);
            // van parking box inside the loop
            Rect(cv, new Vector2(-3.8f, -3.8f), new Vector2(3.8f, -.2f), .16f, y);
            // SPAWN box and lettering
            Rect(cv, new Vector2(-17.6f, -14.3f), new Vector2(-12.4f, -10.7f), .22f, y);
            float tw = TextWidth("SPAWN") * (.9f / 6f);
            cv.Text("SPAWN", new Vector2(-15f - tw * .5f, -12.95f), .9f, y);
            // bay apron in front of the roller door, walkway line along the rooms
            Rect(cv, new Vector2(-21.3f, 2.6f), new Vector2(-11.7f, 6.7f), .16f, y);
            cv.Line(new Vector2(-7.4f, 9.3f), new Vector2(24.4f, 9.3f), .16f, y);
            // gate threshold: yellow / black diagonal stripes
            for (float s = -10f; s < 10f; s += .9f)
                cv.Poly(new[] { new Vector2(23.6f, s), new Vector2(23.6f, s + .45f), new Vector2(24.95f, s + .45f + 1.35f), new Vector2(24.95f, s + 1.35f) }
                    .Select(p => new Vector2(p.x, Mathf.Clamp(p.y, -GateHalf, GateHalf))).ToArray(), y);
            for (float s = -9.55f; s < 10f; s += .9f)
                cv.Poly(new[] { new Vector2(23.6f, s), new Vector2(23.6f, s + .45f), new Vector2(24.95f, s + .45f + 1.35f), new Vector2(24.95f, s + 1.35f) }
                    .Select(p => new Vector2(p.x, Mathf.Clamp(p.y, -GateHalf, GateHalf))).ToArray(), k);
            return cv.Save(Dir + "/Hangar_Markings_v01.png", true);
        }

        /// <summary>Dashes along a polyline by the distance walked from its start (on, off in metres).</summary>
        static void Dashed(Canvas cv, List<Vector2> path, float on, float off, float width, Color c)
        {
            float period = on + off, s0 = 0f;
            for (int i = 0; i + 1 < path.Count; i++)
            {
                Vector2 a = path[i], b = path[i + 1];
                float len = (b - a).magnitude, s1 = s0 + len;
                if (len < 1e-5f) continue;
                for (int k = Mathf.FloorToInt(s0 / period); k * period < s1; k++)
                {
                    float d0 = Mathf.Max(k * period, s0), d1 = Mathf.Min(k * period + on, s1);
                    if (d1 - d0 > 1e-4f) cv.Line(a + (b - a) * ((d0 - s0) / len), a + (b - a) * ((d1 - s0) / len), width, c);
                }
                s0 = s1;
            }
        }

        static void Arrow(Canvas cv, Vector2 at, Vector2 dir, Color c)
        {
            Vector2 side = new(-dir.y, dir.x);
            cv.Line(at - dir * 1.3f, at + dir * .2f, .32f, c);
            cv.Poly(new[] { at + dir * 1.1f, at + side * .6f, at - side * .6f }, c);
        }

        static void Rect(Canvas cv, Vector2 a, Vector2 b, float w, Color c)
        {
            cv.Line(a, new Vector2(b.x, a.y), w, c); cv.Line(new Vector2(b.x, a.y), b, w, c);
            cv.Line(b, new Vector2(a.x, b.y), w, c); cv.Line(new Vector2(a.x, b.y), a, w, c);
        }

        // sign atlas (Hangar_Tex_14_SignAtlas): rows of 1024 x 341 px from the top: VAN UPGRADES, PHARMACY, GEAR (3:1 boards)
        const float SignRowPx = 341f, SignAspect = 1024f / SignRowPx;

        /// <summary>A sign board in front of a wall face (facing -z, the hall), centred at x, the atlas row 'row'.</summary>
        static void Sign(float xc, float yc, float zFace, int row, float height)
        {
            float w = height * SignAspect;
            float u0 = .5f / 1024f, u1 = 1f - .5f / 1024f;
            float v1 = 1f - (row * SignRowPx + .5f) / 1024f, v0 = 1f - ((row + 1) * SignRowPx - .5f) / 1024f;
            var a = A("Signs", mSign, MBoth);
            float zf = zFace - 0.13f, zb = zFace - 0.01f, x0 = xc - w * .5f, x1 = xc + w * .5f, y0 = yc - height * .5f, y1 = yc + height * .5f;
            Quad(a, new Vector3(x0, y0, zf), new Vector3(x1, y0, zf), new Vector3(x1, y1, zf), new Vector3(x0, y1, zf), Vector3.back,
                new[] { new Vector2(u0, v0), new Vector2(u1, v0), new Vector2(u1, v1), new Vector2(u0, v1) });
            // edges: a dark texel of the atlas (the PHARMACY board left of its lettering)
            var dark = new[] { new Vector2(.02f, .645f), new Vector2(.025f, .645f), new Vector2(.025f, .65f), new Vector2(.02f, .65f) };
            Quad(a, new Vector3(x0, y1, zf), new Vector3(x1, y1, zf), new Vector3(x1, y1, zb), new Vector3(x0, y1, zb), Vector3.up, dark);
            Quad(a, new Vector3(x0, y0, zf), new Vector3(x0, y0, zb), new Vector3(x1, y0, zb), new Vector3(x1, y0, zf), Vector3.down, dark);
            Quad(a, new Vector3(x0, y0, zf), new Vector3(x0, y1, zf), new Vector3(x0, y1, zb), new Vector3(x0, y0, zb), Vector3.left, dark);
            Quad(a, new Vector3(x1, y0, zf), new Vector3(x1, y0, zb), new Vector3(x1, y1, zb), new Vector3(x1, y1, zf), Vector3.right, dark);
            ColMM("sign_" + row, new Vector3(x0, y0, zf), new Vector3(x1, y1, zb));
            // a small warm lamp bar above the board
            BoxMM(A("Lamps", mLampPanel, MBoth), new Vector3(x0 + .2f, y1 + .04f, zf), new Vector3(x1 - .2f, y1 + .1f, zb));
        }

        // ------------------------------------------------------------------ build
        public static void Run()
        {
            _log = new StringBuilder();
            _acc = new Dictionary<(string, Material, uint), Acc>();
            _colCount = 0;
            _label = 0;
            if (File.Exists(Dst)) AssetDatabase.DeleteAsset(Dst);
            if (!AssetDatabase.CopyAsset(Src, Dst)) throw new IOException("copy failed: " + Src);
            var scene = EditorSceneManager.OpenScene(Dst);
            var roots = scene.GetRootGameObjects();
            var van = roots.First(r => r.name == "Van");
            var floor = roots.First(r => r.name.StartsWith("VanLab_Floor"));
            foreach (var r in roots.Where(r => r.name.StartsWith("VanOnly test mode"))) Object.DestroyImmediate(r);
            float floorY = floor.transform.position.y;
            _log.AppendLine($"source {Src}; grey floor y {floorY:F3}; van at {van.transform.position}");

            Materials();
            var root = new GameObject(RootName).transform;
            SceneManager.MoveGameObjectToScene(root.gameObject, scene);
            root.position = new Vector3(van.transform.position.x, floorY + 0.04f, van.transform.position.z);
            _cols = new GameObject("Colliders").transform;
            _cols.SetParent(root, false);

            Shell();
            Trusses();
            Rooms();
            Props();
            var lights = Lights(root);
            Markings();
            SaveMeshes(root);
            _log.AppendLine($"hangar root {root.position}; colliders {_colCount}; lights {lights}");

            Actors(scene, root, van, floor);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            _log.AppendLine("saved " + Dst);
            Directory.CreateDirectory(Path.GetDirectoryName(LogFile));
            File.WriteAllText(LogFile, _log.ToString());
        }

        static void Shell()
        {
            // floor slab: the top split into cells along every room boundary (no T-junctions), hall cells lit by the hall
            // lamps, room cells by the room lamps; 4 cm above the grey outside floor, a 1.2 m ramp at the gate
            float[] xs = { -HX, -8f, -5f, 3f, 6f, 17f, HX };
            float[] zs = { -HZ, 7f, 11f, HZ };
            for (int i = 0; i + 1 < xs.Length; i++)
                for (int j = 0; j + 1 < zs.Length; j++)
                {
                    float cx = (xs[i] + xs[i + 1]) * .5f, cz = (zs[j] + zs[j + 1]) * .5f;
                    bool room = (cx < -8f && cz > 7f) || (cx > -5f && cx < 3f && cz > 11f) || (cx > 6f && cx < 17f && cz > 11f);
                    BoxMM(A("Floor", mFloor, room ? MRoom : MHall), new Vector3(xs[i], -.3f, zs[j]), new Vector3(xs[i + 1], 0f, zs[j + 1]), PY);
                }
            BoxMM(A("Floor", mFloor, MBoth | Sun), new Vector3(HX, -.3f, -GateHalf), new Vector3(HX + T, 0f, GateHalf), PY);
            var slabSide = A("Floor", mFloor, MSun);
            BoxMM(slabSide, new Vector3(-HX - T, -.3f, -HZ - T), new Vector3(HX + T, 0f, HZ + T), PX | NX | PZ | NZ);
            ColMM("floor_slab", new Vector3(-HX - T, -.3f, -HZ - T), new Vector3(HX + T, 0f, HZ + T));
            // gate ramp: from the slab top (0) down to 5 mm above the grey floor (-0.04) over 1.2 m
            {
                var a = A("Floor", mFloor, MSun);
                Vector3 p0 = new(HX + T, 0f, -GateHalf), p1 = new(HX + T, 0f, GateHalf), p2 = new(HX + T + 1.2f, -.035f, GateHalf), p3 = new(HX + T + 1.2f, -.035f, -GateHalf);
                Vector3 n = Vector3.Cross(p1 - p0, p3 - p0).normalized; if (n.y < 0) n = -n;
                Quad(a, p0, p1, p2, p3, n);
                Quad(a, p3, p2, new Vector3(p2.x, -.04f, p2.z), new Vector3(p3.x, -.04f, p3.z), Vector3.right);
                Quad(a, p0, p3, new Vector3(p3.x, -.04f, p3.z), new Vector3(p0.x, -.04f, p0.z), Vector3.back);
                Quad(a, p1, new Vector3(p1.x, -.04f, p1.z), new Vector3(p2.x, -.04f, p2.z), p2, Vector3.forward);
                float ang = Mathf.Atan2(.035f, 1.2f) * Mathf.Rad2Deg;
                Quaternion r = Quaternion.Euler(0, 0, -ang);
                Vector3 mid = (p0 + p2) * .5f - (r * Vector3.up) * .1f;
                Col("gate_ramp", mid, new Vector3(1.2f, .2f, 2 * GateHalf), r);
            }

            // walls: corrugated inner and outer sheets (inner lit by the hall / room lamps, outer by the sun)
            var inn = A("Walls_Inner", mWall, MHall);
            var innRoom = A("Walls_Inner", mWall, MRoom);
            var front = A("Wall_Front", mWall, MHall);
            var frontOut = A("Wall_Front", mWall, MSun);
            var outer = A("Walls_Outer", mWall, MSun);
            Func<Vector3, float> eave = _ => Eave, gable = p => RoofUnder(p.z), eaveOut = _ => RoofUnder(HZ + T) - .03f, gableOut = p => RoofUnder(p.z) - .03f;
            Func<Vector3, float> to(float h) => _ => h;
            // back wall (z = +17), u = x; rooms below their roof height (bay -25..-8 to 6 m, pharmacy -5..3 and gear 6..17 to 4.2 m)
            Quaternion back = Quaternion.identity, fr = Quaternion.Euler(0, 180, 0), left = Quaternion.Euler(0, -90, 0), right = Quaternion.Euler(0, 90, 0);
            Vector3 ob = new(0, 0, HZ);
            Sheet(innRoom, ob, back, -HX, -8f, 0f, to(6f)); Sheet(inn, ob, back, -HX, -8f, 6f, eave);
            Sheet(inn, ob, back, -8f, -5f, 0f, eave);
            Sheet(innRoom, ob, back, -5f, 3f, 0f, to(4.2f)); Sheet(inn, ob, back, -5f, 3f, 4.2f, eave);
            Sheet(inn, ob, back, 3f, 6f, 0f, eave);
            Sheet(innRoom, ob, back, 6f, 17f, 0f, to(4.2f)); Sheet(inn, ob, back, 6f, 17f, 4.2f, eave);
            Sheet(inn, ob, back, 17f, HX, 0f, eave);
            Sheet(outer, new Vector3(0, 0, HZ + T), fr, -HX - T, HX + T, 0f, eaveOut);
            // front wall (z = -17), u = -x
            Sheet(front, new Vector3(0, 0, -HZ), fr, -HX, HX, 0f, eave);
            Sheet(frontOut, new Vector3(0, 0, -HZ - T), back, -HX - T, HX + T, 0f, eaveOut);
            // left gable (x = -25), u = z; the bay's side below 6 m for z 7..17
            Vector3 ol = new(-HX, 0, 0);
            Sheet(inn, ol, left, -HZ, 7f, 0f, gable);
            Sheet(innRoom, ol, left, 7f, HZ, 0f, to(6f)); Sheet(inn, ol, left, 7f, HZ, 6f, gable);
            Sheet(outer, new Vector3(-HX - T, 0, 0), right, -HZ - T, HZ + T, 0f, gableOut);
            // right gable (x = +25) with the gate z -7..7, 7.5 m high; inner u = -z, outer u = z
            Vector3 orr = new(HX, 0, 0), oro = new(HX + T, 0, 0);
            Sheet(inn, orr, right, -HZ, -GateHalf, 0f, gable); Sheet(inn, orr, right, GateHalf, HZ, 0f, gable); Sheet(inn, orr, right, -GateHalf, GateHalf, GateH, gable);
            Sheet(outer, oro, left, -HZ - T, -GateHalf, 0f, gableOut); Sheet(outer, oro, left, GateHalf, HZ + T, 0f, gableOut);
            Sheet(outer, oro, left, -GateHalf, GateHalf, GateH, gableOut);
            // wall colliders (to the eaves; nobody reaches higher)
            ColMM("wall_back", new Vector3(-HX - T, 0, HZ), new Vector3(HX + T, Eave, HZ + T));
            ColMM("wall_front", new Vector3(-HX - T, 0, -HZ - T), new Vector3(HX + T, Eave, -HZ));
            ColMM("wall_left", new Vector3(-HX - T, 0, -HZ), new Vector3(-HX, Eave, HZ));
            ColMM("wall_right_a", new Vector3(HX, 0, -HZ), new Vector3(HX + T, Eave, -GateHalf));
            ColMM("wall_right_b", new Vector3(HX, 0, GateHalf), new Vector3(HX + T, Eave, HZ));
            ColMM("wall_right_over_gate", new Vector3(HX, GateH, -GateHalf), new Vector3(HX + T, Eave, GateHalf));

            // columns along the walls under every truss, corner columns, outer corner trims
            var st = A("Steel", mSteel, MHall);
            var stF = A("Wall_Front", mSteel, MHall);
            for (float x = -20f; x <= 20.01f; x += 5f)
            {
                bool inBay = x < -8f, inRoom = (x >= -5.2f && x <= 3.2f) || (x >= 5.8f && x <= 17.2f); // a column on a room wall stays above the room
                if (!inBay && !inRoom) Column(st, A("Steel", mYellow, MHall), "col_b" + x, new Vector3(x - .18f, 0, HZ - .36f), new Vector3(x + .18f, Eave, HZ - .06f));
                else BoxMM(st, new Vector3(x - .18f, inBay ? 6.2f : 4.4f, HZ - .36f), new Vector3(x + .18f, Eave, HZ - .06f));
                Column(stF, A("Wall_Front", mYellow, MHall), "col_f" + x, new Vector3(x - .18f, 0, -HZ + .06f), new Vector3(x + .18f, Eave, -HZ + .36f));
            }
            foreach (float sx in new[] { -1f, 1f })
                foreach (float sz in new[] { -1f, 1f })
                {
                    var acc = sz < 0 ? stF : st;
                    if (!(sx < 0 && sz > 0)) Solid(acc, "corner", new Vector3(sx * HX - .25f - sx * .2f, 0, sz * HZ - .25f - sz * .2f), new Vector3(sx * HX + .25f - sx * .2f, Eave, sz * HZ + .25f - sz * .2f));
                    BoxMM(A("Walls_Outer", mSteel, MSun), new Vector3(sx * (HX + T) - .12f, 0, sz * (HZ + T) - .12f), new Vector3(sx * (HX + T) + .12f, RoofUnder(HZ + T) - .02f, sz * (HZ + T) + .12f));
                }
            // girts along the long walls at 6 m
            BoxMM(stF, new Vector3(-HX, 5.9f, -HZ + .06f), new Vector3(HX, 6.1f, -HZ + .22f));
            BoxMM(st, new Vector3(-8f, 6.2f, HZ - .22f), new Vector3(HX, 6.4f, HZ - .06f));
            // gate: jambs (yellow foot), header beam, the two sliding leaves parked open outside, the rail
            foreach (float s in new[] { -1f, 1f })
            {
                float z0 = s * GateHalf, z1 = s * (GateHalf + .45f);
                Vector3 mn = new(HX - .15f, 0, Mathf.Min(z0, z1)), mx = new(HX + T + .1f, GateH, Mathf.Max(z0, z1));
                Solid(A("Steel", mSteel, MBoth | Sun), "gate_jamb", new Vector3(mn.x, 1.6f, mn.z), mx);
                Solid(A("Steel", mYellow, MBoth | Sun), "gate_jamb_foot", mn, new Vector3(mx.x, 1.6f, mx.z));
                Vector3 lmn = new(HX + T + .15f, -.03f, s > 0 ? GateHalf + .1f : -GateHalf - .1f - 7.4f), lmx = new(HX + T + .4f, GateH + .3f, lmn.z + 7.4f);
                GateLeaf(lmn, lmx);
                ColMM("gate_leaf", lmn, lmx);
            }
            Solid(A("Steel", mSteel, MBoth | Sun), "gate_header", new Vector3(HX - .15f, GateH, -GateHalf - .45f), new Vector3(HX + T + .1f, GateH + .6f, GateHalf + .45f));
            BoxMM(A("Gate", mSteel, MSun), new Vector3(HX + T + .12f, GateH + .3f, -HZ), new Vector3(HX + T + .45f, GateH + .5f, HZ));

            // roof: interior underside, outside top 0.3 m higher with 0.5 m overhangs, fascia and verges
            var rin = A("Roof", mRoofIn, MHall);
            var rout = A("Roof", mRoofOut, MSun);
            float xr = HX + T + Overhang, ze = HZ + T + Overhang, ye = RoofUnder(ze), ridge = Eave + Rise;
            foreach (float s in new[] { -1f, 1f })
            {
                Vector3 e0 = new(-xr, ye, s * ze), e1 = new(xr, ye, s * ze), r0 = new(-xr, ridge, 0), r1 = new(xr, ridge, 0);
                Vector3 nUnder = Vector3.Cross(e1 - e0, r0 - e0).normalized; if (nUnder.y > 0) nUnder = -nUnder;
                Quad(rin, e0, e1, r1, r0, nUnder);
                Vector3 up = Vector3.up * .3f;
                Quad(rout, e0 + up, e1 + up, r1 + up, r0 + up, -nUnder);
                Quad(rout, e0, e1, e1 + up, e0 + up, new Vector3(0, 0, s));
                foreach (float sx in new[] { -1f, 1f })
                {
                    Vector3 a0 = new(sx * xr, ye, s * ze), a1 = new(sx * xr, ridge, 0);
                    Quad(rout, a0, a1, a1 + up, a0 + up, new Vector3(sx, 0, 0));
                }
            }
        }

        /// <summary>A steel column with a hazard-striped foot (0 .. 1.2 m); the joint faces are left out (nothing coplanar).</summary>
        static void Column(Acc steel, Acc foot, string name, Vector3 min, Vector3 max)
        {
            const float Foot = 1.2f;
            BoxMM(foot, min, new Vector3(max.x, Foot, max.z), All & ~PY);
            BoxMM(steel, new Vector3(min.x, Foot, min.z), max, All & ~NY);
            ColMM(name, min, max);
        }

        static void Trusses()
        {
            var a = A("Trusses", mSteel, MHall);
            const int panels = 12;
            float yb = 8.45f;
            for (float x = -20f; x <= 20.01f; x += 5f)
            {
                Beam(a, new Vector3(x, yb, -HZ + .05f), new Vector3(x, yb, HZ - .05f), .2f, .28f);
                Vector3 Top(float z) => new(x, RoofUnder(z) - .15f, z);
                Beam(a, Top(-HZ + .05f), Top(0), .2f, .26f);
                Beam(a, Top(0), Top(HZ - .05f), .2f, .26f);
                for (int k = 1; k < panels; k++)
                {
                    float z = -HZ + k * 2 * HZ / panels, zn = -HZ + (k + 1) * 2 * HZ / panels;
                    float topY = RoofUnder(z) - .28f;
                    if (topY - yb > .4f) Beam(a, new Vector3(x, yb + .14f, z), new Vector3(x, topY, z), .12f, .12f);
                    if (k + 1 < panels)
                    {
                        bool up = k < panels / 2;
                        Vector3 p = up ? new Vector3(x, yb + .14f, z) : new Vector3(x, RoofUnder(z) - .28f, z);
                        Vector3 q = up ? new Vector3(x, RoofUnder(zn) - .28f, zn) : new Vector3(x, yb + .14f, zn);
                        if (Mathf.Abs(q.y - p.y) > .3f) Beam(a, p, q, .1f, .1f);
                    }
                }
            }
            // purlins under the roof, along the hangar
            for (int i = 1; i <= 4; i++)
                foreach (float s in new[] { -1f, 1f })
                {
                    float z = s * HZ * i / 5f;
                    float y = RoofUnder(z) - .12f;
                    BoxMM(a, new Vector3(-HX, y - .1f, z - .08f), new Vector3(HX, y + .1f, z + .08f));
                }
        }

        // ------------------------------------------------------------------ modelled detail (Vadim 30.10 "details are 3D, not painted";
        // ArtDirection §2: chunky parts, three levels of detail, flat faces, one bevel segment of 1-4 cm). Textures only colour.

        /// <summary>A box in a local frame (o, r): local min / max.</summary>
        static void LBox(Acc a, Vector3 o, Quaternion r, Vector3 min, Vector3 max, int faces = All, Cell? cell = null) =>
            Box(a, o + r * ((min + max) * .5f), max - min, r, faces, cell);

        /// <summary>A box with every edge chamfered (one flat segment b wide) in the frame (o, r), local min / max. Main faces get
        /// metric UVs like Box, chamfers and corners planar ones. faces: which main faces to emit (chamfers always).</summary>
        static void Chamfer(Acc a, Vector3 o, Quaternion r, Vector3 min, Vector3 max, float b, int faces = All)
        {
            Vector3 c = (min + max) * .5f, h = (max - min) * .5f;
            b = Mathf.Min(b, Mathf.Min(h.x, Mathf.Min(h.y, h.z)) * .8f);
            Vector3 W(Vector3 l) => o + r * (c + l);
            Vector3 E(int i) => i == 0 ? Vector3.right : i == 1 ? Vector3.up : Vector3.forward;
            int[] bits = { PX, NX, PY, NY, PZ, NZ };
            for (int ax = 0; ax < 3; ax++)
                foreach (int s in new[] { 1, -1 })
                {
                    if ((faces & bits[ax * 2 + (s > 0 ? 0 : 1)]) == 0) continue;
                    Vector3 ln = E(ax) * s, lu = ax == 1 ? Vector3.forward : Vector3.up, lr = Vector3.Cross(ln, lu);
                    float hw = Mathf.Abs(Vector3.Dot(lr, h)) - b, hh = Mathf.Abs(Vector3.Dot(lu, h)) - b, hd = Mathf.Abs(Vector3.Dot(ln, h));
                    Vector3 fc = ln * hd, rd = r * lr, ud = r * lu;
                    Vector3[] p = { W(fc - lr * hw - lu * hh), W(fc + lr * hw - lu * hh), W(fc + lr * hw + lu * hh), W(fc - lr * hw + lu * hh) };
                    Quad(a, p[0], p[1], p[2], p[3], r * ln, p.Select(q => new Vector2(Vector3.Dot(q, rd), Vector3.Dot(q, ud))).ToArray());
                }
            for (int i = 0; i < 3; i++)
                for (int j = i + 1; j < 3; j++)
                {
                    int t = 3 - i - j;
                    foreach (int si in new[] { 1, -1 })
                        foreach (int sj in new[] { 1, -1 })
                        {
                            Vector3 P(float ti, float tj, float tt) => E(i) * ti + E(j) * tj + E(t) * tt;
                            Quad(a, W(P(si * h[i], sj * (h[j] - b), -(h[t] - b))), W(P(si * h[i], sj * (h[j] - b), h[t] - b)),
                                W(P(si * (h[i] - b), sj * h[j], h[t] - b)), W(P(si * (h[i] - b), sj * h[j], -(h[t] - b))), r * (E(i) * si + E(j) * sj).normalized);
                        }
                }
            foreach (int sx in new[] { 1, -1 })
                foreach (int sy in new[] { 1, -1 })
                    foreach (int sz in new[] { 1, -1 })
                        Tri(a, W(new Vector3(sx * h.x, sy * (h.y - b), sz * (h.z - b))), W(new Vector3(sx * (h.x - b), sy * h.y, sz * (h.z - b))),
                            W(new Vector3(sx * (h.x - b), sy * (h.y - b), sz * h.z)), r * new Vector3(sx, sy, sz).normalized);
        }

        /// <summary>Wood cladding boards on a face: local frame (origin, rot), u along the face, v up, the boards standing proud
        /// toward the viewer (local -z). Boards 0.175 m = texture 07's boards (its dark gaps sit in the real grooves), 1.2 cm
        /// grooves, 2.0-2.6 cm proud with small per-board offsets; the face behind shows in the grooves. Ends capped.</summary>
        static void Cladding(Acc a, Vector3 origin, Quaternion rot, float u0, float u1, float v0, float v1, bool capV0 = true)
        {
            const float P = .175f, G = .012f;
            Vector3 W(float u, float v, float d) => origin + rot * new Vector3(u, v, -d);
            for (int k = Mathf.FloorToInt(u0 / P); k * P < u1; k++)
            {
                float ua = Mathf.Max(k * P + G * .5f, u0), ub = Mathf.Min((k + 1) * P - G * .5f, u1);
                if (ub - ua < .005f) continue;
                float d = .02f + (((k * 7919) % 5 + 5) % 5) * .0015f;
                Quad(a, W(ua, v0, d), W(ub, v0, d), W(ub, v1, d), W(ua, v1, d), rot * Vector3.back,
                    new[] { new Vector2(ua, v0), new Vector2(ub, v0), new Vector2(ub, v1), new Vector2(ua, v1) });
                Quad(a, W(ua, v0, 0), W(ua, v0, d), W(ua, v1, d), W(ua, v1, 0), rot * Vector3.left,
                    new[] { new Vector2(ua - d, v0), new Vector2(ua, v0), new Vector2(ua, v1), new Vector2(ua - d, v1) });
                Quad(a, W(ub, v0, 0), W(ub, v1, 0), W(ub, v1, d), W(ub, v0, d), rot * Vector3.right,
                    new[] { new Vector2(ub + d, v0), new Vector2(ub + d, v1), new Vector2(ub, v1), new Vector2(ub, v0) });
                Quad(a, W(ua, v1, 0), W(ub, v1, 0), W(ub, v1, d), W(ua, v1, d), rot * Vector3.up,
                    new[] { new Vector2(ua, v1 + d), new Vector2(ub, v1 + d), new Vector2(ub, v1), new Vector2(ua, v1) });
                if (capV0) Quad(a, W(ua, v0, 0), W(ua, v0, d), W(ub, v0, d), W(ub, v0, 0), rot * Vector3.down,
                    new[] { new Vector2(ua, v0 - d), new Vector2(ua, v0), new Vector2(ub, v0), new Vector2(ub, v0 - d) });
            }
        }

        /// <summary>Roller-door slats on a face: local frame (origin, rot), u along the face, v up; slats 0.1 m = texture 05's
        /// slats (aligned), each a raised band 1.4 cm proud with sloped edges toward the viewer (local -z). Ends capped.</summary>
        static void Slats(Acc a, Vector3 origin, Quaternion rot, float u0, float u1, float v0, float v1)
        {
            const float P = .1f, D = .014f;
            float[] o = { 0f, .015f, .085f, .1f };
            float[] dd = { 0f, D, D, 0f };
            Vector3 W(float u, float v, float d) => origin + rot * new Vector3(u, v, -d);
            float Dep(float v)
            {
                float f = v - Mathf.Floor(v / P) * P;
                for (int i = 0; i < 3; i++) if (f <= o[i + 1]) return Mathf.Lerp(dd[i], dd[i + 1], (f - o[i]) / (o[i + 1] - o[i]));
                return 0f;
            }
            for (int k = Mathf.FloorToInt(v0 / P); k * P < v1; k++)
                for (int i = 0; i < 3; i++)
                {
                    float va = k * P + o[i], vb = k * P + o[i + 1];
                    float ca = Mathf.Max(va, v0), cb = Mathf.Min(vb, v1);
                    if (cb - ca < 1e-4f) continue;
                    float da = Mathf.Lerp(dd[i], dd[i + 1], (ca - va) / (vb - va)), db = Mathf.Lerp(dd[i], dd[i + 1], (cb - va) / (vb - va));
                    Quad(a, W(u0, ca, da), W(u1, ca, da), W(u1, cb, db), W(u0, cb, db), rot * new Vector3(0, -(db - da), -(cb - ca)).normalized,
                        new[] { new Vector2(u0, ca), new Vector2(u1, ca), new Vector2(u1, cb), new Vector2(u0, cb) });
                    if (da > 1e-4f || db > 1e-4f)
                        foreach (var (u, s) in new[] { (u0, -1f), (u1, 1f) })
                            Quad(a, W(u, ca, 0), W(u, cb, 0), W(u, cb, db), W(u, ca, da), rot * new Vector3(s, 0, 0),
                                new[] { new Vector2(0, ca), new Vector2(0, cb), new Vector2(db, cb), new Vector2(da, ca) });
                }
            foreach (var (v, s) in new[] { (v0, -1f), (v1, 1f) })
            {
                float d = Dep(v);
                if (d > 1e-4f) Quad(a, W(u0, v, 0), W(u1, v, 0), W(u1, v, d), W(u0, v, d), rot * new Vector3(0, s, 0),
                    new[] { new Vector2(u0, 0), new Vector2(u1, 0), new Vector2(u1, d), new Vector2(u0, d) });
            }
        }

        // light wood texture 12 (Textures/): its 7 boards between the gap rows; a plank shows one whole board (Cell, not stretched)
        static readonly float[] WoodGaps = { 2f, 145f, 290f, 434f, 585f, 732f, 879f, 1021f };

        static Cell Plank(int k)
        {
            int j = (k % 7 + 7) % 7;
            float r0 = WoodGaps[j] + 10f, r1 = WoodGaps[j + 1] - 10f;
            return new Cell(new Rect(0f, 1f - r1 / 1024f, 1f, (r1 - r0) / 1024f), 1.305f / ((r1 - r0) / 1024f * 1.05f));
        }

        /// <summary>n planks running along the local x, side by side along z with gaps, small height offsets.</summary>
        static void Planks(Acc a, Vector3 o, Quaternion r, Vector3 min, Vector3 max, int n, float gap, int seed, int faces = All)
        {
            float wz = (max.z - min.z - gap * (n - 1)) / n;
            for (int i = 0; i < n; i++)
            {
                float z0 = min.z + i * (wz + gap), dy = (((seed + i * 2) % 3 + 3) % 3) * .003f;
                LBox(a, o, r, new Vector3(min.x, min.y, z0), new Vector3(max.x, max.y - dy, z0 + wz), faces, Plank(seed + i));
            }
        }

        /// <summary>Chunky pallet 1.2 x 0.17 x 1.0 (o = bottom centre): 3 bottom boards, 9 blocks, 3 stringers, 5 top boards with gaps.</summary>
        static void Pallet(Vector3 o, Quaternion r, int seed)
        {
            var wood = A("Props", mPallet, MBoth);
            foreach (float z in new[] { -.43f, 0f, .43f }) LBox(wood, o, r, new Vector3(-.6f, 0f, z - .07f), new Vector3(.6f, .03f, z + .07f), All & ~NY, Plank(seed++));
            foreach (float x in new[] { -.52f, 0f, .52f })
                foreach (float z in new[] { -.43f, 0f, .43f })
                    LBox(wood, o, r, new Vector3(x - .07f, .03f, z - .065f), new Vector3(x + .07f, .1f, z + .065f), All & ~NY & ~PY);
            Quaternion rz = r * Quaternion.Euler(0, 90, 0);
            foreach (float x in new[] { -.52f, 0f, .52f })
                LBox(wood, o + r * new Vector3(x, 0, 0), rz, new Vector3(-.5f, .1f, -.07f), new Vector3(.5f, .13f, .07f), All, Plank(seed++));
            Planks(wood, o, r, new Vector3(-.6f, .13f, -.5f), new Vector3(.6f, .17f, .5f), 5, .07f, seed);
        }

        /// <summary>Military crate (olive metal, graphite hardware): inset body, chamfered lid with a real seam step, bottom band and
        /// corner posts standing proud, corner caps, two chunky latches on the latch sides (1 = local -z, 2 = +z, 3 = both), bar
        /// handles on the ends. o = bottom centre, s = size (x = the long side), r = rotation.</summary>
        static void Crate(Vector3 o, Vector3 s, Quaternion r, int latch, string group = "Props", uint mask = MBoth)
        {
            var body = A(group, mCrate, mask);
            var metal = A(group, mSteel, mask);
            float w = s.x * .5f, h = s.y, d = s.z * .5f, mn = Mathf.Min(s.x, s.z);
            float e = Mathf.Clamp(.05f * mn, .012f, .025f), bev = Mathf.Clamp(.06f * mn, .012f, .03f);
            float lid = Mathf.Clamp(.22f * h, .06f, .13f), band = Mathf.Clamp(.12f * h, .04f, .07f), post = Mathf.Clamp(.14f * mn, .045f, .08f);
            LBox(body, o, r, new Vector3(-w + e, band - .01f, -d + e), new Vector3(w - e, h - lid + .01f, d - e), All & ~PY & ~NY);
            Chamfer(body, o, r, new Vector3(-w, h - lid, -d), new Vector3(w, h, d), bev);
            Chamfer(body, o, r, new Vector3(-w, 0f, -d), new Vector3(w, band, d), bev, All & ~NY);
            foreach (float sx in new[] { -1f, 1f })
                foreach (float sz in new[] { -1f, 1f })
                    Chamfer(body, o, r, new Vector3(sx > 0 ? w - post : -w, band, sz > 0 ? d - post : -d),
                        new Vector3(sx > 0 ? w : -w + post, h - lid, sz > 0 ? d : -d + post), bev * .6f, All & ~PY & ~NY);
            // small crates (shelf goods, under 0.6 m): no corner caps, one latch per side (three levels of detail, nothing fiddly)
            bool small = s.x < .6f;
            float cs = post + .012f, p = .006f;
            if (!small)
            foreach (float sx in new[] { -1f, 1f })
                foreach (float sz in new[] { -1f, 1f })
                    foreach (bool top in new[] { false, true })
                        LBox(metal, o, r, new Vector3(sx > 0 ? w - cs : -w - p, top ? h - cs : 0f, sz > 0 ? d - cs : -d - p),
                            new Vector3(sx > 0 ? w + p : -w + cs, top ? h + p : cs, sz > 0 ? d + p : -d + cs), top ? All : All & ~NY);
            float lw = Mathf.Clamp(.16f * s.x, .06f, .12f), ys = h - lid;
            foreach (float sz in new[] { -1f, 1f })
            {
                if ((latch & (sz < 0 ? 1 : 2)) == 0) continue;
                float zi = sz * (d - e - .003f), zo = sz * (d + .02f), zo2 = sz * (d + .034f);
                foreach (float lx in small ? new[] { 0f } : new[] { -.28f * s.x, .28f * s.x })
                {
                    LBox(metal, o, r, new Vector3(lx - lw * .5f, ys - .55f * lid, Mathf.Min(zi, zo)), new Vector3(lx + lw * .5f, ys + .5f * lid, Mathf.Max(zi, zo)));
                    LBox(metal, o, r, new Vector3(lx - lw * .22f, ys - .35f * lid, Mathf.Min(zi, zo2)), new Vector3(lx + lw * .22f, ys + .25f * lid, Mathf.Max(zi, zo2)));
                }
            }
            float hy = (band + h - lid) * .5f + .02f, hz = Mathf.Min(.14f, .3f * s.z);
            foreach (float sx in new[] { -1f, 1f })
            {
                float xi = sx * (w - e - .003f), xo = sx * (w + .05f), xb0 = sx * (w + .03f), xb1 = sx * (w + .062f);
                foreach (float zc in new[] { -hz, hz })
                    LBox(metal, o, r, new Vector3(Mathf.Min(xi, xo), hy - .025f, zc - .02f), new Vector3(Mathf.Max(xi, xo), hy + .025f, zc + .02f));
                LBox(metal, o, r, new Vector3(Mathf.Min(xb0, xb1), hy - .018f, -hz - .03f), new Vector3(Mathf.Max(xb0, xb1), hy + .018f, hz + .03f));
            }
        }

        /// <summary>A sliding gate leaf: roller-door slats on both faces in a chunky graphite frame (stiles, top and bottom rails).</summary>
        static void GateLeaf(Vector3 mn, Vector3 mx)
        {
            var leaf = A("Gate", mGate, MSun);
            var fr = A("Gate", mSteel, MSun);
            Slats(leaf, new Vector3(mx.x - .03f, 0, 0), Quaternion.Euler(0, -90, 0), mn.z, mx.z, mn.y, mx.y);
            Slats(leaf, new Vector3(mn.x + .03f, 0, 0), Quaternion.Euler(0, 90, 0), -mx.z, -mn.z, mn.y, mx.y);
            const float F = .14f;
            Chamfer(fr, Vector3.zero, Quaternion.identity, new Vector3(mn.x - .01f, mn.y, mn.z), new Vector3(mx.x + .01f, mx.y, mn.z + F), .03f, All & ~NY);
            Chamfer(fr, Vector3.zero, Quaternion.identity, new Vector3(mn.x - .01f, mn.y, mx.z - F), new Vector3(mx.x + .01f, mx.y, mx.z), .03f, All & ~NY);
            Chamfer(fr, Vector3.zero, Quaternion.identity, new Vector3(mn.x - .005f, mx.y - F, mn.z + F - .02f), new Vector3(mx.x + .005f, mx.y - .01f, mx.z - F + .02f), .03f);
            Chamfer(fr, Vector3.zero, Quaternion.identity, new Vector3(mn.x - .005f, mn.y, mn.z + F - .02f), new Vector3(mx.x + .005f, mn.y + F, mx.z - F + .02f), .03f, All & ~NY);
        }

        /// <summary>A room front wall from x0 to x1 at z (0.2 thick), height h, with openings (x0, x1, y0, y1). The hall side
        /// and the reveals are hall-lit, the inner side room-lit; real cladding boards on both sides; colliders per solid piece.</summary>
        static void FrontWall(string name, float x0, float x1, float z, float h, (float x0, float x1, float y0, float y1)[] holes)
        {
            var hall = A("Rooms", mWood, MHall);
            var room = A("Rooms", mWood, MRoom);
            var xs = new List<float> { x0, x1 };
            foreach (var o in holes) { xs.Add(o.x0); xs.Add(o.x1); }
            xs = xs.Distinct().OrderBy(v => v).ToList();
            for (int i = 0; i + 1 < xs.Count; i++)
            {
                float a = xs[i], b = xs[i + 1];
                var cuts = holes.Where(o => o.x0 <= a + 1e-4f && o.x1 >= b - 1e-4f).OrderBy(o => o.y0).ToList();
                float y = 0f;
                var spans = new List<(float, float)>();
                foreach (var c in cuts) { if (c.y0 > y) spans.Add((y, c.y0)); y = Mathf.Max(y, c.y1); }
                if (y < h) spans.Add((y, h));
                foreach (var (y0, y1) in spans)
                {
                    Vector3 mn = new(a, y0, z - .1f), mx = new(b, y1, z + .1f);
                    BoxMM(hall, mn, mx, All & ~PZ);
                    BoxMM(room, mn, mx, PZ);
                    Cladding(hall, new Vector3(0, 0, z - .1f), Quaternion.identity, a, b, y0, y1, y0 > .001f);
                    Cladding(room, new Vector3(0, 0, z + .1f), Quaternion.Euler(0, 180, 0), -b, -a, y0, y1, y0 > .001f);
                    ColMM(name + "_wall", mn, mx);
                }
            }
        }

        static void SideWall(string name, float x, float z0, float h)
        {
            Vector3 mn = new(x - .1f, 0, z0 + .1f), mx = new(x + .1f, h, HZ);
            var acc = A("Rooms", mWood, MBoth);
            BoxMM(acc, mn, mx, All & ~NZ);
            Cladding(acc, new Vector3(x + .1f, 0, 0), Quaternion.Euler(0, -90, 0), z0 + .1f, HZ - .04f, 0f, h, false);
            Cladding(acc, new Vector3(x - .1f, 0, 0), Quaternion.Euler(0, 90, 0), -(HZ - .04f), -(z0 + .1f), 0f, h, false);
            ColMM(name + "_side", mn, mx);
        }

        static void RoomRoof(float x0, float x1, float z0, float h)
        {
            Vector3 mn = new(x0 - .25f, h, z0 - .25f), mx = new(x1 + .25f, h + .2f, HZ - .06f);
            BoxMM(A("Rooms", mWood, MHall), mn, mx, All & ~NY);
            BoxMM(A("Rooms", mWood, MRoom), mn, mx, NY);
            // the ceiling inside: boards along the room depth (u = -x, v = z, proud downward)
            Cladding(A("Rooms", mWood, MRoom), new Vector3(0, h, 0), Quaternion.LookRotation(Vector3.up, Vector3.forward), -(x1 - .1f), -(x0 + .1f), z0 + .1f, HZ - .08f);
            ColMM("room_roof", mn, mx);
        }

        static void Door(float xa, float xb, float z)
        {
            // the leaf stands open into the room, against the inner side of the wall: 6 cm horizontal planks with grooves, two battens
            var a = A("Rooms", mPallet, MBoth);
            float z0 = z + .12f, z1 = z + .12f + (xb - xa) - .05f;
            int k = 0;
            for (float y = .01f; y < 2.24f; y += .15f, k++)
            {
                float d = (k % 2) * .004f;
                BoxMM(a, new Vector3(xa + .02f + d, y, z0), new Vector3(xa + .08f - d, Mathf.Min(y + .142f, 2.25f), z1), All, Plank(k + (int)(xa * 3)));
            }
            foreach (float y in new[] { .35f, 1.8f })
                BoxMM(a, new Vector3(xa + .08f - .002f, y, z0 + .06f), new Vector3(xa + .12f, y + .12f, z1 - .06f), All & ~NX, Plank(k++));
            ColMM("door_leaf", new Vector3(xa + .02f, .01f, z0), new Vector3(xa + .12f, 2.25f, z1));
        }

        static void WindowCounter(float xa, float xb, float z)
        {
            var hall = A("Rooms", mWood, MBoth);
            Planks(A("Rooms", mPallet, MBoth), Vector3.zero, Quaternion.identity, new Vector3(xa - .1f, 1.0f, z - .45f), new Vector3(xb + .1f, 1.07f, z + .7f), 8, .008f, (int)(xa * 10));
            ColMM("counter_shelf", new Vector3(xa - .1f, 1.0f, z - .45f), new Vector3(xb + .1f, 1.07f, z + .7f));
            // the counter cabinet behind the window, inside (cladding boards on its front)
            var cab = A("Rooms", mWood, MRoom);
            Solid(cab, "counter_cabinet", new Vector3(xa, 0, z + .1f), new Vector3(xb, 1.0f, z + .65f), All & ~NY & ~PY);
            Cladding(cab, new Vector3(0, 0, z + .65f), Quaternion.Euler(0, 180, 0), -xb, -xa, 0f, 1.0f, false);
            // glass with a 0.18 m pass slot above the shelf; its collider closes the window (the glass is visible)
            BoxMM(A("Glass", mGlass, MBoth), new Vector3(xa, 1.25f, z - .01f), new Vector3(xb, 2.15f, z + .01f), PZ | NZ);
            ColMM("window_glass", new Vector3(xa, 1.07f, z - .02f), new Vector3(xb, 2.15f, z + .02f));
            BoxMM(hall, new Vector3(xa, 1.22f, z - .03f), new Vector3(xb, 1.25f, z + .03f));
        }

        static void Rooms()
        {
            var id = Quaternion.identity;
            // VAN UPGRADES bay: x -25..-8, front z 7, 6 m high, roller door 8 m x 4.4 m (open, rolled up)
            FrontWall("bay", -HX, -7.9f, 7f, 6f, new[] { (-20.5f, -12.5f, 0f, 4.4f) });
            SideWall("bay", -8f, 7f, 6f);
            RoomRoof(-HX + .05f, -8f, 7f, 6f);
            // roller door: graphite drum housing, steel rails, the curtain rolled down 0.45 m under the drum (real slats both sides)
            Chamfer(A("Rooms", mSteel, MBoth), Vector3.zero, id, new Vector3(-20.9f, 4.4f, 6.59f), new Vector3(-12.1f, 5.0f, 6.89f), .04f);
            ColMM("roller_drum", new Vector3(-20.9f, 4.4f, 6.59f), new Vector3(-12.1f, 5.0f, 6.89f));
            foreach (float x in new[] { -20.75f, -12.45f }) Solid(A("Rooms", mSteel, MBoth), "roller_rail", new Vector3(x, 0, 6.7f), new Vector3(x + .2f, 4.4f, 6.89f));
            var roller = A("Rooms", mRoller, MBoth);
            Slats(roller, new Vector3(0, 0, 6.755f), id, -20.6f, -12.4f, 3.97f, 4.42f);
            Slats(roller, new Vector3(0, 0, 6.785f), Quaternion.Euler(0, 180, 0), 12.4f, 20.6f, 3.97f, 4.42f);
            Chamfer(A("Rooms", mSteel, MBoth), Vector3.zero, id, new Vector3(-20.6f, 3.9f, 6.72f), new Vector3(-12.4f, 3.97f, 6.82f), .015f);
            Sign(-16.5f, 5.49f, 6.9f, 0, .78f);
            // lift: two yellow posts and the top beam, the van drives in between
            var y = A("Bay", mYellow, MRoom | Hall);
            foreach (float x in new[] { -18.65f, -14.35f }) Solid(y, "lift_post", new Vector3(x - .18f, 0, 12.3f), new Vector3(x + .18f, 3.6f, 12.9f));
            Solid(A("Bay", mSteel, MRoom | Hall), "lift_beam", new Vector3(-18.83f, 3.6f, 12.45f), new Vector3(-14.17f, 3.85f, 12.75f));
            // workbench (plank top and lower shelf on a red frame), tool board, red tool cabinet with drawers, trolley, tyres
            var wood = A("Bay", mPallet, MRoom | Hall);
            var red = A("Bay", mRed, MRoom | Hall);
            var hw = A("Bay", mSteel, MRoom | Hall);
            Planks(wood, Vector3.zero, id, new Vector3(-24.6f, .86f, 15.9f), new Vector3(-21.0f, .92f, 16.85f), 6, .008f, 11);
            foreach (float x in new[] { -24.5f, -21.18f })
                foreach (float z in new[] { 15.98f, 16.7f })
                    Chamfer(red, Vector3.zero, id, new Vector3(x, 0, z), new Vector3(x + .08f, .86f, z + .08f), .015f, All & ~NY & ~PY);
            Planks(wood, Vector3.zero, id, new Vector3(-24.46f, .2f, 16.02f), new Vector3(-21.14f, .26f, 16.74f), 5, .01f, 17);
            ColMM("workbench", new Vector3(-24.6f, 0, 15.9f), new Vector3(-21.0f, .92f, 16.85f));
            Chamfer(A("Bay", mPeg, MRoom | Hall), Vector3.zero, id, new Vector3(-24.4f, 1.3f, 16.82f), new Vector3(-21.2f, 2.5f, 16.92f), .02f);
            PegTools(-24.4f, 16.82f);
            Solid(red, "tool_cabinet", new Vector3(-12.2f, 0, 16.1f), new Vector3(-9.2f, 1.1f, 16.85f));
            Chamfer(hw, Vector3.zero, id, new Vector3(-12.25f, 1.1f, 16.05f), new Vector3(-9.15f, 1.16f, 16.87f), .02f);
            for (int i = 0; i < 4; i++)
            {
                float y0 = .08f + i * .25f, y1 = y0 + .22f;
                foreach (float x0 in new[] { -12.12f, -10.66f })
                {
                    Chamfer(red, Vector3.zero, id, new Vector3(x0, y0, 16.075f), new Vector3(x0 + 1.38f, y1, 16.105f), .01f);
                    BoxMM(hw, new Vector3(x0 + .45f, y1 - .08f, 16.035f), new Vector3(x0 + .93f, y1 - .04f, 16.08f));
                }
            }
            Solid(red, "tool_trolley", new Vector3(-21.6f, .08f, 9.6f), new Vector3(-20.8f, 1.0f, 10.2f));
            for (int i = 0; i < 3; i++)
            {
                float y0 = .14f + i * .28f;
                Chamfer(red, Vector3.zero, id, new Vector3(-20.805f, y0, 9.65f), new Vector3(-20.775f, y0 + .24f, 10.15f), .01f);
                BoxMM(hw, new Vector3(-20.78f, y0 + .16f, 9.75f), new Vector3(-20.74f, y0 + .2f, 10.05f));
            }
            foreach (float x in new[] { -21.55f, -20.93f })
                foreach (float z in new[] { 9.65f, 10.07f })
                    BoxMM(A("Bay", mTire, MRoom | Hall), new Vector3(x, 0, z), new Vector3(x + .08f, .08f, z + .08f), All & ~NY);
            var tyre = A("Bay", mTire, MRoom | Hall);
            for (int i = 0; i < 4; i++) Cyl(tyre, new Vector3(-9.2f, i * .25f, 8.4f), .38f, .38f, .24f, 14, i == 3, false);
            ColMM("tyres", new Vector3(-9.6f, 0, 8.0f), new Vector3(-8.8f, 1.0f, 8.8f));
            // ceiling light bars
            foreach (float x in new[] { -21.5f, -16.5f, -11.5f })
                foreach (float z in new[] { 10f, 14f })
                    BoxMM(A("Lamps", mLampPanel, MRoom), new Vector3(x - .7f, 5.86f, z - .12f), new Vector3(x + .7f, 5.96f, z + .12f));

            // PHARMACY: x -5..3, front z 11, 4.2 m; door and window counter
            FrontWall("pharmacy", -5.1f, 3.1f, 11f, 4.2f, new[] { (-4.4f, -3.2f, 0f, 2.3f), (-2.2f, 2.2f, 1.05f, 2.15f) });
            SideWall("pharmacy", -5f, 11f, 4.2f);
            SideWall("pharmacy", 3f, 11f, 4.2f);
            RoomRoof(-5f, 3f, 11f, 4.2f);
            Door(-4.4f, -3.2f, 11f);
            WindowCounter(-2.2f, 2.2f, 11f);
            Sign(-.6f, 3.6f, 10.9f, 1, .7f);
            Shelf(-4.6f, -2.6f, 16.85f, mWhite);
            Shelf(-.2f, 2.6f, 16.85f, mWhite);

            // GEAR: x 6..17, front z 11, 4.2 m; door, window counter, uniforms, helmets, rifle rack
            FrontWall("gear", 5.9f, 17.1f, 11f, 4.2f, new[] { (6.6f, 7.8f, 0f, 2.3f), (9.0f, 15.0f, 1.05f, 2.15f) });
            SideWall("gear", 6f, 11f, 4.2f);
            SideWall("gear", 17f, 11f, 4.2f);
            RoomRoof(6f, 17f, 11f, 4.2f);
            Door(6.6f, 7.8f, 11f);
            WindowCounter(9.0f, 15.0f, 11f);
            Sign(12f, 3.6f, 10.9f, 2, .7f);
            var cloth = A("Gear", mCloth, MRoom | Hall);
            var steel = A("Gear", mSteel, MRoom | Hall);
            Beam(steel, new Vector3(9.6f, 1.85f, 16.4f), new Vector3(12.6f, 1.85f, 16.4f), .06f, .06f);
            for (int i = 0; i < 5; i++)
            {
                float x = 9.9f + i * .6f;
                Chamfer(cloth, Vector3.zero, id, new Vector3(x - .22f, .95f, 16.32f), new Vector3(x + .22f, 1.8f, 16.48f), .03f);
            }
            ColMM("uniform_rack", new Vector3(9.5f, 0, 16.2f), new Vector3(12.7f, 1.9f, 16.9f));
            Shelf(6.3f, 8.9f, 16.85f, mCloth, helmets: true);
            Chamfer(steel, Vector3.zero, id, new Vector3(13.0f, 1.0f, 16.8f), new Vector3(16.5f, 2.3f, 16.9f), .02f);
            for (int i = 0; i < 7; i++)
            {
                float x = 13.35f + i * .45f;
                BoxMM(A("Gear", mTire, MRoom | Hall), new Vector3(x - .04f, 1.1f, 16.68f), new Vector3(x + .04f, 2.15f, 16.8f));
            }
            Crate(new Vector3(13.9f, 0, 16.25f), new Vector3(1.4f, .6f, .7f), id, 1, "Gear", MRoom | Hall);
            ColMM("gear_crate", new Vector3(13.2f, 0, 15.9f), new Vector3(14.6f, .6f, 16.6f));
        }

        /// <summary>Chunky tools on the bay pegboard (board face at z, from x0, 3.2 x 1.2 m from y 1.3): hammers, wrenches,
        /// screwdrivers and a saw, each a few boxes standing proud of the board (accents of 0.2-0.4 m).</summary>
        static void PegTools(float x0, float z)
        {
            var metal = A("Bay", mSteel, MRoom | Hall);
            var red = A("Bay", mRed, MRoom | Hall);
            var wood = A("Bay", mPallet, MRoom | Hall);
            var id = Quaternion.identity;
            Vector3 P(float x, float y, float d) => new(x0 + x, y, z - d);
            void B(Acc a, float xa, float ya, float xb, float yb, float d0, float d1, Cell? c = null) =>
                BoxMM(a, P(xa, ya, d1), P(xb, yb, d0), All & ~PZ, c);
            // two hammers: wooden handle, graphite head
            foreach (float x in new[] { .35f, .75f })
            {
                B(wood, x - .02f, 1.55f, x + .02f, 1.95f, 0f, .04f, Plank((int)(x * 10)));
                B(metal, x - .08f, 1.95f, x + .08f, 2.02f, 0f, .06f);
            }
            // three wrenches (bar + open head), graded sizes
            for (int i = 0; i < 3; i++)
            {
                float x = 1.2f + i * .22f, len = .3f - i * .04f;
                B(metal, x - .018f, 1.6f, x + .018f, 1.6f + len, 0f, .025f);
                B(metal, x - .05f, 1.6f + len, x + .05f, 1.67f + len, 0f, .025f);
            }
            // four screwdrivers: red handle, graphite shaft
            for (int i = 0; i < 4; i++)
            {
                float x = 2.0f + i * .14f;
                B(metal, x - .008f, 1.6f, x + .008f, 1.78f, 0f, .03f);
                B(red, x - .025f, 1.78f, x + .025f, 1.92f, 0f, .05f);
            }
            // a saw: graphite blade with a red handle
            B(metal, 2.62f, 1.62f, 3.0f, 1.76f, 0f, .015f);
            B(red, 2.98f, 1.6f, 3.1f, 1.8f, 0f, .04f);
            // a shelf strip with three tins along the bottom
            B(metal, .2f, 1.38f, 3.0f, 1.42f, 0f, .12f);
            foreach (float x in new[] { .5f, 1.4f, 2.3f })
                Cyl(A("Bay", mRed, MRoom | Hall), P(x, 1.42f, .06f), .045f, .045f, .12f, 8, true, false);
        }

        static void Shelf(float x0, float x1, float zBack, Material goods, bool helmets = false)
        {
            // olive metal shelf: 6 cm posts, 5 cm boards with a chunky front lip
            var steel = A("Props", mShelf, MBoth);
            var id = Quaternion.identity;
            float z0 = zBack - .55f;
            foreach (float x in new[] { x0, x1 - .06f })
                foreach (float z in new[] { z0, zBack - .06f })
                    Chamfer(steel, Vector3.zero, id, new Vector3(x, 0, z), new Vector3(x + .06f, 2.2f, z + .06f), .012f, All & ~NY);
            int n = Mathf.Max(1, Mathf.FloorToInt((x1 - x0 - .2f) / .5f));
            foreach (float y in new[] { .35f, 1.0f, 1.65f })
            {
                BoxMM(steel, new Vector3(x0 + .01f, y - .05f, z0 + .005f), new Vector3(x1 - .01f, y, zBack - .005f));
                Chamfer(steel, Vector3.zero, id, new Vector3(x0 - .008f, y - .09f, z0 - .015f), new Vector3(x1 + .008f, y + .02f, z0 + .04f), .012f);
                var g = A("Props", goods, MBoth);
                for (int i = 0; i < n; i++)
                {
                    float cx = x0 + .25f + i * (x1 - x0 - .3f) / n + .1f;
                    if (helmets)
                    {
                        Cyl(g, new Vector3(cx, y + .03f, zBack - .28f), .17f, .1f, .16f, 10, true, false);
                        Cyl(g, new Vector3(cx, y, zBack - .28f), .2f, .19f, .03f, 10, true, false);
                    }
                    else if (goods == mWhite) BoxMM(g, new Vector3(cx - .18f, y, zBack - .42f), new Vector3(cx + .18f, y + .24f, zBack - .1f), All, NextMedLabel());
                    else Crate(new Vector3(cx, y, zBack - .27f), new Vector3(.34f, .26f + (i % 2) * .06f, .32f), id, 1);
                }
            }
            ColMM("shelf", new Vector3(x0, 0, z0), new Vector3(x1, 2.2f, zBack));
        }

        static void Crates(string name, float x, float z, float rotY, int levels, bool pallet = true)
        {
            Quaternion r = Quaternion.Euler(0, rotY, 0);
            Vector3 o = new(x, 0, z);
            float y = 0f;
            if (pallet)
            {
                Pallet(o, r, name.Sum(ch => ch));
                y = .17f;
            }
            for (int l = 0; l < levels; l++)
            {
                // two long crates side by side per layer, latches on their outer long sides
                foreach (float dz in new[] { -.25f, .25f })
                    Crate(o + r * new Vector3(0, y, dz), new Vector3(1.15f, .58f, .48f), r, dz < 0 ? 1 : 2);
                y += .58f + .006f;
            }
            Col(name, o + Vector3.up * y * .5f, new Vector3(1.2f, y, 1.0f), r);
        }

        static void Barrel(float x, float z)
        {
            // olive drum: body, two rolling hoops, top and bottom chimes, the lid recessed inside the top chime
            var m = A("Props", mShelf, MBoth);
            Vector3 b = new(x, 0, z);
            Cyl(m, b, .3f, .3f, .87f, 12, true, false);
            Cyl(m, b, .31f, .31f, .05f, 12, false, false);
            Cyl(m, b + Vector3.up * .84f, .312f, .312f, .07f, 12, false, false, inner: true);
            Cyl(m, b + Vector3.up * .865f, .312f, .312f, .005f, 12, true, false);
            foreach (float y in new[] { .27f, .58f }) Cyl(m, b + Vector3.up * y, .316f, .316f, .05f, 12, true, true);
            Col("barrel", new Vector3(x, .455f, z), new Vector3(.63f, .91f, .63f), Quaternion.identity);
        }

        static void Props()
        {
            var id = Quaternion.identity;
            // lounge, front-left corner: rug, sofa against the left wall (chamfered base, back, arms, separate cushions),
            // armchair, low plank table on graphite legs, floor lamp
            BoxMM(A("Props", mRug, MHall), new Vector3(-23.7f, 0, -16.2f), new Vector3(-19.5f, .03f, -12.4f), All & ~NY);
            var sofa = A("Props", mSofa, MBoth);
            Chamfer(sofa, Vector3.zero, id, new Vector3(-24.75f, 0, -15.9f), new Vector3(-23.8f, .4f, -13.3f), .03f, All & ~NY);
            ColMM("sofa", new Vector3(-24.75f, 0, -15.9f), new Vector3(-23.8f, .45f, -13.3f));
            Chamfer(sofa, Vector3.zero, id, new Vector3(-24.75f, .4f, -15.9f), new Vector3(-24.5f, .95f, -13.3f), .04f);
            foreach (float z in new[] { -15.9f, -13.52f })
                Chamfer(sofa, Vector3.zero, id, new Vector3(-24.52f, .38f, z), new Vector3(-23.78f, .68f, z + .22f), .04f);
            foreach (var (za, zb) in new[] { (-15.66f, -14.63f), (-14.59f, -13.56f) })
            {
                Chamfer(sofa, Vector3.zero, id, new Vector3(-24.48f, .4f, za), new Vector3(-23.82f, .53f, zb), .04f);
                Chamfer(sofa, Vector3.zero, id, new Vector3(-24.5f, .53f, za + .02f), new Vector3(-24.32f, .88f, zb - .02f), .05f);
            }
            ColMM("sofa_back", new Vector3(-24.75f, .45f, -15.9f), new Vector3(-24.5f, .95f, -13.3f));
            Chamfer(sofa, Vector3.zero, id, new Vector3(-21.4f, 0, -16.85f), new Vector3(-20.4f, .4f, -15.95f), .03f, All & ~NY);
            Chamfer(sofa, Vector3.zero, id, new Vector3(-21.4f, .4f, -16.85f), new Vector3(-20.4f, .95f, -16.6f), .04f);
            Chamfer(sofa, Vector3.zero, id, new Vector3(-21.36f, .4f, -16.58f), new Vector3(-20.44f, .53f, -15.98f), .04f);
            ColMM("armchair", new Vector3(-21.4f, 0, -16.85f), new Vector3(-20.4f, .45f, -15.95f));
            ColMM("armchair_back", new Vector3(-21.4f, .45f, -16.85f), new Vector3(-20.4f, .95f, -16.6f));
            Planks(A("Props", mPallet, MBoth), Vector3.zero, id, new Vector3(-22.7f, .36f, -15.0f), new Vector3(-21.5f, .42f, -13.9f), 6, .01f, 5);
            foreach (float x in new[] { -22.64f, -21.63f })
                foreach (float z in new[] { -14.94f, -14.03f })
                    BoxMM(A("Props", mSteel, MBoth), new Vector3(x, 0, z), new Vector3(x + .07f, .36f, z + .07f), All & ~NY & ~PY);
            ColMM("low_table", new Vector3(-22.7f, 0, -15.0f), new Vector3(-21.5f, .42f, -13.9f));
            Cyl(A("Props", mSteel, MBoth), new Vector3(-24.35f, 0, -16.45f), .04f, .04f, 1.5f, 8, false, false);
            Cyl(A("Props", mSteel, MBoth), new Vector3(-24.35f, 0, -16.45f), .18f, .16f, .05f, 10, true, false);
            Cyl(A("Props", mLampPanel, MBoth), new Vector3(-24.35f, 1.4f, -16.45f), .26f, .18f, .32f, 12, true, true);
            ColMM("floor_lamp", new Vector3(-24.6f, 0, -16.7f), new Vector3(-24.1f, 1.7f, -16.2f));

            // along the left wall (between the lounge and the bay)
            Crates("crates_l1", -24.2f, -9.5f, 90, 2);
            Crates("crates_l2", -24.2f, -7.9f, 90, 1);
            Barrel(-24.4f, -5.6f); Barrel(-24.4f, -4.9f); Barrel(-23.8f, -5.25f);
            Crates("crates_l3", -24.2f, 2.5f, 90, 3);
            Crates("crates_l4", -24.2f, 4.2f, 90, 1);
            // along the front wall
            ShelfFront(-9f, -6.4f);
            Crates("crates_f1", -2.5f, -16.2f, 0, 2);
            Locker(1.0f, 2.3f);
            ShelfFront(6f, 8.6f);
            Crates("crates_f2", 13f, -16.2f, 0, 1);
            Crates("crates_f3", 14.4f, -16.2f, 0, 2);
            Barrel(19.5f, -16.4f); Barrel(20.2f, -16.4f);
            // right wall beside the gate, back-right corner, between the rooms
            Crates("crates_r1", 24.2f, -14.5f, 90, 2);
            Crates("crates_r2", 24.2f, -12.9f, 90, 1);
            Crates("crates_r3", 24.2f, 12.5f, 90, 2);
            Crates("crates_r4", 22.8f, 16.2f, 0, 3);
            Crates("crates_r5", 21.4f, 16.2f, 0, 1);
            Shelf(17.6f, 20.2f, 16.85f, mCrate);
            Barrel(-6.6f, 16.4f); Barrel(-6.0f, 16.1f);
            Crates("crates_b1", 4.5f, 16.2f, 0, 2);

            // string lights: bulbs on a sagging cable along the front and left walls, 3.2 m high, a hook every 3.6 m
            var bulbs = A("StringLights", mBulb, MHall);
            var cable = A("StringLights", mTire, MHall);
            void String(Vector3 a, Vector3 b)
            {
                float len = (b - a).magnitude;
                int spans = Mathf.Max(1, Mathf.RoundToInt(len / 3.6f));
                for (int s = 0; s < spans; s++)
                {
                    Vector3 p = a + (b - a) * s / spans, q = a + (b - a) * (s + 1) / spans;
                    Vector3 prev = p;
                    for (int i = 1; i <= 8; i++)
                    {
                        float t = i / 8f;
                        Vector3 cur = Vector3.Lerp(p, q, t) + Vector3.down * (.32f * 4f * t * (1 - t));
                        Beam(cable, prev, cur, .035f, .035f);
                        if (i % 2 == 0 && i < 8) Bulb(bulbs, cur + Vector3.down * .08f, .065f);
                        prev = cur;
                    }
                    Bulb(bulbs, q + Vector3.down * .08f, .065f);
                }
            }
            String(new Vector3(-24.3f, 3.2f, -16.75f), new Vector3(24.3f, 3.2f, -16.75f));
            String(new Vector3(-24.75f, 3.2f, -16.3f), new Vector3(-24.75f, 3.2f, 6.5f));
            String(new Vector3(24.75f, 3.2f, -16.3f), new Vector3(24.75f, 3.2f, -7.8f));
            String(new Vector3(24.75f, 3.2f, 7.8f), new Vector3(24.75f, 3.2f, 16.3f));
        }

        /// <summary>Olive two-door locker against the front wall (x0..x1, its front at z -16.25): proud door panels, graphite
        /// handles, a vent panel on each door, kick plate, chamfered top.</summary>
        static void Locker(float x0, float x1)
        {
            var lk = A("Props", mShelf, MBoth);
            var hw = A("Props", mSteel, MBoth);
            var id = Quaternion.identity;
            Solid(lk, "cabinet_f", new Vector3(x0, 0, -16.85f), new Vector3(x1, 1.95f, -16.25f), All & ~PY);
            Chamfer(lk, Vector3.zero, id, new Vector3(x0 - .02f, 1.95f, -16.87f), new Vector3(x1 + .02f, 2.02f, -16.23f), .02f);
            float mid = (x0 + x1) * .5f;
            foreach (var (a, b, left) in new[] { (x0 + .04f, mid - .02f, true), (mid + .02f, x1 - .04f, false) })
            {
                Chamfer(lk, Vector3.zero, id, new Vector3(a, .14f, -16.27f), new Vector3(b, 1.9f, -16.232f), .012f);
                float hx = left ? b - .09f : a + .06f;
                BoxMM(hw, new Vector3(hx, .9f, -16.24f), new Vector3(hx + .03f, 1.2f, -16.2f));
                BoxMM(hw, new Vector3(a + .12f, 1.58f, -16.24f), new Vector3(b - .12f, 1.78f, -16.222f));
            }
            BoxMM(hw, new Vector3(x0 + .02f, 0, -16.27f), new Vector3(x1 - .02f, .1f, -16.24f), All & ~NY);
        }

        static void ShelfFront(float x0, float x1)
        {
            // a shelf against the front wall (mirrored Shelf): 6 cm posts, boards, chunky front lip, small crates
            var steel = A("Props", mShelf, MBoth);
            var id = Quaternion.identity;
            float zf = -16.9f, zb = zf + .55f;
            foreach (float x in new[] { x0, x1 - .06f })
                foreach (float z in new[] { zf, zb - .06f })
                    Chamfer(steel, Vector3.zero, id, new Vector3(x, 0, z), new Vector3(x + .06f, 2.2f, z + .06f), .012f, All & ~NY);
            foreach (float y in new[] { .35f, 1.0f, 1.65f })
            {
                BoxMM(steel, new Vector3(x0 + .01f, y - .05f, zf + .005f), new Vector3(x1 - .01f, y, zb - .005f));
                Chamfer(steel, Vector3.zero, id, new Vector3(x0 - .008f, y - .09f, zb - .04f), new Vector3(x1 + .008f, y + .02f, zb + .015f), .012f);
                for (float cx = x0 + .35f; cx < x1 - .3f; cx += .6f)
                    Crate(new Vector3(cx, y, zf + .27f), new Vector3(.4f, .3f, .33f), id, 2);
            }
            ColMM("shelf_front", new Vector3(x0, 0, zf), new Vector3(x1, 2.2f, zb));
        }

        static void Markings()
        {
            var a = A("Markings", mMark, MBoth);
            const float y = .015f;
            Quad(a, new Vector3(-HX, y, -HZ), new Vector3(HX, y, -HZ), new Vector3(HX, y, HZ), new Vector3(-HX, y, HZ), Vector3.up,
                new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) });
        }

        static int Lights(Transform root)
        {
            var g = new GameObject("Lights").transform;
            g.SetParent(root, false);
            int n = 0;
            Color warm = new(1f, .78f, .52f), string_ = new(1f, .68f, .38f), white = new(1f, .9f, .76f);
            Light Make(string name, LightType type, Vector3 p, Color c, float intensity, float range, uint mask, float angle = 0f, bool shadows = false)
            {
                var go = new GameObject(name);
                go.transform.SetParent(g, false);
                go.transform.localPosition = p;
                go.transform.localRotation = Quaternion.Euler(90, 0, 0);
                var l = go.AddComponent<Light>();
                l.type = type;
                l.color = c;
                l.intensity = intensity;
                l.range = range;
                if (type == LightType.Spot) { l.spotAngle = angle; l.innerSpotAngle = angle * .4f; }
                l.shadows = shadows ? LightShadows.Soft : LightShadows.None;
                l.shadowStrength = .8f;
                l.shadowNearPlane = .2f;
                l.lightmapBakeType = LightmapBakeType.Realtime;
                var ld = l.GetUniversalAdditionalLightData();
                ld.renderingLayers = mask;
                ld.customShadowLayers = false;
                n++;
                return l;
            }
            // pendant lamps under the trusses: rod, dark shade, glowing disc, a warm spot pointing down (two cast shadows)
            var shade = A("Pendants", mSteel, MHall);
            var disc = A("Pendants", mLampPanel, MHall);
            foreach (float x in new[] { -20f, -10f, 0f, 10f, 20f })
                foreach (float z in new[] { -10f, -1f, 5f })
                {
                    Beam(shade, new Vector3(x, 8.45f, z), new Vector3(x, 7.36f, z), .05f, .05f);
                    Cyl(shade, new Vector3(x, 7.06f, z), .44f, .14f, .3f, 14, true, false, inner: true);
                    Cyl(disc, new Vector3(x, 7.12f, z), .26f, .26f, .02f, 14, false, true);
                    bool sh = (x == 0f && z == -1f) || (x == -10f && z == -10f);
                    Make($"Pendant {x},{z}", LightType.Spot, new Vector3(x, 7.0f, z), warm, 55f, 14f, Hall, 100f, sh);
                }
            // rooms
            foreach (float x in new[] { -21.5f, -16.5f, -11.5f }) Make("Bay " + x, LightType.Spot, new Vector3(x, 5.75f, 12f), white, 22f, 9f, Hall | Room, 120f);
            Make("Pharmacy", LightType.Point, new Vector3(-1f, 3.6f, 14f), white, 5f, 7.5f, Hall | Room);
            Make("Gear A", LightType.Point, new Vector3(8.8f, 3.6f, 14f), white, 4.5f, 7f, Hall | Room);
            Make("Gear B", LightType.Point, new Vector3(14.2f, 3.6f, 14f), white, 4.5f, 7f, Hall | Room);
            // string-light glow along the walls, the lounge lamp, the signs
            for (float x = -21f; x <= 21.1f; x += 7f) Make("String front " + x, LightType.Point, new Vector3(x, 2.9f, -16.3f), string_, 1.6f, 4.5f, Hall);
            for (float z = -9f; z <= 5.1f; z += 7f) Make("String left " + z, LightType.Point, new Vector3(-24.3f, 2.9f, z), string_, 1.6f, 4.5f, Hall);
            Make("String right a", LightType.Point, new Vector3(24.3f, 2.9f, -12f), string_, 1.6f, 4.5f, Hall);
            Make("String right b", LightType.Point, new Vector3(24.3f, 2.9f, 12f), string_, 1.6f, 4.5f, Hall);
            Make("Lounge lamp", LightType.Point, new Vector3(-24.1f, 1.5f, -16.2f), string_, 2.5f, 5.5f, Hall);
            foreach (var (x, y, z) in new[] { (-16.5f, 5.0f, 6.0f), (-.6f, 3.0f, 10.2f), (12f, 3.0f, 10.2f) })
                Make("Sign glow", LightType.Point, new Vector3(x, y, z), warm, 1.2f, 3.5f, Hall);
            return n;
        }

        static void SaveMeshes(Transform root)
        {
            if (File.Exists(MeshAsset)) AssetDatabase.DeleteAsset(MeshAsset);
            Object container = null;
            var groups = new Dictionary<string, Transform>();
            int idx = 0, tris = 0;
            foreach (var kv in _acc.OrderBy(k => k.Key.g).ThenBy(k => k.Key.m.name))
            {
                var (g, m, mask) = kv.Key;
                var a = kv.Value;
                if (a.V.Count == 0) continue;
                var mesh = new Mesh { name = $"{g}_{m.name}_L{mask}" };
                if (a.V.Count > 65000) mesh.indexFormat = IndexFormat.UInt32;
                mesh.SetVertices(a.V); mesh.SetNormals(a.N); mesh.SetUVs(0, a.U); mesh.SetTriangles(a.T, 0);
                mesh.RecalculateBounds();
                mesh.RecalculateTangents();
                if (container == null) { AssetDatabase.CreateAsset(mesh, MeshAsset); container = mesh; }
                else AssetDatabase.AddObjectToAsset(mesh, container);
                if (!groups.TryGetValue(g, out var gt)) { gt = new GameObject(g).transform; gt.SetParent(root, false); groups[g] = gt; }
                var go = new GameObject(mesh.name);
                go.transform.SetParent(gt, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = go.AddComponent<MeshRenderer>();
                r.sharedMaterial = m;
                r.renderingLayerMask = mask;
                r.shadowCastingMode = m == mMark || m == mGlass ? ShadowCastingMode.Off : ShadowCastingMode.On;
                r.receiveShadows = true;
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic);
                tris += a.T.Count / 3;
                idx++;
            }
            AssetDatabase.SaveAssets();
            _log.AppendLine($"meshes {idx}, triangles {tris}");
        }

        // ------------------------------------------------------------------ van, player, NPCs, HUD, lighting
        static void Actors(Scene scene, Transform root, GameObject van, GameObject floor)
        {
            var roots = scene.GetRootGameObjects();
            // the van parked in the lane loop, facing the gate
            van.transform.SetPositionAndRotation(root.TransformPoint(new Vector3(0f, .05f, -2f)), root.rotation * Quaternion.Euler(0, 90, 0));
            // HUD: no v1 status corner, no objective, own save; trip meter without the W86 teleports
            var dir = roots.First(r => r.name == "[Capture] Stage A director");
            foreach (var mb in dir.GetComponents<MonoBehaviour>())
            {
                var so = new SerializedObject(mb);
                var p0 = so.FindProperty("ShowStatusCorner"); if (p0 != null) p0.boolValue = false;
                var p1 = so.FindProperty("NewGameObjective"); if (p1 != null) p1.stringValue = "";
                var p2 = so.FindProperty("SaveFileName"); if (p2 != null) p2.stringValue = "capture_hangar_v01.json";
                var p3 = so.FindProperty("EditorSlot"); if (p3 != null) p3.stringValue = "capture_hangar_editor_v01.json";
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            var trip = van.GetComponent<OnlyVolunteers.Map.GreyboxTripMeter>();
            if (trip && trip.Spots.Length > 0) { trip.Spots = new OnlyVolunteers.Map.GreyboxTripMeter.Spot[0]; EditorUtility.SetDirty(trip); }

            // four grab-able NPCs standing 5 m off the van's left side, facing it (as VanLab)
            var crowd = roots.First(r => r.name == "Crowd");
            var cd = crowd.GetComponent<OnlyVolunteers.Map.Crowd.CrowdDirector>();
            var templates = cd.Templates.Where(t => t && !t.name.Contains("FOREST") && !t.name.Contains("VIP") && !t.name.Contains("POLICE")).ToList();
            cd.enabled = false;
            var npcRoot = new GameObject("Hangar_NPCs").transform;
            SceneManager.MoveGameObjectToScene(npcRoot.gameObject, scene);
            for (int i = 0; i < 4 && i < templates.Count; i++)
            {
                var t = templates[(i * 7) % templates.Count];
                var g = Object.Instantiate(t, npcRoot);
                g.name = "Hangar_NPC_" + i + "_" + t.name.Replace("CrowdTemplate_", "");
                g.transform.SetPositionAndRotation(root.TransformPoint(new Vector3(-3.75f + i * 2.5f, 0f, 3.2f)), root.rotation * Quaternion.Euler(0, 180, 0));
                g.SetActive(true);
                _log.AppendLine($"npc {g.name} at local {root.InverseTransformPoint(g.transform.position)}");
            }

            // the player on SPAWN looking at the van
            var player = roots.First(r => r.name == "Player_KCC");
            Transform feet = player.GetComponentsInChildren<Component>(true).FirstOrDefault(c => c && c.GetType().Name == "KinematicCharacterMotor")?.transform ?? player.transform;
            Vector3 target = root.TransformPoint(new Vector3(-15f, .05f, -12.5f));
            Vector3 look = van.transform.position - target; look.y = 0f;
            player.transform.RotateAround(feet.position, Vector3.up, Mathf.DeltaAngle(feet.eulerAngles.y, Quaternion.LookRotation(look).eulerAngles.y));
            player.transform.position += target - feet.position;
            _log.AppendLine($"player feet local {root.InverseTransformPoint(feet.position)} yaw {feet.eulerAngles.y:F1}; van local {root.InverseTransformPoint(van.transform.position)} yaw {van.transform.eulerAngles.y:F0}");

            // lighting: the sun (and any directional light) lights the sunlit layer only; the outside floor is sunlit
            foreach (var l in Object.FindObjectsByType<Light>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (l.transform.IsChildOf(root)) continue;
                if (l.type == LightType.Directional)
                {
                    var ld = l.GetUniversalAdditionalLightData();
                    ld.renderingLayers = Sun;
                    ld.customShadowLayers = false;
                    EditorUtility.SetDirty(ld);
                }
                _log.AppendLine($"scene light {l.name} {l.type} enabled {l.enabled} layers {(uint)l.GetUniversalAdditionalLightData().renderingLayers}");
            }
            var floorR = floor.GetComponent<Renderer>();
            floorR.renderingLayerMask = L0 | Sun;
            var look86 = roots.FirstOrDefault(r => r.name == "W86_Look");
            if (look86)
                foreach (var mb in look86.GetComponents<MonoBehaviour>())
                {
                    var so = new SerializedObject(mb);
                    var lb = so.FindProperty("LightBalance"); if (lb != null) { lb.boolValue = false; so.ApplyModifiedPropertiesWithoutUndo(); _log.AppendLine("W86 light balance off"); }
                }
            // moving things start inside: hall-lit, not sunlit (HangarLighting keeps them right at runtime)
            foreach (var r in van.GetComponentsInChildren<Renderer>(true).Concat(player.GetComponentsInChildren<Renderer>(true)).Concat(npcRoot.GetComponentsInChildren<Renderer>(true)))
                r.renderingLayerMask = (r.renderingLayerMask | L0 | Hall) & ~Sun;
            var lightGo = new GameObject("Hangar lighting (sun outside only, dim inside)");
            SceneManager.MoveGameObjectToScene(lightGo, scene);
            var hl = lightGo.AddComponent<HangarLighting>();
            hl.Hangar = root;
            hl.Fixed = new[] { floorR };
            var test = new GameObject("Hangar test mode (idle unless started with -hangarTest)");
            SceneManager.MoveGameObjectToScene(test, scene);
            test.AddComponent<HangarTestMode>();
            RenderSettings.fog = false;

            // checks: the van, the player and the NPCs stand free; the van has a clear way out of the gate
            Physics.SyncTransforms();
            var vanCols = new HashSet<Collider>(van.GetComponentsInChildren<Collider>(true));
            int mask = ~0;
            foreach (string ln in new[] { "VehicleInterior", "NpcSlide", "Player", "NpcBody", "NpcSeated" }) { int i = LayerMask.NameToLayer(ln); if (i >= 0) mask &= ~(1 << i); }
            var hits = Physics.OverlapBox(van.transform.TransformPoint(new Vector3(0, 1.4f, 0)), new Vector3(1.15f, 1.2f, 3.2f), van.transform.rotation, mask, QueryTriggerInteraction.Ignore)
                .Where(c => !vanCols.Contains(c)).Select(c => c.name).ToList();
            _log.AppendLine("van overlaps: " + (hits.Count == 0 ? "none" : string.Join(", ", hits)));
            Vector3 from = root.TransformPoint(new Vector3(0f, 1.45f, -2f));
            bool blocked = Physics.BoxCast(from, new Vector3(3.2f, 1.2f, 1.25f), root.right, out RaycastHit hit, root.rotation, 40f, mask, QueryTriggerInteraction.Ignore);
            _log.AppendLine("drive-out box cast (van 2.5 m wide, 2.4 m tall) to +x 40 m: " + (blocked && !vanCols.Contains(hit.collider) ? $"HIT {hit.collider.name} at {hit.distance:F1} m" : "clear"));
            Vector3 pf = root.TransformPoint(new Vector3(-15f, .06f, -12.5f));
            _log.AppendLine("player capsule at SPAWN: " + (Physics.CheckCapsule(pf + Vector3.up * .4f, pf + Vector3.up * 1.4f, .35f, mask, QueryTriggerInteraction.Ignore) ? "BLOCKED" : "free"));
            foreach (var x in new[] { -3.75f, -1.25f, 1.25f, 3.75f })
            {
                Vector3 p = root.TransformPoint(new Vector3(x, .06f, 3.2f));
                _log.AppendLine($"npc spot {x}: " + (Physics.CheckCapsule(p + Vector3.up * .4f, p + Vector3.up * 1.4f, .3f, mask, QueryTriggerInteraction.Ignore) ? "BLOCKED" : "free"));
            }
            // doorways: a 0.35 m capsule passes each room door (walk through the middle of the opening)
            foreach (var (nm, x, z) in new[] { ("pharmacy door", -3.8f, 11f), ("gear door", 7.2f, 11f), ("bay door", -16.5f, 7f) })
            {
                Vector3 p = root.TransformPoint(new Vector3(x, .06f, z));
                _log.AppendLine($"{nm}: " + (Physics.CheckCapsule(p + Vector3.up * .4f, p + Vector3.up * 1.5f, .34f, mask, QueryTriggerInteraction.Ignore) ? "BLOCKED" : "passable"));
            }
        }

        /// <summary>Batch entry: rebuild the scene, render the review shots, then the Hangar player build (OV_BUILD_ONLY=Hangar).</summary>
        public static void RunShotsBuild()
        {
            Run();
            Shots();
            if (Environment.GetEnvironmentVariable("OV_BUILD_ONLY") == "Hangar") VadimBuilds.BuildAll();
        }

        // ------------------------------------------------------------------ editor review shots (batch)
        public static void Shots()
        {
            var scene = EditorSceneManager.OpenScene(Dst);
            var root = GameObject.Find(RootName).transform;
            Directory.CreateDirectory(ShotDir);
            var hl = Object.FindFirstObjectByType<HangarLighting>();
            var sh = new SphericalHarmonicsL2();
            sh.AddAmbientLight(hl.InsideGround);
            sh.AddDirectionalLight(Vector3.up, hl.InsideSky - hl.InsideGround, 1f);
            RenderSettings.ambientMode = AmbientMode.Custom;
            RenderSettings.ambientProbe = sh;
            RenderSettings.reflectionIntensity = hl.InsideReflection;
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            var go = new GameObject("ShotCam");
            var cam = go.AddComponent<Camera>();
            cam.farClipPlane = 1500f; cam.nearClipPlane = .05f;
            var cd = cam.GetUniversalAdditionalCameraData();
            cd.renderPostProcessing = true;
            cd.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
            void Show(string group, bool on) { var t = root.Find(group); if (t) t.gameObject.SetActive(on); }
            // plan view without the roof and trusses
            Show("Roof", false); Show("Trusses", false); Show("Pendants", false);
            cam.orthographic = true; cam.orthographicSize = 19f;
            go.transform.SetPositionAndRotation(root.TransformPoint(new Vector3(0, 60, 0)), Quaternion.Euler(90, 0, 0));
            Shot(cam, 2400, 1700, "top_plan_no_roof");
            // cutaway like the reference: roof and front wall off, from the front-left above
            Show("Wall_Front", false);
            cam.orthographic = false; cam.fieldOfView = 45f;
            go.transform.position = root.TransformPoint(new Vector3(-12, 34, -52));
            go.transform.LookAt(root.TransformPoint(new Vector3(0, 0, 2)));
            Shot(cam, 2400, 1350, "cutaway_front_left");
            Show("Wall_Front", true); Show("Roof", true); Show("Trusses", true); Show("Pendants", true);
            // outside with the roof
            go.transform.position = root.TransformPoint(new Vector3(60, 25, -45));
            go.transform.LookAt(root.TransformPoint(new Vector3(0, 4, 0)));
            Shot(cam, 2400, 1350, "outside_gate_side");
            // ground level (1.7 m) views
            cam.fieldOfView = 60f;
            foreach (var (n, x, z, lx, ly, lz) in new[]
            {
                ("g01_spawn_to_van", -15f, -12.5f, 0f, 1f, -2f), ("g02_hall_to_rooms", 0f, -14f, 0f, 2.5f, 17f), ("g03_bay_inside", -16.5f, 8.2f, -16.5f, 1.5f, 17f),
                ("g04_pharmacy_inside", 1.8f, 16.2f, -1f, 1.2f, 11f), ("g05_gear_inside", 11.5f, 11.8f, 11.5f, 1.5f, 17f), ("g06_lounge", -15.5f, -9.5f, -22f, .8f, -14.5f),
                ("g07_gate_from_inside", 6f, -1f, 25f, 2f, 0f), ("g08_trusses_up", 0f, -6f, 0f, 9f, 2f), ("g09_corner_diagonal", -23f, -15f, 25f, 1.5f, 17f),
                // close-ups of the modelled detail (crates, pallet, cladding, shelf, gate leaf, locker, wall ribs)
                ("g10_crates_close", -21.6f, -8.2f, -24.2f, .6f, -9.4f), ("g11_pallet_close", -22.7f, 1.0f, -24.0f, .15f, 2.5f),
                ("g12_cladding_close", -1.6f, 9.4f, -3.4f, 1.4f, 10.9f), ("g13_shelf_crates", -7.7f, -14.7f, -7.7f, 1.0f, -16.9f),
                ("g14_gate_leaf_out", 31.5f, -17f, 25.6f, 3f, -10.5f), ("g15_locker_crates", 0f, -14.4f, .4f, 1f, -16.6f),
                ("g16_wall_ribs", 10f, -15.2f, 15f, 2.2f, -17f),
            })
            {
                go.transform.position = root.TransformPoint(new Vector3(x, 1.7f, z));
                go.transform.LookAt(root.TransformPoint(new Vector3(lx, ly, lz)));
                Shot(cam, 1600, 900, n);
            }
            Object.DestroyImmediate(go);
        }

        static void Shot(Camera cam, int w, int h, string name)
        {
            var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32) { antiAliasing = 2 };
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            tex.Apply();
            File.WriteAllBytes(Path.Combine(ShotDir, name + ".png"), tex.EncodeToPNG());
            RenderTexture.active = null;
            cam.targetTexture = null;
            Object.DestroyImmediate(tex);
            rt.Release();
        }
    }
}
