using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Art.MapTexturesW86
{
    public static partial class TexW86T1
    {
        static void Sidewalk(Batch b, float x0, float x1, float z0, float z1)
        {
            Ground(b, "g_side", x0, z0, x1, z1, .15f, Own("g_side"));
            Box(b, "k_conc", new Vector3((x0 + x1) / 2, .075f, z0), new Vector3(x1 - x0, .15f, .2f), Own("k_conc"));
            Ground(b, "g_asph", x0, z0 - 9f, x1, z0, .0f, Own("g_asph"));
        }

        // ================================================================== DOWNTOWN specials (D4 / O1 consistent, real 3D windows)
        static void Downtown(Transform root)
        {
            SignWords();
            Lit("blue_lamp", X("6FA8FF"), null, 1, 1, .5f, 0, 0); S["blue_lamp"].M.EnableKeyword("_EMISSION"); S["blue_lamp"].M.SetColor("_EmissionColor", X("6FA8FF") * 1.5f);
            // T43 police / taxi depot / annex / arch house: D4 block with accents
            var st = NewStation(root, "T43", "downtown", "police, taxi depot, annex, arch house");
            { var g = new Batch(); Sidewalk(g, -40, 40, -4, 30); Flush(g, st.T, "T43_ground"); }
            Vars(st, (v, b, p) =>
            {
                var pal = v == "a" ? new DPal { Wall = "d4_plaster", Wc = X("5F6C75"), Gc = X("55616A"), Stone = X("CEC4B1"), Frame = X("2F3437") }
                        : v == "b" ? new DPal { Wall = "d4_brick", Wc = X("7A4437"), Gc = X("6A4034"), Stone = X("D1C8B6"), Frame = X("2F3437") }
                        : new DPal { Wall = "tt7_trav", Wc = X("D6CCB8"), Gc = X("3E3F40"), GroundWall = "tt7_stone", Stone = X("C9BFAA"), Frame = X("6A5434") };
                Use("T43", v, "upper walls", pal.Wall); Use("T43", v, "ground floor walls", pal.GroundWall ?? pal.Wall); Use("T43", v, "trims / cornice", "d4_trim");
                Use("T43", v, "frames, bands (vertex colour)", "d4_flat"); Use("T43", v, "glass", "d4_glass"); Use("T43", v, "sign letters", "sign_words");
                // police 05-10: 22 x 14 x 4 floors at x -24..-2
                DBlock(b, -24f, -2f, -2f, 12f, 4, 4.4f, 3.33f, pal, 3.4f, 1.4f, 1.9f);
                Box(b, "d4_flat", new Vector3(-13f, 4.95f, -2.12f), new Vector3(22.2f, .7f, .1f), X("2E4A7A"));
                SignText(b, 0, new Vector3(-13f, 4.95f, -2.2f), .42f, W);
                BoxMM(b, "d4_flat", new Vector3(-15f, 3.2f, -3.6f), new Vector3(-11f, 3.38f, -2f), X("2F3437"));
                foreach (float x in new[] { -15.3f, -10.7f }) Box(b, "blue_lamp", new Vector3(x, 2.4f, -2.12f), new Vector3(.25f, .4f, .14f), W);
                Cyl(b, "flat_metal", new Vector3(-23f, .15f, -3.2f), new Vector3(-23f, 9f, -3.2f), .06f, 8, X("C9C6C0"));
                // taxi depot 05-12: 16 x 12 x 2 floors at x 4..20, yellow band, 3 garage doors
                var tp = new DPal { Wall = pal.Wall, Wc = pal.Wc, Gc = pal.Gc, GroundWall = pal.GroundWall, Stone = pal.Stone, Frame = pal.Frame };
                DBlock(b, 4f, 20f, -2f, 10f, 2, 4.6f, 3.4f, tp, 4f, 1.4f, 1.8f, true, false);
                foreach (int i in new[] { 0, 1, 2 }) BoxMM(b, "tt7_shutter", new Vector3(5.3f + i * 4.8f, .15f, -2.06f), new Vector3(8.9f + i * 4.8f, 3.6f, -2.0f), X("7E8284"));
                Box(b, "d4_flat", new Vector3(12f, 4.1f, -2.12f), new Vector3(16.2f, .5f, .1f), X("E1B53A"));
                SignText(b, 1, new Vector3(12f, 4.1f, -2.2f), .36f, X("262628"));
            });
            AddShot(st, "police", new Vector3(-22f, 1.7f, -15f), new Vector3(-12f, 7f, 4f));
            AddShot(st, "taxi", new Vector3(4f, 1.7f, -13f), new Vector3(12f, 3.5f, 2f));

            // T44 base-4 garage (B101) + loft (B116): D4 brick + roller-shutter bays
            st = NewStation(root, "T44", "downtown", "base-4 garage and loft");
            { var g = new Batch(); Sidewalk(g, -30, 30, -4, 30); Flush(g, st.T, "T44_ground"); }
            Vars(st, (v, b, p) =>
            {
                Color wc = Pick3(v, X("6A4034"), X("3D3E3B"), X("A8AA9A")), door = Pick3(v, X("8C8F90"), X("E2DDD1"), X("33463D"));
                string wall = v == "c" ? "d4_plaster" : "d4_brick";
                Use("T44", v, "walls", wall); Use("T44", v, "garage doors (roller shutters)", "tt7_shutter"); Use("T44", v, "trims", "d4_trim");
                float x0 = -10f, x1 = 8f, z0 = -2f, z1 = 12f, h = 5.5f;
                var holes = new List<Rect>();
                for (int i = 0; i < 3; i++) holes.Add(Rect.MinMaxRect(1.2f + i * 5.2f, .02f, 5.0f + i * 5.2f, 3.9f));
                HoleWall(b, wall, new Vector3(x0, 0, z0), Vector3.right, Vector3.forward, x1 - x0, 0, h, holes, .35f, wc);
                Face(b, wall, new Vector3(x1, 0, z1), Vector3.left, x1 - x0, Vector3.up, h, Vector3.forward, wc);
                var side = new List<Rect> { Rect.MinMaxRect(2f, 3.9f, 5.6f, 5.0f), Rect.MinMaxRect(7f, 3.9f, 10.6f, 5.0f), Rect.MinMaxRect(11.5f, .02f, 12.6f, 2.3f) };
                HoleWall(b, wall, new Vector3(x0, 0, z1), Vector3.back, Vector3.right, z1 - z0, 0, h, side, .25f, wc);
                Face(b, wall, new Vector3(x1, 0, z0), Vector3.forward, z1 - z0, Vector3.up, h, Vector3.right, wc);
                foreach (var hr in holes)
                {
                    Face(b, "tt7_shutter", new Vector3(x0 + hr.xMin, hr.yMin, z0 + .3f), Vector3.right, hr.width, Vector3.up, hr.height, Vector3.back, door);
                    Box(b, "d4_trim", new Vector3(x0 + hr.center.x, hr.yMax + .18f, z0 - .04f), new Vector3(hr.width + .5f, .36f, .1f), X("CEC4B1"));
                    Box(b, "d4_flat", new Vector3(x0 + hr.center.x, hr.yMax - .25f, z0 + .2f), new Vector3(hr.width, .45f, .12f), X("3A3C3E"));
                }
                for (int i = 0; i < 2; i++) Window(b, new Vector3(x0, 0, z1), Vector3.back, Vector3.right, side[i], .25f, X("2F3437"), X("CEC4B1"), true, "d4_glass", "d4_flat", true);
                Face(b, "d4_flat", new Vector3(x0 + .25f, .02f, z1 - 11.5f), Vector3.back, 1.1f, Vector3.up, 2.28f, Vector3.left, X("33463D"));
                Ground(b, "d4_flat", x0, z0, x1, z1, h, X("4A4C4E"));
                Box(b, "d4_trim", new Vector3((x0 + x1) / 2, h - .15f, z0 - .1f), new Vector3(x1 - x0 + .3f, .35f, .22f), X("CEC4B1"));
                BoxMM(b, wall, new Vector3(x0, h, z0), new Vector3(x1, h + .7f, z0 + .3f), wc);
                // loft B116 next to it: 4 floors brick with big steel windows
                var lp = new DPal { Wall = wall, Wc = Mul(wc, 1.05f), Gc = Mul(wc, .95f), Stone = X("BDB5A5"), Frame = X("2B2D2F"), Lintel = true };
                DBlock(b, 10f, 26f, -2f, 12f, 4, 4.4f, 3.6f, lp, 4f, 2.6f, 2.4f, true, false);
            });
            AddShot(st, "eye", new Vector3(-14f, 1.7f, -14f), new Vector3(2f, 4f, 3f));

            // T45 van shop 05-07, gas station 05-41 (+ canopy), diner 05-40
            st = NewStation(root, "T45", "downtown", "van shop, gas station, diner");
            { var g = new Batch(); Sidewalk(g, -40, 40, -4, 30); Ground(g, "g_asph", -40, -3.9f, 40, -4f, .001f, Own("g_asph")); Flush(g, st.T, "T45_ground"); }
            Vars(st, (v, b, p) =>
            {
                var pal = v == "a" ? new DPal { Wall = "d4_plaster", Wc = X("C6BBA3"), Gc = X("B6A58F"), Stone = X("D1C8B6"), Frame = X("2F3437"), Shops = true }
                        : v == "b" ? new DPal { Wall = "d4_brick", Wc = X("8A4E3F"), Gc = X("6A4034"), Stone = X("CFC7B4"), Frame = X("33463D"), Shops = true }
                        : new DPal { Wall = "d4_plaster", Wc = X("3B4144"), Gc = X("33393C"), Stone = X("9EA2A4"), Frame = X("B9BDBF"), Shops = true };
                Color band = Pick3(v, X("A33A33"), X("33463D"), X("2E4A7A"));
                Use("T45", v, "walls", pal.Wall); Use("T45", v, "storefronts (glass)", "d4_glass"); Use("T45", v, "frames / canopy / bands (vertex colour)", "d4_flat"); Use("T45", v, "sign letters", "sign_words");
                // van shop: 12 x 10 x 2 floors
                DBlock(b, -34f, -22f, -2f, 8f, 2, 4.6f, 3.6f, pal, 3.6f, 1.5f, 1.8f, true, false);
                Box(b, "d4_flat", new Vector3(-28f, 4.25f, -2.12f), new Vector3(12.2f, .55f, .1f), band);
                SignText(b, 4, new Vector3(-28f, 4.25f, -2.2f), .38f, W);
                // diner: 14 x 8 x 4.5 single storey, glazing all along, banded fascia
                var dp = new DPal { Wall = pal.Wall, Wc = pal.Wc, Gc = pal.Gc, Stone = pal.Stone, Frame = pal.Frame, Shops = true };
                DBlock(b, -16f, -2f, -2f, 6f, 1, 4.5f, 3f, dp, 3.5f, 1.4f, 1.8f, false, true);
                Box(b, "d4_flat", new Vector3(-9f, 4.0f, -2.14f), new Vector3(14.3f, .8f, .14f), band);
                Box(b, "flat_gloss", new Vector3(-9f, 3.55f, -2.18f), new Vector3(14.3f, .08f, .1f), X("C9CDD0"));
                SignText(b, 3, new Vector3(-9f, 4.0f, -2.24f), .55f, W);
                // gas station shop 10 x 8 x 4 + canopy 14 x 9 on 4 columns, fascia band
                DBlock(b, 8f, 18f, 2f, 10f, 1, 4f, 3f, new DPal { Wall = pal.Wall, Wc = pal.Wc, Gc = pal.Gc, Stone = pal.Stone, Frame = pal.Frame, Shops = true }, 3.3f, 1.4f, 1.8f, false, false);
                BoxMM(b, "d4_flat", new Vector3(5f, 5.0f, -10f), new Vector3(21f, 5.25f, 0f), X("E9E6DF"));
                BoxMM(b, "d4_flat", new Vector3(4.9f, 4.4f, -10.1f), new Vector3(21.1f, 5.3f, -9.9f), X("E9E6DF"));
                BoxMM(b, "d4_flat", new Vector3(4.9f, 4.6f, -10.15f), new Vector3(21.1f, 4.85f, -10.1f), band);
                SignText(b, 2, new Vector3(13f, 4.85f, -10.2f), .5f, band);
                foreach (float x in new[] { 7f, 19f }) foreach (float z in new[] { -8f, -2f }) Box(b, "d4_flat", new Vector3(x, 2.5f, z), new Vector3(.4f, 5f, .4f), X("C9C6C0"));
                Ground(b, "k_conc", 5f, -10f, 21f, 1.9f, .02f, Own("k_conc"));
                foreach (float x in new[] { 10f, 16f }) Box(b, "d4_flat", new Vector3(x, .9f, -5f), new Vector3(.8f, 1.8f, .5f), X("D8D4CA"));
            });
            AddShot(st, "eye", new Vector3(-30f, 1.7f, -16f), new Vector3(-12f, 3f, 2f));
            AddShot(st, "gas", new Vector3(2f, 1.7f, -18f), new Vector3(13f, 3f, -2f));

            // T46 classical house B110 (stucco_SK3b, 3 floors, 13.8 m): pilasters, entablature, tall windows
            st = NewStation(root, "T46", "downtown", "classical house B110");
            { var g = new Batch(); Sidewalk(g, -40, 40, -4, 30); Flush(g, st.T, "T46_ground"); }
            Vars(st, (v, b, p) =>
            {
                var pal = v == "a" ? new DPal { Wall = "d4_plaster", Wc = X("D9D2C2"), Gc = X("C9C1AF"), GroundWall = "tt7_ashlar", Stone = X("E6E0D2"), Frame = X("E4DFD3"), Lintel = true }
                        : v == "b" ? new DPal { Wall = "tt7_trav", Wc = X("D8CFBC"), Gc = X("BDB5A5"), GroundWall = "tt7_ashlar", Stone = X("E0D8C6"), Frame = X("6A5434"), Lintel = true }
                        : new DPal { Wall = "d4_brick", Wc = X("94604A"), Gc = X("D1C8B6"), GroundWall = "tt7_ashlar", Stone = X("D1C8B6"), Frame = X("E2DDD1"), Lintel = true };
                Use("T46", v, "upper walls", pal.Wall); Use("T46", v, "rusticated ground floor", "tt7_ashlar"); Use("T46", v, "pilasters / entablature", "d4_trim");
                float x0 = -14f, x1 = 14f, z0 = -2f, z1 = 12f;
                DBlock(b, x0, x1, z0, z1, 3, 5.0f, 4.0f, pal, 4f, 1.5f, 2.6f, false, true);
                for (int i = 0; i <= 7; i++)
                {
                    float x = x0 + i * 4f;
                    Box(b, "d4_trim", new Vector3(x, 9.0f, z0 - .12f), new Vector3(.6f, 8.0f, .24f), pal.Stone);
                    Box(b, "d4_trim", new Vector3(x, 5.2f, z0 - .16f), new Vector3(.8f, .4f, .32f), pal.Stone);
                }
                Box(b, "d4_trim", new Vector3(0, 13.1f, z0 - .2f), new Vector3(x1 - x0 + .8f, 1.0f, .4f), pal.Stone);
                Box(b, "d4_trim", new Vector3(0, 13.7f, z0 - .35f), new Vector3(x1 - x0 + 1.2f, .25f, .7f), Mul(pal.Stone, .95f));
                for (int i = 0; i < 7; i++)
                {
                    float x = x0 + 2f + i * 4f;
                    var pts = new[] { new Vector3(x - 1.0f, 8.6f, z0 - .08f), new Vector3(x + 1.0f, 8.6f, z0 - .08f), new Vector3(x, 9.2f, z0 - .08f) };
                    TriN(b, "d4_flat", pts[0], pts[1], pts[2], Vector3.back, Vector2.zero, Vector2.right, Vector2.up, pal.Stone);
                }
                BoxMM(b, "d4_flat", new Vector3(-2.5f, 0, z0 - .8f), new Vector3(2.5f, .3f, z0), X("BDB5A5"));
            });
            AddShot(st, "eye", new Vector3(-14f, 1.7f, -16f), new Vector3(0f, 7f, 3f));

            // T54 square booth 05-36 + 8 flagpoles (DC3 family)
            Kit("flag", "T1_flag_fabric_albedo.png", 1f, "T1_flag_fabric_normal.png", .6f);
            st = NewStation(root, "T54", "downtown", "square booth and flagpoles");
            { var g = new Batch(); Ground(g, "g_side", -40, -40, 40, 40, .02f, Own("g_side")); Flush(g, st.T, "T54_ground"); }
            Vars(st, (v, b, p) =>
            {
                Color body = Pick3(v, X("2F3437"), X("33463D"), X("E4DFD3")), trim = Pick3(v, X("6E7276"), X("B08D57"), X("8E9396"));
                Use("T54", v, "booth body / trims (vertex colour)", "d4_flat"); Use("T54", v, "booth glass", "d4_glass"); Use("T54", v, "flags (fabric, vertex colour)", "flag");
                BoxMM(b, "d4_flat", new Vector3(-1.6f, 0, 0), new Vector3(1.6f, .9f, 2.2f), body);
                Face(b, "d4_glass", new Vector3(-1.5f, .9f, -.01f), Vector3.right, 3f, Vector3.up, 1.4f, Vector3.back, X("3E4B55"));
                BoxMM(b, "d4_flat", new Vector3(-1.6f, .9f, .1f), new Vector3(1.6f, 2.3f, 2.2f), body);
                BoxMM(b, "d4_flat", new Vector3(-2f, 2.3f, -.5f), new Vector3(2f, 2.5f, 2.5f), trim);
                Box(b, "d4_flat", new Vector3(0, .95f, -.15f), new Vector3(3.1f, .06f, .35f), trim);
                string[] fc = { "2E4A7A", "A33A33", "E9E6DF", "3F5E4A" };
                for (int i = 0; i < 4; i++)
                {
                    float x = 4.5f + i * 2.4f;
                    Cyl(b, "flat_metal", new Vector3(x, 0, 2f), new Vector3(x, 8f, 2f), .05f, 8, X("C9C6C0"));
                    Panel(b, "flag", new Vector3(x + .05f, 6.0f, 2f), Vector3.right, 1.8f, 1.2f, Vector3.back, new Rect(0, 0, 1.8f, 1.2f), X(fc[i]));
                    Panel(b, "flag", new Vector3(x + 1.85f, 6.0f, 2f), Vector3.left, 1.8f, 1.2f, Vector3.forward, new Rect(0, 0, 1.8f, 1.2f), X(fc[i]));
                }
            });
            AddShot(st, "eye", new Vector3(-4f, 1.7f, -8f), new Vector3(3f, 2.5f, 2f));

            // T55 square benches (DC3: concrete + larch)
            st = NewStation(root, "T55", "downtown", "square benches");
            { var g = new Batch(); Ground(g, "g_side", -40, -40, 40, 40, .02f, Own("g_side")); Flush(g, st.T, "T55_ground"); }
            Vars(st, (v, b, p) =>
            {
                for (int i = 0; i < 2; i++)
                {
                    float x = -2.5f + i * 5f;
                    if (v == "a") { Use("T55", v, "base", "tt7_conc"); Use("T55", v, "seat", "tt7_larch"); BoxMM(b, "tt7_conc", new Vector3(x - 1.5f, 0, -.3f), new Vector3(x + 1.5f, .38f, .3f), Own("tt7_conc")); for (int k = 0; k < 5; k++) BoxMM(b, "tt7_larch", new Vector3(x - 1.6f, .38f, -.32f + k * .13f), new Vector3(x + 1.6f, .45f, -.22f + k * .13f), Own("tt7_larch")); }
                    if (v == "b") { Use("T55", v, "frame (flat metal)", "flat_metal"); Use("T55", v, "slats", "tt7_teak"); foreach (float dx in new[] { -1.2f, 1.2f }) BoxMM(b, "flat_metal", new Vector3(x + dx - .04f, 0, -.3f), new Vector3(x + dx + .04f, .42f, .3f), X("2B2D2F")); for (int k = 0; k < 5; k++) BoxMM(b, "tt7_teak", new Vector3(x - 1.5f, .42f, -.32f + k * .13f), new Vector3(x + 1.5f, .47f, -.22f + k * .13f), Own("tt7_teak")); BoxMM(b, "tt7_teak", new Vector3(x - 1.5f, .55f, .3f), new Vector3(x + 1.5f, .9f, .36f), Own("tt7_teak")); }
                    if (v == "c") { Use("T55", v, "granite block", "tt7_stone"); BoxMM(b, "tt7_stone", new Vector3(x - 1.5f, 0, -.35f), new Vector3(x + 1.5f, .46f, .35f), X("9C9C98")); }
                }
            });
            AddShot(st, "eye", new Vector3(-3f, 1.7f, -4.5f), new Vector3(0f, .3f, .5f));

            // T56 lamps (MP flat colours): a black (as is), b white (DC3 square), c dark green -> recolour the dark parts
            RecolourStation(root, "T56", "downtown", "old-town street lamps", new[] { MPF + "LAMPS/lamp_oldtown_single.prefab", MPF + "LAMPS/lamp_oldtown_double.prefab" }, X("E4DFD3"), X("33463D"), 4f);
            // T57 square umbrellas: b cream canvas, c dark green
            RecolourStation(root, "T57", "downtown", "square umbrellas", new[] { MPF + "BEACH/beach_umbrella_red.prefab", MPF + "BEACH/beach_umbrella_red.prefab" }, X("E2D8C2"), X("3F5E4A"), 4f, true);

            Color db = new(.93f, .89f, .82f), dc = new(.80f, .82f, .86f);
            PropStation(root, "T59", "downtown", "fire hydrants", new[] { MPF + "TRAFFIC/fire_hydrant.prefab", MPF + "TRAFFIC/fire_hydrant.prefab" }, "g_side", db, dc * .9f, 1.5f);
            PropStation(root, "T60", "downtown", "road signs", new[] { MPF + "TRAFFIC/sign_stop.prefab", MPF + "TRAFFIC/sign_giveway.prefab" }, "g_side", db, dc * .9f, 2.2f);
            PropStation(root, "T61", "downtown", "parked sedans / hatchbacks", new[] { MPF + "CARS/car_sedan_red.prefab", MPF + "CARS/car_sedan_blue.prefab", MPF + "CARS/car_sedan_beige.prefab" }, "g_asph", db, dc * .9f, 5f);
            PropStation(root, "T62", "downtown", "yard bins", new[] { MPF + "BINS/garbage_container_closed.prefab", MPF + "BINS/trashbin_tipping.prefab" }, "g_side", db, dc * .9f, 2.5f);
            PropStation(root, "T64", "downtown", "bus stop 05-14", new[] { MPF + "BUS_STOP/busstop_shelter.prefab" }, "g_side", db, dc * .9f, 4f);

            // T63 metal bollards (SK6a): a as is, b black, c dark green
            st = NewStation(root, "T63", "downtown", "bollards");
            { var g = new Batch(); Sidewalk(g, -20, 20, -1, 10); Flush(g, st.T, "T63_ground"); }
            Vars(st, (v, b, p) =>
            {
                string k = v == "a" ? "cur_metal" : "k_metal"; Use("T63", v, "bollard", k);
                Color c = Pick3(v, Own("cur_metal"), X("2B2D2F"), X("33463D"));
                for (int i = 0; i < 6; i++)
                {
                    float x = -5f + i * 1.8f;
                    Cyl(b, k, new Vector3(x, .15f, -.5f), new Vector3(x, 1.05f, -.5f), .09f, 12, c);
                    Cyl(b, k, new Vector3(x, 1.05f, -.5f), new Vector3(x, 1.12f, -.5f), .11f, 12, c, true, .06f);
                }
            });
            AddShot(st, "eye", new Vector3(-6f, 1.6f, -4.5f), new Vector3(0f, .8f, -.5f));

            // T66 yards / parking / forecourt (concrete SK3c, 4 m tile)
            CopyOf("T66a_concrete", GEN + "/Materials/W85_concrete_SK3c_nofield.mat", m => { m.SetColor("_BaseColor", m.GetColor("_BaseColor") * .72f); }, 4, 4, false);
            S["T66a_concrete"].Own = Own("cur_sk3c");
            MapM("T66c_slabs", "T1_concrete_slabs_old_albedo.png", 6f, 4f, "T1_concrete_slabs_old_normal.png", .6f);
            DecalMaterials();
            st = NewStation(root, "T66", "downtown", "yards, parking 05-03, forecourts");
            { var g = new Batch(); Ground(g, "g_side", -60, -60, 60, 60, -.01f, Own("g_side")); Flush(g, st.T, "T66_ground"); }
            Vars(st, (v, b, p) =>
            {
                string k = Pick3(v, "T66a_concrete", "g_asph", "T66c_slabs"); Use("T66", v, "zone surface (Zone_05-*)", k); if (v == "b") Use("T66", v, "parking bays", "dec_marks_b");
                Ground(b, k, -14f, -2f, 14f, 18f, .02f, v == "a" ? Own("cur_sk3c") : v == "b" ? Own("g_asph") : W);
                if (v == "b") for (int i = 0; i < 9; i++) Decal(b, "dec_marks_b", new Vector3(-11f + i * 2.6f, .04f, 12f), 2.6f, 5.2f, 0, Cell(1, 3, 60, 60, 452, 452), W);
                Face(b, "d4_brick", new Vector3(-14f, 0, 18f), Vector3.right, 28f, Vector3.up, 9f, Vector3.back, X("7A4437"));
            });
            foreach (string v in VS)
            {
                Prop(MPF + "CARS/car_sedan_blue.prefab", st.V[v], new Vector3(-6f, .02f, 12f), 0f);
                Prop(MPF + "BINS/garbage_container_closed.prefab", st.V[v], new Vector3(8f, .02f, 16.5f), 180f);
            }
            AddShot(st, "eye", new Vector3(-6f, 1.7f, -6f), new Vector3(2f, .5f, 10f));

            // T67 alley plugs / yard walls (brick SK3a): a as is, b D4 brick + door, c D4 plaster + door
            st = NewStation(root, "T67", "downtown", "alley end plugs, yard walls");
            { var g = new Batch(); Ground(g, "g_asph_old", -30, -30, 30, 30, 0, Own("g_asph_old")); Flush(g, st.T, "T67_ground"); }
            Vars(st, (v, b, p) =>
            {
                string k = Pick3(v, "cur_brick", "d4_brick", "d4_plaster"); Color c = Pick3(v, Own("cur_brick"), X("6A4034"), X("9C8F7A"));
                Use("T67", v, "plug wall", k); if (v != "a") Use("T67", v, "door / frame / downpipe (vertex colour)", "d4_flat");
                var holes = v == "a" ? new List<Rect>() : new List<Rect> { Rect.MinMaxRect(3.4f, 0, 4.6f, 2.3f) };
                HoleWall(b, k, new Vector3(-4f, 0, 6f), Vector3.right, Vector3.forward, 8f, 0, 10f, holes, .25f, c);
                foreach (float x in new[] { -4.2f, 4.2f }) Face(b, "d4_brick", new Vector3(x, 0, -10f), Vector3.forward, 16f, Vector3.up, 12f, x < 0 ? Vector3.right : Vector3.left, X("7A4437"));
                if (v != "a")
                {
                    Face(b, "d4_flat", new Vector3(-.6f, 0, 6.25f), Vector3.right, 1.2f, Vector3.up, 2.3f, Vector3.back, X("33463D"));
                    FBox(b, "d4_flat", new Vector3(-4f, 0, 6f), Vector3.right, Vector3.forward, 4f, 2.45f, -.05f, new Vector3(1.6f, .2f, .12f), X("BDB5A5"));
                    Cyl(b, "flat_metal", new Vector3(2.8f, 0, 5.9f), new Vector3(2.8f, 10f, 5.9f), .06f, 8, X("5E6264"));
                }
            });
            AddShot(st, "eye", new Vector3(-1.5f, 1.7f, -6f), new Vector3(0f, 3f, 6f));

            // T123 road markings (decal quads on A5): a GPT cleaned, b own clean, c own worn
            st = NewStation(root, "T123", "downtown", "road markings");
            { var g = new Batch(); Ground(g, "g_side", -40, -40, 40, -7.6f, .15f, Own("g_side")); Ground(g, "g_side", -40, 7.6f, 40, 40, .15f, Own("g_side")); Ground(g, "g_asph", -40, -7.6f, 40, 7.6f, 0, Own("g_asph")); Flush(g, st.T, "T123_ground"); }
            Vars(st, (v, b, p) =>
            {
                string k = Pick3(v, "dec_gpt_marks", "dec_marks_b", "dec_marks_c"); Use("T123", v, "road marking atlas (mesh decals)", k);
                Rect solid, dash, stop, zebra, arrow;
                if (v == "a")
                {
                    solid = Rect.MinMaxRect(.1167f, .7979f, .1338f, .9521f); dash = Rect.MinMaxRect(.3667f, .7871f, .3838f, .9521f);
                    stop = Rect.MinMaxRect(.5479f, .8633f, .7021f, .8867f); zebra = Rect.MinMaxRect(.7998f, .8062f, .9487f, .9434f); arrow = Rect.MinMaxRect(.0957f, .5513f, .1553f, .6973f);
                }
                else
                {
                    solid = Cell(0, 0, 236, 32, 276, 480); dash = Cell(0, 1, 236, 32, 276, 240); stop = Cell(0, 2, 40, 226, 472, 286);
                    zebra = Cell(0, 3, 40, 40, 472, 472); arrow = Cell(1, 0, 182, 40, 330, 470);
                }
                // road along X (local), centre dashed line, edge lines, stop line + zebra at x 8..12, arrows
                for (float x = -38f; x < 6f; x += 6f) Decal(b, k, new Vector3(x + 1.5f, .02f, 0), .15f, 3f, 90f, dash, W);
                foreach (float z in new[] { -7f, 7f }) for (float x = -38f; x < 38f; x += 4f) Decal(b, k, new Vector3(x + 2f, .02f, z), .15f, 4f, 90f, solid, W);
                Decal(b, k, new Vector3(7.2f, .02f, -3.6f), 7f, .45f, 90f, stop, W);
                for (int i = 0; i < 3; i++) Decal(b, k, new Vector3(10.5f, .02f, -5f + i * 5f), 4.5f, 3f, 0f, zebra, W);
                Decal(b, k, new Vector3(-6f, .02f, -3.6f), .9f, 3f, -90f, arrow, W);
            });
            AddShot(st, "eye", new Vector3(-8f, 1.7f, -4.5f), new Vector3(9f, 0f, -1f));
        }

        // recolour station: dark parts (b / c colour) or the fabric (saturated) parts get an absolute colour
        static void RecolourStation(Transform root, string code, string district, string title, string[] prefabs, Color cb, Color cc, float spacing, bool fabric = false)
        {
            var st = NewStation(root, code, district, title);
            StGround(st, "g_side");
            foreach (string v in VS)
            {
                for (int i = 0; i < prefabs.Length; i++)
                {
                    var go = Prop(prefabs[i], st.V[v], new Vector3((i - (prefabs.Length - 1) / 2f) * spacing, 0, 0), 160f);
                    if (!go || v == "a") continue;
                    Color target = v == "b" ? cb : cc;
                    foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                    {
                        var ms = r.sharedMaterials;
                        for (int k = 0; k < ms.Length; k++)
                        {
                            var m = ms[k]; if (!m) continue;
                            string prop = m.HasProperty("_BaseColor") ? "_BaseColor" : m.HasProperty("_Color") ? "_Color" : null;
                            if (prop == null) continue;
                            Color c0 = m.GetColor(prop); Color.RGBToHSV(c0, out float hh, out float ss, out float vv);
                            string nm = m.name.ToLowerInvariant();
                            bool glow = nm.Contains("glow") || nm.Contains("light") || nm.Contains("glass") || nm.Contains("emiss") || nm.Contains("bulb") || m.IsKeywordEnabled("_EMISSION");
                            bool hit = !glow && (fabric ? ss > .35f && vv > .25f : vv < .32f);
                            if (!hit) continue;
                            string key = m.name + "_" + code + v;
                            if (!TintCache.TryGetValue(key, out var tm))
                            {
                                tm = new Material(m) { name = "T1_" + Safe(key) }; tm.SetColor(prop, target);
                                AssetDatabase.CreateAsset(tm, MatDir + "/PropTint/T1_" + Safe(key) + ".mat"); TintCache[key] = tm;
                            }
                            ms[k] = tm;
                        }
                        r.sharedMaterials = ms;
                    }
                }
                UseAsset(code, v, "props", v == "a" ? "prefabs unchanged" : $"{MatDir}/PropTint/T1_<material>_{code}{v}.mat ({(fabric ? "canvas" : "dark metal")} -> #{ColorUtility.ToHtmlStringRGB(v == "b" ? cb : cc)})");
            }
            AddShot(st, "eye", new Vector3(-3.5f, 1.7f, -6.5f), new Vector3(0, 2.6f, 0));
        }
    }
}
