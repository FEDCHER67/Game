using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Art.MapTexturesW86
{
    public static partial class TexW86T1
    {
        static void OneTint(string key) { var s = S[key]; s.M.SetVector("_TintRef", Vector4.one); s.Own = W; EditorUtility.SetDirty(s.M); }

        // chain-link materials (T31, also T34 / T91 / gabions): a URP Lit alpha clip + coverage-preserving mips, b / c own veil shader
        static void ChainMaterials()
        {
            if (S.ContainsKey("T31a_net")) return;
            var thin = T("T1_chainlink_rgba.png", false, true, 1024, true);
            var thick = T("T1_chainlink_thick_rgba.png", false, true, 1024, true);
            Lit("T31a_net", X("9EA3A4"), thin, 1, 1, .35f, .3f, 1, true, true);
            var sh = Shader.Find("OnlyVolunteers/W86/T1_ChainLinkVeil");
            foreach (var (key, tex, hex) in new[] { ("T31b_net", thin, "9EA3A4"), ("T31c_net", thick, "3D5A45") })
            {
                if (!sh) { Note("chain-link veil shader missing, fallback to Lit"); Lit(key, X(hex), tex, 1, 1, .35f, .3f, 1, true, true); continue; }
                var m = new Material(sh) { name = "T1_" + key, enableInstancing = true };
                m.SetTexture("_BaseMap", tex); m.SetColor("_BaseColor", X(hex));
                m.SetFloat("_VeilBoost", 1.6f); m.SetFloat("_VeilMax", .3f); m.SetFloat("_VeilStart", 1.5f); m.SetFloat("_VeilRange", 2.0f);
                if (key == "T31c_net") { m.SetFloat("_VeilBoost", 1.3f); m.SetFloat("_VeilMax", .36f); m.SetFloat("_Smoothness", .2f); m.SetFloat("_Metallic", 0f); }
                Save(key, new Surf { M = m, TU = 1, TV = 1, NoShadow = true });
            }
        }

        static void NetPanel(Batch b, string key, Vector3 p0, Vector3 p1, float y0, float y1)
        {
            Vector3 d = p1 - p0; float L = d.magnitude; Vector3 n = Vector3.Cross(Vector3.up, d.normalized);
            Q(b, key, p0 + Vector3.up * y0, p1 + Vector3.up * y0, p1 + Vector3.up * y1, p0 + Vector3.up * y1, n, new Vector2(0, y0), new Vector2(L, y0), new Vector2(L, y1), new Vector2(0, y1), W);
        }

        // ================================================================== ROUGH
        static void Rough(Transform root)
        {
            ChainMaterials();
            // T26 garages (slot rough_garage: walls metal_rusty t0 3, roof metal_rusty t0 3) + door atlas
            MapM("T26a_walls", TTB4 + "/Textures/KH3_silicate_brick_white_albedo.png", 1f, 3f);
            MapM("T26b_walls", "T1_plaster_grey_albedo.png", 3f, 3f, "T1_concrete_light_normal.png", .4f);
            MapM("T26c_walls", "T1_galv_rust_albedo.png", 1.2f, 3f, "T1_galv_rust_normal.png", .8f, .35f, .3f);
            MapM("T26a_roof", "T1_roof_tar_albedo.png", 4f, 3f, "T1_roof_tar_normal.png", .6f);
            MapM("T26b_roof", "T1_rust_sheet_albedo.png", 2f, 3f, "T1_rust_sheet_normal.png", .8f, .25f, .2f);
            MapM("T26c_roof", "T1_roof_tar_albedo.png", 4f, 3f, "T1_roof_tar_normal.png", .6f);
            MapM("doors_med", "T1_garage_doors_med_albedo.png", 1f, 1f, "T1_garage_doors_normal.png", .8f, .3f, .25f, null, 2048);
            MapM("doors_heavy", "T1_garage_doors_heavy_albedo.png", 1f, 1f, "T1_garage_doors_normal.png", .8f, .3f, .25f, null, 2048);
            var st = NewStation(root, "T26", "rough", "garage rows");
            StGround(st, "g_worn");
            Vars(st, (v, b, p) =>
            {
                string wk = "T26" + v + "_walls", rk = "T26" + v + "_roof", dk = v == "b" ? "doors_heavy" : "doors_med";
                Use("T26", v, "walls (slot rough_garage)", wk); Use("T26", v, "roof (slot rough_garage)", rk); Use("T26", v, "door leaves (atlas 4 styles x 4 colours, new geometry)", dk);
                Ground(b, "g_asph_old", -14f, -8f, 14f, -3.05f, .01f, Own("g_asph_old"));
                string[] cTint = { "D6CFC4", "BFC6CC", "C9BDA8", "B7BDB2", "D1C3B4", "C2C8C0" };
                for (int i = 0; i < 7; i++)
                {
                    float x0 = -12f + i * 3.4f, x1 = x0 + 3.4f;
                    Color wc = v == "c" ? X(cTint[i % 6]) : W;
                    Block(b, wk, wc, x0, x1, -3f, 3f, 0f, 2.6f, null, W);
                    BoxMM(b, rk, new Vector3(x0, 2.6f, -3.25f), new Vector3(x1, 2.72f, 3.1f), W);
                    Box(b, "flat", new Vector3((x0 + x1) / 2, 2.62f, -3.25f), new Vector3(3.4f, .22f, .06f), X("4A4846"));
                    int cell = (int)(Hash("G" + i + v, 3) * 16); int row = cell / 4, col = cell % 4;
                    var uv = Cell(row, col, 0, 512 * (1 - .835f), 512, 512);
                    Vector3 o = new(x0 + .4f, .02f, -3.04f);
                    Panel(b, dk, o, Vector3.right, 2.6f, 2.2f, Vector3.back, uv, W);
                    Face(b, dk, o + Vector3.right * 2.6f, Vector3.forward, .04f, Vector3.up, 2.2f, Vector3.right, W);
                    Face(b, dk, o + Vector3.forward * .04f, Vector3.back, .04f, Vector3.up, 2.2f, Vector3.left, W);
                }
            });
            AddShot(st, "eye", new Vector3(-9f, 1.7f, -10.5f), new Vector3(1f, 1.4f, -1f));
            AddShot(st, "close", new Vector3(-4f, 1.7f, -7f), new Vector3(-4f, 1.3f, -3f));
            // door prefabs (16 cells) of the medium-rust atlas
            for (int cell = 0; cell < 16; cell++)
            {
                var b = new Batch(); var uv = Cell(cell / 4, cell % 4, 0, 512 * (1 - .835f), 512, 512);
                Panel(b, "doors_med", new Vector3(-1.3f, 0, 0), Vector3.right, 2.6f, 2.2f, Vector3.back, uv, W);
                Face(b, "doors_med", new Vector3(1.3f, 0, 0), Vector3.forward, .04f, Vector3.up, 2.2f, Vector3.right, W);
                Face(b, "doors_med", new Vector3(-1.3f, 0, .04f), Vector3.back, .04f, Vector3.up, 2.2f, Vector3.left, W);
                var tmp = new GameObject("tmp"); var go = Flush(b, tmp.transform, $"T1_GarageDoor_{cell:00}");
                if (go) MakePrefab(go, $"T1_GarageDoor_{cell:00}");
                Object.DestroyImmediate(tmp);
            }
            UseAsset("T26", "a", "door prefabs", PrefabDir + "/T1_GarageDoor_00..15.prefab (2.6 x 2.2 m, pivot bottom centre of the outer face, faces -Z)");

            // T27 shop "24" + kiosks (slot rough_shop: shop walls stucco_SK3b t0 4; kiosk walls metal_painted_SK6a t0 3 -> split the slot)
            MapM("T27a_shop", "T1_tile_facade_albedo.png", 1.5f, 4f, "T1_tile_facade_normal.png", .5f, .3f, 0f, "C8B79C");
            MapM("T27b_shop", TTB4 + "/Textures/KH4_red_brick_muted_albedo.png", 1f, 4f);
            MapM("T27c_shop", "T1_plaster_grey_albedo.png", 3f, 4f, "T1_concrete_light_normal.png", .4f);
            MapM("T27a_kiosk", "T1_painted_metal_albedo.png", 2f, 3f, null, .5f, .3f, .2f, "D9D5CB");
            MapM("T27b_kiosk", "T1_metal_green_rust_albedo.png", 2f, 3f, null, .5f, .3f, .2f);
            MapM("T27c_kiosk", "T1_painted_metal_albedo.png", 2f, 3f, null, .5f, .3f, .2f, "6C7073");
            Lit("grille", W, T("T1_grille_rgba.png", false, true), 2, 2, .3f, .5f, 1, true, false);
            Emit("sign24", W, .9f, T("T1_sign_24_albedo.png"));
            st = NewStation(root, "T27", "rough", "shop 24 and kiosks");
            StGround(st, "g_worn");
            Vars(st, (v, b, p) =>
            {
                string sk = "T27" + v + "_shop", kk = "T27" + v + "_kiosk";
                Use("T27", v, "shop walls (slot rough_shop)", sk); Use("T27", v, "kiosk walls (new slot rough_kiosk)", kk);
                Use("T27", v, "window grille", "grille"); Use("T27", v, "sign 24 light box", "sign24");
                Ground(b, "g_asph_old", -12f, -9f, 12f, -.05f, .01f, Own("g_asph_old"));
                // shop 12 x 8 x 3.6 with two storefront windows + door, grilles, light box, canopy
                float x0 = -9f, x1 = 3f, z0 = 0f, z1 = 8f;
                var holes = new List<Rect> { Rect.MinMaxRect(1f, .8f, 4.4f, 2.8f), Rect.MinMaxRect(5.2f, .05f, 6.6f, 2.4f), Rect.MinMaxRect(7.4f, .8f, 10.8f, 2.8f) };
                HoleWall(b, sk, new Vector3(x0, 0, z0), Vector3.right, Vector3.forward, x1 - x0, 0, 3.6f, holes, .2f, W);
                Face(b, sk, new Vector3(x1, 0, z1), Vector3.left, x1 - x0, Vector3.up, 3.6f, Vector3.forward, W);
                Face(b, sk, new Vector3(x0, 0, z1), Vector3.back, z1 - z0, Vector3.up, 3.6f, Vector3.left, W);
                Face(b, sk, new Vector3(x1, 0, z0), Vector3.forward, z1 - z0, Vector3.up, 3.6f, Vector3.right, W);
                Ground(b, "k_tar", x0, z0, x1, z1, 3.6f, Own("k_tar"));
                foreach (var h in holes)
                {
                    bool door = h.yMin < .1f;
                    Face(b, door ? "flat" : "d4_glass", new Vector3(x0 + h.xMin, h.yMin, z0 + .2f), Vector3.right, h.width, Vector3.up, h.height, Vector3.back, door ? X("5A6068") : X("3E4B55"));
                    if (!door) Face(b, "grille", new Vector3(x0 + h.xMin, h.yMin, z0 + .08f), Vector3.right, h.width, Vector3.up, h.height, Vector3.back, X("3A3C3E"));
                    FBox(b, "flat", new Vector3(x0, 0, z0), Vector3.right, Vector3.forward, h.center.x, h.yMin - .04f, .05f, new Vector3(h.width + .1f, .08f, .3f), X("8E8A82"));
                }
                Panel(b, "sign24", new Vector3(x0 + 4.6f, 2.95f, z0 - .12f), Vector3.right, 2.8f, .7f, Vector3.back, new Rect(0, 0, 1, 1), W);
                Box(b, "flat", new Vector3(x0 + 6f, 2.95f, z0 - .06f), new Vector3(3.0f, .8f, .1f), X("2E2E30"));
                BoxMM(b, "flat_metal", new Vector3(x0 + 4.7f, 2.45f, z0 - 1.2f), new Vector3(x0 + 7.1f, 2.55f, z0), X("6C7073"));
                Box(b, "flat", new Vector3((x0 + x1) / 2, .25f, z0 - .02f), new Vector3(x1 - x0, .5f, .06f), X("6E6A63"));
                // kiosk 3 x 2.4 x 2.6 with counter window + grille
                float kx0 = 5f, kx1 = 8f, kz0 = 1f, kz1 = 3.4f;
                var kh = new List<Rect> { Rect.MinMaxRect(.4f, 1.0f, 2.6f, 2.1f) };
                HoleWall(b, kk, new Vector3(kx0, 0, kz0), Vector3.right, Vector3.forward, kx1 - kx0, 0, 2.6f, kh, .08f, W);
                Face(b, kk, new Vector3(kx1, 0, kz1), Vector3.left, kx1 - kx0, Vector3.up, 2.6f, Vector3.forward, W);
                Face(b, kk, new Vector3(kx0, 0, kz1), Vector3.back, kz1 - kz0, Vector3.up, 2.6f, Vector3.left, W);
                Face(b, kk, new Vector3(kx1, 0, kz0), Vector3.forward, kz1 - kz0, Vector3.up, 2.6f, Vector3.right, W);
                Face(b, "d4_glass", new Vector3(kx0 + .4f, 1.0f, kz0 + .08f), Vector3.right, 2.2f, Vector3.up, 1.1f, Vector3.back, X("3E4B55"));
                Face(b, "grille", new Vector3(kx0 + .4f, 1.0f, kz0 - .02f), Vector3.right, 2.2f, Vector3.up, 1.1f, Vector3.back, X("3A3C3E"));
                BoxMM(b, kk, new Vector3(kx0 - .15f, 2.6f, kz0 - .25f), new Vector3(kx1 + .15f, 2.75f, kz1 + .1f), Mul(W, .8f));
                Box(b, "flat", new Vector3((kx0 + kx1) / 2, .95f, kz0 - .15f), new Vector3(2.6f, .06f, .3f), X("8E8A82"));
                if (v == "a") Box(b, "flat", new Vector3((kx0 + kx1) / 2, 2.35f, kz0 - .01f), new Vector3(3f, .25f, .02f), X("3F5F7E"));
            });
            AddShot(st, "eye", new Vector3(-5f, 1.7f, -8f), new Vector3(-.5f, 1.7f, 2f));

            // T28 transformer booths (new slot rough_transformer; walls brick_SK3a t0 3)
            MapM("T28a_walls", TTB4 + "/Textures/KH3_silicate_brick_white_albedo.png", 1f, 3f);
            MapM("T28b_walls", "T1_plaster_whitewash_albedo.png", 3f, 3f, "T1_plaster_whitewash_normal.png", .4f);
            Lit("danger", W, T("T1_danger_plate_rgba.png", false, true, 256), 1, 1, .3f, 0, 1, false, true);
            st = NewStation(root, "T28", "rough", "transformer booths");
            StGround(st, "g_worn");
            Vars(st, (v, b, p) =>
            {
                string wk = Pick3(v, "T28a_walls", "T28b_walls", "cur_panel");
                Use("T28", v, "walls (new slot rough_transformer)", wk); Use("T28", v, "door (flat metal)", "k_metal"); Use("T28", v, "danger plate", "danger");
                Block(b, wk, wk == "cur_panel" ? Own(wk) : W, -2.1f, 2.1f, 0f, 4.2f, 0, 3f, "k_tar", Own("k_tar"), .25f);
                if (v == "b") Box(b, "flat", new Vector3(0, .35f, -.01f), new Vector3(4.22f, .7f, .04f), X("3E5F7E"));
                BoxMM(b, "k_metal", new Vector3(-.65f, 0, -.06f), new Vector3(.65f, 2.2f, 0f), X("6C7073"));
                Box(b, "flat", new Vector3(0, 1.1f, -.07f), new Vector3(.03f, 2.2f, .02f), X("3A3C3E"));
                Panel(b, "danger", new Vector3(-.2f, 1.5f, -.075f), Vector3.right, .4f, .4f, Vector3.back, new Rect(0, 0, 1, 1), W);
                foreach (float x in new[] { -1.5f, 1.5f }) Box(b, "flat", new Vector3(x, 2.4f, -.02f), new Vector3(.6f, .3f, .06f), X("4A4C4E"));
            });
            AddShot(st, "eye", new Vector3(-3.5f, 1.7f, -5.5f), new Vector3(0, 1.6f, 1.5f));

            // T29 border checkpoint building (slot generic_concrete -> new slot rough_kpp; walls concrete_panel_SK3c t0 4)
            MapM("T29a_walls", "T1_panel_p5_albedo.png", 3f, 4f, "T1_panel_p5_normal.png", .7f, .12f, 0f, null, 1024, 3.6f);
            MapM("T29b_walls", TTB4 + "/Textures/KH3_silicate_brick_white_albedo.png", 1f, 4f);
            MapM("T29c_walls", "T1_painted_metal_albedo.png", 2f, 4f, null, .5f, .3f, .2f, "D6D2C6");
            Kit("stripes", "T1_stripes_rw_albedo.png", 1f); OneTint("stripes");
            st = NewStation(root, "T29", "rough", "border checkpoint (KPP) building");
            StGround(st, "g_worn");
            Vars(st, (v, b, p) =>
            {
                string wk = "T29" + v + "_walls"; Use("T29", v, "walls (new slot rough_kpp)", wk); Use("T29", v, "barrier arm", "stripes");
                Ground(b, "g_asph_old", -12f, -10f, 12f, -.05f, .01f, Own("g_asph_old"));
                float x0 = -4f, x1 = 4f, z0 = 0f, z1 = 5f, h = 3.4f;
                var holes = new List<Rect> { Rect.MinMaxRect(.8f, 1.0f, 5.6f, 2.4f), Rect.MinMaxRect(6.4f, .05f, 7.4f, 2.3f) };
                HoleWall(b, wk, new Vector3(x0, 0, z0), Vector3.right, Vector3.forward, x1 - x0, 0, h, holes, .15f, W);
                Face(b, wk, new Vector3(x1, 0, z1), Vector3.left, x1 - x0, Vector3.up, h, Vector3.forward, W);
                var sh = new List<Rect> { Rect.MinMaxRect(1.2f, 1.0f, 3.6f, 2.4f) };
                HoleWall(b, wk, new Vector3(x0, 0, z1), Vector3.back, Vector3.right, z1 - z0, 0, h, sh, .15f, W);
                Face(b, wk, new Vector3(x1, 0, z0), Vector3.forward, z1 - z0, Vector3.up, h, Vector3.right, W);
                Window(b, new Vector3(x0, 0, z0), Vector3.right, Vector3.forward, holes[0], .15f, X("D9D5CB"), X("9A968E"), false, "glass_dark", "flat");
                Window(b, new Vector3(x0, 0, z1), Vector3.back, Vector3.right, sh[0], .15f, X("D9D5CB"), X("9A968E"), false, "glass_dark", "flat");
                Face(b, "k_metal", new Vector3(x0 + 6.4f, .05f, z0 + .15f), Vector3.right, 1f, Vector3.up, 2.25f, Vector3.back, X("6C7073"));
                BoxMM(b, "k_conc", new Vector3(x0 - .3f, h, z0 - .3f), new Vector3(x1 + .3f, h + .3f, z1 + .3f), Own("k_conc"));
                BoxMM(b, "k_conc", new Vector3(x0 + 5.6f, 2.5f, z0 - 1.4f), new Vector3(x1 + .2f, 2.62f, z0), Own("k_conc"));
                if (v == "a") Box(b, "flat", new Vector3(0, 3.05f, z0 - .02f), new Vector3(8f, .25f, .03f), X("3E5F7E"));
                // barrier
                Box(b, "flat_metal", new Vector3(-6.5f, .55f, -3f), new Vector3(.4f, 1.1f, .4f), X("C2332C"));
                var s2 = S["stripes"];
                Q(b, "stripes", new Vector3(-6.3f, .95f, -3.05f), new Vector3(1.5f, .95f, -3.05f), new Vector3(1.5f, 1.07f, -3.05f), new Vector3(-6.3f, 1.07f, -3.05f), Vector3.back,
                    Vector2.zero, new Vector2(7.8f, 0), new Vector2(7.8f, .12f), new Vector2(0, .12f), W);
                Box(b, "stripes", new Vector3(-2.4f, 1.01f, -3f), new Vector3(7.8f, .12f, .08f), W);
            });
            AddShot(st, "eye", new Vector3(-6.5f, 1.7f, -7.5f), new Vector3(-.5f, 1.8f, 2f));

            // T30 sliding gates + posts (painted metal SK6a)
            MapM("T30b_gate", "T1_metal_green_rust_albedo.png", 2f, 3f, null, .5f, .3f, .3f);
            MapM("T30c_gate", "T1_galv_rust_albedo.png", 1.2f, 3f, "T1_galv_rust_normal.png", .7f, .35f, .3f);
            st = NewStation(root, "T30", "rough", "sliding gate, rail, posts");
            StGround(st, "g_worn");
            Vars(st, (v, b, p) =>
            {
                string gk = Pick3(v, "cur_metal", "T30b_gate", "T30c_gate"); Use("T30", v, "gate / rail / posts", gk);
                Color c = v == "a" ? Own(gk) : W;
                Ground(b, "g_asph_old", -8f, -6f, 8f, 6f, .01f, Own("g_asph_old"));
                BoxMM(b, gk, new Vector3(-3f, .15f, -.04f), new Vector3(3f, 2.3f, .04f), c);
                foreach (float x in new[] { -3f, 0f, 3f }) Box(b, gk, new Vector3(x, 1.22f, -.08f), new Vector3(.08f, 2.15f, .08f), Mul(c, .85f));
                foreach (float y in new[] { .2f, 1.22f, 2.25f }) Box(b, gk, new Vector3(0, y, -.08f), new Vector3(6f, .08f, .08f), Mul(c, .85f));
                Box(b, gk, new Vector3(1.5f, .05f, 0), new Vector3(10f, .08f, .08f), Mul(c, .7f));
                foreach (float x in new[] { -3.3f, 3.3f, 9.3f }) Box(b, gk, new Vector3(x, 1.3f, 0), new Vector3(.25f, 2.6f, .25f), c);
            });
            AddShot(st, "eye", new Vector3(-3f, 1.7f, -7f), new Vector3(.5f, 1.2f, 0f));

            // T31 border chain-link (Fence_04-border-fence*: fence_net, 1 m tile, 3 m net); also posts + barbed strands
            st = NewStation(root, "T31", "rough", "border chain-link (visibility at 30-60 m)");
            StGround(st, "g_worn");
            Vars(st, (v, b, p) =>
            {
                string nk = "T31" + v + "_net"; Use("T31", v, "net (fence_net users: border, port, football box)", nk);
                float L = 90f;
                for (float x = -10f; x < L; x += 3f)
                {
                    NetPanel(b, nk, new Vector3(x, 0, 0), new Vector3(x + 3f, 0, 0), 0f, 3.0f);
                    Cyl(b, "flat_metal", new Vector3(x, 0, 0), new Vector3(x, 3.3f, 0), .045f, 8, X("7E8384"));
                }
                Cyl(b, "flat_metal", new Vector3(-10f, 2.98f, 0), new Vector3(L, 2.98f, 0), .025f, 6, X("7E8384"), false);
                foreach (float y in new[] { 3.12f, 3.26f }) Cyl(b, "flat_metal", new Vector3(-10f, y, -.12f), new Vector3(L, y, -.12f), .006f, 4, X("5E6264"), false);
            });
            AddShot(st, "along", new Vector3(-6f, 1.7f, -7f), new Vector3(40f, 1.3f, 0f));
            AddShot(st, "far40", new Vector3(30f, 1.7f, -40f), new Vector3(30f, 1.5f, 0f));

            // T33 concrete panel fence (W85_concrete_panel_SK3c, 4 m tile; fence h 2.2 -> quad 2.5 m tall incl. 0.3 m buried)
            MapM("T33b_panel", "T1_po2_rhombus_albedo.png", 4f, 4f, "T1_po2_rhombus_normal.png", 1f, .12f, 0f, null, 1024, 2.5f);
            MapM("T33c_panel", "T1_po2_ribbed_albedo.png", 4f, 4f, "T1_po2_ribbed_normal.png", 1f, .12f, 0f, null, 1024, 2.5f);
            st = NewStation(root, "T33", "rough", "concrete panel fence");
            StGround(st, "g_worn");
            Vars(st, (v, b, p) =>
            {
                string k = Pick3(v, "cur_panel", "T33b_panel", "T33c_panel"); Use("T33", v, "fence panels (Fence_04-fence-*)", k);
                Color c = v == "a" ? Own(k) : W; var s = S[k];
                for (int i = 0; i < 5; i++)
                {
                    float x0 = -8f + i * 4f;
                    foreach (var (z, n) in new[] { (0f, Vector3.back), (.16f, Vector3.forward) })
                        Q(b, k, new Vector3(x0, -.3f, z), new Vector3(x0 + 4f, -.3f, z), new Vector3(x0 + 4f, 2.2f, z), new Vector3(x0, 2.2f, z), n,
                            new Vector2(0, 0), new Vector2(4f / s.TU, 0), new Vector2(4f / s.TU, 2.5f / s.TV), new Vector2(0, 2.5f / s.TV), c);
                    Box(b, "k_conc", new Vector3(x0, 1.15f, .08f), new Vector3(.24f, 2.4f, .3f), Own("k_conc"));
                }
            });
            AddShot(st, "eye", new Vector3(-7f, 1.7f, -7f), new Vector3(2f, 1.1f, 0f));

            // T34 football box: boards 1.2 m + net to 4 m
            MapM("T34a_boards", "T1_boards_green_chipped_albedo.png", 2f, 3f, "T1_boards_green_chipped_normal.png", .7f);
            MapM("T34b_boards", "T1_painted_metal_albedo.png", 2f, 3f, null, .5f, .3f, .2f, "3F5F7E");
            MapM("T34c_boards", "T1_boards_grey_albedo.png", 2f, 3f, "T1_boards_grey_normal.png", .7f);
            st = NewStation(root, "T34", "rough", "football box: boards + net");
            StGround(st, "g_worn");
            Vars(st, (v, b, p) =>
            {
                string bk = "T34" + v + "_boards"; Use("T34", v, "boards (Fence_04-football-box_board)", bk); Use("T34", v, "net", "T31b_net");
                Ground(b, "g_asph_old", -12f, 0f, 12f, 20f, .01f, Own("g_asph_old"));
                foreach (var (a, c2) in new[] { (new Vector3(-12, 0, 0), new Vector3(12, 0, 0)), (new Vector3(-12, 0, 0), new Vector3(-12, 0, 20)) })
                {
                    Vector3 d = c2 - a; float L = d.magnitude; Vector3 n = Vector3.Cross(Vector3.up, d.normalized); var s = S[bk];
                    foreach (var nn in new[] { n, -n })
                        Q(b, bk, a, c2, c2 + Vector3.up * 1.2f, a + Vector3.up * 1.2f, nn, Vector2.zero, new Vector2(L / s.TU, 0), new Vector2(L / s.TU, 1.2f / s.TV), new Vector2(0, 1.2f / s.TV), W);
                    NetPanel(b, "T31b_net", a, c2, 1.2f, 4f);
                    for (float t = 0; t <= L; t += 3f) Cyl(b, "flat_metal", a + d.normalized * t, a + d.normalized * t + Vector3.up * 4.05f, .05f, 8, X("4A4E50"));
                }
            });
            AddShot(st, "eye", new Vector3(-6.5f, 1.6f, -4.5f), new Vector3(-10f, 1.2f, 3f));

            // T36 floodlight masts (SK6a)
            MapM("T36b_mast", "T1_metal_grey_rust_albedo.png", 2f, 3f, null, .5f, .3f, .3f);
            MapM("T36c_mast", "T1_painted_metal_albedo.png", 2f, 3f, null, .5f, .3f, .3f, "3A3D40");
            st = NewStation(root, "T36", "rough", "floodlight masts");
            StGround(st, "g_worn");
            Vars(st, (v, b, p) =>
            {
                string k = Pick3(v, "cur_metal", "T36b_mast", "T36c_mast"); Use("T36", v, "mast", k);
                Color c = v == "a" ? Own(k) : W;
                foreach (float x in new[] { -3f, 5f })
                {
                    Cyl(b, k, new Vector3(x, 0, 2f), new Vector3(x, 9f, 2f), .14f, 10, c, true, .09f);
                    Box(b, k, new Vector3(x, 9.1f, 1.9f), new Vector3(1.4f, .5f, .35f), c);
                    Face(b, "flat_gloss", new Vector3(x - .6f, 8.9f, 1.72f), Vector3.right, 1.2f, Vector3.up, .4f, Vector3.back, X("D8D8D0"));
                }
            });
            AddShot(st, "eye", new Vector3(-5f, 1.7f, -7f), new Vector3(1f, 5f, 2f));

            // StreetKit / MP palette props of the Rough: b faded Soviet, c dark rusty
            Color fb = new(.84f, .85f, .86f), fc = new(.74f, .68f, .62f);
            PropStation(root, "T37", "rough", "playgrounds", new[] { MPF + "PLAYGROUND/play_swings.prefab", MPF + "PLAYGROUND/play_slide.prefab", MPF + "PLAYGROUND/play_carousel.prefab", MPF + "PLAYGROUND/play_sandbox.prefab" }, "g_worn", fb, fc, 4.5f);
            PropStation(root, "T38", "rough", "skips and bins", new[] { MPF + "BINS/garbage_container_open.prefab", MPF + "BINS/trashbin_tipping.prefab", MPF + "BINS/garbage_container_closed.prefab" }, "g_worn", fb, fc, 2.6f);
            PropStation(root, "T39", "rough", "street lamps", new[] { MPF + "LAMPS/lamp_soviet.prefab", MPF + "LAMPS/lamp_soviet.prefab" }, "g_worn", fb, fc, 5f, 4.5f);
            PropStation(root, "T40", "rough", "parked cars", new[] { MPF + "CARS/car_hatchback.prefab", MPF + "CARS/car_hatchback.prefab" }, "g_worn", fb, fc, 5f);
            PropStation(root, "T41", "rough", "benches and concrete urns", new[] { MPF + "BENCHES/bench_soviet.prefab", MPF + "BENCHES/bench_soviet_broken.prefab", MPF + "BINS/trashbin_concrete.prefab" }, "g_worn", fb, fc, 2.8f);

            // T42 club neon heart (box -> emissive quad on the wall)
            foreach (string v in VS)
            {
                var tex = T($"T1_neon_heart_{v}_rgba.png", false, true, 512);
                var col = v == "a" ? X("FF4696") : v == "b" ? X("FF3232") : X("D23CFF");
                var s = Lit("T42" + v + "_neon", W, tex, 1, 1, .3f, 0, 2, false, true);
                s.M.EnableKeyword("_EMISSION"); s.M.SetTexture("_EmissionMap", tex); s.M.SetColor("_EmissionColor", W * 6f);
                s.M.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None; EditorUtility.SetDirty(s.M);
            }
            Ref("kh2", TTB4 + "/Materials/TT_KH2.mat", 6.4f, 5.6f);
            st = NewStation(root, "T42", "rough", "club neon heart");
            StGround(st, "g_worn");
            Vars(st, (v, b, p) =>
            {
                string k = "T42" + v + "_neon"; Use("T42", v, "neon (quad on the club wall, emissive)", k);
                Face(b, "kh2", new Vector3(-6f, 0, 0), Vector3.right, 12f, Vector3.up, 6f, Vector3.back, Own("kh2"));
                Box(b, "flat", new Vector3(0, 3.2f, -.03f), new Vector3(1.9f, 1.8f, .05f), X("1E1E22"));
                Panel(b, k, new Vector3(-.9f, 2.3f, -.07f), Vector3.right, 1.8f, 1.8f, Vector3.back, new Rect(0, 0, 1, 1), W);
                Box(b, "flat", new Vector3(1.6f, 1.1f, -.05f), new Vector3(1.1f, 2.2f, .08f), X("2C2E30"));
            });
            AddShot(st, "eye", new Vector3(-2f, 1.7f, -6f), new Vector3(0, 2.8f, 0));

            // T124 road wear (on the Rough ring: old asphalt): a GPT cleaned, b own, c own heavy
            DecalMaterials();
            st = NewStation(root, "T124", "rough", "road wear: cracks, patches, manholes, oil");
            StGround(st, "g_worn");
            Vars(st, (v, b, p) =>
            {
                Ground(b, "g_asph_old", -4f, -10f, 4f, 40f, .01f, Own("g_asph_old"));
                if (v == "a")
                {
                    Use("T124", v, "wear", "dec_gpt_wear"); Use("T124", v, "utility", "dec_gpt_util"); Use("T124", v, "oil", "dec_gpt_oil");
                    // GPT RoadWear / StreetUtility / OilTar elements (ATLAS_UV.json, Unity bottom-left uv)
                    Decal(b, "dec_gpt_wear", new Vector3(-1.2f, .025f, 2f), 3.5f, 1.5f, 0, Rect.MinMaxRect(.1743f, .8555f, .3262f, .8999f), W);
                    Decal(b, "dec_gpt_wear", new Vector3(1.4f, .025f, 7f), 3.0f, 1.5f, 30, Rect.MinMaxRect(.6743f, .8423f, .8262f, .9131f), W);
                    Decal(b, "dec_gpt_wear", new Vector3(-.5f, .025f, 12f), 2.5f, 1.5f, 0, Rect.MinMaxRect(.6787f, .5811f, .8198f, .6724f), W);
                    Decal(b, "dec_gpt_util", new Vector3(1.2f, .025f, 4f), .8f, .8f, 0, Rect.MinMaxRect(.0635f, .7295f, .2705f, .9365f), W);
                    Decal(b, "dec_gpt_util", new Vector3(3.5f, .025f, 9f), .8f, .55f, 0, Rect.MinMaxRect(.396f, .7593f, .6045f, .9072f), W);
                    Decal(b, "dec_gpt_oil", new Vector3(-1.8f, .025f, 9f), 1.4f, 1.2f, 0, Rect.MinMaxRect(.0625f, .6709f, .2695f, .8467f), W);
                    Decal(b, "dec_gpt_wear", new Vector3(0f, .025f, 17f), 2.5f, 1.3f, 0, Rect.MinMaxRect(.187f, .0884f, .3262f, .1631f), W);
                }
                else
                {
                    string k = v == "b" ? "dec_wear_b" : "dec_wear_c"; Use("T124", v, "wear / utility / oil atlas", k);
                    Decal(b, k, new Vector3(-1.5f, .025f, 2f), 2f, 2f, 0, Cell(0, 0, 0, 0, 512, 512), W);
                    Decal(b, k, new Vector3(1.6f, .025f, 7f), 2f, 2f, 30, Cell(0, 1, 0, 0, 512, 512), W);
                    Decal(b, k, new Vector3(-.5f, .025f, 12f), 3f, 2f, 0, Cell(1, 0, 0, 0, 512, 512), W);
                    Decal(b, k, new Vector3(1.2f, .025f, 4f), 1.0f, 1.0f, 0, Cell(2, 0, 0, 0, 512, 512), W);
                    Decal(b, k, new Vector3(3.6f, .025f, 9f), 1.0f, 1.0f, 0, Cell(2, 1, 0, 0, 512, 512), W);
                    Decal(b, k, new Vector3(-1.8f, .025f, 9f), 1.6f, 1.6f, 0, Cell(1, 2, 0, 0, 512, 512), W);
                    Decal(b, k, new Vector3(0f, .025f, 18f), .9f, 6f, 0, Cell(2, 2, 0, 0, 512, 512), W);
                    if (v == "c")
                    {
                        Decal(b, k, new Vector3(1.5f, .025f, 15f), 2.4f, 2.4f, 0, Cell(3, 0, 0, 0, 512, 512), W);
                        Decal(b, k, new Vector3(-2f, .025f, 16f), 2.6f, 2.6f, 0, Cell(3, 1, 0, 0, 512, 512), W);
                        Decal(b, k, new Vector3(2f, .025f, 1f), 2.2f, 2.2f, 0, Cell(3, 3, 0, 0, 512, 512), W);
                    }
                }
            });
            AddShot(st, "eye", new Vector3(-1.2f, 1.6f, -1.5f), new Vector3(.5f, 0f, 7f));

            // T132 steppe beyond the border fence (Steppe_far plane now / W86 backdrop terrain): a current, b / c own macro
            MapM("T132b_steppe", "T1_steppe_macro_albedo.png", 64f, 64f);
            MapM("T132c_steppe", "T1_steppe_macro_warm_albedo.png", 64f, 64f);
            Ref("cur_steppe", GEN + "/Materials/W85_steppe_far.mat", 1f, 1f);
            st = NewStation(root, "T132", "rough", "steppe beyond the border fence");
            StGround(st, "g_worn");
            Vars(st, (v, b, p) =>
            {
                string k = Pick3(v, "cur_steppe", "T132b_steppe", "T132c_steppe"); Use("T132", v, "steppe surface (Steppe_far / backdrop terrain layer)", k);
                float R = 900f;
                if (v == "a")
                    Q(b, k, new Vector3(-R, .05f, 6f), new Vector3(R, .05f, 6f), new Vector3(R, .05f, R), new Vector3(-R, .05f, R), Vector3.up,
                        Vector2.zero, new Vector2(2 * R / 4800f * 600f, 0), new Vector2(2 * R / 4800f * 600f, (R - 6f) / 2400f * 300f), new Vector2(0, (R - 6f) / 2400f * 300f), W);
                else Ground(b, k, -R, 6f, R, R, .05f, W);
                for (float x = -60f; x < 60f; x += 3f)
                {
                    NetPanel(b, "T31b_net", new Vector3(x, 0, 3f), new Vector3(x + 3f, 0, 3f), 0f, 3f);
                    Cyl(b, "flat_metal", new Vector3(x, 0, 3f), new Vector3(x, 3.3f, 3f), .045f, 8, X("7E8384"));
                }
            });
            AddShot(st, "eye", new Vector3(0f, 1.7f, -4f), new Vector3(0f, 1.2f, 60f));
            AddShot(st, "steppe", new Vector3(0f, 2.5f, 10f), new Vector3(8f, 0f, 40f));
        }

        // decal materials (mesh decals: URP Lit transparent, receive shadows, no shadow casting)
        static void DecalMaterials()
        {
            if (S.ContainsKey("dec_marks_b")) return;
            Lit("dec_gpt_marks", W, T("T1_gpt_RoadMarks_clean_rgba.png", false, true, 2048), 1, 1, .2f, 0, 2, false, true);
            Lit("dec_gpt_wear", W, T("T1_gpt_RoadWear_clean_rgba.png", false, true, 2048), 1, 1, .2f, 0, 2, false, true);
            Lit("dec_gpt_util", W, T("T1_gpt_StreetUtility_clean_rgba.png", false, true, 2048), 1, 1, .3f, .2f, 2, false, true);
            Lit("dec_gpt_oil", W, T("T1_gpt_OilTar_clean_rgba.png", false, true, 1024), 1, 1, .6f, 0, 2, false, true);
            Lit("dec_marks_b", W, T("T1_roadmarks_clean_rgba.png", false, true, 2048), 1, 1, .25f, 0, 2, false, true);
            Lit("dec_marks_c", W, T("T1_roadmarks_worn_rgba.png", false, true, 2048), 1, 1, .2f, 0, 2, false, true);
            var wn = T("T1_roadwear_normal.png", true, false, 2048);
            Lit("dec_wear_b", W, T("T1_roadwear_b_rgba.png", false, true, 2048), 1, 1, .25f, 0, 2, false, true, wn);
            Lit("dec_wear_c", W, T("T1_roadwear_c_rgba.png", false, true, 2048), 1, 1, .25f, 0, 2, false, true, wn);
            Lit("dec_foam_gpt", W, T("T1_gpt_shore_foam_clean_rgba.png", false, true, 1024), 8, 1, .3f, 0, 2, false, true);
            Lit("dec_foam_b", W, T("T1_shore_foam_b_rgba.png", false, true, 1024), 8, 1, .3f, 0, 2, false, true);
        }
    }
}
