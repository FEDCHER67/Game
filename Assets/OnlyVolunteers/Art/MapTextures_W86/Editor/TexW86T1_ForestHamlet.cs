using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Art.MapTexturesW86
{
    public static partial class TexW86T1
    {
        // ================================================================== FOREST
        static void Forest(Transform root)
        {
            // T01 wagon of base 1 (slot forest_wagon: walls metal_rusty t0 3 m, roof metal_rusty t0 3 m)
            MapM("T01a_walls", "T1_boards_red_albedo.png", 2f, 3f, "T1_boards_red_normal.png", .7f);
            MapM("T01b_walls", "T1_boards_green_albedo.png", 2f, 3f, "T1_boards_green_normal.png", .7f);
            MapM("T01c_walls", "T1_boards_grey_albedo.png", 2f, 3f, "T1_boards_grey_normal.png", .7f);
            MapM("T01a_roof", "T1_roof_tar_albedo.png", 4f, 3f, "T1_roof_tar_normal.png", .6f);
            MapM("T01b_roof", "T1_rust_sheet_albedo.png", 2f, 3f, "T1_rust_sheet_normal.png", .8f, .25f, .2f);
            MapM("T01c_roof", "T1_galv_rust_albedo.png", 1.2f, 3f, "T1_galv_rust_normal.png", .8f, .35f, .3f);
            var st = NewStation(root, "T01", "forest", "wagon of base 1");
            StGround(st, "g_forest");
            Vars(st, (v, b, p) =>
            {
                string wk = "T01" + v + "_walls", rk = "T01" + v + "_roof";
                Use("T01", v, "walls (slot forest_wagon)", wk); Use("T01", v, "roof (slot forest_wagon)", rk);
                float L = 16f, Wd = 3.2f, y0 = 1.05f, y1 = 3.45f;
                float x0 = -L / 2, x1 = L / 2, z0 = -Wd / 2, z1 = Wd / 2;
                // doors in the long side: two sliding doors (holes darkened) + door leaves proud of the wall
                var holes = new List<Rect> { Rect.MinMaxRect(L / 2 - 1.0f, y0 + .05f, L / 2 + 1.0f, y0 + 2.0f) };
                HoleWall(b, wk, new Vector3(x0, 0, z0), Vector3.right, Vector3.forward, L, y0, y1, holes, .05f, W);
                Face(b, "flat", new Vector3(-1.0f, y0 + .05f, z0 + .05f), Vector3.right, 2f, Vector3.up, 1.95f, Vector3.back, X("1E1C1A"));
                FBox(b, wk, new Vector3(x0, 0, z0), Vector3.right, Vector3.forward, L / 2 + 1.7f, y0 + 1.0f, -.06f, new Vector3(2.1f, 2.1f, .06f), Mul(W, .92f));
                FBox(b, "flat", new Vector3(x0, 0, z0), Vector3.right, Vector3.forward, L / 2, y0 + 2.12f, -.08f, new Vector3(5.4f, .08f, .08f), X("2A2928"));
                Face(b, wk, new Vector3(x1, y0, z1), Vector3.left, L, Vector3.up, y1 - y0, Vector3.forward, W);
                Face(b, wk, new Vector3(x0, y0, z1), Vector3.back, Wd, Vector3.up, y1 - y0, Vector3.left, W);
                Face(b, wk, new Vector3(x1, y0, z0), Vector3.forward, Wd, Vector3.up, y1 - y0, Vector3.right, W);
                // corner / frame posts (darker boards), small vents
                foreach (float x in new[] { x0, -L / 4, L / 4, x1 })
                    foreach (float z in new[] { z0, z1 })
                        Box(b, "flat", new Vector3(x, (y0 + y1) / 2, z), new Vector3(.12f, y1 - y0, .12f), X("2C2A28"));
                foreach (float x in new[] { -L / 2 + 1.2f, L / 2 - 1.2f })
                    Face(b, "flat", new Vector3(x - .3f, y1 - .65f, z0 - .01f), Vector3.right, .6f, Vector3.up, .35f, Vector3.back, X("1E1C1A"));
                // barrel roof (arc, 10 segments), ends closed with the wall key
                int n = 10; float rise = .45f, over = .15f; var rs = S[rk];
                for (int i = 0; i < n; i++)
                {
                    float a0 = (float)i / n, a1 = (float)(i + 1) / n;
                    float za = Mathf.Lerp(z0 - over, z1 + over, a0), zb = Mathf.Lerp(z0 - over, z1 + over, a1);
                    float ya = y1 + rise * (1 - Mathf.Pow(2 * a0 - 1, 2)), yb = y1 + rise * (1 - Mathf.Pow(2 * a1 - 1, 2));
                    float s0 = a0 * (Wd + 2 * over), s1 = a1 * (Wd + 2 * over);
                    var nn = Vector3.Cross(new Vector3(1, 0, 0), new Vector3(0, yb - ya, zb - za)).normalized; if (nn.y < 0) nn = -nn;
                    Q(b, rk, new Vector3(x0 - over, ya, za), new Vector3(x1 + over, ya, za), new Vector3(x1 + over, yb, zb), new Vector3(x0 - over, yb, zb), nn,
                        new Vector2(0, s0 / rs.TV), new Vector2((L + 2 * over) / rs.TU, s0 / rs.TV), new Vector2((L + 2 * over) / rs.TU, s1 / rs.TV), new Vector2(0, s1 / rs.TV), W);
                    foreach (float x in new[] { x0, x1 })
                        TriN(b, wk, new Vector3(x, y1, za), new Vector3(x, ya, za), new Vector3(x, yb, zb), x == x0 ? Vector3.left : Vector3.right, Vector2.zero, new Vector2(0, (ya - y1) / 3f), new Vector2((zb - za) / 3f, (yb - y1) / 3f), W);
                }
                // underframe, wheelsets, rails
                Box(b, "flat_metal", new Vector3(0, y0 - .2f, 0), new Vector3(L - .6f, .35f, Wd - .4f), X("2B2A29"));
                foreach (float x in new[] { -L / 2 + 2.2f, -L / 2 + 4.0f, L / 2 - 4.0f, L / 2 - 2.2f })
                    foreach (float z in new[] { -.75f, .75f })
                        Cyl(b, "flat_metal", new Vector3(x, .46f, z - .07f), new Vector3(x, .46f, z + .07f), .45f, 14, X("3A3634"));
                foreach (float z in new[] { -.75f, .75f }) Box(b, "flat_metal", new Vector3(0, .07f, z), new Vector3(L + 8f, .14f, .07f), X("5E4A3E"));
                for (float x = -L / 2 - 3.6f; x < L / 2 + 4f; x += .65f) Box(b, "k_boards_tar", new Vector3(x, .03f, 0), new Vector3(.24f, .14f, 2.4f), Own("k_boards_tar"));
                // step ladder at the door
                for (int k = 0; k < 3; k++) Box(b, "k_boards_grey", new Vector3(1.0f, .2f + k * .3f, z0 - .45f + k * .12f), new Vector3(1.4f, .06f, .3f), Own("k_boards_grey"));
            });
            AddShot(st, "eye", new Vector3(-11f, 2.2f, -12f), new Vector3(1f, 2.2f, 0f));
            AddShot(st, "close", new Vector3(2.5f, 1.7f, -5.2f), new Vector3(.5f, 2.2f, 0f));

            // T03 log bench (box -> log model): bark / birch / debarked; end rings
            Kit("T03a_log", "T1_bark_brown_albedo.png", 1f, "T1_bark_brown_normal.png", .9f);
            Kit("T03b_log", "T1_bark_birch_albedo.png", 1f, "T1_bark_birch_normal.png", .7f);
            Kit("T03c_log", "T1_log_debarked_albedo.png", 1f, null);
            MapM("logend", "T1_logend_albedo.png", 1f, 1f);
            st = NewStation(root, "T03", "forest", "log bench at the campfire");
            StGround(st, "g_forest");
            Vars(st, (v, b, p) =>
            {
                string k = "T03" + v + "_log"; Use("T03", v, "log bark", k); Use("T03", v, "log ends", "logend");
                Cyl(b, k, new Vector3(-2.9f, .27f, 0), new Vector3(2.9f, .27f, 0), .27f, 14, Own(k), true, .24f, null, new Rect(0, 0, 1, 1), "logend");
                Cyl(b, k, new Vector3(-1.2f, .22f, 1.6f), new Vector3(1.4f, .24f, 2.3f), .22f, 12, Own(k), true, -1f, null, new Rect(0, 0, 1, 1), "logend");
                // campfire ring stand-in (dark ash disc + stones) for context
                Cyl(b, "flat", new Vector3(0, 0, 3.6f), new Vector3(0, .02f, 3.6f), 1.1f, 20, X("3B3734"));
                for (int i = 0; i < 12; i++) { float a = i * Mathf.PI * 2 / 12; Box(b, "rock", new Vector3(Mathf.Cos(a) * 1.25f, .12f, 3.6f + Mathf.Sin(a) * 1.25f), new Vector3(.35f, .25f, .3f), Own("rock"), i * 31f); }
            });
            AddShot(st, "eye", new Vector3(-2.2f, 1.5f, -2.6f), new Vector3(.2f, .3f, .5f));

            // T04 collapsed rail tunnel mouth: portal materials = T127 family, rock fall
            TunnelPortalMaterials();
            st = NewStation(root, "T04", "forest", "collapsed rail tunnel mouth");
            StGround(st, "g_forest");
            Vars(st, (v, b, p) =>
            {
                string k = PortalKey(v); Use("T04", v, "portal walls (01-tunnel-mouth)", k);
                // slope (earth) behind the portal
                Q(b, "g_forest", new Vector3(-14, 0, 1), new Vector3(14, 0, 1), new Vector3(14, 9, 9), new Vector3(-14, 9, 9), new Vector3(0, .7f, -.7f),
                    new Vector2(0, 0), new Vector2(3.5f, 0), new Vector2(3.5f, 1.5f), new Vector2(0, 1.5f), Own("g_forest"));
                float wdt = 10f, ht = 8f;
                var holes = new List<Rect> { Rect.MinMaxRect(wdt / 2 - 2.6f, 0, wdt / 2 + 2.6f, 5.2f) };
                HoleWall(b, k, new Vector3(-wdt / 2, 0, 1f), Vector3.right, Vector3.forward, wdt, 0, ht, holes, 1.2f, Own(k));
                Face(b, "flat", new Vector3(-2.6f, 0, 2.2f), Vector3.right, 5.2f, Vector3.up, 5.2f, Vector3.back, X("141312"));
                Box(b, k, new Vector3(0, ht + .25f, .8f), new Vector3(wdt + .6f, .5f, .9f), Mul(Own(k), .95f));
                // boulders filling the mouth
                var rnd = new System.Random(4);
                for (int i = 0; i < 14; i++)
                {
                    float x = (float)(rnd.NextDouble() * 4.6 - 2.3), y = (float)(rnd.NextDouble() * 2.6), s = (float)(.6 + rnd.NextDouble() * .9);
                    Box(b, "rock", new Vector3(x, y * .7f + s * .4f, 1.2f - (float)rnd.NextDouble() * 1.4f), new Vector3(s * 1.2f, s, s), Own("rock"), (float)rnd.NextDouble() * 90f);
                }
            });
            AddShot(st, "eye", new Vector3(-4f, 1.7f, -9f), new Vector3(0, 3f, 1f));

            // T05 swamp: W85_water_swamp copies without the white rim; b with duckweed; c peat brown
            string sw = GEN + "/Materials/W85_water_swamp.mat";
            void NoRim(Material m, string deep, string shallow)
            {
                m.SetColor("_Color_Deep", X(deep)); m.SetColor("_Color_Shallow", X(shallow)); m.SetColor("_OV_ColorMid", Color.Lerp(X(deep), X(shallow), .5f));
                m.SetColor("_OV_ShoreColor", X(shallow)); m.SetFloat("_OV_IntersectionWidth", 0f); m.SetFloat("_OV_InnerWidth", 0f); m.SetFloat("_OV_OuterStrength", 0f);
                var fc = m.GetColor("_OV_FoamColor"); fc.a = 0f; m.SetColor("_OV_FoamColor", fc); m.SetFloat("_OV_CrestFoam", 0f); m.SetFloat("_OV_SoftContact", .35f);
                m.SetFloat("_OV_ShoreTintStrength", 0f);
            }
            CopyOf("T05a_water", sw, m => NoRim(m, "1B2418", "2E3A26"));
            CopyOf("T05b_water", sw, m => NoRim(m, "1B2418", "2E3A26"));
            CopyOf("T05c_water", sw, m => { NoRim(m, "1E1812", "3A2E22"); m.SetFloat("_OV_Clarity", .2f); });
            Lit("T05b_duckweed", W, T("T1_duckweed_rgba.png", false, true), 4f, 4f, .2f, 0f, 1, false, true);
            Kit("bank_mud", "T1_bank_mud_albedo.png", 4f, "T1_bank_mud_normal.png", .6f, .35f);
            Kit("bank_pebbles", "T1_bank_pebbles_albedo.png", 3f, "T1_bank_pebbles_normal.png", .8f, .25f);
            st = NewStation(root, "T05", "forest", "swamp");
            PondGround(st, "g_forest", 13f);
            Vars(st, (v, b, p) =>
            {
                string wk = "T05" + v + "_water"; Use("T05", v, "water (Water_Bog_*)", wk);
                PondBank(b, "bank_mud", 13f);
                Ground(b, wk, -13, -13, 13, 13, -.25f, W);
                if (v == "b")
                {
                    Use("T05", v, "duckweed overlay plane (new, +2 cm)", "T05b_duckweed");
                    Ground(b, "T05b_duckweed", -12.5f, -12.5f, 12.5f, 12.5f, -.23f, W);
                }
            });
            AddShot(st, "eye", new Vector3(-6f, 1.7f, -17f), new Vector3(2f, -.3f, 2f));

            // T06 forest lake bank (shared bank family with T22 / T129 / T131): a terrain only, b wet mud, c pebbles
            st = NewStation(root, "T06", "forest", "lake bank");
            PondGround(st, "g_forest", 13f);
            Vars(st, (v, b, p) =>
            {
                string bk = Pick3(v, "g_forest", "bank_mud", "bank_pebbles"); if (v == "a") UseAsset("T06", v, "bank strip", "none (terrain unchanged)"); else Use("T06", v, "bank material (test mesh; map: terrain layer below)", bk);
                Use("T06", v, "water (unchanged)", "water_flow");
                PondBank(b, bk, 13f);
                Ground(b, "water_flow", -13, -13, 13, 13, -.25f, W);
            });
            AddShot(st, "eye", new Vector3(-7f, 1.7f, -17f), new Vector3(2f, -.4f, 0f));

            // T133 forest trees (terrain prototypes; tints of the approved pines for b / c)
            st = NewStation(root, "T133", "forest", "forest trees");
            StGround(st, "g_forest");
            foreach (string v in VS)
            {
                Color? t = v == "a" ? null : v == "b" ? new Color(1f, .95f, .82f) : new Color(.82f, .88f, .86f);
                int i = 0;
                foreach (var (path, x, z) in new[] { ("Pine_A_v04", -4f, 4f), ("Pine_B_v04", 3f, 7f), ("Pine_C_v04", 9f, 2f), ("Pine_A_v04", -10f, 10f), ("Pine_B_v04", 1f, 16f) })
                    Prop("Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Prefabs/" + path + ".prefab", st.V[v], new Vector3(x, 0, z), 40f * i++, 1f, t, "T133" + v);
            }
            UseAsset("T133", "a", "trees", "Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Prefabs/Pine_*_v04.prefab (unchanged)");
            UseAsset("T133", "b", "trees", MatDir + "/PropTint/*_b.mat (warmer tint copies)");
            UseAsset("T133", "c", "trees", MatDir + "/PropTint/*_c.mat (cooler, darker tint copies)");
            AddShot(st, "eye", new Vector3(-8f, 1.7f, -10f), new Vector3(1f, 5f, 6f));

            // X01 railway dead end (no object yet): rails + sleepers + ballast
            Kit("X01_ballast_grey", "T1_ballast_grey_albedo.png", 2f, "T1_ballast_normal.png", .8f);
            Kit("X01_ballast_brown", "T1_ballast_brown_albedo.png", 2f, "T1_ballast_normal.png", .8f);
            st = NewStation(root, "X01", "forest", "railway dead end (track to the collapsed tunnel)");
            StGround(st, "g_forest");
            Vars(st, (v, b, p) =>
            {
                string bal = v == "a" ? "X01_ballast_grey" : "X01_ballast_brown", sl = v == "a" ? "k_conc" : "k_boards_tar";
                Color rail = v == "a" ? X("6E6A66") : X("6A4A3C");
                Use("X01", v, "ballast", bal); Use("X01", v, "sleepers", sl); Use("X01", v, "rails (flat metal + vertex colour)", "flat_metal");
                float L = 40f;
                Box(b, bal, new Vector3(0, .15f, 8f), new Vector3(3.0f, .3f, L), Own(bal));
                Q(b, bal, new Vector3(-1.5f, .3f, 8 - L / 2), new Vector3(-1.5f, .3f, 8 + L / 2), new Vector3(-2.4f, 0f, 8 + L / 2), new Vector3(-2.4f, 0f, 8 - L / 2), new Vector3(-.3f, 1, 0), Vector2.zero, new Vector2(0, L / 2), new Vector2(.5f, L / 2), new Vector2(.5f, 0), Own(bal));
                Q(b, bal, new Vector3(1.5f, .3f, 8 - L / 2), new Vector3(1.5f, .3f, 8 + L / 2), new Vector3(2.4f, 0f, 8 + L / 2), new Vector3(2.4f, 0f, 8 - L / 2), new Vector3(.3f, 1, 0), Vector2.zero, new Vector2(0, L / 2), new Vector2(.5f, L / 2), new Vector2(.5f, 0), Own(bal));
                for (float z = 8 - L / 2 + .3f; z < 8 + L / 2; z += .62f) Box(b, sl, new Vector3(0, .36f, z), new Vector3(2.6f, .16f, .25f), Own(sl) * (v == "a" ? .95f : 1f));
                foreach (float x in new[] { -.76f, .76f })
                {
                    Box(b, "flat_metal", new Vector3(x, .5f, 8f), new Vector3(.07f, .14f, L), rail);
                    Box(b, "flat_metal", new Vector3(x, .45f, 8f), new Vector3(.15f, .03f, L), rail);
                }
                if (v == "c")
                {   // overgrown: meadow patches over the ballast and between the sleepers
                    var rnd = new System.Random(7);
                    for (int i = 0; i < 26; i++) { float x = (float)(rnd.NextDouble() * 4 - 2), z = 8 - L / 2 + (float)rnd.NextDouble() * L; Ground(b, "g_meadow", x - .5f, z - .7f, x + .5f, z + .7f, .45f, Own("g_meadow")); }
                }
                // buffer stop at the end
                Box(b, sl, new Vector3(0, .8f, 8 + L / 2 - .4f), new Vector3(2.4f, .5f, .3f), Own(sl));
                Box(b, "flat_metal", new Vector3(0, .5f, 8 + L / 2 - .2f), new Vector3(2.2f, 1f, .2f), X("6A3A30"));
            });
            AddShot(st, "eye", new Vector3(-2.2f, 1.7f, -9f), new Vector3(.2f, .3f, 6f));
            UseAsset("X01", "c", "note", "variant c = b + grass patches over the ballast");
        }

        // pond / bank geometry: square hole 2*h, bank slopes from y 0 at r = h + 3 down to -1.2 at r = h - 3 (four trapezoids), bottom
        static void PondGround(Station st, string key, float h)
        {
            var b = new Batch(); float o = h + 3f, R = 70f;
            Ground(b, key, -R, -R, R, -o, 0, Own(key)); Ground(b, key, -R, o, R, R, 0, Own(key));
            Ground(b, key, -R, -o, -o, o, 0, Own(key)); Ground(b, key, o, -o, R, o, 0, Own(key));
            Flush(b, st.T, st.Code + "_ground");
        }

        static void PondBank(Batch b, string key, float h)
        {
            float o = h + 3f, i = h - 3f; var s = S[key]; Color c = Own(key);
            var outer = new[] { new Vector3(-o, 0, -o), new Vector3(o, 0, -o), new Vector3(o, 0, o), new Vector3(-o, 0, o) };
            var inner = new[] { new Vector3(-i, -1.2f, -i), new Vector3(i, -1.2f, -i), new Vector3(i, -1.2f, i), new Vector3(-i, -1.2f, i) };
            for (int k = 0; k < 4; k++)
            {
                Vector3 a = outer[k], b1 = outer[(k + 1) % 4], c2 = inner[(k + 1) % 4], d = inner[k];
                Q(b, key, a, b1, c2, d, Vector3.up, new Vector2(a.x / s.TU, a.z / s.TV), new Vector2(b1.x / s.TU, b1.z / s.TV), new Vector2(c2.x / s.TU, c2.z / s.TV), new Vector2(d.x / s.TU, d.z / s.TV), c);
            }
            Ground(b, key, -i, -i, i, i, -1.2f, Mul(c, .8f));
        }

        // ================================================================== HAMLET
        static void Hamlet(Transform root)
        {
            // T07 sheds (slot hamlet_shed: walls boards_SK5a t0 3, roof roof_profsheet_SK4c t0 3)
            MapM("T07a_walls", "T1_boards_dark_albedo.png", 2f, 3f, "T1_boards_dark_normal.png", .7f);
            MapM("T07b_walls", "T1_boards_tar_albedo.png", 2f, 3f, "T1_boards_tar_normal.png", .7f);
            MapM("T07c_walls", "T1_boards_grey_albedo.png", 2f, 3f, "T1_boards_grey_normal.png", .7f);
            MapM("T07a_roof", "T1_rust_sheet_albedo.png", 2f, 3f, "T1_rust_sheet_normal.png", .8f, .25f, .2f);
            MapM("T07b_roof", "T1_standing_seam_albedo.png", 2f, 3f, "T1_standing_seam_normal.png", .8f, .3f, .2f, "4A4D50");
            MapM("T07c_roof", "T1_galv_rust_albedo.png", 1.2f, 3f, "T1_galv_rust_normal.png", .8f, .35f, .3f);
            var st = NewStation(root, "T07", "hamlet", "sheds, coops, pigsties, ruins");
            StGround(st, "g_meadow");
            Vars(st, (v, b, p) =>
            {
                string wk = "T07" + v + "_walls", rk = "T07" + v + "_roof";
                Use("T07", v, "walls (slot hamlet_shed)", wk); Use("T07", v, "roof (slot hamlet_shed)", rk);
                ShedBox(b, wk, rk, -6f, -2f, 0f, 3.6f, 2.4f, .5f, true);
                ShedBox(b, wk, rk, -.8f, 2.4f, .5f, 4.1f, 2.4f, .5f, true);
                ShedBox(b, wk, rk, 3.6f, 6.1f, 1f, 3f, 1.8f, .4f, true);
                // doors (same boards, darker) + coop hatch
                foreach (var (x, wdt, hh) in new[] { (-4f, 1.1f, 1.9f), (.8f, 1.0f, 1.9f), (4.85f, .5f, .6f) })
                    Box(b, wk, new Vector3(x, hh / 2 + .02f, x < 3 ? (x < -1 ? -.03f : .47f) : .97f), new Vector3(wdt, hh, .06f), Mul(W, .78f));
                Face(b, "flat", new Vector3(-2.9f, 1.3f, -.02f), Vector3.right, .5f, Vector3.up, .4f, Vector3.back, X("1E1D1B"));
            });
            AddShot(st, "eye", new Vector3(-6f, 1.7f, -8f), new Vector3(0f, 1.3f, 1.5f));
            AddShot(st, "roof", new Vector3(-7f, 6f, -7f), new Vector3(0f, 1.2f, 2f));

            // T08 church (slot hamlet_church: walls stucco_SK3b t0 4, roof roof_tile_SK4a t0 3)
            MapM("T08a_walls", "T1_plaster_whitewash_albedo.png", 3f, 4f, "T1_plaster_whitewash_normal.png", .4f);
            MapM("T08b_walls", "T1_brick_red_albedo.png", 1.6f, 4f, "T1_brick_red_normal.png", .7f);
            MapM("T08c_walls", "T1_logs_wall_albedo.png", 2.08f, 4f, "T1_logs_wall_normal.png", .9f);
            MapM("T08a_roof", "T1_standing_seam_albedo.png", 2f, 3f, "T1_standing_seam_normal.png", .8f, .35f, .25f, "3F5E4A");
            MapM("T08b_roof", "T1_standing_seam_albedo.png", 2f, 3f, "T1_standing_seam_normal.png", .8f, .35f, .25f, "4A4D50");
            MapM("T08c_roof", "T1_shingle_wood_albedo.png", 2f, 3f, "T1_shingle_wood_normal.png", .9f);
            st = NewStation(root, "T08", "hamlet", "church");
            StGround(st, "g_meadow");
            Vars(st, (v, b, p) =>
            {
                string wk = "T08" + v + "_walls", rk = "T08" + v + "_roof";
                Use("T08", v, "walls (slot hamlet_church)", wk); Use("T08", v, "roof (slot hamlet_church)", rk);
                Color trim = v == "b" ? X("D9D2C2") : v == "a" ? X("E9E4D8") : X("5A4636");
                Color plinth = v == "c" ? X("6E6A63") : X("8E8A82");
                // nave 14 x 9 x 6.5 + gable; apse; bell tower 5 x 5 x 13 with tent roof and cupola
                var holes = new List<Rect>();
                for (int i = 0; i < 4; i++) holes.Add(Rect.MinMaxRect(2.2f + i * 3.0f, 2.2f, 3.3f + i * 3.0f, 4.6f));
                HoleWall(b, wk, new Vector3(-4f, 0, -4.5f), Vector3.right, Vector3.forward, 14f, 0, 6.5f, holes, .35f, W);
                foreach (var h in holes)
                {
                    Face(b, "glass_dark", new Vector3(-4f + h.xMin, h.yMin, -4.15f), Vector3.right, h.width, Vector3.up, h.height, Vector3.back, W);
                    Box(b, "flat", new Vector3(-4f + h.center.x, h.yMax + .15f, -4.55f), new Vector3(h.width + .3f, .3f, .1f), trim);
                    Box(b, "flat", new Vector3(-4f + h.center.x, h.yMin - .05f, -4.55f), new Vector3(h.width + .2f, .1f, .14f), trim);
                }
                Face(b, wk, new Vector3(10f, 0, 4.5f), Vector3.left, 14f, Vector3.up, 6.5f, Vector3.forward, W);
                Face(b, wk, new Vector3(10f, 0, -4.5f), Vector3.forward, 9f, Vector3.up, 6.5f, Vector3.right, W);
                Face(b, wk, new Vector3(-4f, 0, 4.5f), Vector3.back, 9f, Vector3.up, 6.5f, Vector3.left, W);
                Gable(b, rk, wk, -4f, 10f, -4.5f, 4.5f, 6.5f, 10.5f, .5f, true, W, W);
                Box(b, "flat", new Vector3(3f, .35f, -4.52f), new Vector3(14.1f, .7f, .1f), plinth);
                Box(b, "flat", new Vector3(3f, 6.4f, -4.55f), new Vector3(14.2f, .25f, .14f), trim);
                // apse
                Block(b, wk, W, 10f, 13.5f, -3f, 3f, 0, 5.5f, null, W);
                Gable(b, rk, wk, 10f, 13.8f, -3f, 3f, 5.5f, 8f, .4f, true, W, W);
                // bell tower (west end)
                Block(b, wk, W, -9.5f, -4f, -2.75f, 2.75f, 0, 13f, null, W);
                var th = new List<Rect> { Rect.MinMaxRect(1.9f, 9.5f, 3.6f, 12f) };
                Face(b, "flat", new Vector3(-7.6f, 9.5f, -2.77f), Vector3.right, 1.7f, Vector3.up, 2.5f, Vector3.back, X("2A2826"));
                Box(b, "flat", new Vector3(-6.75f, 13.1f, 0), new Vector3(5.9f, .3f, 5.9f), trim);
                // tent roof (pyramid) + drum + cupola
                Vector3 apex = new(-6.75f, 17.5f, 0); float hx = 3.0f; var rs = S[rk];
                var cs = new[] { new Vector3(-6.75f - hx, 13.25f, -hx), new Vector3(-6.75f + hx, 13.25f, -hx), new Vector3(-6.75f + hx, 13.25f, hx), new Vector3(-6.75f - hx, 13.25f, hx) };
                for (int k = 0; k < 4; k++)
                {
                    var a = cs[k]; var c2 = cs[(k + 1) % 4];
                    var nn = Vector3.Cross(c2 - a, apex - a).normalized; if (nn.y < 0) nn = -nn;
                    TriN(b, rk, a, c2, apex, nn, Vector2.zero, new Vector2(2 * hx / rs.TU, 0), new Vector2(hx / rs.TU, 5f / rs.TV), W);
                }
                Cyl(b, "flat_metal", new Vector3(-6.75f, 17.2f, 0), new Vector3(-6.75f, 18.4f, 0), .45f, 12, v == "a" ? X("3F5E4A") : v == "b" ? X("4A4D50") : X("6E5A44"));
                Cyl(b, "flat_metal", new Vector3(-6.75f, 18.4f, 0), new Vector3(-6.75f, 19.6f, 0), .7f, 12, v == "a" ? X("B89A4E") : v == "b" ? X("4A4D50") : X("6E5A44"), true, .02f);
                Box(b, "flat_metal", new Vector3(-6.75f, 20.2f, 0), new Vector3(.08f, 1.2f, .08f), X("B89A4E"));
                Box(b, "flat_metal", new Vector3(-6.75f, 20.4f, 0), new Vector3(.6f, .08f, .08f), X("B89A4E"));
                // door
                Box(b, "flat", new Vector3(-6.75f, 1.3f, -2.8f), new Vector3(1.6f, 2.6f, .1f), X("4A3A2C"));
            });
            AddShot(st, "eye", new Vector3(-14f, 1.7f, -17f), new Vector3(1f, 6f, 0f));

            // T09 hut of base 2: a = approved H5 house (HH_House_v03 colourway a, dark roof); b whitewash; c cream siding
            MapM("T09b_walls", "T1_plaster_whitewash_albedo.png", 3f, 3f, "T1_plaster_whitewash_normal.png", .4f);
            MapM("T09c_walls", "T1_siding_cream_albedo.png", 2f, 3f, "T1_siding_cream_normal.png", .6f);
            st = NewStation(root, "T09", "hamlet", "hut of base 2 (grandpa)");
            StGround(st, "g_meadow");
            var hhAsset = AssetDatabase.LoadAssetAtPath<GameObject>(TTB4 + "/House/HH_House_v03.fbx");
            if (hhAsset)
            {
                var h = (GameObject)PrefabUtility.InstantiatePrefab(hhAsset, st.V["a"]);
                h.transform.localPosition = new Vector3(0, 0, 1f); h.transform.localRotation = Quaternion.identity;
                var dark = AssetDatabase.LoadAssetAtPath<Material>(GEN + "/Materials/Rollout/W85_HH_Roof_a_dark1.mat");
                foreach (var r in h.GetComponentsInChildren<Renderer>(true))
                {
                    if (r.name.StartsWith("UCX_")) { r.enabled = false; continue; }
                    var ms = r.sharedMaterials;
                    for (int i = 0; i < ms.Length; i++) if (ms[i] && ms[i].name.StartsWith("TT_HH_Roof_") && dark) ms[i] = dark;
                    r.sharedMaterials = ms;
                }
                UseAsset("T09", "a", "house model (RolloutH5, colourway a, roof W85_HH_Roof_a_dark1)", TTB4 + "/House/HH_House_v03.fbx");
            }
            else Note("HH_House_v03 missing");
            foreach (string v in new[] { "b", "c" })
            {
                var b = new Batch();
                string wk = "T09" + v + "_walls"; Use("T09", v, "walls (slot hamlet_base2)", wk); Use("T09", v, "roof (slot hamlet_base2)", "hh_roof_dark");
                HutBody(b, wk, v == "b" ? X("3E6D8C") : X("4E6B55"));
                Flush(b, st.V[v], "T09_" + v);
            }
            AddShot(st, "eye", new Vector3(-7f, 1.7f, -10f), new Vector3(0, 2.2f, 1f));

            // T10 hay shelter: open posts + roof (needs geometry: open sides), bales inside
            Kit("T14a_bale", "T1_haybale_a_albedo.png", 1f, "T1_haybale_normal.png", .7f);
            Kit("T14b_bale", "T1_haybale_b_albedo.png", 1f, "T1_haybale_normal.png", .7f);
            Kit("T14c_bale", "T1_haybale_c_albedo.png", 1f, "T1_haybale_normal.png", .7f);
            foreach (string v in VS) OneTint("T14" + v + "_bale");
            st = NewStation(root, "T10", "hamlet", "hay shelter");
            StGround(st, "g_meadow");
            Vars(st, (v, b, p) =>
            {
                string post = Pick3(v, "k_boards_dark", "k_bark", "k_boards_grey"), rk = "T07" + v + "_roof";
                Use("T10", v, "posts / beams (new geometry)", post); Use("T10", v, "roof (slot hamlet_hay_shelter, new)", rk);
                float x0 = -5f, x1 = 5f, z0 = -3f, z1 = 3f, hgt = 4f;
                foreach (float x in new[] { x0, 0f, x1 }) foreach (float z in new[] { z0, z1 })
                        if (post == "k_bark") Cyl(b, post, new Vector3(x, 0, z), new Vector3(x, hgt, z), .14f, 8, Own(post)); else Box(b, post, new Vector3(x, hgt / 2, z), new Vector3(.2f, hgt, .2f), Own(post));
                foreach (float z in new[] { z0, z1 }) Box(b, post, new Vector3(0, hgt - .1f, z), new Vector3(10.4f, .2f, .2f), Own(post));
                Gable(b, rk, null, x0, x1, z0, z1, hgt, hgt + 1.5f, .4f, true, W, W);
                for (int i = 0; i < 4; i++) Bale(b, "T14a_bale", new Vector3(-3.6f + i * 2.2f, .75f, -.8f), 0f);
                for (int i = 0; i < 3; i++) Bale(b, "T14a_bale", new Vector3(-2.5f + i * 2.2f, .75f, 1.0f), 0f);
                for (int i = 0; i < 2; i++) Bale(b, "T14a_bale", new Vector3(-1.4f + i * 2.2f, 2.15f, .1f), 0f);
            });
            AddShot(st, "eye", new Vector3(-8f, 1.7f, -9f), new Vector3(0, 2f, 0f));

            // T11 water tower (slot hamlet_water_tower: walls brick_SK3a t0 3, roof profsheet t0 3)
            MapM("T11a_tank", "T1_steel_plates_albedo.png", 3f, 3f, "T1_steel_plates_normal.png", .6f, .35f, .3f, "8E9497");
            MapM("T11b_tank", "T1_steel_plates_albedo.png", 3f, 3f, "T1_steel_plates_normal.png", .6f, .35f, .3f, "3F5E4A");
            MapM("T11c_tank", "T1_steel_plates_albedo.png", 3f, 3f, "T1_steel_plates_normal.png", .6f, .35f, .3f, "7FA2BC");
            MapM("T11b_shaft", "T1_brick_red_albedo.png", 1.6f, 3f, "T1_brick_red_normal.png", .7f);
            st = NewStation(root, "T11", "hamlet", "water tower");
            StGround(st, "g_meadow");
            Vars(st, (v, b, p) =>
            {
                string tank = "T11" + v + "_tank", shaft = v == "b" ? "T11b_shaft" : tank;
                Use("T11", v, "walls / shaft (slot hamlet_water_tower)", shaft); Use("T11", v, "tank + roof", tank);
                Cyl(b, shaft, new Vector3(0, 0, 0), new Vector3(0, 9.2f, 0), 1.3f, 16, W, false);
                Cyl(b, tank, new Vector3(0, 8.6f, 0), new Vector3(0, 9.4f, 0), 1.3f, 16, W, false, 2.6f);
                Cyl(b, tank, new Vector3(0, 9.4f, 0), new Vector3(0, 12.6f, 0), 2.6f, 20, W, false);
                Cyl(b, tank, new Vector3(0, 12.6f, 0), new Vector3(0, 13.9f, 0), 2.75f, 20, Mul(W, .85f), false, .15f);
                Cyl(b, "flat_metal", new Vector3(0, 12.6f, 0), new Vector3(0, 12.7f, 0), 2.9f, 20, X("3A3A3A"));
                for (int i = 0; i < 18; i++) Box(b, "flat_metal", new Vector3(-1.38f, .3f + i * .5f, 0), new Vector3(.04f, .04f, .5f), X("3A3A3A"));
                Box(b, "flat_metal", new Vector3(-1.38f, 4.6f, -.25f), new Vector3(.05f, 9.2f, .05f), X("3A3A3A"));
                Box(b, "flat_metal", new Vector3(-1.38f, 4.6f, .25f), new Vector3(.05f, 9.2f, .05f), X("3A3A3A"));
                Box(b, "flat", new Vector3(0, 1.0f, -1.33f), new Vector3(.9f, 2f, .1f), X("4A4744"));
            });
            AddShot(st, "eye", new Vector3(-7f, 1.7f, -12f), new Vector3(0, 7f, 0f));

            // T12 bus stop (box generic_concrete -> pavilion prefab)
            Kit("mosaic", "T1_mosaic_albedo.png", 1f); OneTint("mosaic");
            Kit("kh3", TTB4 + "/Textures/KH3_silicate_brick_white_albedo.png", 1f);
            Kit("kh4", TTB4 + "/Textures/KH4_red_brick_muted_albedo.png", 1f);
            st = NewStation(root, "T12", "hamlet", "bus stop");
            StGround(st, "g_meadow");
            { var g = new Batch(); Ground(g, "g_asph", -6, -4.5f, 6, -1.6f, .01f, Own("g_asph")); Flush(g, st.T, "T12_road"); }
            Vars(st, (v, b, p) =>
            {
                string wall = Pick3(v, "k_conc", "k_metal", "kh3"), roof = Pick3(v, "k_conc", "k_galv", "k_tar");
                Color wc = v == "b" ? X("3F5F7E") : Own(wall);
                Use("T12", v, "walls", wall); Use("T12", v, "roof", roof); if (v == "a") Use("T12", v, "mosaic panel", "mosaic");
                BoxMM(b, wall, new Vector3(-2.2f, 0, 1.0f), new Vector3(2.2f, 2.5f, 1.2f), wc);
                BoxMM(b, wall, new Vector3(-2.2f, 0, -.6f), new Vector3(-2.0f, 2.5f, 1.2f), wc);
                BoxMM(b, wall, new Vector3(2.0f, 0, -.6f), new Vector3(2.2f, 2.5f, 1.2f), wc);
                BoxMM(b, roof, new Vector3(-2.5f, 2.5f, -1.0f), new Vector3(2.5f, 2.68f, 1.45f), Own(roof));
                if (v == "a") Panel(b, "mosaic", new Vector3(-1.95f, .55f, .98f), Vector3.right, 3.9f, 1.85f, Vector3.back, new Rect(0, 0, 1, 1), W);
                if (v == "b") for (int i = 0; i < 4; i++) Box(b, "k_metal", new Vector3(-1.5f + i, 1.3f, 1.1f), new Vector3(.06f, 2.5f, .24f), X("2E3A48"));
                Box(b, "k_boards_warm", new Vector3(0, .45f, .65f), new Vector3(3.4f, .06f, .45f), Own("k_boards_warm"));
                foreach (float x in new[] { -1.4f, 1.4f }) Box(b, "flat_metal", new Vector3(x, .22f, .65f), new Vector3(.06f, .44f, .4f), X("3A3A3A"));
            });
            AddShot(st, "eye", new Vector3(-3.5f, 1.7f, -6.5f), new Vector3(.3f, 1.3f, .5f));
            foreach (string v in VS) { var go = st.V[v].GetComponentInChildren<MeshRenderer>()?.gameObject; if (go) UseAsset("T12", v, "prefab (replaces the B_02-U-STOP box)", MakePrefab(go, "T1_BusStop_" + v)); }

            // T13 / T15 PilotKit yard props (P19 atlas): a as is, b warm (H5 wood), c grey-weathered
            PropStation(root, "T13", "hamlet", "well, cart, firewood, stump, buckets, table (PilotKit P19)", new[]
            {
                "Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v01/Prefabs/WELL_RURAL_v01.prefab", "Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v01/Prefabs/CART_WOODEN_v01.prefab",
                "Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v01/Prefabs/WOODPILE_v01.prefab", "Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v02/Prefabs/AXE_STUMP_LOGS_v02.prefab",
                "Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v02/Prefabs/BUCKET_WATERING_v02.prefab", "Assets/OnlyVolunteers/Art/StyleKit_v3/PilotKit_v02/Prefabs/PICNIC_TABLE_v02.prefab",
            }, "g_meadow", new Color(1f, .9f, .78f) * .92f, new Color(.86f, .88f, .9f) * .86f, 3.2f);

            // T14 round hay bales: own bale mesh + straw / spiral atlas (replaces the octagon PilotKit bale)
            st = NewStation(root, "T14", "hamlet", "round hay bales");
            StGround(st, "g_meadow");
            Kit("T21b_stubble", "T1_field_stubble_b_albedo.png", 4f, "T1_field_stubble_normal.png", .6f);
            Vars(st, (v, b, p) =>
            {
                string k = "T14" + v + "_bale"; Use("T14", v, "bale atlas", k);
                Ground(b, "T21b_stubble", -14, -6, 14, 18, .01f, Own("T21b_stubble"));
                var pos = new[] { (-3f, 1f, 10f), (0f, 3.5f, 80f), (3f, 1.5f, 30f), (6f, 6f, 0f), (-6f, 7f, 60f) };
                foreach (var (x, z, yaw) in pos) Bale(b, k, new Vector3(x, .75f, z), yaw);
            });
            AddShot(st, "eye", new Vector3(-5f, 1.7f, -6f), new Vector3(0f, .7f, 3f));
            // prefabs (one per colourway) for the integrator
            foreach (string v in VS)
            {
                var b = new Batch(); Bale(b, "T14" + v + "_bale", new Vector3(0, .75f, 0), 0f);
                var tmp = new GameObject("tmp"); var go = Flush(b, tmp.transform, "T1_HayBale_" + v);
                if (go) UseAsset("T14", v, "prefab", MakePrefab(go, "T1_HayBale_" + v));
                Object.DestroyImmediate(tmp);
            }

            // T16 tractors, park benches, tank (StreetKit palette)
            PropStation(root, "T16", "hamlet", "tractors, benches (StreetKit palette)", new[] { MPF + "HEAVY/tractor_small.prefab", MPF + "BENCHES/bench_park.prefab" },
                "g_meadow", new Color(1f, .92f, .82f) * .9f, new Color(.84f, .86f, .88f) * .82f, 4.5f);

            // T19 fishing jetty (Zone_02-FISH-DOCK: boards_SK5a t0 3) on piles over the river
            MapM("T19b_deck", "T1_boards_grey_albedo.png", 2f, 3f, "T1_boards_grey_normal.png", .7f);
            MapM("T19c_deck", "T1_boards_tar_albedo.png", 2f, 3f, "T1_boards_tar_normal.png", .7f);
            st = NewStation(root, "T19", "hamlet", "fishing jetty");
            PondGround(st, "g_meadow", 13f);
            Vars(st, (v, b, p) =>
            {
                string dk = Pick3(v, "cur_pier", "T19b_deck", "T19c_deck"); Use("T19", v, "deck (Zone_02-FISH-DOCK)", dk);
                PondBank(b, "bank_mud", 13f);
                Ground(b, "water_flow", -13, -13, 13, 13, -.25f, W);
                // deck along -Z bank into the water, rotated 90 deg (boards across)
                float x0 = -1.0f, x1 = 1.0f, z0 = -17f, z1 = -7f, y = .35f;
                var s = S[dk];
                Q(b, dk, new Vector3(x0, y, z0), new Vector3(x1, y, z0), new Vector3(x1, y, z1), new Vector3(x0, y, z1), Vector3.up,
                    new Vector2(z0 / s.TU, x0 / s.TV), new Vector2(z0 / s.TU, x1 / s.TV), new Vector2(z1 / s.TU, x1 / s.TV), new Vector2(z1 / s.TU, x0 / s.TV), W);
                Box(b, dk, new Vector3(0, y - .1f, (z0 + z1) / 2), new Vector3(2f, .18f, z1 - z0), Mul(W, .7f));
                for (float z = z0 + .5f; z < z1; z += 2.5f) foreach (float x in new[] { x0 + .1f, x1 - .1f }) Cyl(b, "k_bark", new Vector3(x, -1.3f, z), new Vector3(x, y - .05f, z), .11f, 8, Own("k_bark"));
            });
            AddShot(st, "eye", new Vector3(-5f, 1.7f, -22f), new Vector3(0, -.2f, -10f));

            // T21 fields: GPT layers (current) / own b / own c
            string gp = LayerTex(GEN + "/Terrain/W85_L09_field_plowed.terrainlayer"), gs = LayerTex(GEN + "/Terrain/W85_L10_field_stubble.terrainlayer");
            if (gp != null) Kit("T21a_plowed", gp, 4f); else Kit("T21a_plowed", "T1_field_plowed_b_albedo.png", 4f);
            if (gs != null) Kit("T21a_stubble", gs, 4f); else Kit("T21a_stubble", "T1_field_stubble_b_albedo.png", 4f);
            Kit("T21b_plowed", "T1_field_plowed_b_albedo.png", 4f, "T1_field_plowed_b_normal.png", .8f);
            Kit("T21c_plowed", "T1_field_plowed_c_albedo.png", 4f, "T1_field_plowed_b_normal.png", .8f);
            Kit("T21c_stubble", "T1_field_stubble_c_albedo.png", 4f, "T1_field_stubble_normal.png", .6f);
            st = NewStation(root, "T21", "hamlet", "fields: plowed, stubble, vegetable plots");
            StGround(st, "g_meadow");
            Vars(st, (v, b, p) =>
            {
                string pk = "T21" + v + "_plowed", sk = "T21" + v + "_stubble";
                Use("T21", v, "plowed (terrain layer L09)", pk); Use("T21", v, "stubble (terrain layer L10)", sk);
                Ground(b, pk, -22, -2, -1, 30, .02f, Own(pk));
                Ground(b, sk, 1, -2, 22, 30, .02f, Own(sk));
            });
            AddShot(st, "eye", new Vector3(-1f, 1.7f, -8f), new Vector3(0, -.5f, 12f));

            // T22 pond bank (bank family) + T129 river: reuse the T06 variants
            st = NewStation(root, "T22", "hamlet", "pond bank");
            PondGround(st, "g_meadow", 13f);
            Vars(st, (v, b, p) =>
            {
                string bk = Pick3(v, "g_meadow", "bank_mud", "bank_pebbles"); if (v == "a") UseAsset("T22", v, "bank strip", "none (terrain unchanged)"); else Use("T22", v, "bank material (test mesh; map: terrain layer below)", bk);
                PondBank(b, bk, 13f); Ground(b, "water_flow", -13, -13, 13, 13, -.25f, W);
            });
            AddShot(st, "eye", new Vector3(-7f, 1.7f, -17f), new Vector3(2f, -.4f, 0f));

            // T23 operating shed of base 2 ([Capture] cubes: Plank / Roof / Tile / Concrete / Wood)
            MapM("T23_tiles", "T1_tiles_white_albedo.png", 1f, 1f, "T1_tiles_white_normal.png", .5f, .5f);
            MapM("T23_floor", "T1_concrete_light_albedo.png", 3f, 3f, "T1_concrete_light_normal.png", .4f);
            MapM("T23a_planks", "T1_boards_warm_albedo.png", 2f, 2f, "T1_boards_warm_normal.png", .7f);
            MapM("T23b_planks", "T1_boards_dark_albedo.png", 2f, 2f, "T1_boards_dark_normal.png", .7f);
            MapM("T23c_planks", "T1_boards_whitewash_albedo.png", 2f, 2f, "T1_boards_whitewash_normal.png", .7f);
            MapM("T23a_roof", "T1_standing_seam_albedo.png", 2f, 2f, "T1_standing_seam_normal.png", .8f, .3f, .2f, "45484A");
            MapM("T23b_roof", "T1_rust_sheet_albedo.png", 2f, 2f, "T1_rust_sheet_normal.png", .8f, .25f, .2f);
            MapM("T23c_roof", "T1_galv_rust_albedo.png", 1.2f, 2f, "T1_galv_rust_normal.png", .8f, .35f, .3f);
            MapM("T23_wood", "T1_boards_tar_albedo.png", 2f, 2f, "T1_boards_tar_normal.png", .6f);
            st = NewStation(root, "T23", "hamlet", "operating shed of base 2");
            StGround(st, "g_meadow");
            Vars(st, (v, b, p) =>
            {
                string pk = "T23" + v + "_planks", rk = "T23" + v + "_roof";
                Use("T23", v, "Capture_Shed_Plank_v01 ->", pk); Use("T23", v, "Capture_Shed_Roof_v01 ->", rk); Use("T23", v, "Capture_Shed_Tile_v01 ->", "T23_tiles");
                Use("T23", v, "Capture_Shed_Concrete_v01 ->", "T23_floor"); Use("T23", v, "Capture_Shed_Wood_v01 ->", "T23_wood");
                BoxMM(b, "T23_floor", new Vector3(-2.5f, 0, -2f), new Vector3(2.5f, .12f, 2f), W);
                BoxMM(b, "T23_tiles", new Vector3(.4f, .12f, .2f), new Vector3(2.4f, .14f, 1.9f), W);
                BoxMM(b, pk, new Vector3(-2.5f, .12f, 1.9f), new Vector3(2.5f, 2.6f, 2.0f), W);
                BoxMM(b, pk, new Vector3(-2.5f, .12f, -2f), new Vector3(-2.4f, 2.6f, 2f), W);
                BoxMM(b, pk, new Vector3(2.4f, .12f, -2f), new Vector3(2.5f, 2.6f, 2f), W);
                BoxMM(b, "T23_tiles", new Vector3(.4f, .14f, 1.85f), new Vector3(2.38f, 1.6f, 1.9f), W);
                foreach (float x in new[] { -2.3f, 2.3f }) BoxMM(b, "T23_wood", new Vector3(x - .08f, .12f, -2.08f), new Vector3(x + .08f, 2.4f, -1.92f), W);
                BoxMM(b, "T23_wood", new Vector3(-2.5f, 2.3f, -2.1f), new Vector3(2.5f, 2.45f, -1.9f), W);
                ShedRoof(b, rk, -2.5f, 2.5f, -2f, 2f, 2.45f, 2.75f, .3f, false, W);
                BoxMM(b, "T23_wood", new Vector3(-2.3f, 1.2f, 1.5f), new Vector3(-.5f, 1.25f, 1.88f), W);
                Box(b, "flat", new Vector3(1.4f, .9f, .9f), new Vector3(1.9f, .08f, .7f), X("B9BDBF"));
                Box(b, "flat", new Vector3(1.4f, .45f, .9f), new Vector3(.1f, .8f, .1f), X("7A7E80"));
            });
            AddShot(st, "eye", new Vector3(-2.5f, 1.7f, -5.5f), new Vector3(.4f, 1.1f, 1f));

            // T24 paint table (G20 cubes / cylinders): table boards + tin
            MapM("T24a_table", "T1_boards_grey_albedo.png", 2f, 2f, "T1_boards_grey_normal.png", .7f);
            MapM("T24b_table", "T1_boards_tar_albedo.png", 2f, 2f, "T1_boards_tar_normal.png", .7f);
            MapM("T24c_table", "T1_boards_green_chipped_albedo.png", 2f, 2f, "T1_boards_green_chipped_normal.png", .7f);
            MapM("T24_tin", "T1_painted_metal_albedo.png", 1f, 1f, null, .5f, .55f, .6f, "A9ADB0");
            st = NewStation(root, "T24", "hamlet", "grandpa's paint table");
            StGround(st, "g_meadow");
            Vars(st, (v, b, p) =>
            {
                string tk = "T24" + v + "_table"; Use("T24", v, "G20_OldWood ->", tk); Use("T24", v, "G20_Tin ->", "T24_tin");
                BoxMM(b, tk, new Vector3(-1.1f, .78f, -.4f), new Vector3(1.1f, .84f, .4f), W);
                foreach (float x in new[] { -1f, 1f }) foreach (float z in new[] { -.32f, .32f }) BoxMM(b, tk, new Vector3(x - .04f, 0, z - .04f), new Vector3(x + .04f, .78f, z + .04f), Mul(W, .85f));
                string[] cols = { "2F5E8C", "3D6B48", "C49A3A", "A33A33" };
                for (int i = 0; i < 4; i++)
                {
                    float x = -.75f + i * .45f;
                    Cyl(b, "T24_tin", new Vector3(x, .84f, -.05f), new Vector3(x, 1.06f, -.05f), .09f, 14, W);
                    Cyl(b, "flat", new Vector3(x, .9f, -.05f), new Vector3(x, .99f, -.05f), .093f, 14, X(cols[i]), false);
                }
            });
            AddShot(st, "eye", new Vector3(-1.2f, 1.6f, -2.4f), new Vector3(0, .9f, 0));

            // T25 grandpa's yard props (GY flat colours)
            PropStation(root, "T25", "hamlet", "rocking chair, barrels, paint cans (GrandpaYard)", new[]
            {
                "Assets/OnlyVolunteers/Art/Props/GrandpaYard_v01/Prefabs/GY_RockingChair_Red.prefab", "Assets/OnlyVolunteers/Art/Props/GrandpaYard_v01/Prefabs/GY_Barrel_Wood.prefab",
                "Assets/OnlyVolunteers/Art/Props/GrandpaYard_v01/Prefabs/GY_Drum_Rain.prefab", "Assets/OnlyVolunteers/Art/Props/GrandpaYard_v01/Prefabs/GY_PaintCan_Ochre.prefab",
            }, "g_meadow", new Color(1f, .9f, .8f) * .9f, new Color(.85f, .87f, .9f) * .82f, 1.6f);

            // T129 river banks (bank family), channel in the Hamlet light
            st = NewStation(root, "T129", "hamlet", "river banks (also T131 mountain lake / plunge pool)");
            {
                var g = new Batch();
                Ground(g, "g_meadow", -70, -70, 70, -12, 0, Own("g_meadow")); Ground(g, "g_meadow", -70, 12, 70, 70, 0, Own("g_meadow"));
                Flush(g, st.T, "T129_ground");
            }
            Vars(st, (v, b, p) =>
            {
                string bk = Pick3(v, "g_meadow", "bank_mud", "bank_pebbles"); if (v == "a") UseAsset("T129", v, "bank strip", "none (terrain unchanged)"); else Use("T129", v, "bank material (test mesh; map: terrain layer below)", bk); Use("T129", v, "water (unchanged)", "water_flow");
                var s = S[bk]; Color c = Own(bk);
                foreach (int sg in new[] { -1, 1 })
                    Q(b, bk, new Vector3(-70, 0, 12 * sg), new Vector3(70, 0, 12 * sg), new Vector3(70, -1.4f, 6 * sg), new Vector3(-70, -1.4f, 6 * sg), Vector3.up,
                        new Vector2(-70 / s.TU, 12 * sg / s.TV), new Vector2(70 / s.TU, 12 * sg / s.TV), new Vector2(70 / s.TU, 6 * sg / s.TV), new Vector2(-70 / s.TU, 6 * sg / s.TV), c);
                Ground(b, bk, -70, -6, 70, 6, -1.4f, Mul(c, .8f));
                Ground(b, "water_flow", -70, -10, 70, 10, -.45f, W);
            });
            AddShot(st, "eye", new Vector3(-4f, 1.7f, -15f), new Vector3(5f, -1.2f, -8f));

            // T130 waterfall: a as is, b + foam ring / strip at the foot, c + spray billboards
            Lit("foam_ring", W, T("T1_foam_ring_rgba.png", false, true, 512), 1, 1, .3f, 0, 2, false, true);
            Lit("spray", W, T("T1_spray_rgba.png", false, true, 512), 1, 1, .1f, 0, 2, true, true);
            st = NewStation(root, "T130", "hamlet", "waterfalls (mountain / sea)");
            PondGround(st, "g_meadow", 9f);
            Vars(st, (v, b, p) =>
            {
                Use("T130", v, "waterfall (unchanged)", "waterfall");
                PondBank(b, "bank_pebbles", 9f); Ground(b, "water_flow", -9, -9, 9, 9, -.25f, W);
                Box(b, "rock", new Vector3(0, 7f, 9f), new Vector3(24f, 14f, 6f), Own("rock"));
                Panel(b, "waterfall", new Vector3(-2.5f, -.3f, 5.9f), Vector3.right, 5f, 14.3f, Vector3.back, new Rect(0, 0, 1, 3), W);
                if (v != "a")
                {
                    Use("T130", v, "foam ring at the foot (new quad)", "foam_ring");
                    Decal(b, "foam_ring", new Vector3(0, -.22f, 4.5f), 9f, 7f, 0f, new Rect(0, 0, 1, 1), W);
                }
                if (v == "c")
                {
                    Use("T130", v, "spray billboards (new quads)", "spray");
                    for (int i = 0; i < 3; i++) Panel(b, "spray", new Vector3(-3.5f + i * 2.2f, -.3f, 5.2f - i * .3f), Vector3.right, 3.2f, 3.2f, Vector3.back, new Rect(0, 0, 1, 1), W);
                }
            });
            AddShot(st, "eye", new Vector3(-6f, 1.7f, -14f), new Vector3(0f, 4f, 6f));
        }

        static void ShedBox(Batch b, string wk, string rk, float x0, float x1, float z0, float z1, float h, float rise, bool highFront, Color? col = null)
        {
            Color c = col ?? W;
            Face(b, wk, new Vector3(x0, 0, z0), Vector3.right, x1 - x0, Vector3.up, h + rise, Vector3.back, c, x0, 0);
            Face(b, wk, new Vector3(x1, 0, z1), Vector3.left, x1 - x0, Vector3.up, h, Vector3.forward, c, -x1, 0);
            Face(b, wk, new Vector3(x0, 0, z1), Vector3.back, z1 - z0, Vector3.up, h, Vector3.left, c, -z1, 0);
            Face(b, wk, new Vector3(x1, 0, z0), Vector3.forward, z1 - z0, Vector3.up, h, Vector3.right, c, z0, 0);
            foreach (float x in new[] { x0, x1 })
                TriN(b, wk, new Vector3(x, h, z0), new Vector3(x, h + rise, z0), new Vector3(x, h, z1), x == x0 ? Vector3.left : Vector3.right, new Vector2(0, h / 3f), new Vector2(0, (h + rise) / 3f), new Vector2((z1 - z0) / 3f, h / 3f), c);
            ShedRoof(b, rk, x0, x1, z0, z1, h, h + rise, .3f, highFront, W);
        }

        static void Bale(Batch b, string key, Vector3 c, float yaw)
        {
            var q = Quaternion.Euler(0, yaw, 0);
            Vector3 ax = q * Vector3.right * .6f;
            Cyl(b, key, c - ax, c + ax, .75f, 18, W, true, -1f, new Rect(0, 0, .5f, 1), new Rect(.5f, 0, .5f, .5f));
        }

        // hut of base 2 (variants b / c): box 9 x 6.5 x 3 + gable, windows with shutters, porch
        static void HutBody(Batch b, string wk, Color shutter)
        {
            float x0 = -4.5f, x1 = 4.5f, z0 = -2f, z1 = 4.5f, h = 3f;
            var holes = new List<Rect> { Rect.MinMaxRect(1.2f, 1.0f, 2.2f, 2.3f), Rect.MinMaxRect(6.8f, 1.0f, 7.8f, 2.3f), Rect.MinMaxRect(4.0f, .2f, 5.0f, 2.3f) };
            HoleWall(b, wk, new Vector3(x0, 0, z0), Vector3.right, Vector3.forward, x1 - x0, 0, h, holes, .2f, W);
            Face(b, wk, new Vector3(x1, 0, z1), Vector3.left, x1 - x0, Vector3.up, h, Vector3.forward, W);
            Face(b, wk, new Vector3(x0, 0, z1), Vector3.back, z1 - z0, Vector3.up, h, Vector3.left, W);
            Face(b, wk, new Vector3(x1, 0, z0), Vector3.forward, z1 - z0, Vector3.up, h, Vector3.right, W);
            Gable(b, "hh_roof_dark", wk, x0, x1, z0, z1, h, h + 2.4f, .5f, true, W, W);
            foreach (var hr in holes.Take(2))
            {
                Window(b, new Vector3(x0, 0, z0), Vector3.right, Vector3.forward, hr, .15f, X("E9E4D8"), X("E9E4D8"), false, "glass_dark", "flat");
                foreach (int sg in new[] { -1, 1 })
                    FBox(b, "flat", new Vector3(x0, 0, z0), Vector3.right, Vector3.forward, hr.center.x + sg * (hr.width / 2 + .3f), hr.center.y, -.05f, new Vector3(.5f, hr.height + .1f, .04f), shutter);
            }
            Face(b, "flat", new Vector3(x0 + 4.0f, .2f, z0 + .15f), Vector3.right, 1f, Vector3.up, 2.1f, Vector3.back, X("5A4636"));
            BoxMM(b, "k_boards_warm", new Vector3(-1.2f, 0, -3.6f), new Vector3(1.2f, .25f, -2f), Own("k_boards_warm"));
            BoxMM(b, "flat", new Vector3(x0, 0, z0 - .02f), new Vector3(x1, .45f, z0 + .02f), X("7E6E62"));
        }

        // prop station: the same prefabs per variant, a original, b / c tinted copies
        static void PropStation(Transform root, string code, string district, string title, string[] prefabs, string ground, Color tb, Color tc, float spacing, float lookY = .7f)
        {
            var st = NewStation(root, code, district, title);
            StGround(st, ground);
            foreach (string v in VS)
            {
                Color? t = v == "a" ? null : v == "b" ? tb : tc;
                for (int i = 0; i < prefabs.Length; i++)
                {
                    float x = (i - (prefabs.Length - 1) / 2f) * spacing, z = (i % 2) * spacing * .5f;
                    Prop(prefabs[i], st.V[v], new Vector3(x, 0, z), 160f + i * 25f, 1f, t, code + v);
                }
                UseAsset(code, v, "props", v == "a" ? "prefabs unchanged: " + string.Join(", ", prefabs.Select(p => System.IO.Path.GetFileNameWithoutExtension(p)))
                    : $"{MatDir}/PropTint/T1_<material>_{code}{v}.mat (tint x {(t ?? W).r:0.00},{(t ?? W).g:0.00},{(t ?? W).b:0.00})");
            }
            float w = prefabs.Length * spacing;
            AddShot(st, "eye", new Vector3(-w * .18f, 1.7f, -w * .32f - 2.2f), new Vector3(0, lookY, spacing * .3f));
        }
    }
}
