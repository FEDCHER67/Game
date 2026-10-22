using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Art.MapTexturesW86
{
    // Stations of TexW86T1: one per inventory code (Forest, Hamlet, Rough, Downtown specials, World). Variant a / b / c per station.
    public static partial class TexW86T1
    {
        static readonly Color W = Color.white;
        const string TTB4 = "Assets/OnlyVolunteers/Art/TextureTest_v01/Built_v04";
        const string TTB7 = "Assets/OnlyVolunteers/Art/TextureTest_v01/Built_v07";
        const string GEN = "Assets/OnlyVolunteers/Map/W85Build/Generated/v01";
        const string MPF = "Assets/OnlyVolunteers/Art/Map/Prefabs/";
        static readonly string[] VS = { "a", "b", "c" };

        static Color Own(string key) => S[key].Own;
        static Color Mul(Color c, float k) => new(c.r * k, c.g * k, c.b * k, 1f);

        static string LayerTex(string path)
        {
            var tl = AssetDatabase.LoadAssetAtPath<TerrainLayer>(path);
            return tl && tl.diffuseTexture ? AssetDatabase.GetAssetPath(tl.diffuseTexture) : null;
        }

        // ================================================================== surfaces used by several stations
        static void Surfaces()
        {
            Kit("g_meadow", "Assets/OnlyVolunteers/Art/Map/Textures/Detail/TL_meadow_albedo.png", 8);
            Kit("g_worn", "Assets/OnlyVolunteers/Art/Map/Textures/Detail/TL_worn_grass_albedo.png", 8);
            Kit("g_sand", "Assets/OnlyVolunteers/Art/Map/Textures/Detail/TL_sand_albedo.png", 8);
            string ff = LayerTex(GEN + "/Terrain/W85_L04_forest_floor_p10.terrainlayer");
            if (ff != null) Kit("g_forest", ff, 8); else Kit("g_forest", "Assets/OnlyVolunteers/Art/Map/Textures/Detail/TL_worn_grass_albedo.png", 8);
            string rock = LayerTex(GEN + "/Terrain/W85_L07_rock_macro.terrainlayer");
            Kit("rock", rock ?? "Assets/OnlyVolunteers/Art/StyleKit_v3/Textures/3c_concrete_panels/3c_concrete_panels_v07_albedo.png", 12);
            Ref("g_asph", GEN + "/Materials/W85_asphalt_A5d12.mat", 6, 6);
            Ref("g_asph_old", "Assets/OnlyVolunteers/Art/TextureTest_v01/Built/Materials/TT_asphalt_old.mat", 6, 6);
            Ref("g_side", GEN + "/Materials/W85_sidewalk_S1.mat", 3, 3);
            Ref("cur_sk3c", GEN + "/Materials/W85_concrete_SK3c_nofield.mat", 4, 4);
            Ref("cur_panel", GEN + "/Materials/W85_concrete_panel_SK3c_nofield.mat", 4, 4);
            Ref("cur_brick", GEN + "/Materials/W85_brick_SK3a_nofield.mat", 3, 3);
            Ref("cur_boards", GEN + "/Materials/W85_boards_SK5a_nofield.mat", 3, 3);
            Ref("cur_pier", "Assets/OnlyVolunteers/Map/W76Build/Generated/v01/Materials/W76_boards_pier_SK5a_v02.mat", 3, 3);
            Ref("cur_metal", "Assets/OnlyVolunteers/Map/LookV3/Materials/v19/V3S17_6a_painted_metal_panels.mat", 3, 3);
            Ref("water_flow", GEN + "/Materials/W85_water_flow.mat", 1, 1).NoShadow = true;
            Ref("waterfall", GEN + "/Materials/W85_waterfall.mat", 1, 1).NoShadow = true;
            Ref("d4_plaster", TTB4 + "/Materials/TT_acg_plaster.mat", 3, 3);
            Ref("d4_brick", TTB4 + "/Materials/TT_brick_paint.mat", 3, 3);
            Ref("d4_trim", TTB4 + "/Materials/TT_trim.mat", 2, .45f);
            Ref("d4_flat", TTB4 + "/Materials/TT_flat.mat", 1, 1);
            Ref("d4_glass", TTB4 + "/Materials/TT_Glass_Downtown.mat", 1, 1);
            Ref("tt7_trav", TTB7 + "/Materials/TT7_travertine.mat", 2.4f, 2.4f);
            Ref("tt7_larch", TTB7 + "/Materials/TT7_larch.mat", 1.2f, 1.2f);
            Ref("tt7_teak", TTB7 + "/Materials/TT7_teak.mat", 1.2f, 1.2f);
            Ref("tt7_conc", TTB7 + "/Materials/TT7_conc.mat", 2.4f, 2.4f);
            Ref("tt7_rubble", TTB7 + "/Materials/TT7_rubble_grey.mat", 2.2f, 2.2f);
            Ref("tt7_stone", TTB7 + "/Materials/TT7_stone.mat", 1f, 1f);
            Ref("tt7_ashlar", TTB7 + "/Materials/TT7_ashlar.mat", 2.4f, 2.4f);
            Ref("tt7_board", TTB7 + "/Materials/TT7_board.mat", 2f, 2f);
            Ref("tt7_shutter", TTB7 + "/Materials/TT7_shutter.mat", 2f, 2f);
            Ref("hh_roof_dark", GEN + "/Materials/Rollout/W85_HH_Roof_a_dark1.mat", 1, 1);
            // the W85 generic meshes carry no vertex colour (white): show the current materials exactly as the map draws them
            foreach (string k in new[] { "cur_sk3c", "cur_panel", "cur_brick", "cur_boards", "cur_pier", "cur_metal" }) S[k].Own = W;
            Flat("flat", .12f); Flat("flat_metal", .4f, .45f); Flat("flat_gloss", .8f, .1f);
            Lit("glass_dark", X("2F3B43"), null, 1, 1, .88f, .2f, 0);
            Lit("water_stand", new Color(.30f, .40f, .38f, .7f), null, 1, 1, .9f, 0, 2, false, true);
            // own kit materials (vertex colour)
            Kit("k_metal", "T1_painted_metal_albedo.png", 2f, null, .5f, .3f, .2f);
            Kit("k_boards_dark", "T1_boards_dark_albedo.png", 2f, "T1_boards_dark_normal.png", .6f);
            Kit("k_boards_grey", "T1_boards_grey_albedo.png", 2f, "T1_boards_grey_normal.png", .6f);
            Kit("k_boards_tar", "T1_boards_tar_albedo.png", 2f, "T1_boards_tar_normal.png", .6f);
            Kit("k_boards_warm", "T1_boards_warm_albedo.png", 2f, "T1_boards_warm_normal.png", .6f);
            Kit("k_bark", "T1_bark_brown_albedo.png", 1f, "T1_bark_brown_normal.png", .8f);
            Kit("k_conc", "T1_concrete_light_albedo.png", 3f, "T1_concrete_light_normal.png", .4f);
            Kit("k_galv", "T1_galv_rust_albedo.png", 1.2f, "T1_galv_rust_normal.png", .8f, .35f, .3f);
            Kit("k_rust", "T1_rust_sheet_albedo.png", 2f, "T1_rust_sheet_normal.png", .8f, .25f, .2f);
            Kit("k_tar", "T1_roof_tar_albedo.png", 4f, "T1_roof_tar_normal.png", .6f);
            Note($"surfaces: {S.Count}");
        }

        static void BuildStations(Transform root)
        {
            var steps = new (string name, Action a)[]
            {
                ("forest", () => Forest(root)), ("hamlet", () => Hamlet(root)), ("rough", () => Rough(root)),
                ("downtown", () => Downtown(root)), ("world", () => World(root)),
            };
            foreach (var (name, a) in steps)
            {
                try { a(); }
                catch (Exception e) { Note($"STATIONS {name} FAILED: {e}"); Debug.LogException(e); }
            }
        }

        // ------------------------------------------------------------------ helpers
        delegate void VarBuild(string v, Batch b, Transform parent);

        static void Vars(Station st, VarBuild build)
        {
            foreach (string v in VS)
            {
                var b = new Batch();
                build(v, b, st.V[v]);
                Flush(b, st.V[v], st.Code + "_" + v);
            }
        }

        static void StGround(Station st, string key, float half = 70f, float y = 0f)
        {
            var b = new Batch();
            Ground(b, key, -half, -half, half, half, y, Own(key));
            Flush(b, st.T, st.Code + "_ground");
        }

        static int Vi(string v) => v == "a" ? 0 : v == "b" ? 1 : 2;
        static T Pick3<T>(string v, T a, T b, T c) => v == "a" ? a : v == "b" ? b : c;

        // simple rectangular block: walls (four faces, one key), flat roof slab + parapet
        static void Block(Batch b, string wall, Color wc, float x0, float x1, float z0, float z1, float y0, float h, string roof, Color rc, float parapet = 0f)
        {
            Face(b, wall, new Vector3(x0, y0, z0), Vector3.right, x1 - x0, Vector3.up, h, Vector3.back, wc, x0, y0);
            Face(b, wall, new Vector3(x1, y0, z1), Vector3.left, x1 - x0, Vector3.up, h, Vector3.forward, wc, -x1, y0);
            Face(b, wall, new Vector3(x0, y0, z1), Vector3.back, z1 - z0, Vector3.up, h, Vector3.left, wc, -z1, y0);
            Face(b, wall, new Vector3(x1, y0, z0), Vector3.forward, z1 - z0, Vector3.up, h, Vector3.right, wc, z0, y0);
            if (roof != null) Ground(b, roof, x0, z0, x1, z1, y0 + h, rc);
            if (parapet > 0f)
            {
                float t = .25f, yt = y0 + h;
                BoxMM(b, wall, new Vector3(x0, yt, z0), new Vector3(x1, yt + parapet, z0 + t), wc);
                BoxMM(b, wall, new Vector3(x0, yt, z1 - t), new Vector3(x1, yt + parapet, z1), wc);
                BoxMM(b, wall, new Vector3(x0, yt, z0), new Vector3(x0 + t, yt + parapet, z1), wc);
                BoxMM(b, wall, new Vector3(x1 - t, yt, z0), new Vector3(x1, yt + parapet, z1), wc);
            }
        }

        // atlas cell rect (row / col of a 4 x 4 atlas; pixel box x0,y0,x1,y1 top-based inside a 512 cell) -> Unity uv rect
        static Rect Cell(int row, int col, float x0, float y0, float x1, float y1, int cells = 4, float cellPx = 512f)
        {
            float cw = 1f / cells;
            float u0 = col * cw + x0 / cellPx * cw, u1 = col * cw + x1 / cellPx * cw;
            float vTop = 1f - row * cw;
            float v0 = vTop - y1 / cellPx * cw, v1 = vTop - y0 / cellPx * cw;
            return Rect.MinMaxRect(u0, v0, u1, v1);
        }

        // flat decal quad on a ground at y, centre c (x,z), size (along x, along z), yaw, uv rect
        static void Decal(Batch b, string key, Vector3 c, float sx, float sz, float yaw, Rect uv, Color col)
        {
            var q = Quaternion.Euler(0, yaw, 0);
            Vector3 ex = q * Vector3.right * sx * .5f, ez = q * Vector3.forward * sz * .5f;
            Q(b, key, c - ex - ez, c + ex - ez, c + ex + ez, c - ex + ez, Vector3.up,
                new Vector2(uv.xMin, uv.yMin), new Vector2(uv.xMax, uv.yMin), new Vector2(uv.xMax, uv.yMax), new Vector2(uv.xMin, uv.yMax), col);
        }

        // vertical quad with explicit uv rect (signs, panels): bottom-left o, along ex (L), up (H), normal n
        static void Panel(Batch b, string key, Vector3 o, Vector3 ex, float L, float H, Vector3 n, Rect uv, Color col)
        {
            Q(b, key, o, o + ex * L, o + ex * L + Vector3.up * H, o + Vector3.up * H, n,
                new Vector2(uv.xMin, uv.yMin), new Vector2(uv.xMax, uv.yMin), new Vector2(uv.xMax, uv.yMax), new Vector2(uv.xMin, uv.yMax), col);
        }

        // D4-style window unit in a face frame (o = face origin, ex along, F inward): glass at recess, frame, mullion, sill, lintel / surround
        static void Window(Batch b, Vector3 o, Vector3 ex, Vector3 F, Rect h, float r, Color frame, Color stone, bool lintel, string glass = "d4_glass", string trimKey = "d4_flat", bool transom = false)
        {
            Vector3 n = -F;
            Face(b, glass, FP(o, ex, F, h.xMin, h.yMin, r), ex, h.width, Vector3.up, h.height, n, X("3E4B55"));
            float t = .07f, zc = r - .03f;
            FBox(b, trimKey, o, ex, F, h.center.x, h.yMin + t / 2, zc, new Vector3(h.width, t, .06f), frame);
            FBox(b, trimKey, o, ex, F, h.center.x, h.yMax - t / 2, zc, new Vector3(h.width, t, .06f), frame);
            FBox(b, trimKey, o, ex, F, h.xMin + t / 2, h.center.y, zc, new Vector3(t, h.height, .06f), frame);
            FBox(b, trimKey, o, ex, F, h.xMax - t / 2, h.center.y, zc, new Vector3(t, h.height, .06f), frame);
            FBox(b, trimKey, o, ex, F, h.center.x, h.center.y, zc, new Vector3(.05f, h.height, .05f), frame);
            if (transom) FBox(b, trimKey, o, ex, F, h.center.x, h.yMin + h.height * .7f, zc, new Vector3(h.width, .05f, .05f), frame);
            FBox(b, trimKey, o, ex, F, h.center.x, h.yMin - .04f, (r - .08f) / 2, new Vector3(h.width + .2f, .08f, r + .08f), stone);
            if (lintel) FBox(b, trimKey, o, ex, F, h.center.x, h.yMax + .11f, -.015f, new Vector3(h.width + .24f, .22f, .05f), stone);
            else
            {
                FBox(b, trimKey, o, ex, F, h.xMin - .06f, h.center.y + .06f, -.012f, new Vector3(.12f, h.height + .12f, .03f), stone);
                FBox(b, trimKey, o, ex, F, h.xMax + .06f, h.center.y + .06f, -.012f, new Vector3(.12f, h.height + .12f, .03f), stone);
                FBox(b, trimKey, o, ex, F, h.center.x, h.yMax + .06f, -.012f, new Vector3(h.width + .24f, .12f, .03f), stone);
            }
        }

        // storefront unit: large glass in a recess, dark frame, mullions, optional door
        static void Shop(Batch b, Vector3 o, Vector3 ex, Vector3 F, Rect h, float r, Color frame, bool door, string glass = "d4_glass")
        {
            Vector3 n = -F;
            Face(b, glass, FP(o, ex, F, h.xMin, h.yMin, r), ex, h.width, Vector3.up, h.height, n, X("3E4B55"));
            float t = .09f, zc = r - .04f;
            FBox(b, "d4_flat", o, ex, F, h.center.x, h.yMin + .2f, zc, new Vector3(h.width, .4f, .08f), frame);
            FBox(b, "d4_flat", o, ex, F, h.center.x, h.yMax - t / 2, zc, new Vector3(h.width, t, .08f), frame);
            FBox(b, "d4_flat", o, ex, F, h.xMin + t / 2, h.center.y, zc, new Vector3(t, h.height, .08f), frame);
            FBox(b, "d4_flat", o, ex, F, h.xMax - t / 2, h.center.y, zc, new Vector3(t, h.height, .08f), frame);
            int m = Mathf.Max(1, Mathf.RoundToInt(h.width / 1.6f));
            for (int i = 1; i < m; i++) FBox(b, "d4_flat", o, ex, F, h.xMin + h.width * i / m, h.center.y, zc, new Vector3(.06f, h.height, .07f), frame);
            FBox(b, "d4_flat", o, ex, F, h.center.x, h.yMax - .55f, zc, new Vector3(h.width, .06f, .07f), frame);
            if (door) FBox(b, "d4_flat", o, ex, F, h.xMin + .6f, h.yMin + 1.1f, zc - .02f, new Vector3(1.1f, 2.2f, .05f), Mul(frame, 1.15f));
        }

        // rectangular D4-like block with 3D windows on the front (-Z) and left (-X) faces
        sealed class DPal { public string Wall = "d4_plaster", GroundWall; public Color Wc, Gc, Stone, Frame, Accent = Color.clear; public bool Lintel = true, Shops = false; public string Glass = "d4_glass"; }

        static void DBlock(Batch b, float x0, float x1, float z0, float z1, int floors, float gf, float fh, DPal p, float bay = 3.4f, float winW = 1.4f, float winH = 1.9f, bool cornice = true, bool sideFace = true)
        {
            float H = gf + (floors - 1) * fh;
            string gw = p.GroundWall ?? p.Wall;
            // faces: front (-Z) and left (-X) with windows; back / right plain
            var faces = new List<(Vector3 o, Vector3 ex, Vector3 F, float L, bool win)>
            {
                (new Vector3(x0, 0, z0), Vector3.right, Vector3.forward, x1 - x0, true),
                (new Vector3(x0, 0, z1), Vector3.back, Vector3.right, z1 - z0, sideFace),
                (new Vector3(x1, 0, z1), Vector3.left, Vector3.back, x1 - x0, false),
                (new Vector3(x1, 0, z0), Vector3.forward, Vector3.left, z1 - z0, false),
            };
            foreach (var f in faces)
            {
                int nb = Mathf.Max(1, Mathf.FloorToInt(f.L / bay));
                float bw = f.L / nb;
                var holesG = new List<Rect>(); var holesU = new List<Rect>();
                if (f.win)
                {
                    for (int i = 0; i < nb; i++)
                    {
                        float cx = bw * (i + .5f);
                        if (p.Shops) holesG.Add(Rect.MinMaxRect(cx - bw * .5f + .35f, .45f, cx + bw * .5f - .35f, gf - .7f));
                        else holesG.Add(Rect.MinMaxRect(cx - winW / 2, 1.0f, cx + winW / 2, 1.0f + Mathf.Min(winH + .4f, gf - 1.6f)));
                        for (int fl = 1; fl < floors; fl++)
                        {
                            float yb = gf + (fl - 1) * fh + .9f;
                            holesU.Add(Rect.MinMaxRect(cx - winW / 2, yb, cx + winW / 2, yb + winH));
                        }
                    }
                }
                HoleWall(b, gw, f.o, f.ex, f.F, f.L, 0f, gf, holesG, .25f, p.Gc, 0);
                HoleWall(b, p.Wall, f.o + Vector3.up * gf, f.ex, f.F, f.L, gf, H, holesU, .22f, p.Wc, 0);
                foreach (var h in holesG)
                    if (p.Shops) Shop(b, f.o, f.ex, f.F, h, .25f, p.Frame, h.center.x < bw, p.Glass);
                    else Window(b, f.o, f.ex, f.F, h, .25f, p.Frame, p.Stone, p.Lintel, p.Glass);
                foreach (var h in holesU) Window(b, f.o, f.ex, f.F, h, .22f, p.Frame, p.Stone, p.Lintel, p.Glass);
                // plinth band + belt over the ground floor
                FBox(b, "d4_flat", f.o, f.ex, f.F, f.L / 2, .2f, -.04f, new Vector3(f.L + .1f, .4f, .1f), Mul(p.Stone, .8f));
                if (floors > 1) FBox(b, "d4_trim", f.o, f.ex, f.F, f.L / 2, gf + .12f, -.06f, new Vector3(f.L + .14f, .26f, .14f), p.Stone);
                if (cornice) FBox(b, "d4_trim", f.o, f.ex, f.F, f.L / 2, H - .2f, -.12f, new Vector3(f.L + .3f, .42f, .26f), p.Stone);
            }
            Ground(b, "d4_flat", x0, z0, x1, z1, H, X("4A4C4E"));
            float t = .3f, pp = .8f;
            BoxMM(b, p.Wall, new Vector3(x0, H, z0), new Vector3(x1, H + pp, z0 + t), p.Wc);
            BoxMM(b, p.Wall, new Vector3(x0, H, z0), new Vector3(x0 + t, H + pp, z1), p.Wc);
            BoxMM(b, p.Wall, new Vector3(x0, H, z1 - t), new Vector3(x1, H + pp, z1), p.Wc);
            BoxMM(b, p.Wall, new Vector3(x1 - t, H, z0), new Vector3(x1, H + pp, z1), p.Wc);
        }

        // sign letters from T1_sign_words (row index 0..7) on a band: centre c on a -Z facing wall
        static Surf SignWords() => S.ContainsKey("sign_words") ? S["sign_words"] : Lit("sign_words", W, T("T1_sign_words_rgba.png", false, true, 2048), 1, 1, .3f, 0, 2, false, true);

        static readonly float[] SignFrac = { .147f, .092f, .083f, .126f, .109f, .168f, .175f, .086f };   // word width / 2048 (Oswald Bold 104 px)

        // sign letters from T1_sign_words (row 0..7) on a band: centre c, letter height in metres, wall normal n (default -Z)
        static void SignText(Batch b, int row, Vector3 c, float letterH, Color col, Vector3? ex = null, Vector3? n = null)
        {
            SignWords();
            Vector3 e = ex ?? Vector3.right, nn = n ?? Vector3.back;
            float w = SignFrac[row] * 1.1f, hgt = letterH * 128f / 86f, width = hgt * 16f * w;
            var uv = Rect.MinMaxRect(.5f - w / 2, 1f - (row + 1) / 8f, .5f + w / 2, 1f - row / 8f);
            Panel(b, "sign_words", c - e * width / 2 - Vector3.up * hgt / 2 + nn * .02f, e, width, hgt, nn, uv, col);
        }
    }
}
