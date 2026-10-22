using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Art.MapTexturesW86
{
    // The T2 groups: code (INVENTORY.md T-number, X* = surfaces the inventory missed that the chosen v07 sets do not cover), district,
    // three variants. Builders take a frame (front = -Z), a size (x length, y height, z depth; 0 = the W85 data size) and the variant.
    public static partial class TexW86T2
    {
        sealed class G
        {
            public string Code, District, Title;
            public Action<Transform> Make;
            public (string name, Vector3 pos, Vector3 target)[] Shots;
        }

        static (string, Vector3, Vector3) Sh(string n, float x, float y, float z, float tx, float ty, float tz) => (n, new Vector3(x, y, z), new Vector3(tx, ty, tz));

        static readonly List<G> Groups = new()
        {
            // ---------------- Construction
            new G { Code = "T69", District = "Construction", Title = "Old dormitory 34 x 11.2 m, 4 floors", Make = MakeT69,
                Shots = new[] { Sh("eye", -24, 1.7f, -30, 2, 6, 0), Sh("wide", -40, 14, -46, 0, 5, 0) } },
            new G { Code = "T79", District = "Construction", Title = "Transformer booth 4.4 x 4.4 m", Make = MakeT79,
                Shots = new[] { Sh("eye", -5, 1.7f, -6.5f, 0, 1.5f, 0) } },
            new G { Code = "XC1", District = "Construction", Title = "Fuel kiosk + canopy (gas station of the site)", Make = MakeXC1,
                Shots = new[] { Sh("eye", -11, 1.7f, -12, 2, 2.4f, 1) } },
            // ---------------- Port
            new G { Code = "T81", District = "Port", Title = "Storage tanks d 15.2 x 10 m", Make = MakeT81,
                Shots = new[] { Sh("eye", -14, 1.7f, -17, 2, 6, 2) } },
            new G { Code = "T89", District = "Port", Title = "Port yard 176 x 81 m + light masts", Make = MakeT89,
                Shots = new[] { Sh("eye", -14, 1.7f, -10, 4, .5f, 14), Sh("wide", -30, 10, -26, 4, 0, 14) } },
            new G { Code = "T90", District = "Port", Title = "Concrete pier / quay edge, bollards, fenders", Make = MakeT90,
                Shots = new[] { Sh("eye", 14, 2.9f, 22, 24, .9f, 30), Sh("side", 32, 1.8f, 6, 24, .8f, 14) } },
            // ---------------- Elite
            new G { Code = "T97", District = "Elite", Title = "Clipped hedges of the villa plots (183 blocks)", Make = MakeT97,
                Shots = new[] { Sh("eye", -8, 1.7f, -6, 2, 1.0f, 1) } },
            new G { Code = "T98", District = "Elite", Title = "Villa pools 14 x 5.4 m on decks", Make = MakeT98,
                Shots = new[] { Sh("eye", -8.5f, 2.2f, -6.5f, 0, .2f, 0) } },
            new G { Code = "T100", District = "Elite", Title = "Yacht piers (boards)", Make = MakeT100,
                Shots = new[] { Sh("eye", -4, 2.9f, 6, -7, 1.0f, 26) } },
            new G { Code = "T102", District = "Elite", Title = "Villa / cove loungers + umbrellas", Make = MakeT102,
                Shots = new[] { Sh("eye", -3.5f, 1.8f, -2.5f, 1, .5f, 2.2f) } },
            // ---------------- Quiet Valley
            new G { Code = "T106", District = "Valley", Title = "Sea waterfall rock (7 x 8 x 10 m block)", Make = MakeT106,
                Shots = new[] { Sh("eye", -9, 2.0f, -12, 0, 4.5f, 0) } },
            new G { Code = "XQ1", District = "Valley", Title = "Casino sign without a name (Q3 casino)", Make = MakeXQ1,
                Shots = new[] { Sh("eye", -6, 1.7f, -11, 1.5f, 4.8f, 0) } },
            // ---------------- Beach
            new G { Code = "T107", District = "Beach", Title = "Beach bars x2, rental hut, Elite cabana", Make = MakeT107,
                Shots = new[] { Sh("bar", -6, 1.7f, -10, 1, 1.9f, -1), Sh("huts", 10, 1.7f, -9, 23, 1.4f, 6) } },
            new G { Code = "T108", District = "Beach", Title = "Lifeguard towers (2)", Make = MakeT108,
                Shots = new[] { Sh("eye", 1, 1.7f, -8, 2.5f, 2.8f, 0) } },
            new G { Code = "T109", District = "Beach", Title = "Beach umbrellas (68) - colour sets", Make = MakeT109,
                Shots = new[] { Sh("eye", -4, 1.7f, -5, 2, 1.3f, 3) } },
            new G { Code = "T110", District = "Beach", Title = "Beach loungers (16) - colour sets", Make = MakeT110,
                Shots = new[] { Sh("eye", -3.5f, 1.5f, -3, .5f, .2f, 1.5f) } },
            new G { Code = "T112", District = "Beach", Title = "Pier, pier head, promenade, dune walks (boards)", Make = MakeT112,
                Shots = new[] { Sh("eye", 0, 2.9f, 2, 0, 1.0f, 30), Sh("dune", 18, 1.7f, -14, 22, .3f, 2) } },
            new G { Code = "T113", District = "Beach", Title = "Pier square (now Downtown M3 tiles)", Make = MakeT113,
                Shots = new[] { Sh("eye", -12, 1.7f, -10, 2, 0, 4) } },
            new G { Code = "T114", District = "Beach", Title = "Palms (beach 59 + Elite 16) - leaf / bark colour", Make = MakeT114,
                Shots = new[] { Sh("eye", -6, 1.7f, -10, 1, 5, 0) } },
            // ---------------- Tramduro
            new G { Code = "T115", District = "Tramduro", Title = "Palace 48 x 22 x 9.6 m (portico, columns, balustrade)", Make = MakeT115,
                Shots = new[] { Sh("eye", -18, 1.7f, -40, 0, 6, 0), Sh("close", -9, 1.7f, -22, 0, 5, -8) } },
            new G { Code = "T116", District = "Tramduro", Title = "Open arched hangar 44 x 30 x 8 m", Make = MakeT116,
                Shots = new[] { Sh("eye", -26, 1.7f, -28, 0, 3.5f, 0), Sh("wide", -46, 16, -44, 0, 3, 0) } },
            new G { Code = "T117", District = "Tramduro", Title = "Bridge KPP booth + boom barrier", Make = MakeT117,
                Shots = new[] { Sh("eye", -6, 1.7f, -10, -1, 1.5f, -1) } },
            new G { Code = "T120", District = "Tramduro", Title = "Monument pedestal, speech stage, portico steps", Make = MakeT120,
                Shots = new[] { Sh("eye", -2, 1.9f, -15, 2, 1.2f, -2) } },
            new G { Code = "T121", District = "Tramduro", Title = "Golf greens 8 x 7 m (inventory: 'flower beds')", Make = MakeT121,
                Shots = new[] { Sh("eye", -6, 1.7f, -8, 0, 0, 1) } },
            new G { Code = "T122", District = "Tramduro", Title = "Perimeter fence ~670 m + barbed wire", Make = MakeT122,
                Shots = new[] { Sh("eye", -14, 1.7f, -9, 4, 1.8f, 1) } },
            new G { Code = "XT1", District = "Tramduro", Title = "Military concrete (yard, aprons, plinths) + helipad", Make = MakeXT1,
                Shots = new[] { Sh("eye", -16, 4.5f, -20, 0, 0, 2) } },
            new G { Code = "T125", District = "Tramduro", Title = "Tramduro bridge on piers (parapets, kerbs, slab, piers)", Make = MakeT125,
                Shots = new[] { Sh("eye", -30, 3.0f, -24, 0, 6, 0), Sh("deck", -1.5f, 9.7f, -30, 0, 8.6f, 10) } },
        };

        // ================================================================== shared helpers for the stages
        static void Ground(Transform gr, string key, float half, string hex = null, float y = 0f)
        {
            var c = Group(gr, "ctx_ground"); var b = new Batch();
            Plane(b, key, F0, -half, -half, half, half, y, hex == null ? Own(key) : X(hex));
            Flush(b, c, curGroup + "_ground");
        }
        static void GroundR(Transform gr, string key, float x0, float z0, float x1, float z1, string hex = null, float y = 0f, string name = "ctx_ground")
        {
            var c = Group(gr, name); var b = new Batch();
            Plane(b, key, F0, x0, z0, x1, z1, y, hex == null ? Own(key) : X(hex));
            Flush(b, c, curGroup + "_" + name);
        }
        static void Sea(Transform gr, float x0, float z0, float x1, float z1, float y = -.3f)
        {
            var c = Group(gr, "ctx_sea"); var b = new Batch();
            Plane(b, "sea", F0, x0, z0, x1, z1, y, Color.white);
            Flush(b, c, curGroup + "_sea");
        }
        static readonly Fr F0 = Fr.Yaw(Vector3.zero, 0);

        // build three variants with one builder (size from the data)
        static void Three(Transform gr, Action<Batch, Fr, int, Transform> build)
        {
            for (int v = 0; v < 3; v++)
            {
                var t = Group(gr, Vars[v]); var b = new Batch();
                build(b, F0, v, t);
                Flush(b, t, curGroup + Vars[v]);
            }
        }

        static Vector3 Sz(Vector3 s, float x, float y, float z) => new(s.x > 0 ? s.x : x, s.y > 0 ? s.y : y, s.z > 0 ? s.z : z);
        static Color Shade(Color c, float k) => new(c.r * k, c.g * k, c.b * k, 1f);

        // builders for Generate(): code -> (batch, frame, size, variant, parent)
        static readonly Dictionary<string, Action<Batch, Fr, Vector3, int, Transform>> Builders = new()
        {
            ["T69"] = (b, f, s, v, t) => Dorm(b, f, s, v),
            ["T79"] = (b, f, s, v, t) => Transformer(b, f, s, v),
            ["XC1kiosk"] = (b, f, s, v, t) => Kiosk(b, f, s, v),
            ["XC1canopy"] = (b, f, s, v, t) => FuelCanopy(b, f, s, v),
            ["T81"] = (b, f, s, v, t) => Tank(b, f, s, v),
            ["T89mark"] = (b, f, s, v, t) => YardMarks(b, f, s, v),
            ["T98"] = (b, f, s, v, t) => Pool(b, f, s, v, false),
            ["T106"] = (b, f, s, v, t) => WaterfallRock(b, f, s, v),
            ["XQ1"] = (b, f, s, v, t) => CasinoSign(b, f, s, v),
            ["T107bar"] = (b, f, s, v, t) => BeachBar(b, f, s, v, genTint),
            ["T107hut"] = (b, f, s, v, t) => RentalHut(b, f, s, v, genTint),
            ["T107cabana"] = (b, f, s, v, t) => Cabana(b, f, s, v),
            ["T115"] = (b, f, s, v, t) => Palace(b, f, s, v),
            ["T116"] = (b, f, s, v, t) => Hangar(b, f, s, v),
            ["T117"] = (b, f, s, v, t) => KppBooth(b, f, s, v),
            ["T117barrier"] = (b, f, s, v, t) => Barrier(b, f, s, v),
            ["T120pedestal"] = (b, f, s, v, t) => Pedestal(b, f, s, v),
            ["T120stage"] = (b, f, s, v, t) => SpeechStage(b, f, s, v),
            ["T120steps"] = (b, f, s, v, t) => PorticoSteps(b, f, s, v),
            ["T121"] = (b, f, s, v, t) => GolfGreen(b, f, s, v),
            ["XT1heli"] = (b, f, s, v, t) => Helipad(b, f, s, v),
        };
        static readonly Dictionary<string, Action<Batch, List<Vector3>, int>> LineBuilders = new()
        {
            ["T97"] = (b, l, v) => HedgeLine(b, l, v, 1.8f, .9f),
            ["T122"] = (b, l, v) => PerimeterLine(b, l, v),
            ["T90"] = (b, l, v) => QuayEdgeLine(b, l, v),
        };

        // =========================================================================================== CONSTRUCTION
        // T69 old dormitory: 4 floors x 3 m, 10 bays, two entrances with canopies on the front (south), plinth, parapet, downpipes.
        static readonly string[][] DormPal =
        {   //          wall key, wall,    base key,     base,     frame,    lintel/trim, canopy
            new[] { "plaster", "DCC9A2", "brick_roman", "9A5A45", "F2F0EA", "EFE6D2", "CFC9BD" },
            new[] { "kh3", "E8E5DD", "conc", "B9B4A8", "8A6A4A", "C9C5BC", "BDB8AE" },
            new[] { "panel", "BDB7A9", "conc", "9C978C", "F2F0EA", "9A4A3A", "C4BFB4" },
        };
        static void Dorm(Batch b, Fr f, Vector3 size, int v)
        {
            var s = Sz(size, 34f, 12f, 11.2f); var p = DormPal[v];
            float L = s.x, D = s.z, H = s.y, plinth = .6f, fh = 2.75f;
            int floors = 4; float bay = L / 10f;
            Color wall = X(p[1]), bas = X(p[3]), frame = X(p[4]), trim = X(p[5]), can = X(p[6]);
            var corners = new[] { new Vector2(-L / 2, -D / 2), new Vector2(L / 2, -D / 2), new Vector2(L / 2, D / 2), new Vector2(-L / 2, D / 2) };
            float[] entr = { -L / 2 + bay * 2.5f, L / 2 - bay * 2.5f };
            for (int i = 0; i < 4; i++)
            {
                var w = f.Wall(corners[i], corners[(i + 1) % 4]);
                float WL = (corners[(i + 1) % 4] - corners[i]).magnitude;
                var holes = new List<Rect>();
                int nb = Mathf.Max(1, Mathf.RoundToInt(WL / bay));
                float bw = WL / nb;
                for (int k = 0; k < nb; k++)
                {
                    float cx = bw * (k + .5f);
                    bool front = i == 0, isEntr = front && entr.Any(e => Mathf.Abs(e + L / 2 - cx) < bw * .5f);
                    for (int fl = 0; fl < floors; fl++)
                    {
                        float y0 = plinth + fl * fh;
                        if (isEntr)
                        {
                            if (fl == 0) holes.Add(new Rect(cx - .8f, plinth, 1.6f, 2.3f));
                            else holes.Add(new Rect(cx - .45f, y0 - 1.0f, .9f, 1.3f));        // stair window between floors
                            continue;
                        }
                        if (i % 2 == 1 && (k == 0 || k == nb - 1)) continue;                    // blind end bays
                        holes.Add(new Rect(cx - .75f, y0 + .85f, 1.5f, 1.45f));
                    }
                }
                OpeningsWall(b, p[0], w, WL, plinth, H, wall, holes, .22f);
                WallBox(b, p[2], w, -.06f, WL + .06f, 0, plinth, .08f, bas);
                foreach (var h in holes)
                {
                    bool door = h.yMin <= plinth + .01f;
                    if (door)
                    {
                        Box(b, "flat", w, new Vector3(h.center.x, h.center.y, .2f), new Vector3(h.width, h.height, .06f), X("6B4A35"));
                        Box(b, "flat", w, new Vector3(h.center.x, h.center.y + .2f, .16f), new Vector3(.06f, h.height - .4f, .04f), X("4A3426"));
                        // canopy on brackets + steps
                        Box(b, p[0] == "plaster" ? "conc" : "conc", w, new Vector3(h.center.x, h.yMax + .45f, -.7f), new Vector3(2.6f, .16f, 1.4f), can);
                        Box(b, "flat", w, new Vector3(h.center.x - 1.1f, h.yMax + .15f, -.6f), new Vector3(.1f, .5f, 1.2f), can);
                        Box(b, "flat", w, new Vector3(h.center.x + 1.1f, h.yMax + .15f, -.6f), new Vector3(.1f, .5f, 1.2f), can);
                        Box(b, "conc", w, new Vector3(h.center.x, plinth - .18f, -.6f), new Vector3(2.4f, .2f, 1.2f), Shade(can, .95f));
                        Box(b, "conc", w, new Vector3(h.center.x, plinth - .42f, -.8f), new Vector3(2.4f, .2f, 1.6f), Shade(can, .9f));
                        continue;
                    }
                    Window(b, w, h, .22f, frame, trim, true);
                    if (v == 1) Box(b, "flat", w, new Vector3(h.center.x, h.yMax + .1f, -.01f), new Vector3(h.width + .3f, .2f, .04f), trim);   // concrete lintel
                }
                // downpipes at the wall ends (front and back)
                if (i % 2 == 0) foreach (float x in new[] { .25f, WL - .25f }) Box(b, "flat_metal", w, new Vector3(x, H / 2, -.1f), new Vector3(.12f, H, .12f), X("8E8E88"));
                // cornice band / string course
                WallBox(b, "flat", w, -.1f, WL + .1f, H - .35f, H - .05f, .12f, trim);
                if (v == 2 && i == 0) foreach (float e in entr) WallBox(b, "flat", w, e + L / 2 - 1.3f, e + L / 2 + 1.3f, plinth + 2.6f, H - .35f, .05f, trim);   // coloured stair cores
            }
            // roof + parapet
            Plane(b, "roof_flat", f, -L / 2, -D / 2, L / 2, D / 2, H - .1f, Own("roof_flat"));
            for (int i = 0; i < 4; i++)
            {
                var w = f.Wall(corners[i], corners[(i + 1) % 4]); float WL = (corners[(i + 1) % 4] - corners[i]).magnitude;
                Box(b, "conc", w, new Vector3(WL / 2, H + .25f, .1f), new Vector3(WL, .5f, .2f), Shade(wall, .97f));
                Box(b, "flat", w, new Vector3(WL / 2, H + .53f, .1f), new Vector3(WL + .04f, .06f, .28f), X("8E8E88"));
            }
        }

        static void MakeT69(Transform gr)
        {
            Ground(gr, "dirt", 160);
            Three(gr, (b, f, v, t) => { Dorm(b, f, Vector3.zero, v); Plane(b, "asph_light", f, -20, -14, 20, -5.6f, .02f, X("9C9A94")); });
        }

        // T79 transformer booth 4.4 x 4.4 x 2.8: double steel doors with louvres, flat roof overhang, warning triangle (no text)
        static readonly string[][] TrPal =
        {
            new[] { "kh3", "E8E5DD", "6E7F74", "conc", "BDB8AE" },
            new[] { "plaster", "B9C4B4", "7A7E80", "conc", "C4C0B8" },
            new[] { "wallpanel", "BDB8AA", "5E6A70", "conc", "B5B0A4" },
        };
        static void Transformer(Batch b, Fr f, Vector3 size, int v)
        {
            var s = Sz(size, 4.4f, 2.8f, 4.4f); var p = TrPal[v];
            float L = s.x, D = s.z, H = s.y;
            Color wall = X(p[1]), door = X(p[2]);
            var c = new[] { new Vector2(-L / 2, -D / 2), new Vector2(L / 2, -D / 2), new Vector2(L / 2, D / 2), new Vector2(-L / 2, D / 2) };
            for (int i = 0; i < 4; i++)
            {
                var w = f.Wall(c[i], c[(i + 1) % 4]); float WL = (c[(i + 1) % 4] - c[i]).magnitude;
                var holes = new List<Rect>();
                if (i == 0) holes.Add(new Rect(WL / 2 - .9f, 0, 1.8f, 2.2f));
                if (i == 2) holes.Add(new Rect(WL / 2 - .5f, 1.6f, 1.0f, .5f));
                OpeningsWall(b, p[0], w, WL, 0, H, wall, holes, .12f);
                if (v == 2) WallBox(b, "hazard", w, 0, WL, 0, .35f, .02f, Own("hazard"));
                foreach (var h in holes)
                {
                    Box(b, "flat_metal", w, new Vector3(h.center.x, h.center.y, .1f), new Vector3(h.width, h.height, .05f), door);
                    int n = Mathf.FloorToInt(h.height / .14f);
                    for (int k = 1; k < n; k += (h.height > 1 ? 1 : 1))
                        if (h.height < 1f || k < 5 || k > n - 5) Box(b, "flat_metal", w, new Vector3(h.center.x, h.yMin + k * .14f, .06f), new Vector3(h.width - .16f, .03f, .05f), Shade(door, .8f));
                    if (h.height > 1f)
                    {
                        Box(b, "flat_metal", w, new Vector3(h.center.x, h.center.y, .06f), new Vector3(.04f, h.height, .05f), Shade(door, .75f));
                        // warning triangle (yellow, black rim), no text
                        var tw = w; float ty = h.center.y + .25f, tx = h.center.x + .45f;
                        var mb = b["flat"];
                        Vector3 A = tw.P(tx - .2f, ty - .17f, .03f), B = tw.P(tx, ty + .18f, .03f), C = tw.P(tx + .2f, ty - .17f, .03f);
                        mb.Tri(A, B, C, Vector2.zero, Vector2.zero, Vector2.zero, X("26262A"));
                        Vector3 A2 = tw.P(tx - .15f, ty - .135f, .025f), B2 = tw.P(tx, ty + .125f, .025f), C2 = tw.P(tx + .15f, ty - .135f, .025f);
                        mb.Tri(A2, B2, C2, Vector2.zero, Vector2.zero, Vector2.zero, X("F0C23A"));
                    }
                }
            }
            Box(b, p[3], f, new Vector3(0, H + .1f, 0), new Vector3(L + .5f, .2f, D + .5f), X(p[4]));
            Plane(b, "conc", f, -L / 2 - .6f, -D / 2 - .6f, L / 2 + .6f, D / 2 + .6f, .03f, X("B5B0A6"));
        }
        static void MakeT79(Transform gr) { Ground(gr, "dirt", 80); Three(gr, (b, f, v, t) => Transformer(b, f, Vector3.zero, v)); }

        // XC1 fuel kiosk 5.2 x 5.6 x 2.8 (glazed front to the pumps, door, service window) + canopy 12 x 6.8, clear 4.6 m, 4 columns
        static readonly string[][] KioskPal =
        {   // wall key, wall, band, frame
            new[] { "panel", "F2F2EE", "C8372D", "3A3F42" },
            new[] { "panel", "DCE3E6", "2E5E9E", "3A3F42" },
            new[] { "trapez", "C9CCCC", "3E8A5A", "3A3F42" },
        };
        static void Kiosk(Batch b, Fr f, Vector3 size, int v)
        {
            var s = Sz(size, 5.2f, 2.8f, 5.6f); var p = KioskPal[v];
            float L = s.x, D = s.z, H = s.y;
            Color wall = X(p[1]), band = X(p[2]), frame = X(p[3]);
            var c = new[] { new Vector2(-L / 2, -D / 2), new Vector2(L / 2, -D / 2), new Vector2(L / 2, D / 2), new Vector2(-L / 2, D / 2) };
            for (int i = 0; i < 4; i++)
            {
                var w = f.Wall(c[i], c[(i + 1) % 4]); float WL = (c[(i + 1) % 4] - c[i]).magnitude;
                var holes = new List<Rect>();
                if (i == 0) { holes.Add(new Rect(.3f, .5f, WL - 1.9f, 1.9f)); holes.Add(new Rect(WL - 1.35f, 0, 1.0f, 2.2f)); }   // glazed front + door (to the pumps)
                if (i == 3) holes.Add(new Rect(WL / 2 - .6f, 1.0f, 1.2f, .9f));                     // service window (to the road)
                OpeningsWall(b, p[0], w, WL, 0, H, wall, holes, .12f);
                foreach (var h in holes)
                {
                    Box(b, "glass_dark", w, new Vector3(h.center.x, h.center.y, .1f), new Vector3(h.width, h.height, .01f), Color.white);
                    for (float x = h.xMin; x <= h.xMax + .01f; x += h.width / Mathf.Max(1, Mathf.Round(h.width / 1.2f)))
                        Box(b, "flat_metal", w, new Vector3(Mathf.Clamp(x, h.xMin + .03f, h.xMax - .03f), h.center.y, .08f), new Vector3(.06f, h.height, .06f), frame);
                    Box(b, "flat_metal", w, new Vector3(h.center.x, h.yMin + .03f, .08f), new Vector3(h.width, .06f, .06f), frame);
                    Box(b, "flat_metal", w, new Vector3(h.center.x, h.yMax - .03f, .08f), new Vector3(h.width, .06f, .06f), frame);
                }
                WallBox(b, "flat", w, -.15f, WL + .15f, H - .05f, H + .35f, .15f, band);
            }
            Box(b, "flat", f, new Vector3(0, H + .42f, 0), new Vector3(L + .3f, .08f, D + .3f), X("E6E6E2"));
            Box(b, "flat_metal", f, new Vector3(L / 2 - 1, H + .65f, D / 4), new Vector3(1.0f, .45f, .7f), X("C9CCCC"));      // AC unit
        }
        static void FuelCanopy(Batch b, Fr f, Vector3 size, int v)
        {
            var s = Sz(size, 12f, 4.6f, 6.8f); var p = KioskPal[v];
            float L = s.x, D = s.z, H = s.y;
            Color band = X(p[2]);
            foreach (float x in new[] { -L / 2 + 1.5f, L / 2 - 1.5f })
                foreach (float z in new[] { -D / 2 + 1.4f, D / 2 - 1.4f })
                {
                    Box(b, "flat", f, new Vector3(x, H / 2, z), new Vector3(.45f, H, .45f), X("F2F2EE"));
                    Box(b, "flat", f, new Vector3(x, .5f, z), new Vector3(.5f, 1.0f, .5f), band);
                }
            Box(b, "flat", f, new Vector3(0, H + .45f, 0), new Vector3(L, .9f, D), X("F2F2EE"), true);
            foreach (int sg in new[] { -1, 1 })
            {
                Box(b, "flat", f, new Vector3(0, H + .45f, sg * (D / 2 + .01f)), new Vector3(L + .02f, .26f, .04f), band);
                Box(b, "flat", f, new Vector3(sg * (L / 2 + .01f), H + .45f, 0), new Vector3(.04f, .26f, D + .02f), band);
            }
            for (int i = -2; i <= 2; i++) for (int j = -1; j <= 1; j += 2)
                    Box(b, "lamp_warm", f, new Vector3(i * 2.2f, H - .02f, j * 1.6f), new Vector3(1.2f, .04f, .3f), Color.white, true, false);
        }
        static void MakeXC1(Transform gr)
        {
            Ground(gr, "dirt", 90);
            Three(gr, (b, f, v, t) =>
            {
                Plane(b, "conc", f, -10, -6, 12, 10, .02f, X("BDB8AE"));
                FuelCanopy(b, f.Sub(0, 0, -1), Vector3.zero, v);
                Kiosk(b, f.Sub(10.5f, 0, -1.3f, 90), Vector3.zero, v);                                  // data: glazed front + door west to the pumps (yaw 90)
                Box(b, "flat", f, new Vector3(0, .5f, -1), new Vector3(3.6f, 1.0f, .9f), X("D9D7D0"));   // pump island stand-in
            });
        }

        // =========================================================================================== PORT
        // T81 storage tank d 15.2 x 10 m: welded shell (panel texture = plates), low cone roof, top rail, wind girder, caged ladder, bund
        static readonly string[][] TankPal =
        {   // shell, band, rail
            new[] { "F2F2EE", "5E8E86", "5E8E86" },
            new[] { "8FA5B5", "F2F2EE", "E8E8E4" },
            new[] { "5E8E86", "F2F2EE", "E3B23C" },
        };
        static void Tank(Batch b, Fr f, Vector3 size, int v)
        {
            var s = Sz(size, 15.2f, 10f, 15.2f); var p = TankPal[v];
            float r = s.x / 2, H = s.y;
            Color shell = X(p[0]), band = X(p[1]), rail = X(p[2]);
            Vector3 c = f.P(0, 0, 0);
            CylF(b, "panel", c, f.R, Vector3.up, f.F, r, H - 1.4f, 40, shell, false);
            CylF(b, "panel", c + Vector3.up * (H - 1.4f), f.R, Vector3.up, f.F, r, 1.4f, 40, band, false);
            CylF(b, "panel", c + Vector3.up * H, f.R, Vector3.up, f.F, r + .05f, 1.1f, 40, Shade(shell, .96f), true, false, .7f);
            Ring(b, "flat_metal", c + Vector3.up * (H - 2.2f), r, r + .45f, 40, Shade(band, .9f));
            for (int i = 0; i < 40; i++)
            {
                float a = 2 * Mathf.PI * i / 40;
                Vector3 d = f.R * Mathf.Sin(a) + f.F * Mathf.Cos(a), q = c + d * (r - .1f) + Vector3.up * H;
                Box(b, "flat_metal", Fr.Yaw(q, 0), new Vector3(0, .55f, 0), new Vector3(.05f, 1.1f, .05f), rail);
                float a1 = 2 * Mathf.PI * (i + 1) / 40; Vector3 d1 = f.R * Mathf.Sin(a1) + f.F * Mathf.Cos(a1);
                Beam(b, "flat_metal", q + Vector3.up * 1.1f, c + d1 * (r - .1f) + Vector3.up * (H + 1.1f), .05f, .05f, rail);
            }
            // caged ladder on the front-left
            Vector3 ld = (f.R * -.5f - f.F * .866f).normalized, lt = Vector3.Cross(Vector3.up, ld).normalized, lb = c + ld * (r + .35f);
            foreach (int sg in new[] { -1, 1 }) Beam(b, "flat_metal", lb + lt * sg * .25f, lb + lt * sg * .25f + Vector3.up * (H + 1.1f), .06f, .06f, rail);
            for (float y = .3f; y < H + 1; y += .3f) Beam(b, "flat_metal", lb - lt * .25f + Vector3.up * y, lb + lt * .25f + Vector3.up * y, .03f, .03f, rail);
            for (float y = 2.4f; y < H + 1; y += .9f)
                for (int k = 0; k < 6; k++)
                {
                    float a0 = Mathf.PI * k / 6, a1 = Mathf.PI * (k + 1) / 6;
                    Vector3 P(float a) => lb + Vector3.up * y + lt * Mathf.Cos(a) * .4f + ld * Mathf.Sin(a) * .5f;
                    Beam(b, "flat_metal", P(a0), P(a1), .04f, .04f, rail);
                }
            // bund wall (r + 4 m, 1 m) and a pipe
            float rb = r + 4f;
            CylF(b, "conc", c, f.R, Vector3.up, f.F, rb, 1.0f, 48, X("BDB8AE"), false);
            CylF(b, "conc", c, f.F, Vector3.up, f.R, rb - .3f, 1.0f, 48, X("B5B0A4"), false);
            Ring(b, "conc", c + Vector3.up * 1.0f, rb - .3f, rb, 48, X("C4C0B8"));
            CylAx(b, "flat_metal", c + f.R * (r + 2.2f) + Vector3.up * .8f, f.R, .22f, 4.4f, 12, X("8E8E88"));
        }
        static void MakeT81(Transform gr)
        {
            Ground(gr, "conc", 120, "C4C0B8");
            Three(gr, (b, f, v, t) => { Tank(b, f, Vector3.zero, v); Tank(b, f.Sub(22, 0, 13), Vector3.zero, v); });
        }

        // T89 port yard: map materials on a builder-style yard patch (tile 4 m) + painted bay lines (geometry) + light masts
        static void YardMarks(Batch b, Fr f, Vector3 size, int v)
        {
            if (v == 2) return;
            var s = Sz(size, 60f, 0f, 40f);
            Color line = v == 0 ? X("E3B23C") : X("E8E8E4"), walk = X("E3B23C");
            for (float x = -s.x / 2 + 3; x <= s.x / 2 - 3; x += 6f) Plane(b, "flat", f, x - .07f, -s.z / 2 + 4, x + .07f, -2, .07f, line);
            Plane(b, "flat", f, -s.x / 2 + 3, -2.07f, s.x / 2 - 3, -1.93f, .07f, line);
            if (v == 1) { Plane(b, "flat", f, -s.x / 2 + 1, 2, s.x / 2 - 1, 2.15f, .07f, walk); Plane(b, "flat", f, -s.x / 2 + 1, 3.3f, s.x / 2 - 1, 3.45f, .07f, walk); }
        }
        static void LightMast(Batch b, Fr f, float x, float z)
        {
            Cyl(b, "flat_metal", f.P(x, 0, z), .22f, 16, 10, X("C9CCCC"), true, .14f);
            Box(b, "flat_metal", f, new Vector3(x, 16.1f, z), new Vector3(1.6f, .3f, .5f), X("8E8E88"));
            for (int k = -1; k <= 1; k++) Box(b, "lamp_warm", f, new Vector3(x + k * .5f, 15.9f, z - .1f), new Vector3(.35f, .12f, .3f), Color.white);
        }
        static void MakeT89(Transform gr)
        {
            Ground(gr, "meadow", 200);
            var mats = new[] { MapMats["T89a_yard"].m, MapMats["T89b_yard"].m, MapMats["T89c_yard"].m };
            for (int v = 0; v < 3; v++)
            {
                var t = Group(gr, Vars[v]); var b = new Batch();
                MapFlat(t, "T89" + Vars[v] + "_Zone_06-yard", F0, new[] { new Vector2(-40, -30), new Vector2(40, -30), new Vector2(40, 40), new Vector2(-40, 40) }, .04f, 4f, mats[v]);
                YardMarks(b, F0.Sub(0, 0, 10), new Vector3(60, 0, 40), v);
                LightMast(b, F0, -12, 22); LightMast(b, F0, 20, 30);
                // two containers for scale (v07 P1 colours)
                Box(b, "trapez", F0, new Vector3(6, 1.3f, 14), new Vector3(12.2f, 2.6f, 2.44f), X("3E6A9A"));
                Box(b, "trapez", F0, new Vector3(6, 1.3f, 17), new Vector3(12.2f, 2.6f, 2.44f), X("A8473A"));
                Flush(b, t, curGroup + Vars[v]);
            }
        }

        // T90 concrete pier: deck (map material, builder Pier style 1.2 m over the sea + 0.4 m skirt) + edge band, bollards, fenders
        static void QuayEdgeLine(Batch b, List<Vector3> l, int v)
        {
            for (int i = 1; i < l.Count; i++)
            {
                Vector3 a = l[i - 1], c = l[i], d = c - a; d.y = 0; float L = d.magnitude; if (L < .1f) continue;
                d /= L; Vector3 n = Vector3.Cross(Vector3.up, d);              // n = left of the walking direction = the sea side
                var w = new Fr { O = a, R = d, F = -n };                        // wall frame: x along, z into the land
                if (v == 0) Box(b, "flat", w, new Vector3(L / 2, .02f, .25f), new Vector3(L, .04f, .5f), X("F0C23A"));
                else if (v == 1)
                {   // yellow / black hatch (atlas row 0) on the top of a 0.6 m kerb band
                    var s = S["hazard"]; var mb = b["hazard"];
                    Vector3 A = w.P(0, .12f, 0), B = w.P(0, .12f, .6f), C = w.P(L, .12f, .6f), D = w.P(L, .12f, 0);
                    mb.Quad(A, B, C, D, new(0, .755f), new(0, .995f), new(L / s.TU, .995f), new(L / s.TU, .755f), Own("hazard"));
                    Box(b, "conc", w, new Vector3(L / 2, .06f, .3f), new Vector3(L, .12f, .6f), X("C9C6BF"), false, false);
                }
                else Box(b, "stone", w, new Vector3(L / 2, .12f, .35f), new Vector3(L, .24f, .7f), X("9A9894"));
                for (float x = 3f; x < L - 1; x += 12f)
                {
                    Vector3 q = w.P(x, 0, .55f);
                    Cyl(b, "flat_metal", q, .18f, .55f, 10, X("2E2E30"), false);
                    Cyl(b, "flat_metal", q + Vector3.up * .55f, .28f, .1f, 10, X("2E2E30"));
                }
                for (float x = 6f; x < L - 1; x += 8f)
                    Box(b, v == 2 ? "teak" : "flat", w, new Vector3(x, -.45f, -.16f), new Vector3(.4f, .8f, .3f), v == 2 ? X("6B4A2E") : X("26262A"));
            }
        }
        static void MakeT90(Transform gr)
        {
            GroundR(gr, "conc", -80, -80, 80, -1, "C4C0B8", 1.2f);
            GroundR(gr, "conc", -80, -1, -2, 30, "C4C0B8", 1.2f, "ctx_ground2");
            Sea(gr, -120, -1, 140, 160);
            var mats = new[] { MapMats["T90a_pier"].m, MapMats["T90b_pier"].m, MapMats["T90c_pier"].m };
            var skirt = new[] { MapMats["T90a_skirt"].m, MapMats["T90b_skirt"].m, MapMats["T90c_skirt"].m };
            var poly = new[] { new Vector2(-2, -1), new Vector2(24, -1), new Vector2(24, 30), new Vector2(-2, 30) };
            for (int v = 0; v < 3; v++)
            {
                var t = Group(gr, Vars[v]); var b = new Batch();
                MapFlat(t, "T90" + Vars[v] + "_Pier_06-pier", F0, poly, 1.2f, 4f, mats[v]);
                MapStrip(t, "T90" + Vars[v] + "_PierSkirt_06-pier", F0, poly, .8f, 1.2f, 1f, 1f, skirt[v], true);
                QuayEdgeLine(b, new List<Vector3> { new(24, 1.2f, -1), new(24, 1.2f, 30), new(-2, 1.2f, 30) }, v);
                // piles under the deck
                for (float x = 0; x <= 24; x += 6) for (float z = 3; z <= 30; z += 6) Cyl(b, "conc", F0.P(x, -3, z), .35f, 3.8f, 10, X("A8A49A"), false);
                Flush(b, t, curGroup + Vars[v]);
            }
        }

        // =========================================================================================== ELITE
        // T97 hedge along a line: body + narrower crown + irregular top lumps, 3 m blocks (as the W85 hedge boxes)
        static readonly string[] HedgeKey = { "hedge_box", "hedge_laurel", "hedge_bougain" };
        static void HedgeLine(Batch b, List<Vector3> l, int v, float h, float wdt)
        {
            string key = HedgeKey[v];
            for (int i = 1; i < l.Count; i++)
            {
                Vector3 a = l[i - 1], c = l[i], d = c - a; d.y = 0; float L = d.magnitude; if (L < .1f) continue;
                d /= L; var w = new Fr { O = a, R = d, F = Vector3.Cross(d, Vector3.up) };
                int k = Mathf.Max(1, Mathf.CeilToInt(L / 3f));
                for (int j = 0; j < k; j++)
                {
                    float s0 = L * j / k, s1 = L * (j + 1) / k, sl = s1 - s0;
                    string id = $"{a.x:0}{a.z:0}{j}";
                    float hh = h * (.97f + .06f * Hash(id, 1));
                    Color col = Shade(Own(key), .96f + .08f * Hash(id, 2));
                    Box(b, key, w, new Vector3((s0 + s1) / 2, (hh - .25f) / 2 - .05f, 0), new Vector3(sl + .04f, hh - .15f, wdt), col);
                    Box(b, key, w, new Vector3((s0 + s1) / 2, hh - .14f, 0), new Vector3(sl + .02f, .2f, wdt - .14f), Shade(col, 1.04f), false);
                    int lumps = Mathf.Max(2, Mathf.RoundToInt(sl / .9f));
                    for (int m = 0; m < lumps; m++)
                    {
                        float x = s0 + sl * (m + .5f) / lumps + (Hash(id, 10 + m) - .5f) * .3f;
                        float lw = .55f + .35f * Hash(id, 20 + m), lh = .06f + .1f * Hash(id, 30 + m);
                        Box(b, key, w, new Vector3(x, hh - .04f + lh / 2, (Hash(id, 40 + m) - .5f) * .2f), new Vector3(lw, lh, wdt - .3f), Shade(col, 1.07f), false);
                    }
                }
            }
        }
        static void MakeT97(Transform gr)
        {
            Ground(gr, "lawn", 120);
            var mats = new[] { MapMats["T97a_hedge"].m, MapMats["T97b_hedge"].m, MapMats["T97c_hedge"].m };
            for (int v = 0; v < 3; v++)
            {
                var t = Group(gr, Vars[v]); var b = new Batch();
                HedgeLine(b, new List<Vector3> { new(-2, 0, 0), new(12, 0, 0), new(12, 0, 14) }, v, 1.8f, .9f);
                Plane(b, "setts_sand", F0, -8, -3.4f, 14, -.8f, .03f, X("D8C9A8"));
                Flush(b, t, curGroup + Vars[v]);
                // the W85 hedge as it is now (cube primitive, UV 0..1 per face) with the map material: proof of T2M_T97*
                for (int k = 0; k < 3; k++)
                {
                    var cube = GameObject.CreatePrimitive(PrimitiveType.Cube); cube.name = "T97" + Vars[v] + "_Hedge_07-V0x-plot_map"; cube.transform.SetParent(t, false);
                    Object.DestroyImmediate(cube.GetComponent<Collider>());
                    cube.transform.localPosition = new Vector3(-3.55f - k * 3.05f, .8f, 0); cube.transform.localScale = new Vector3(3.05f, 1.8f, .9f);
                    cube.GetComponent<MeshRenderer>().sharedMaterial = mats[v];
                }
            }
        }

        // T98 villa pool: deck raised 0.3 m on a stone plinth, basin 14 x 5.4 x 1.5 m in tiles, coping, water 0.12 m under the deck,
        // corner steps, chrome ladder. (W85 today: the pool / water sit under the lawn because the terrain is not cut - see report.)
        static readonly string[][] PoolPal =
        {   // deck key, deck, basin, coping key, coping, plinth key, plinth
            new[] { "deck_teak", null, "7FD3D8", "travertine", "E8DFCC", "rubble_grey", "B8B4AC" },
            new[] { "slab_lime", "EDE6D6", "A9DCE8", "marble", "F4F2EC", "conc", "D8D3C8" },
            new[] { "setts_sand", "D8C9A8", "3E6E80", "stone", "9A9894", "rubble_grey", "A8A49C" },
        };
        static void Pool(Batch b, Fr f, Vector3 size, int v, bool water = true)
        {
            var s = Sz(size, 21f, .3f, 9.5f); var p = PoolPal[v];
            float L = s.x, D = s.z, dy = s.y, pl = Mathf.Min(14f, L - 4f), pd = Mathf.Min(5.4f, D - 2.5f), depth = 1.5f;
            Color deck = p[1] == null ? Own(p[0]) : X(p[1]), basin = X(p[2]), cop = X(p[4]), plin = X(p[6]);
            float px = 0, pz = -.2f;
            // deck as four strips around the basin (coping 0.35 m inside them)
            float cw = .35f;
            Plane(b, p[0], f, -L / 2, -D / 2, L / 2, pz - pd / 2 - cw, dy, deck);
            Plane(b, p[0], f, -L / 2, pz + pd / 2 + cw, L / 2, D / 2, dy, deck);
            Plane(b, p[0], f, -L / 2, pz - pd / 2 - cw, px - pl / 2 - cw, pz + pd / 2 + cw, dy, deck);
            Plane(b, p[0], f, px + pl / 2 + cw, pz - pd / 2 - cw, L / 2, pz + pd / 2 + cw, dy, deck);
            var outer = new[] { new Vector2(-L / 2, -D / 2), new Vector2(L / 2, -D / 2), new Vector2(L / 2, D / 2), new Vector2(-L / 2, D / 2) };
            Skirt(b, p[5], f, outer, -.1f, dy, plin);
            // coping ring
            BoxF(b, p[3], f, new Vector3(px - pl / 2 - cw, dy, pz - pd / 2 - cw), new Vector3(px + pl / 2 + cw, dy + .05f, pz - pd / 2), cop);
            BoxF(b, p[3], f, new Vector3(px - pl / 2 - cw, dy, pz + pd / 2), new Vector3(px + pl / 2 + cw, dy + .05f, pz + pd / 2 + cw), cop);
            BoxF(b, p[3], f, new Vector3(px - pl / 2 - cw, dy, pz - pd / 2), new Vector3(px - pl / 2, dy + .05f, pz + pd / 2), cop);
            BoxF(b, p[3], f, new Vector3(px + pl / 2, dy, pz - pd / 2), new Vector3(px + pl / 2 + cw, dy + .05f, pz + pd / 2), cop);
            // basin (inward walls + floor) and steps
            var inner = new List<Vector2> { new(px - pl / 2, pz - pd / 2), new(px + pl / 2, pz - pd / 2), new(px + pl / 2, pz + pd / 2), new(px - pl / 2, pz + pd / 2) };
            Skirt(b, "mosaic", f, inner, dy - depth, dy, basin, true);
            Plane(b, "mosaic", f, px - pl / 2, pz - pd / 2, px + pl / 2, pz + pd / 2, dy - depth, Shade(basin, .92f));
            for (int k = 0; k < 3; k++) BoxF(b, "mosaic", f, new Vector3(px - pl / 2, dy - depth, pz - pd / 2), new Vector3(px - pl / 2 + 1.6f - k * .4f, dy - .35f - k * .38f, pz + pd / 2 - 2.6f), Shade(basin, 1.04f));
            // ladder
            foreach (float z in new[] { pz - .3f, pz + .3f })
            {
                Vector3 q = f.P(px + pl / 2 - .25f, dy, z);
                Beam(b, "flat_gloss", q + Vector3.up * .8f, q - Vector3.up * 1.0f, .04f, .04f, X("D9DBDC"));
                Beam(b, "flat_gloss", q + Vector3.up * .8f, q + Vector3.up * .8f + f.R * .4f, .04f, .04f, X("D9DBDC"));
            }
            // water surface (own transparent, the W85 water shader needs the map); the map keeps its Water_Pool mesh + water area
            if (!water) return;
            var mb = b["water_pool"];
            Vector3 A = f.P(px - pl / 2, dy - .12f, pz - pd / 2), B = f.P(px - pl / 2, dy - .12f, pz + pd / 2), C = f.P(px + pl / 2, dy - .12f, pz + pd / 2), Dd = f.P(px + pl / 2, dy - .12f, pz - pd / 2);
            mb.Quad(A, B, C, Dd, Vector2.zero, Vector2.up, Vector2.one, Vector2.right, Color.white);
        }
        static void MakeT98(Transform gr)
        {
            Ground(gr, "lawn", 120);
            Three(gr, (b, f, v, t) =>
            {
                Pool(b, f, Vector3.zero, v);
                var lo = new[] { PropMats["T102b_frame"], PropMats["T102b_bed"] };
                for (int k = 0; k < 2; k++) SetMats(Prop("BEACH/beach_sunlounger", t, new Vector3(-6 + k * 1.4f, .3f, -3.9f), 90), lo);
            });
        }

        // T100 Elite piers / T112 beach boards: builder Pier style decks (UV = world / 3 m) with the map materials
        static List<Vector2> PierPoly(int kind) => kind == 0
            ? new List<Vector2> { new(0, 0), new(28, 0), new(28, 14), new(24, 14), new(24, 4), new(0, 4) }
            : new List<Vector2> { new(-5, 0), new(5, 0), new(5, 30), new(15, 30), new(15, 42), new(-15, 42), new(-15, 30), new(-5, 30) };
        static void PierDecks(Transform t, string code, int kind, Material deck, Material skirt, Fr f)
        {
            var poly = PierPoly(kind);
            var tri = Triangulate(poly);
            var v3 = poly.Select(q => f.P(q.x, 1.2f, q.y)).ToList();
            var uv = v3.Select(q => new Vector2(q.x, q.z) / 3f).ToList();
            MapMesh(t, code + "_Pier", v3, uv, tri, deck);
            MapStrip(t, code + "_PierSkirt", f, poly, .8f, 1.2f, 1f, 1f, skirt, true);
            var b = new Batch();
            for (int i = 0; i < poly.Count; i++)
            {
                Vector2 a = poly[i], c = poly[(i + 1) % poly.Count]; float L = (c - a).magnitude;
                for (float s = 0; s < L; s += 4f) { var q = Vector2.Lerp(a, c, s / L); Cyl(b, "teak", f.P(q.x, -2, q.y), .14f, 3.0f, 8, X("5E4A38"), false); }
            }
            Flush(b, t, code + "_piles");
        }
        static List<int> Triangulate(List<Vector2> poly)
        {   // ear clipping (simple polygons, either winding), triangles facing up
            var idx = Enumerable.Range(0, poly.Count).ToList(); var tris = new List<int>();
            float area = 0; for (int i = 0; i < poly.Count; i++) { var a = poly[i]; var c = poly[(i + 1) % poly.Count]; area += a.x * c.y - c.x * a.y; }
            bool ccw = area > 0; int guard = 0;
            while (idx.Count > 3 && guard++ < 1000)
            {
                bool cut = false;
                for (int i = 0; i < idx.Count; i++)
                {
                    int i0 = idx[(i + idx.Count - 1) % idx.Count], i1 = idx[i], i2 = idx[(i + 1) % idx.Count];
                    Vector2 a = poly[i0], b = poly[i1], c = poly[i2];
                    float cr = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
                    if (ccw ? cr <= 1e-5f : cr >= -1e-5f) continue;
                    bool inside = false;
                    foreach (int j in idx)
                    {
                        if (j == i0 || j == i1 || j == i2) continue;
                        var p = poly[j];
                        float d1 = (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x), d2 = (c.x - b.x) * (p.y - b.y) - (c.y - b.y) * (p.x - b.x), d3 = (a.x - c.x) * (p.y - c.y) - (a.y - c.y) * (p.x - c.x);
                        if (ccw ? (d1 > 0 && d2 > 0 && d3 > 0) : (d1 < 0 && d2 < 0 && d3 < 0)) { inside = true; break; }
                    }
                    if (inside) continue;
                    if (ccw) tris.AddRange(new[] { i0, i2, i1 }); else tris.AddRange(new[] { i0, i1, i2 });
                    idx.RemoveAt(i); cut = true; break;
                }
                if (!cut) break;
            }
            if (idx.Count == 3) { if (ccw) tris.AddRange(new[] { idx[0], idx[2], idx[1] }); else tris.AddRange(new[] { idx[0], idx[1], idx[2] }); }
            return tris;
        }
        static void MakeT100(Transform gr)
        {
            GroundR(gr, "sand", -80, -80, 80, 2, null, .3f);
            Sea(gr, -120, 2, 120, 160, .0f);
            var deck = new[] { MapMats["T100a_deck"].m, MapMats["T100b_deck"].m, MapMats["T100c_deck"].m };
            for (int v = 0; v < 3; v++) { var t = Group(gr, Vars[v]); PierDecks(t, "T100" + Vars[v], 0, deck[v], deck[v], Fr.Yaw(new Vector3(-2, 0, 4), -90)); }
        }

        // T102 Elite loungers + umbrellas (prefabs, material sets) on a teak deck by the cove
        static void MakeT102(Transform gr)
        {
            Ground(gr, "sand", 60);
            var c = Group(gr, "ctx_deck"); var bb = new Batch();
            Plane(bb, "deck_teak", F0, -5, -3, 7, 5, .25f, Own("deck_teak"));
            Flush(bb, c, curGroup + "_deck");
            for (int v = 0; v < 3; v++)
            {
                var t = Group(gr, Vars[v]);
                for (int k = 0; k < 4; k++)
                {
                    var lo = Prop("BEACH/beach_sunlounger", t, new Vector3(-2.5f + k * 1.6f, .25f, 1.2f), 0);
                    var um = Prop(k % 2 == 0 ? "BEACH/beach_umbrella_red" : "BEACH/beach_umbrella_teal", t, new Vector3(-1.7f + k * 1.6f, .25f, 2.6f), 0);
                    SetMats(lo, LoungerSet("T102", v, k)); SetMats(um, UmbrellaSet("T102", v, k));
                }
            }
        }

        // =========================================================================================== QUIET VALLEY
        static readonly string[] RockKey = { "rockmacro", "rock_grey", "rock_warm" };
        static void WaterfallRock(Batch b, Fr f, Vector3 size, int v)
        {
            var s = Sz(size, 8f, 10f, 7f);
            string key = RockKey[v];
            Rock(b, key, f, new Vector3(0, s.y * .42f, 0), s, 61, Own(key), 6);
            Rock(b, key, f, new Vector3(-s.x * .45f, s.y * .2f, s.z * .15f), s * .55f, 62, Shade(Own(key), .95f), 4);
            Rock(b, key, f, new Vector3(s.x * .42f, s.y * .15f, -s.z * .2f), s * .4f, 63, Shade(Own(key), 1.03f), 4);
        }
        static void MakeT106(Transform gr)
        {
            GroundR(gr, "meadow", -100, -3, 100, 100, null, .05f);
            Sea(gr, -120, -200, 120, -3f, -.2f);
            var c = Group(gr, "ctx_fall"); var bb = new Batch();
            // waterfall sheet + foam (stand-ins: the W85 waterfall shader needs the map)
            var mb = bb["waterfall"];
            Vector3 A = new(-1.2f, -.2f, -3.2f), B = new(-1.4f, 9.6f, -2.2f), C = new(1.4f, 9.6f, -2.2f), D = new(1.2f, -.2f, -3.2f);
            mb.Quad(A, B, C, D, Vector2.zero, Vector2.up, Vector2.one, Vector2.right, Color.white);
            Ring(bb, "flat", new Vector3(0, -.1f, -3.4f), 0, 2.2f, 16, X("F2F6F8"));
            Flush(bb, c, curGroup + "_fall");
            Three(gr, (b, f, v, t) => WaterfallRock(b, f, Vector3.zero, v));
        }

        // XQ1 casino sign, no name: "CASINO" only. a: gold 3D letters on a black fascia + bulb rows; b: red neon tubes on a dark board with a
        // bulb border; c: vertical blade sign at the corner (letters stacked, gold), bulbs on both edges. Frame origin = sign centre on the wall.
        static readonly Dictionary<char, (float w, Vector2[][] strokes)> Font = new()
        {
            ['C'] = (.7f, new[] { Arc(.38f, .5f, .33f, .48f, 40, 320, 9) }),
            ['A'] = (.72f, new[] { new[] { new Vector2(0, 0), new Vector2(.36f, 1), new Vector2(.72f, 0) }, new[] { new Vector2(.16f, .36f), new Vector2(.56f, .36f) } }),
            ['S'] = (.68f, new[] { new[] { new Vector2(.66f, .84f), new Vector2(.5f, .98f), new Vector2(.2f, .98f), new Vector2(.05f, .82f), new Vector2(.09f, .62f), new Vector2(.35f, .52f), new Vector2(.6f, .42f), new Vector2(.66f, .2f), new Vector2(.5f, .02f), new Vector2(.2f, .02f), new Vector2(.03f, .16f) } }),
            ['I'] = (.22f, new[] { new[] { new Vector2(.11f, 0), new Vector2(.11f, 1) } }),
            ['N'] = (.7f, new[] { new[] { new Vector2(0, 0), new Vector2(0, 1), new Vector2(.7f, 0), new Vector2(.7f, 1) } }),
            ['O'] = (.76f, new[] { Arc(.38f, .5f, .35f, .48f, 0, 360, 14) }),
        };
        static Vector2[] Arc(float cx, float cy, float rx, float ry, float a0, float a1, int n)
        {
            var l = new Vector2[n + 1];
            for (int i = 0; i <= n; i++) { float a = Mathf.Deg2Rad * Mathf.Lerp(a0, a1, i / (float)n); l[i] = new Vector2(cx + Mathf.Cos(a) * rx, cy + Mathf.Sin(a) * ry); }
            return l;
        }
        // text in the wall frame w (x along, y up, z into the wall), left-bottom at (x, y), letter height h, stroke t, standing out by depth
        static float Text(Batch b, string key, Fr w, string text, float x, float y, float h, float t, float depth, Color col, float z0 = 0f)
        {
            Vector3 n = -w.F;
            foreach (char ch in text)
            {
                if (!Font.TryGetValue(ch, out var g)) { x += h * .4f; continue; }
                foreach (var st in g.strokes)
                    for (int i = 1; i < st.Length; i++)
                    {
                        Vector3 p0 = w.P(x + st[i - 1].x * h, y + st[i - 1].y * h, z0 - depth / 2), p1 = w.P(x + st[i].x * h, y + st[i].y * h, z0 - depth / 2);
                        Vector3 d = p1 - p0; float L = d.magnitude; if (L < 1e-4f) continue;
                        Vector3 Za = d / L, Xa = n, Ya = Vector3.Cross(Za, Xa);
                        OBox(b, key, (p0 + p1) / 2, Xa, Ya, Za, new Vector3(depth, t, L + t * .9f), col);
                    }
                x += (g.w + .22f) * h;
            }
            return x;
        }
        static float TextWidth(string text, float h) => text.Sum(ch => Font.TryGetValue(ch, out var g) ? (g.w + .22f) * h : h * .4f) - .22f * h;

        static void Bulbs(Batch b, Fr w, float x0, float x1, float y, float step, float z)
        {
            for (float x = x0; x <= x1 + .001f; x += step) Box(b, "bulb", w, new Vector3(x, y, z), new Vector3(.11f, .11f, .11f), Color.white);
        }
        static void CasinoSign(Batch b, Fr f, Vector3 size, int v)
        {
            const string word = "CASINO";
            if (v == 0)
            {
                float h = 1.15f, tw = TextWidth(word, h), W = tw + 1.6f, Hh = 1.9f;
                Box(b, "flat_gloss", f, new Vector3(0, 0, -.25f), new Vector3(W, Hh, .5f), X("1E1C1E"));
                Box(b, "flat_gold", f, new Vector3(0, Hh / 2 + .04f, -.25f), new Vector3(W + .08f, .08f, .54f), X("C9A64A"));
                Box(b, "flat_gold", f, new Vector3(0, -Hh / 2 - .04f, -.25f), new Vector3(W + .08f, .08f, .54f), X("C9A64A"));
                Text(b, "flat_gold", f, word, -tw / 2, -h / 2, h, .17f, .16f, X("D8B24E"), -.5f);
                Bulbs(b, f, -W / 2 + .2f, W / 2 - .2f, Hh / 2 - .18f, .38f, -.52f);
                Bulbs(b, f, -W / 2 + .2f, W / 2 - .2f, -Hh / 2 + .18f, .38f, -.52f);
            }
            else if (v == 1)
            {
                float h = 1.05f, tw = TextWidth(word, h), W = tw + 1.4f, Hh = 1.8f;
                Box(b, "flat", f, new Vector3(0, 0, -.1f), new Vector3(W, Hh, .2f), X("2B1A1E"));
                Text(b, "neon_red", f, word, -tw / 2, -h / 2, h, .08f, .08f, Color.white, -.22f);
                foreach (float yy in new[] { Hh / 2 - .12f, -Hh / 2 + .12f }) Box(b, "neon_white", f, new Vector3(0, yy, -.22f), new Vector3(W - .2f, .05f, .05f), Color.white);
                foreach (float xx in new[] { W / 2 - .1f, -W / 2 + .1f }) Box(b, "neon_white", f, new Vector3(xx, 0, -.22f), new Vector3(.05f, Hh - .2f, .05f), Color.white);
            }
            else
            {   // blade sign standing out of the wall (frame: x along the wall, z into the wall) - letters on both faces of the blade
                float h = .78f, Hb = 7.2f, Wb = 1.5f, T = .45f;
                var blade = f.Sub(0, 0, -Wb / 2 - .2f, 90);              // blade frame: x across the wall (out), z along the wall
                Box(b, "flat_gloss", blade, new Vector3(0, 0, 0), new Vector3(Wb, Hb, T), X("4A1420"));
                Box(b, "flat_gold", blade, new Vector3(0, Hb / 2 + .06f, 0), new Vector3(Wb + .12f, .12f, T + .06f), X("C9A64A"));
                Box(b, "flat_gold", blade, new Vector3(0, -Hb / 2 - .06f, 0), new Vector3(Wb + .12f, .12f, T + .06f), X("C9A64A"));
                foreach (int side in new[] { -1, 1 })
                {
                    var face = blade.Sub(0, 0, side * T / 2, side > 0 ? 180 : 0);
                    for (int i = 0; i < word.Length; i++)
                    {
                        string ch = word[i].ToString(); float lw = TextWidth(ch, h);
                        Text(b, "flat_gold", face, ch, -lw / 2, Hb / 2 - .55f - (i + 1) * 1.08f, h, .13f, .1f, X("D8B24E"), -.01f);
                    }
                    foreach (float xx in new[] { -Wb / 2 + .14f, Wb / 2 - .14f })
                        for (float yy = -Hb / 2 + .2f; yy < Hb / 2 - .1f; yy += .36f) Box(b, "bulb", face, new Vector3(xx, yy, -.04f), new Vector3(.1f, .1f, .1f), Color.white);
                }
                Box(b, "flat_metal", f, new Vector3(0, Hb / 2 - .4f, -.1f), new Vector3(.12f, .12f, .4f), X("2E2E30"));
            }
        }
        static void MakeXQ1(Transform gr)
        {
            Ground(gr, "asphalt", 80);
            var c = Group(gr, "ctx_casino"); var bb = new Batch();
            // Q3 casino front stand-in (v07 Q3 colours): burgundy plaster, gold trim, black canopy, entrance glass
            var w = F0.Wall(new Vector2(-14, 0), new Vector2(14, 0));
            Wall(bb, "plaster", w, 0, 28, 0, 7.2f, X("7A2E36"));
            WallBox(bb, "flat_gold", w, -.1f, 28.1f, 6.9f, 7.25f, .25f, X("C9A44C"));
            WallBox(bb, "flat_gold", w, -.1f, 28.1f, .0f, .5f, .12f, X("4A1420"));
            Box(bb, "flat", w, new Vector3(14, 3.4f, -1.6f), new Vector3(10, .3f, 3.2f), X("1E2022"));
            foreach (float x in new[] { 9.3f, 18.7f }) Box(bb, "flat_gold", w, new Vector3(x, 1.7f, -3.0f), new Vector3(.25f, 3.4f, .25f), X("C9A64A"));
            Box(bb, "glass_dark", w, new Vector3(14, 1.5f, -.03f), new Vector3(6, 3, .02f), Color.white);
            foreach (float x in new[] { 3f, 6f, 22f, 25f }) Box(bb, "glass_dark", w, new Vector3(x, 3.2f, -.03f), new Vector3(1.6f, 2.4f, .02f), Color.white);
            Flush(bb, c, curGroup + "_casino");
            for (int v = 0; v < 3; v++)
            {
                var t = Group(gr, Vars[v]); var b = new Batch();
                if (v < 2) CasinoSign(b, w.Sub(14, 5.2f, 0), Vector3.zero, v);
                else CasinoSign(b, w.Sub(27f, 6.4f, 0), Vector3.zero, v);
                Flush(b, t, curGroup + Vars[v]);
            }
        }

        // =========================================================================================== BEACH
        // T107 beach bar 16 x 8 x 3.4 (data: pastel art-deco cocktail bar, striped roof / awning, counter to the sea), rental hut 5 x 4,
        // Elite cabana 12 x 8 (open canopy). Front (-Z) = the sea.
        static void Awning(Batch b, Fr f, float x0, float x1, float yTop, float zTop, float yLow, float zLow, int row)
        {
            var s = S["stripes"]; var mb = b["stripes"];
            float v0 = 1f - (row + 1) / 8f + .01f, v1 = 1f - row / 8f - .01f;
            Vector3 A = f.P(x0, yLow, zLow), B = f.P(x0, yTop, zTop), C = f.P(x1, yTop, zTop), D = f.P(x1, yLow, zLow);
            mb.Quad(A, B, C, D, new(x0 / s.TU, v0), new(x0 / s.TU, v1), new(x1 / s.TU, v1), new(x1 / s.TU, v0), Own("stripes"));
            mb.Quad(D, C, B, A, new(x1 / s.TU, v0), new(x1 / s.TU, v1), new(x0 / s.TU, v1), new(x0 / s.TU, v0), Shade(Own("stripes"), .8f));
            // scalloped valance
            for (float x = x0; x < x1 - .01f; x += .5f)
            {
                Vector3 p0 = f.P(x, yLow, zLow), p1 = f.P(Mathf.Min(x + .5f, x1), yLow, zLow), pm = f.P(Mathf.Min(x + .25f, x1), yLow - .22f, zLow);
                float u0 = x / s.TU, u1 = Mathf.Min(x + .5f, x1) / s.TU;
                mb.Tri(p0, pm, p1, new(u0, v0 + .05f), new((u0 + u1) / 2, v0 + .02f), new(u1, v0 + .05f), Own("stripes"));
                mb.Tri(p1, pm, p0, new(u1, v0 + .05f), new((u0 + u1) / 2, v0 + .02f), new(u0, v0 + .05f), Own("stripes"));
            }
        }
        static void Stool(Batch b, Fr f, float x, float z, Color seat, int v)
        {
            Cyl(b, v == 1 ? "teak" : "flat_gloss", f.P(x, 0, z), .05f, .75f, 8, v == 1 ? X("6B4A2E") : X("D9DBDC"), false);
            Cyl(b, v == 1 ? "teak" : "flat", f.P(x, 0, z), .2f, .04f, 10, v == 1 ? X("6B4A2E") : X("B9BDBF"));
            Cyl(b, v == 1 ? "teak" : "flat", f.P(x, .75f, z), .21f, .08f, 10, seat);
        }
        static void HipRoof(Batch b, string key, Fr f, float x0, float z0, float x1, float z1, float y0, float rise, float inset, Color col)
        {
            var s = S[key]; var mb = b[key];
            Vector3 a = f.P(x0, y0, z0), bb = f.P(x1, y0, z0), c = f.P(x1, y0, z1), d = f.P(x0, y0, z1);
            Vector3 ta = f.P(x0 + inset, y0 + rise, z0 + inset), tb = f.P(x1 - inset, y0 + rise, z0 + inset), tc = f.P(x1 - inset, y0 + rise, z1 - inset), td = f.P(x0 + inset, y0 + rise, z1 - inset);
            float sl = Mathf.Sqrt(rise * rise + inset * inset);
            void Q(Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3, float L)
            {
                mb.Quad(p0, p3, p2, p1, new(0, 0), new(0, sl / s.TV), new(L / s.TU, sl / s.TV), new(L / s.TU, 0), col);
                mb.Quad(p1, p2, p3, p0, new(L / s.TU, 0), new(L / s.TU, sl / s.TV), new(0, sl / s.TV), new(0, 0), Shade(col, .7f));
            }
            Q(a, bb, tb, ta, x1 - x0); Q(bb, c, tc, tb, z1 - z0); Q(c, d, td, tc, x1 - x0); Q(d, a, ta, td, z1 - z0);
            if (inset * 2 < Mathf.Min(x1 - x0, z1 - z0) - .01f) mb.Quad(ta, td, tc, tb, Vector2.zero, Vector2.up, Vector2.one, Vector2.right, col);
        }
        static void BeachBar(Batch b, Fr f, Vector3 size, int v, string tint)
        {
            var s = Sz(size, 16f, 3.4f, 8f);
            float L = s.x, D = s.z, H = s.y;
            Color pastel = X(tint ?? "F6C9C4"), white = X("F4F2EC");
            int row = tint != null && tint.ToUpper().StartsWith("BF") ? 1 : 0;
            // deck under the whole bar
            Plane(b, v == 1 ? "deck_teak" : "deck_bleached", f, -L / 2 - 1, -D / 2 - 2.2f, L / 2 + 1, D / 2 + .5f, .12f, v == 1 ? Own("deck_teak") : Own("deck_bleached"));
            Box(b, v == 1 ? "deck_teak" : "deck_bleached", f, new Vector3(0, .05f, -.85f), new Vector3(L + 2, .1f, D + 2.7f), Shade(v == 1 ? Own("deck_teak") : Own("deck_bleached"), .8f), false, false);
            float zb = -.4f;                                            // back block from zb to D/2; open bar in front under the roof
            var bk = new[] { new Vector2(-L / 2, zb), new Vector2(L / 2, zb), new Vector2(L / 2, D / 2), new Vector2(-L / 2, D / 2) };
            string wk = v == 1 ? "deck_teak" : v == 2 ? "planks_w" : "plaster";
            Color wc = v == 1 ? Own("deck_teak") : v == 2 ? white : pastel;
            for (int i = 0; i < 4; i++)
            {
                var w = f.Wall(bk[i], bk[(i + 1) % 4]); float WL = (bk[(i + 1) % 4] - bk[i]).magnitude;
                var holes = new List<Rect>();
                if (i == 0) holes.Add(new Rect(WL / 2 - .5f, .12f, 1.0f, 2.2f));                   // door behind the counter
                if (i % 2 == 1) holes.Add(new Rect(WL / 2 - .45f, 1.5f, .9f, .9f));                 // side windows
                OpeningsWall(b, wk, w, WL, .12f, H - .1f, wc, holes, .1f);
                foreach (var h in holes)
                {
                    if (h.yMin < .2f) Box(b, "flat", w, new Vector3(h.center.x, h.center.y, .08f), new Vector3(h.width, h.height, .04f), v == 0 ? white : X("6E8A9A"));
                    else if (v == 0) { CylAx(b, "glass_dark", w.P(h.center.x, h.center.y, .05f), w.F, .38f, .02f, 16, Color.white); }
                    else Box(b, "glass_dark", w, new Vector3(h.center.x, h.center.y, .05f), new Vector3(h.width, h.height, .02f), Color.white);
                }
                if (v == 0) for (int k = 0; k < 3; k++) WallBox(b, "flat", w, -.05f, WL + .05f, 2.2f + k * .22f, 2.3f + k * .22f, .03f, white);   // speed lines
                if (v == 2) for (float x = .6f; x < WL; x += 1.2f) WallBox(b, "flat", w, x - .05f, x + .05f, .12f, H - .1f, .03f, i % 2 == 0 ? X("8EC5E8") : X("F4D35E"));
            }
            // counter (front of the open bar) + back shelf
            Color ctr = v == 0 ? white : v == 1 ? Own("deck_teak") : X("8EC5E8");
            Box(b, v == 1 ? "deck_teak" : "plaster", f, new Vector3(0, .65f, -D / 2 + .9f), new Vector3(L - 4f, 1.05f, .5f), ctr);
            Box(b, v == 1 ? "teak" : "terrazzo", f, new Vector3(0, 1.21f, -D / 2 + .85f), new Vector3(L - 3.8f, .07f, .75f), v == 1 ? X("8A5E3A") : Own("terrazzo"));
            foreach (int sg in new[] { -1, 1 }) Box(b, v == 1 ? "deck_teak" : "plaster", f, new Vector3(sg * (L / 2 - 2.25f), .65f, (-D / 2 + .9f + zb) / 2), new Vector3(.5f, 1.05f, zb + D / 2 - .9f), ctr);
            Box(b, "flat", f, new Vector3(0, 1.5f, zb - .2f), new Vector3(L - 5, .05f, .35f), X("E6E2D8"));
            for (int k = 0; k < 6; k++) Stool(b, f, -5 + k * 2f, -D / 2 - .1f, v == 0 ? (k % 2 == 0 ? X("2FA3A8") : X("E8735E")) : v == 1 ? X("6B4A2E") : X("2E4A78"), v);
            if (v == 1)
            {   // tiki: log posts + thatch hip roof
                foreach (float x in new[] { -L / 2 + .3f, L / 2 - .3f, -L / 6, L / 6 })
                    Cyl(b, "teak", f.P(x, 0, -D / 2 + .1f), .17f, H, 8, X("6B4A2E"), false);
                Box(b, "teak", f, new Vector3(0, H - .1f, -D / 2 + .1f), new Vector3(L, .25f, .3f), X("5E4030"));
                HipRoof(b, "thatch", f, -L / 2 - .9f, -D / 2 - 1.1f, L / 2 + .9f, D / 2 + .9f, H, 2.3f, 3.2f, Own("thatch"));
                foreach (float x in new[] { -L / 2 - .4f, L / 2 + .4f })
                {
                    Cyl(b, "teak", f.P(x, 0, -D / 2 - 1.3f), .05f, 1.9f, 6, X("6B4A2E"), false);
                    Box(b, "lamp_warm", f, new Vector3(x, 2.0f, -D / 2 - 1.3f), new Vector3(.16f, .22f, .16f), Color.white);
                }
                return;
            }
            // roof slab with rounded (chamfered) front corners, parapet, front columns
            Color slab = v == 0 ? white : X("F2F2EE");
            Box(b, "plaster", f, new Vector3(0, H - .12f, -.2f), new Vector3(L + .6f, .24f, D + .4f), slab);
            foreach (float x in new[] { -L / 2 + .3f, L / 2 - .3f }) Cyl(b, "flat", f.P(x, 0, -D / 2 + .1f), .2f, H - .24f, 12, white, false);
            if (v == 0)
            {
                foreach (var (x0, x1, z) in new[] { (-L / 2 - .3f, L / 2 + .3f, -D / 2 - .4f), (-L / 2 - .3f, L / 2 + .3f, D / 2) })
                    Box(b, "plaster", f, new Vector3(0, H + .15f, z + .08f), new Vector3(x1 - x0, .3f, .16f), slab);
                foreach (float x in new[] { -L / 2 - .22f, L / 2 + .22f }) Box(b, "plaster", f, new Vector3(x, H + .15f, -.2f), new Vector3(.16f, .3f, D + .4f), slab);
                // stepped art-deco crown over the centre (no text), neon outline
                Box(b, "plaster", f, new Vector3(0, H + .65f, -D / 2 - .3f), new Vector3(5.2f, 1.0f, .3f), pastel);
                Box(b, "plaster", f, new Vector3(0, H + 1.35f, -D / 2 - .3f), new Vector3(3.0f, .5f, .3f), pastel);
                Box(b, "plaster", f, new Vector3(0, H + 1.75f, -D / 2 - .3f), new Vector3(1.2f, .3f, .3f), pastel);
                for (int k = 0; k < 3; k++) Box(b, "flat", f, new Vector3(0, H + .35f + k * .22f, -D / 2 - .47f), new Vector3(4.6f, .08f, .04f), white);
                Box(b, "neon_white", f, new Vector3(0, H + 1.12f, -D / 2 - .48f), new Vector3(4.9f, .05f, .05f), Color.white);
                Awning(b, f, -L / 2 + 1.5f, L / 2 - 1.5f, H - .3f, -D / 2 - .4f, H - 1.0f, -D / 2 - 2.0f, row);
            }
            else
            {   // painted beach huts: pitched white metal roof + navy stripe awning
                var rs = S["trapez"]; var mb = b["trapez"];
                float y0 = H, y1 = H + 1.3f, zr0 = -D / 2 - .5f, zr1 = D / 2 + .3f, zm = (zr0 + zr1) / 2;
                foreach (var (za, zc) in new[] { (zr0, zm), (zr1, zm) })
                {
                    Vector3 A = f.P(-L / 2 - .4f, y0, za), B = f.P(-L / 2 - .4f, y1, zc), C = f.P(L / 2 + .4f, y1, zc), Dd = f.P(L / 2 + .4f, y0, za);
                    float sl = Mathf.Sqrt((zc - za) * (zc - za) + 1.69f);
                    if (za < zc) mb.Quad(A, B, C, Dd, new(0, 0), new(0, sl / rs.TV), new(L / rs.TU, sl / rs.TV), new(L / rs.TU, 0), X("F2F2EE"));
                    else mb.Quad(Dd, C, B, A, new(L / rs.TU, 0), new(L / rs.TU, sl / rs.TV), new(0, sl / rs.TV), new(0, 0), X("F2F2EE"));
                }
                foreach (int sg in new[] { -1, 1 })
                {
                    var g = b["planks_w"];
                    Vector3 A = f.P(sg * (L / 2), y0, zr0 + .5f), B = f.P(sg * (L / 2), y1, zm), C = f.P(sg * (L / 2), y0, zr1 - .3f);
                    if (sg > 0) g.Tri(A, B, C, Vector2.zero, new(.5f, .8f), Vector2.right, white); else g.Tri(C, B, A, Vector2.zero, new(.5f, .8f), Vector2.right, white);
                }
                Awning(b, f, -L / 2 + 1.5f, L / 2 - 1.5f, H - .3f, -D / 2 - .4f, H - 1.0f, -D / 2 - 2.0f, 2);
            }
        }
        static void RentalHut(Batch b, Fr f, Vector3 size, int v, string tint)
        {
            var s = Sz(size, 5f, 2.8f, 4f);
            float L = s.x, D = s.z, H = s.y;
            Color pastel = X(tint ?? "BFE7E4"), white = X("F4F2EC");
            string wk = v == 1 ? "deck_teak" : v == 2 ? "planks_w" : "plaster";
            Color wc = v == 1 ? Own("deck_teak") : v == 2 ? X("8EC5E8") : pastel;
            var c = new[] { new Vector2(-L / 2, -D / 2), new Vector2(L / 2, -D / 2), new Vector2(L / 2, D / 2), new Vector2(-L / 2, D / 2) };
            for (int i = 0; i < 4; i++)
            {
                var w = f.Wall(c[i], c[(i + 1) % 4]); float WL = (c[(i + 1) % 4] - c[i]).magnitude;
                var holes = new List<Rect>();
                if (i == 0) holes.Add(new Rect(.6f, 1.0f, WL - 1.2f, 1.1f));
                if (i == 1) holes.Add(new Rect(WL / 2 - .45f, 0, .9f, 2.1f));
                OpeningsWall(b, wk, w, WL, 0, H, wc, holes, .1f);
                foreach (var h in holes) Box(b, h.yMin < .1f ? "flat" : "glass_dark", w, new Vector3(h.center.x, h.center.y, .08f), new Vector3(h.width, h.height, .03f), h.yMin < .1f ? white : Color.white);
                if (i == 0)
                {
                    Box(b, "flat", w, new Vector3(WL / 2, .98f, -.2f), new Vector3(WL - 1.0f, .06f, .45f), white);
                    if (v == 1) Box(b, "thatch", w, new Vector3(WL / 2, 2.35f, -.6f), new Vector3(WL - .6f, .12f, 1.2f), Own("thatch"));
                    else Awning(b, w.Sub(0, 0, 0), .4f, WL - .4f, 2.35f, -.05f, 1.95f, -1.0f, v == 0 ? 0 : 2);
                }
                if (v == 0) for (int k = 0; k < 2; k++) WallBox(b, "flat", w, -.05f, WL + .05f, 2.3f + k * .2f, 2.38f + k * .2f, .03f, white);
            }
            if (v == 1) HipRoof(b, "thatch", f, -L / 2 - .7f, -D / 2 - .7f, L / 2 + .7f, D / 2 + .7f, H, 1.6f, 2.4f, Own("thatch"));
            else Box(b, "plaster", f, new Vector3(0, H + .1f, 0), new Vector3(L + .5f, .2f, D + .5f), white);
            // SUP / board rack (colourful boards)
            for (int k = 0; k < 4; k++) Box(b, "flat_gloss", f.Sub(L / 2 + .7f, 0, -1 + k * .45f), new Vector3(0, 1.4f, 0), new Vector3(.1f, 2.8f, .7f), X(new[] { "F2C14E", "2FA3A8", "E8735E", "F4F2EC" }[k]));
        }
        static void Cabana(Batch b, Fr f, Vector3 size, int v)
        {
            var s = Sz(size, 12f, 3f, 8f);
            float L = s.x, D = s.z, H = s.y;
            Plane(b, v == 2 ? "deck_bleached" : "deck_teak", f, -L / 2, -D / 2, L / 2, D / 2, .2f, v == 2 ? Own("deck_bleached") : Own("deck_teak"));
            Box(b, v == 2 ? "deck_bleached" : "deck_teak", f, new Vector3(0, .1f, 0), new Vector3(L, .2f, D), Shade(v == 2 ? Own("deck_bleached") : Own("deck_teak"), .8f), false, false);
            foreach (float x in new[] { -L / 2 + .3f, 0, L / 2 - .3f }) foreach (float z in new[] { -D / 2 + .3f, D / 2 - .3f })
                    Cyl(b, v == 1 ? "teak" : "flat", f.P(x, .2f, z), .12f, H - .2f, 10, v == 1 ? X("6B4A2E") : X("F4F2EC"), false);
            if (v == 1) HipRoof(b, "thatch", f, -L / 2 - .8f, -D / 2 - .8f, L / 2 + .8f, D / 2 + .8f, H, 2.0f, 3.0f, Own("thatch"));
            else
            {
                HipRoof(b, "canvas", f, -L / 2 - .3f, -D / 2 - .3f, L / 2 + .3f, D / 2 + .3f, H, 1.1f, 2.2f, X("F4F2EC"));
                for (float x = -L / 2 - .3f; x < L / 2; x += .6f) Box(b, "canvas", f, new Vector3(x + .3f, H - .1f, -D / 2 - .3f), new Vector3(.58f, .22f, .02f), X("EFE9DD"));
            }
            Box(b, "flat", f, new Vector3(0, .65f, D / 2 - .8f), new Vector3(6, .9f, .5f), v == 1 ? X("6B4A2E") : X("F4F2EC"));
        }
        static void MakeT107(Transform gr)
        {
            GroundR(gr, "sand", -160, -30, 160, 160);
            Sea(gr, -160, -400, 160, -30, -.25f);
            Three(gr, (b, f, v, t) =>
            {
                BeachBar(b, f, Vector3.zero, v, "F6C9C4");
                RentalHut(b, f.Sub(20, 0, 2), Vector3.zero, v, "BFE7E4");
                Cabana(b, f.Sub(26, 0, 13), Vector3.zero, v);
            });
        }

        // T108 lifeguard towers: prefab material sets (data tints: west #F4D35E, east #9BD08A)
        static void MakeT108(Transform gr)
        {
            GroundR(gr, "sand", -100, -26, 100, 100);
            Sea(gr, -160, -400, 160, -26, -.25f);
            for (int v = 0; v < 3; v++)
            {
                var t = Group(gr, Vars[v]);
                for (int k = 0; k < 2; k++) SetMats(Prop("BEACH/beach_lifeguard_tower", t, new Vector3(-1 + k * 6.5f, 0, 0), 180), TowerSet(v, k));
            }
        }
        static void MakeT109(Transform gr)
        {
            Ground(gr, "sand", 100);
            Sea(gr, -160, -400, 160, -30, -.25f);
            for (int v = 0; v < 3; v++)
            {
                var t = Group(gr, Vars[v]);
                for (int k = 0; k < 6; k++)
                {
                    var um = Prop(k % 2 == 0 ? "BEACH/beach_umbrella_red" : "BEACH/beach_umbrella_teal", t, new Vector3(-3 + (k % 3) * 4.2f, 0, (k / 3) * 4.5f), k * 37);
                    SetMats(um, UmbrellaSet("T109", v, k));
                }
            }
        }
        static void MakeT110(Transform gr)
        {
            Ground(gr, "sand", 100);
            Sea(gr, -160, -400, 160, -30, -.25f);
            for (int v = 0; v < 3; v++)
            {
                var t = Group(gr, Vars[v]);
                for (int k = 0; k < 6; k++) SetMats(Prop("BEACH/beach_sunlounger", t, new Vector3(-2 + (k % 3) * 1.5f, 0, (k / 3) * 3f), 0), LoungerSet("T110", v, k));
            }
        }
        static void MakeT112(Transform gr)
        {
            GroundR(gr, "sand", -80, -80, 80, 2, null, .3f);
            Sea(gr, -160, 2, 160, 200, .0f);
            var deck = new[] { MapMats["T112a_deck"].m, MapMats["T112b_deck"].m, MapMats["T112c_deck"].m };
            for (int v = 0; v < 3; v++)
            {
                var t = Group(gr, Vars[v]);
                PierDecks(t, "T112" + Vars[v], 1, deck[v], deck[v], Fr.Yaw(new Vector3(0, 0, -2), 0));
                // dune walk 2.4 m (builder Ribbon: UV across / 3, along / 3)
                var v3 = new List<Vector3>(); var uv = new List<Vector2>(); var tri = new List<int>();
                for (int k = 0; k <= 10; k++)
                {
                    float z = -12 + k * 2.4f, x = 22 + Mathf.Sin(k * .5f) * 1.2f;
                    v3.Add(new Vector3(x - 1.2f, .45f, z)); v3.Add(new Vector3(x + 1.2f, .45f, z));
                    uv.Add(new Vector2(0, z / 3f)); uv.Add(new Vector2(2.4f / 3f, z / 3f));
                    if (k > 0) { int n = v3.Count; tri.AddRange(new[] { n - 4, n - 2, n - 1, n - 4, n - 1, n - 3 }); }
                }
                MapMesh(t, "T112" + Vars[v] + "_Boardwalk_09-dune-walk", v3, uv, tri, deck[v]);
            }
        }
        static void MakeT113(Transform gr)
        {
            Ground(gr, "sand", 80);
            var mats = new[] { MapMats["T113a_plaza"].m, MapMats["T113b_plaza"].m, MapMats["T113c_plaza"].m };
            for (int v = 0; v < 3; v++)
            {
                var t = Group(gr, Vars[v]);
                MapFlat(t, "T113" + Vars[v] + "_Zone_09-pier-square", F0, new[] { new Vector2(-14, -8), new Vector2(14, -8), new Vector2(14, 14), new Vector2(-14, 14) }, .06f, 8f, mats[v]);
                var b = new Batch();
                foreach (float x in new[] { -6f, 6f }) { Prop("BENCHES/bench_park", t, new Vector3(x, .06f, 5), 0); }
                Flush(b, t, curGroup + Vars[v]);
            }
        }
        static void MakeT114(Transform gr)
        {
            GroundR(gr, "sand", -100, -40, 100, 100);
            Sea(gr, -160, -400, 160, -40, -.25f);
            for (int v = 0; v < 3; v++)
            {
                var t = Group(gr, Vars[v]);
                string[] names = { "Palm_A", "Palm_B", "Palm_C" };
                for (int k = 0; k < 3; k++)
                {
                    string path = v == 0 ? $"Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/{names[k]}_v04_03.prefab" : $"{PrefabDir}/{names[k]}_v04_03_T114{Vars[v]}.prefab";
                    var go = Prop(path, t, new Vector3(-4 + k * 5f, 0, k % 2 * 2f), k * 70);
                }
            }
        }

        // =========================================================================================== TRAMDURO
        // T115 palace 48 x 22 x 9.6 m: rusticated plinth, 3 floors of tall windows with surrounds (pediments on the piano nobile),
        // string courses, end pavilions with pilasters, central hexastyle portico with pediment on steps, cornice, balustrade, flag.
        static readonly string[][] PalacePal =
        {   //  wall key, wall,   trim key, trim,     base key,  base,     accent,   frame,    door,     roof
            new[] { "plaster", "F2EFE8", "marble", "F6F4EE", "marble", "E6E2D9", "C9A64A", "F4F2EC", "4A3A2E", "9A9A96" },
            new[] { "plaster", "E8DCC2", "travertine", "E2D6BC", "travertine", "D2C4A6", "8A6A3C", "6E5A3A", "3E4A3A", "A8A096" },
            new[] { "plaster", "E6C0B3", "plaster", "F4F0E8", "ashlar", "D8D2C6", "C9A64A", "F4F2EC", "4A3A2E", "9A9A96" },
        };
        static void Palace(Batch b, Fr f, Vector3 size, int v)
        {
            var s = Sz(size, 48f, 9.6f, 22f); var p = PalacePal[v];
            float L = s.x, D = s.z, H = s.y, pl = 1.0f;
            Color wall = X(p[1]), trim = X(p[3]), bas = X(p[5]), acc = X(p[6]), frame = X(p[7]), door = X(p[8]);
            float bay = 3.0f, portW = 18.4f, portD = 4.6f;
            var c = new[] { new Vector2(-L / 2, -D / 2), new Vector2(L / 2, -D / 2), new Vector2(L / 2, D / 2), new Vector2(-L / 2, D / 2) };
            float[] fy = { pl + .55f, 4.55f, 7.75f }; float[] fhgt = { 2.3f, 2.4f, 1.2f };
            for (int i = 0; i < 4; i++)
            {
                var w = f.Wall(c[i], c[(i + 1) % 4]); float WL = (c[(i + 1) % 4] - c[i]).magnitude;
                int nb = Mathf.Max(1, Mathf.RoundToInt(WL / bay)); float bw = WL / nb;
                var holes = new List<Rect>();
                for (int k = 0; k < nb; k++)
                {
                    float cx = bw * (k + .5f);
                    bool centre = i == 0 && Mathf.Abs(cx - WL / 2) < bw * .6f;
                    for (int fl = 0; fl < 3; fl++)
                    {
                        float ww = fl == 2 ? 1.1f : 1.35f;
                        if (centre && fl == 0) { holes.Add(new Rect(cx - 1.2f, pl, 2.4f, 3.4f)); continue; }   // main door
                        holes.Add(new Rect(cx - ww / 2, fy[fl], ww, fhgt[fl]));
                    }
                }
                OpeningsWall(b, p[0], w, WL, pl, H, wall, holes, .3f);
                // rusticated plinth
                WallBox(b, p[4], w, -.15f, WL + .15f, 0, pl, .15f, bas);
                WallBox(b, p[2], w, -.18f, WL + .18f, pl - .08f, pl + .06f, .2f, trim);
                foreach (var h in holes)
                {
                    if (h.yMin <= pl + .01f)
                    {   // double door with fanlight and frame
                        Box(b, "flat", w, new Vector3(h.center.x, pl + 1.4f, .26f), new Vector3(h.width, 2.8f, .06f), door);
                        Box(b, "flat", w, new Vector3(h.center.x, pl + 1.4f, .22f), new Vector3(.05f, 2.8f, .04f), Shade(door, .8f));
                        Box(b, "glass_dark", w, new Vector3(h.center.x, pl + 3.1f, .26f), new Vector3(h.width, .6f, .02f), Color.white);
                        Box(b, v == 1 ? "flat_metal" : "flat_gold", w, new Vector3(h.center.x, pl + 2.83f, .2f), new Vector3(h.width, .08f, .06f), acc);
                        WallBox(b, p[2], w, h.xMin - .35f, h.xMin, pl, h.yMax + .35f, .08f, trim);
                        WallBox(b, p[2], w, h.xMax, h.xMax + .35f, pl, h.yMax + .35f, .08f, trim);
                        WallBox(b, p[2], w, h.xMin - .35f, h.xMax + .35f, h.yMax, h.yMax + .35f, .08f, trim);
                        continue;
                    }
                    Window(b, w, h, .3f, frame, trim, h.height > 2f, "glass_dark", .16f, trim);
                    bool nobile = Mathf.Abs(h.yMin - fy[1]) < .1f;
                    if (nobile && i % 2 == 0)
                    {
                        int k = Mathf.FloorToInt(h.center.x / bw);
                        if (k % 2 == 0) Pediment(b, p[2], w, h.center.x, h.yMax + .16f, h.width + .7f, .45f, .14f, trim);
                        else WallBox(b, p[2], w, h.xMin - .3f, h.xMax + .3f, h.yMax + .16f, h.yMax + .32f, .16f, trim);
                        // little balcony balustrade under the piano-nobile windows of the front
                        if (i == 0)
                        {
                            Box(b, p[2], w, new Vector3(h.center.x, h.yMin - .12f, -.22f), new Vector3(h.width + .5f, .1f, .45f), trim);
                            for (float x = h.xMin - .15f; x <= h.xMax + .16f; x += .22f) Box(b, p[2], w, new Vector3(x, h.yMin - .38f, -.36f), new Vector3(.09f, .45f, .09f), trim);
                        }
                    }
                    else if (Mathf.Abs(h.yMin - fy[0]) < .1f) WallBox(b, p[2], w, h.xMin - .3f, h.xMax + .3f, h.yMax + .16f, h.yMax + .3f, .12f, trim);
                }
                // string courses, end-pavilion pilasters, cornice
                WallBox(b, p[2], w, -.1f, WL + .1f, 4.05f, 4.3f, .12f, trim);
                WallBox(b, p[2], w, -.1f, WL + .1f, 7.3f, 7.48f, .1f, trim);
                foreach (float x in new[] { .35f, bw * 2 - .1f, WL - bw * 2 + .1f, WL - .35f })
                    WallBox(b, p[2], w, x - .35f, x + .35f, pl, H - .5f, .14f, trim);
                WallBox(b, p[2], w, -.25f, WL + .25f, H - .5f, H - .2f, .3f, trim);
                WallBox(b, p[2], w, -.45f, WL + .45f, H - .2f, H, .5f, trim);
                // balustrade: base, balusters, top rail, pedestals every bay
                WallBox(b, p[2], w, -.4f, WL + .4f, H, H + .16f, .38f, trim);
                for (float x = -.3f; x <= WL + .3f; x += .3f)
                {
                    if (Mathf.Abs(((x + .3f) % bay) - 0f) < .15f) continue;
                    Box(b, p[2], w, new Vector3(x, H + .48f, -.2f), new Vector3(.13f, .5f, .13f), trim, false);
                }
                for (float x = -.3f; x <= WL + .35f; x += bay) Box(b, p[2], w, new Vector3(x, H + .45f, -.2f), new Vector3(.38f, .6f, .38f), trim, false);
                WallBox(b, p[2], w, -.42f, WL + .42f, H + .73f, H + .86f, .42f, trim);
            }
            Plane(b, "roof_flat", f, -L / 2, -D / 2, L / 2, D / 2, H - .05f, X(p[9]));
            // portico: floor, steps, 6 columns, entablature, pediment
            float z0 = -D / 2 - portD;
            Box(b, p[4], f, new Vector3(0, pl / 2, (z0 - D / 2) / 2), new Vector3(portW + 1.2f, pl, portD), bas);
            for (int k = 0; k < 5; k++)
                Box(b, p[4], f, new Vector3(0, pl * (4.5f - k) / 5f / 2, z0 - .45f * (k + .5f)), new Vector3(portW - 2 + k * .4f, pl * (5 - k) / 5f, .45f), Shade(bas, 1f - k * .01f));
            float colH = H - .9f - pl;
            for (int k = 0; k < 6; k++)
            {
                float x = -portW / 2 + 1.0f + k * (portW - 2.0f) / 5f, z = z0 + .7f;
                Box(b, p[2], f, new Vector3(x, pl + .15f, z), new Vector3(1.05f, .3f, 1.05f), trim);
                Cyl(b, p[2], f.P(x, pl + .3f, z), .43f, colH - .6f, 16, trim, false, .38f);
                Box(b, p[2], f, new Vector3(x, pl + colH - .15f, z), new Vector3(1.0f, .3f, 1.0f), trim);
                if (v != 1) Cyl(b, "flat_gold", f.P(x, pl + colH - .42f, z), .41f, .1f, 16, acc, false);
            }
            Box(b, p[2], f, new Vector3(0, H - .45f, (z0 + -D / 2) / 2 + .05f), new Vector3(portW + .4f, .9f, portD + .1f), trim);
            var wf = f.Wall(new Vector2(-L / 2, -D / 2), new Vector2(L / 2, -D / 2));
            Pediment(b, p[2], wf, L / 2, H, portW + .4f, 2.4f, portD + .05f, trim);
            var tym = wf.Sub(0, 0, -portD - .06f);
            CylAx(b, v == 1 ? "flat_metal" : "flat_gold", tym.P(L / 2, H + .95f, -.03f), wf.F, .55f, .06f, 20, acc);    // plain disc emblem
            // roof flag
            Cyl(b, "flat_metal", f.P(0, H, 0), .07f, 6.5f, 8, X("D9DBDC"), true);
            Box(b, "flat_gold", f, new Vector3(0, H + 6.6f, 0), new Vector3(.2f, .2f, .2f), acc);
            Box(b, "canvas", f, new Vector3(1.3f, H + 5.6f, 0), new Vector3(2.4f, .8f, .03f), X("2F6B4F"));
            Box(b, "canvas", f, new Vector3(1.3f, H + 5.07f, 0), new Vector3(2.4f, .26f, .031f), X("F4F2EC"));
        }
        static void MakeT115(Transform gr)
        {
            Ground(gr, "lawn", 200);
            var c = Group(gr, "ctx_forecourt"); var bb = new Batch();
            Plane(bb, "slab_lime", F0, -14, -40, 14, -15.6f, .03f, X("E6E0D2"));
            Flush(bb, c, curGroup + "_court");
            Three(gr, (b, f, v, t) => Palace(b, f, Vector3.zero, v));
        }

        // T116 open arched hangar 44 x 30 x 8: segmental arch (posts 3 m), corrugated sheet roof, ribs every 6 m, closed back wall
        static readonly string[][] HangarPal =
        {   // roof key, roof, ribs, back key, back
            new[] { "wave", "8A8656", "5E6B3E", "wallpanel", "C9C2B0" },
            new[] { "camo", null, "3E4232", "camo", null },
            new[] { "wave", "4E5A3E", "2F3A2C", "wallpanel", "B4A57A" },
        };
        static void Hangar(Batch b, Fr f, Vector3 size, int v)
        {
            var s = Sz(size, 44f, 8f, 30f); var p = HangarPal[v];
            float W = s.x, H = s.y, D = s.z, post = 3f;
            Color roof = p[1] == null ? Own(p[0]) : X(p[1]), rib = X(p[2]), back = p[4] == null ? Own(p[3]) : X(p[4]);
            float half = W / 2, sag = H - post, R = (half * half + sag * sag) / (2 * sag), cy = H - R;
            int n = 16;
            Vector2 ArcP(int i) { float x = -half + W * i / n; return new Vector2(x, cy + Mathf.Sqrt(R * R - x * x)); }
            var rs = S[p[0]]; var mb = b[p[0]];
            float arc = 0;
            for (int i = 0; i < n; i++)
            {
                Vector2 a = ArcP(i), c2 = ArcP(i + 1); float seg = (c2 - a).magnitude;
                Vector3 A = f.P(a.x, a.y, -D / 2), B = f.P(c2.x, c2.y, -D / 2), C = f.P(c2.x, c2.y, D / 2), Dd = f.P(a.x, a.y, D / 2);
                mb.Quad(A, Dd, C, B, new(-D / 2 / rs.TU, arc / rs.TV), new(D / 2 / rs.TU, arc / rs.TV), new(D / 2 / rs.TU, (arc + seg) / rs.TV), new(-D / 2 / rs.TU, (arc + seg) / rs.TV), roof);
                mb.Quad(B, C, Dd, A, new(-D / 2 / rs.TU, (arc + seg) / rs.TV), new(D / 2 / rs.TU, (arc + seg) / rs.TV), new(D / 2 / rs.TU, arc / rs.TV), new(-D / 2 / rs.TU, arc / rs.TV), Shade(roof, .62f));
                arc += seg;
            }
            for (float z = -D / 2; z <= D / 2 + .01f; z += 6f)
            {
                for (int i = 0; i < n; i++) { Vector2 a = ArcP(i), c2 = ArcP(i + 1); Beam(b, "flat_metal", f.P(a.x, a.y - .25f, z), f.P(c2.x, c2.y - .25f, z), .3f, .5f, rib); }
                foreach (int sg in new[] { -1, 1 }) Box(b, "flat_metal", f, new Vector3(sg * (half - .2f), post / 2, z), new Vector3(.4f, post, .4f), rib);
            }
            foreach (int sg in new[] { -1, 1 }) Box(b, "flat_metal", f, new Vector3(sg * (half - .2f), post - .2f, 0), new Vector3(.3f, .4f, D), rib);
            // back wall under the arch (vertical strips)
            var bs = S[p[3]]; var bm = b[p[3]];
            for (int i = 0; i < n; i++)
            {
                Vector2 a = ArcP(i), c2 = ArcP(i + 1);
                float x0 = a.x, x1 = c2.x;
                Vector3 A = f.P(x1, 0, D / 2), B = f.P(x1, c2.y, D / 2), C = f.P(x0, a.y, D / 2), Dd = f.P(x0, 0, D / 2);
                bm.Quad(Dd, C, B, A, new(-x0 / bs.TU, 0), new(-x0 / bs.TU, a.y / bs.TV), new(-x1 / bs.TU, c2.y / bs.TV), new(-x1 / bs.TU, 0), back);
                bm.Quad(A, B, C, Dd, new(-x1 / bs.TU, 0), new(-x1 / bs.TU, c2.y / bs.TV), new(-x0 / bs.TU, a.y / bs.TV), new(-x0 / bs.TU, 0), Shade(back, .75f));
            }
            Plane(b, "conc", f, -half - 1, -D / 2 - 6, half + 1, D / 2 + .5f, .04f, X("B9B4A8"));
            for (int k = -2; k <= 2; k++) Plane(b, "flat", f, k * 8 - .07f, -D / 2 - 5, k * 8 + .07f, D / 2 - 3, .05f, X("E3B23C"));
        }
        static void MakeT116(Transform gr) { Ground(gr, "conc", 150, "BDB8AE"); Three(gr, (b, f, v, t) => Hangar(b, f, Vector3.zero, v)); }

        // T117 KPP booth 6.4 x 5.2 x 3.2 with ribbon windows, roof overhang, searchlight + boom barrier (arm 6.4 m)
        static readonly string[][] KppPal =
        {   // wall key, wall, base, frame, roof, arm row (hazard atlas), post
            new[] { "wallpanel", "B9B4A4", "6B6A4E", "3E4232", "BDB8AE", "2", "3E4232" },
            new[] { "plaster", "F2EFE8", "C9A64A", "F4F2EC", "F4F2EC", "2", "F4F2EC" },
            new[] { "conc", "9A9580", "8A7D5A", "3E4232", "8E8A7E", "0", "26262A" },
        };
        static void KppBooth(Batch b, Fr f, Vector3 size, int v)
        {
            var s = Sz(size, 6.4f, 3.2f, 5.2f); var p = KppPal[v];
            float L = s.x, D = s.z, H = s.y;
            Color wall = X(p[1]), bas = X(p[2]), frame = X(p[3]);
            var c = new[] { new Vector2(-L / 2, -D / 2), new Vector2(L / 2, -D / 2), new Vector2(L / 2, D / 2), new Vector2(-L / 2, D / 2) };
            for (int i = 0; i < 4; i++)
            {
                var w = f.Wall(c[i], c[(i + 1) % 4]); float WL = (c[(i + 1) % 4] - c[i]).magnitude;
                var holes = new List<Rect> { new Rect(.5f, 1.1f, WL - 1.0f - (i == 0 ? 1.4f : 0), 1.2f) };
                if (i == 0) holes.Add(new Rect(WL - 1.4f, 0, .9f, 2.2f));
                OpeningsWall(b, p[0], w, WL, 0, H, wall, holes, .15f);
                WallBox(b, v == 1 ? "flat_gold" : "flat", w, -.05f, WL + .05f, 0, v == 1 ? .25f : .6f, .04f, bas);
                foreach (var h in holes)
                {
                    if (h.yMin < .1f) { Box(b, "flat_metal", w, new Vector3(h.center.x, h.center.y, .12f), new Vector3(h.width, h.height, .05f), Shade(frame, 1.2f)); continue; }
                    Box(b, "glass_dark", w, new Vector3(h.center.x, h.center.y, .12f), new Vector3(h.width, h.height, .02f), Color.white);
                    for (float x = h.xMin; x <= h.xMax + .01f; x += h.width / Mathf.Max(1, Mathf.Round(h.width / 1.1f)))
                        Box(b, "flat_metal", w, new Vector3(Mathf.Clamp(x, h.xMin + .03f, h.xMax - .03f), h.center.y, .1f), new Vector3(.06f, h.height, .05f), frame);
                    Box(b, "flat", w, new Vector3(h.center.x, h.yMin - .04f, 0), new Vector3(h.width + .1f, .08f, .3f), frame);
                }
            }
            Box(b, v == 1 ? "plaster" : "conc", f, new Vector3(0, H + .12f, 0), new Vector3(L + 1.0f, .24f, D + 1.0f), X(p[4]));
            if (v == 1) Box(b, "flat_gold", f, new Vector3(0, H + .27f, 0), new Vector3(L + 1.04f, .06f, D + 1.04f), X("C9A64A"));
            Cyl(b, "flat_metal", f.P(L / 2 - .6f, H + .24f, -D / 2 + .6f), .06f, .6f, 8, X("2E2E30"), false);
            CylAx(b, "flat_metal", f.P(L / 2 - .6f, H + .95f, -D / 2 + .5f), f.F, .22f, .45f, 12, X("3A3F42"));
            if (v == 2)
            {   // sandbag ring around the base
                for (int i = 0; i < 4; i++)
                {
                    var w = f.Wall(c[i], c[(i + 1) % 4]); float WL = (c[(i + 1) % 4] - c[i]).magnitude;
                    for (int r = 0; r < 3; r++)
                        for (float x = (r % 2) * .3f - .2f; x < WL + .2f; x += .6f)
                        {
                            if (i == 0 && x > WL - 1.6f && x < WL - .3f) continue;
                            Box(b, "canvas", w, new Vector3(x + .3f, .12f + r * .24f, -.45f), new Vector3(.56f, .22f, .4f), X(r % 2 == 0 ? "B4A57A" : "A89A70"));
                        }
                }
            }
        }
        static void Barrier(Batch b, Fr f, Vector3 size, int v)
        {
            var p = KppPal[v]; float L = size.x > 0 ? size.x : 6.4f; int row = int.Parse(p[5]);
            Box(b, "flat_metal", f, new Vector3(0, .55f, 0), new Vector3(.4f, 1.1f, .4f), X(p[6]));
            Box(b, "flat_metal", f, new Vector3(-.5f, .95f, 0), new Vector3(.6f, .3f, .3f), X("3A3F42"));
            var s = S["hazard"]; var mb = b["hazard"];
            float v0 = 1f - (row + 1) / 4f + .03f, v1 = v0 + .16f;
            float y0 = .9f, y1 = 1.04f, z0 = -.06f, z1 = .06f;
            Vector3 P(float x, float y, float z) => f.P(x, y, z);
            mb.Quad(P(0, y0, z0), P(0, y1, z0), P(L, y1, z0), P(L, y0, z0), new(0, v0), new(0, v1), new(L / s.TU, v1), new(L / s.TU, v0), Own("hazard"));
            mb.Quad(P(L, y0, z1), P(L, y1, z1), P(0, y1, z1), P(0, y0, z1), new(L / s.TU, v0), new(L / s.TU, v1), new(0, v1), new(0, v0), Own("hazard"));
            mb.Quad(P(0, y1, z0), P(0, y1, z1), P(L, y1, z1), P(L, y1, z0), new(0, v0), new(0, v1), new(L / s.TU, v1), new(L / s.TU, v0), Own("hazard"));
            mb.Quad(P(0, y0, z1), P(0, y0, z0), P(L, y0, z0), P(L, y0, z1), new(0, v0), new(0, v1), new(L / s.TU, v1), new(L / s.TU, v0), Own("hazard"));
            Box(b, "flat_metal", f, new Vector3(L - .1f, .45f, 0), new Vector3(.12f, .9f, .12f), X(p[6]));
            Box(b, "flat", f, new Vector3(.35f, 1.1f, -.22f), new Vector3(.14f, .14f, .05f), X("C8372D"));
        }
        static void MakeT117(Transform gr)
        {
            Ground(gr, "lawn", 100);
            Three(gr, (b, f, v, t) =>
            {
                Plane(b, "asphalt", f, -20, -9, 20, -2.6f, .02f, Own("asphalt"));
                KppBooth(b, f, Vector3.zero, v);
                Barrier(b, f.Sub(-5.2f, 0, -3.0f, 180), new Vector3(6.4f, 0, 0), v);
            });
        }

        // T120 pedestal (stepped 4.8 x 4.8 x 1.3), speech stage 16 x 9 x 0.8 with steps + lectern + carpet, portico steps 10 x 4
        static readonly string[][] StagePal =
        {   // stone key, stone, cloth, metal
            new[] { "marble", "F2F0EA", "A8302C", "C9A64A" },
            new[] { "stone", "55585C", "6E1F2A", "8A6A3C" },
            new[] { "travertine", "E2D6BC", "2B3A5E", "C9A64A" },
        };
        static void Pedestal(Batch b, Fr f, Vector3 size, int v)
        {
            var p = StagePal[v]; float S0 = size.x > 0 ? size.x : 4.8f, H = size.y > 0 ? size.y : 1.3f;
            for (int k = 0; k < 3; k++) Box(b, p[0], f, new Vector3(0, H / 3 * (k + .5f), 0), new Vector3(S0 - k * .8f, H / 3, S0 - k * .8f), Shade(X(p[1]), 1f - k * .015f));
            Box(b, v == 1 ? "flat_metal" : "flat_gold", f, new Vector3(0, H + .03f, 0), new Vector3(S0 - 1.55f, .06f, S0 - 1.55f), X(p[3]));
        }
        static void SpeechStage(Batch b, Fr f, Vector3 size, int v)
        {
            var p = StagePal[v]; var s = Sz(size, 16f, .8f, 9f);
            float L = s.x, D = s.z, H = s.y;
            Color stone = X(p[1]), cloth = X(p[2]), metal = X(p[3]);
            Plane(b, p[0], f, -L / 2, -D / 2, L / 2, D / 2, H, stone);
            var c = new List<Vector2> { new(-L / 2, -D / 2), new(L / 2, -D / 2), new(L / 2, D / 2), new(-L / 2, D / 2) };
            Skirt(b, "canvas", f, c, 0, H - .08f, cloth);
            Skirt(b, v == 1 ? "flat_metal" : "flat_gold", f, c, H - .08f, H, metal);
            for (int k = 0; k < 4; k++) Box(b, p[0], f, new Vector3(0, H * (k + .5f) / 4 - H / 8 + .0f, -D / 2 - .5f * (4 - k) + .25f), new Vector3(8f, H * (k + 1) / 4, .5f), Shade(stone, .98f));
            Box(b, "canvas", f, new Vector3(0, H + .015f, -D / 2 + 2.2f), new Vector3(1.4f, .03f, 4.4f), cloth);
            Box(b, "teak", f, new Vector3(0, H + .6f, -D / 2 + 4.4f), new Vector3(1.4f, 1.2f, .8f), X("5E4030"));
            Cyl(b, v == 1 ? "flat_metal" : "flat_gold", f.P(0, H + .7f, -D / 2 + 3.99f), .22f, .02f, 16, metal);
            foreach (int sg in new[] { -1, 1 })
            {
                Cyl(b, "flat_metal", f.P(sg * (L / 2 - 1), H, D / 2 - 1), .05f, 5.5f, 8, X("D9DBDC"));
                Box(b, "canvas", f, new Vector3(sg * (L / 2 - 1) + .9f, H + 4.9f, D / 2 - 1), new Vector3(1.8f, .6f, .03f), cloth);
            }
        }
        static void PorticoSteps(Batch b, Fr f, Vector3 size, int v)
        {
            var p = StagePal[v]; var s = Sz(size, 10f, 1f, 4f);
            for (int k = 0; k < 5; k++) Box(b, p[0], f, new Vector3(0, s.y * (5 - k) / 5f / 2, -s.z / 2 + s.z * (k + .5f) / 5f - s.z), new Vector3(s.x, s.y * (5 - k) / 5f, s.z / 5f), X(p[1]));
        }
        static void MakeT120(Transform gr)
        {
            Ground(gr, "lawn", 100);
            Three(gr, (b, f, v, t) =>
            {
                Plane(b, "slab_lime", f, -14, -12, 10, 8, .02f, X("E2DDD0"));
                SpeechStage(b, f.Sub(-4, 0, 0), Vector3.zero, v);
                Pedestal(b, f.Sub(8, 0, -2), Vector3.zero, v);
                // statue stand-in (the gold statue is a model task): block + figure silhouette
                Box(b, StagePal[v][0], f, new Vector3(8, 1.3f + .5f, -2), new Vector3(1.6f, 1.0f, 1.6f), X(StagePal[v][1]));
                Cyl(b, "flat_gold", f.P(8, 2.3f, -2), .42f, 2.2f, 10, X("C9A64A"), true, .3f);
                Box(b, "flat_gold", f, new Vector3(8, 4.7f, -2), new Vector3(.45f, .5f, .45f), X("C9A64A"));
            });
        }

        // T121 golf green 8 x 7 m: a putting green with mowing stripes + fringe + flag + bunker; b raised green with a stone curb;
        // c formal flower bed (the inventory's reading) with a stone curb
        static void GolfGreen(Batch b, Fr f, Vector3 size, int v)
        {
            var s = Sz(size, 8f, .2f, 7f);
            float rx = s.x / 2, rz = s.z / 2;
            if (v == 2)
            {
                var o = Ellipse(rx, rz, 28); var i2 = Ellipse(rx - .25f, rz - .25f, 28);
                Poly(b, "flowerbed", f, i2, .25f, Own("flowerbed"));
                Skirt(b, "stone", f, o, 0, .3f, X("C9C4B8"));
                for (int k = 0; k < o.Count; k++) { var a = o[k]; var c = o[(k + 1) % o.Count]; var a2 = i2[k]; var c2 = i2[(k + 1) % o.Count];
                    var mb = b["stone"]; mb.QuadUp(f.P(a.x, .3f, a.y), f.P(a2.x, .3f, a2.y), f.P(c2.x, .3f, c2.y), f.P(c.x, .3f, c.y), Vector2.zero, Vector2.up, Vector2.one, Vector2.right, X("D2CDC2")); }
                Skirt(b, "flowerbed", f, i2, .2f, .25f, Shade(Own("flowerbed"), .8f), true);
                return;
            }
            Color fringe = X("5E9440"), g1 = X("7DB85A"), g2 = X("6EA84E");
            float y = v == 1 ? .18f : .04f;
            Poly(b, "green_fine", f, Ellipse(rx + .6f, rz + .6f, 32), y - .01f, fringe);
            int strips = 8;
            for (int k = 0; k < strips; k++)
            {
                float x0 = -rx + 2 * rx * k / strips, x1 = -rx + 2 * rx * (k + 1) / strips;
                var pts = new List<Vector2>();
                for (int j = 0; j <= 4; j++) { float x = Mathf.Lerp(x0, x1, j / 4f); float h = rz * Mathf.Sqrt(Mathf.Max(0, 1 - x * x / (rx * rx))); pts.Add(new Vector2(x, -h)); }
                for (int j = 4; j >= 0; j--) { float x = Mathf.Lerp(x0, x1, j / 4f); float h = rz * Mathf.Sqrt(Mathf.Max(0, 1 - x * x / (rx * rx))); pts.Add(new Vector2(x, h)); }
                Poly(b, "green_fine", f, pts, y, v == 1 ? g1 : (k % 2 == 0 ? g1 : g2));
            }
            if (v == 1) { Skirt(b, "stone", f, Ellipse(rx + .6f, rz + .6f, 32), 0, y, X("D2CDC2")); }
            Ring(b, "flat", f.P(.8f, y + .005f, .5f), 0, .12f, 10, X("26262A"));
            Cyl(b, "flat", f.P(.8f, y, .5f), .02f, 2.1f, 6, X("F4F2EC"), true);
            var fm = b["canvas"];
            fm.Tri(f.P(.8f, y + 2.08f, .5f), f.P(1.45f, y + 1.88f, .5f), f.P(.8f, y + 1.68f, .5f), Vector2.zero, Vector2.right, Vector2.up, v == 1 ? X("F2C14E") : X("C8372D"));
            fm.Tri(f.P(.8f, y + 1.68f, .5f), f.P(1.45f, y + 1.88f, .5f), f.P(.8f, y + 2.08f, .5f), Vector2.zero, Vector2.right, Vector2.up, v == 1 ? X("F2C14E") : X("C8372D"));
            if (v == 0) Poly(b, "sand", f, Ellipse(1.6f, .9f, 18, rx + .9f, -rz * .4f), .03f, X("EADFC6"));
        }
        static void MakeT121(Transform gr)
        {
            Ground(gr, "lawn", 100);
            Three(gr, (b, f, v, t) => { GolfGreen(b, f, Vector3.zero, v); GolfGreen(b, f.Sub(10, 0, 9), Vector3.zero, v); });
        }

        // T122 perimeter: a precast wall + barbed strands on outriggers; b wall + concertina coil; c chain-link on concrete posts + strands
        static void PerimeterLine(Batch b, List<Vector3> l, int v)
        {
            Color wall = X("BFB8A8"), postC = X("A8A296"), wire = X("3A3A38");
            float H = 3.6f;                                                   // data: 4 m fence with barbed wire (wall 3.6 + wire on top)
            for (int i = 1; i < l.Count; i++)
            {
                Vector3 a = l[i - 1], c = l[i], d = c - a; d.y = 0; float L = d.magnitude; if (L < .1f) continue;
                d /= L; var w = new Fr { O = a, R = d, F = Vector3.Cross(d, Vector3.up) };   // F = right of travel = outside for a CCW line
                int k = Mathf.Max(1, Mathf.CeilToInt(L / 3f));
                for (int j = 0; j < k; j++)
                {
                    float s0 = L * j / k, s1 = L * (j + 1) / k, sm = (s0 + s1) / 2;
                    float y = Mathf.Lerp(a.y, c.y, sm / L);
                    if (v < 2) Box(b, "wallpanel", w, new Vector3(sm, y + H / 2 - .3f, 0), new Vector3(s1 - s0 - .02f, H + .3f, .18f), wall);
                    else
                    {
                        var mb = b["chain"]; var cs = S["chain"];
                        Vector3 A = w.P(s0, y - .05f, 0), B = w.P(s0, y + H, 0), C = w.P(s1, y + H, 0), D = w.P(s1, y - .05f, 0);
                        mb.Quad(A, B, C, D, new(s0 / cs.TU, 0), new(s0 / cs.TU, H / cs.TV), new(s1 / cs.TU, H / cs.TV), new(s1 / cs.TU, 0), Color.white);
                    }
                    Box(b, "conc", w, new Vector3(s0, y + (H + .2f) / 2 - .3f, 0), new Vector3(.26f, H + .5f, .26f), postC);
                    if (v == 1)
                    {
                        for (float x = s0; x < s1 - .01f; x += .5f)
                        {
                            Vector3 cc = w.P(x + .25f, y + H + .38f, 0);
                            for (int q = 0; q < 6; q++)
                            {
                                float a0 = Mathf.PI * 2 * q / 6, a1 = Mathf.PI * 2 * (q + 1) / 6;
                                Vector3 P0 = cc + Vector3.up * Mathf.Cos(a0) * .34f + w.F * Mathf.Sin(a0) * .34f + w.R * (q / 6f - .5f) * .3f;
                                Vector3 P1 = cc + Vector3.up * Mathf.Cos(a1) * .34f + w.F * Mathf.Sin(a1) * .34f + w.R * ((q + 1) / 6f - .5f) * .3f;
                                Beam(b, "flat_metal", P0, P1, .014f, .014f, wire);
                            }
                        }
                        continue;
                    }
                    // outrigger arm leaning out (45 deg, 0.6 m) + 3 strands
                    Vector3 p0 = w.P(s0, y + H + .15f, 0), p1 = w.P(s0, y + H + .15f + .42f, .42f);
                    Beam(b, "flat_metal", p0, p1, .04f, .04f, X("4A4A46"));
                    for (int st = 1; st <= 3; st++)
                    {
                        float t2 = st / 3f;
                        Vector3 q0 = Vector3.Lerp(p0, p1, t2), q1 = q0 + w.R * (s1 - s0);
                        Beam(b, "flat_metal", q0, q1, .016f, .016f, wire);
                        for (float x = .25f; x < s1 - s0; x += .5f) Beam(b, "flat_metal", q0 + w.R * x - Vector3.up * .05f, q0 + w.R * x + Vector3.up * .05f, .01f, .01f, wire);
                    }
                }
                var last = w.P(L, Mathf.Lerp(a.y, c.y, 1f) + (H + .2f) / 2 - .3f, 0);
                Box(b, "conc", Fr.Yaw(last, 0), Vector3.zero, new Vector3(.26f, H + .5f, .26f), postC);
            }
        }
        static void MakeT122(Transform gr)
        {
            Ground(gr, "lawn", 100);
            Three(gr, (b, f, v, t) =>
            {
                PerimeterLine(b, new List<Vector3> { new(-24, 0, 6), new(12, 0, 6), new(12, 0, 30) }, v);
                Plane(b, "dirt", f, -24, 4.6f, 12, 7.4f, .02f, X("9A8466"));
            });
        }

        // XT1 military concrete + helipad 24 x 24 (H in a circle, edge lights)
        static void Helipad(Batch b, Fr f, Vector3 size, int v)
        {
            float S0 = size.x > 0 ? size.x : 24f, y = .05f;
            Color mark = X("F4F2EC"), edge = v == 1 ? X("E3B23C") : X("E3B23C");
            Ring(b, "flat", f.P(0, y, 0), S0 * .36f, S0 * .36f + .5f, 40, v == 2 ? X("E3B23C") : mark);
            Color hc = v == 0 ? X("E3B23C") : mark;
            Plane(b, "flat", f, -2.6f, -3.5f, -1.6f, 3.5f, y + .002f, hc);
            Plane(b, "flat", f, 1.6f, -3.5f, 2.6f, 3.5f, y + .002f, hc);
            Plane(b, "flat", f, -1.6f, -.5f, 1.6f, .5f, y + .002f, hc);
            foreach (int sg in new[] { -1, 1 })
            {
                Plane(b, "flat", f, -S0 / 2, sg * S0 / 2 - .3f, S0 / 2, sg * S0 / 2 + .3f, y - .002f, edge);
                Plane(b, "flat", f, sg * S0 / 2 - .3f, -S0 / 2, sg * S0 / 2 + .3f, S0 / 2, y - .003f, edge);
            }
            for (float x = -S0 / 2; x <= S0 / 2 + .01f; x += 4f)
                foreach (int sg in new[] { -1, 1 })
                {
                    Box(b, "lamp_warm", f, new Vector3(x, .1f, sg * (S0 / 2 + .6f)), new Vector3(.25f, .2f, .25f), Color.white);
                    Box(b, "lamp_warm", f, new Vector3(sg * (S0 / 2 + .6f), .1f, x), new Vector3(.25f, .2f, .25f), Color.white);
                }
        }
        static void MakeXT1(Transform gr)
        {
            Ground(gr, "lawn", 100);
            var mats = new[] { MapMats["XT1a_concrete"].m, MapMats["XT1b_concrete"].m, MapMats["XT1c_concrete"].m };
            for (int v = 0; v < 3; v++)
            {
                var t = Group(gr, Vars[v]); var b = new Batch();
                MapFlat(t, "XT1" + Vars[v] + "_Zone_10-helipad", F0, new[] { new Vector2(-16, -16), new Vector2(16, -16), new Vector2(16, 16), new Vector2(-16, 16) }, .04f, 4f, mats[v]);
                Helipad(b, F0, Vector3.zero, v);
                Flush(b, t, curGroup + Vars[v]);
            }
        }

        // T125 bridge (W85 BuildBridge geometry and UVs, 64 m piece): deck 8.8, carriageway 6.4 (asphalt A5, approved), kerbs, slab,
        // parapets 1.1 m, piers every 21 m as cubes - all with the T2M bridge materials
        static void MakeT125(Transform gr)
        {
            GroundR(gr, "sand", -100, -100, 100, -34, null, 1.0f);
            GroundR(gr, "sand", -100, 34, 100, 100, null, 1.0f, "ctx_ground2");
            Sea(gr, -200, -200, 200, 200, 0f);
            var asphalt = AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Map/W85Build/Generated/v01/Materials/W85_asphalt_A5d12.mat");
            for (int v = 0; v < 3; v++)
            {
                var t = Group(gr, Vars[v]);
                string V = Vars[v];
                Material par = MapMats["T125" + V + "_parapets"].m, slab = MapMats["T125" + V + "_slab"].m, kerbM = MapMats["T125" + V + "_kerbs"].m, pier = MapMats["T125" + V + "_piers"].m;
                float deckY = 8f, deck = 8.8f, carr = 6.4f;
                var pts = new List<Vector2>(); for (int i = 0; i <= 32; i++) pts.Add(new Vector2(0, -32 + i * 2f));
                var dv = new List<Vector3>(); var du = new List<Vector2>(); var dt = new List<int>();
                var kv = new List<Vector3>(); var ku = new List<Vector2>(); var kt = new List<int>();
                var sv = new List<Vector3>(); var su = new List<Vector2>(); var st = new List<int>();
                var rv = new List<Vector3>(); var ru = new List<Vector2>(); var rt = new List<int>();
                void Q(List<Vector3> V3, List<Vector2> U2, List<int> T3, Vector3 a, Vector3 b2, Vector3 c, Vector3 d, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud, bool both)
                {
                    int n = V3.Count; V3.AddRange(new[] { a, b2, c, d }); U2.AddRange(new[] { ua, ub, uc, ud }); T3.AddRange(new[] { n, n + 1, n + 2, n, n + 2, n + 3 });
                    if (both) { n = V3.Count; V3.AddRange(new[] { d, c, b2, a }); U2.AddRange(new[] { ud, uc, ub, ua }); T3.AddRange(new[] { n, n + 1, n + 2, n, n + 2, n + 3 }); }
                }
                for (int i = 1; i < pts.Count; i++)
                {
                    Vector2 a = pts[i - 1], b2 = pts[i], d = (b2 - a).normalized, nrm = new(-d.y, d.x); float L = (b2 - a).magnitude, ya = deckY, yb = deckY;
                    Q(dv, du, dt, new(a.x - carr / 2, ya + .02f, a.y), new(b2.x - carr / 2, yb + .02f, b2.y), new(b2.x + carr / 2, yb + .02f, b2.y), new(a.x + carr / 2, ya + .02f, a.y),
                        new(a.x - carr / 2, a.y), new(b2.x - carr / 2, b2.y), new(b2.x + carr / 2, b2.y), new(a.x + carr / 2, a.y), false);
                    foreach (int sg in new[] { -1, 1 })
                    {
                        Vector2 i0 = a + nrm * sg * carr * .5f, i1 = b2 + nrm * sg * carr * .5f, o0 = a + nrm * sg * deck * .5f, o1 = b2 + nrm * sg * deck * .5f;
                        Vector3 I0 = new(i0.x, ya + .17f, i0.y), I1 = new(i1.x, yb + .17f, i1.y), O0 = new(o0.x, ya + .17f, o0.y), O1 = new(o1.x, yb + .17f, o1.y);
                        if (sg > 0) Q(kv, ku, kt, I0, I1, O1, O0, Vector2.zero, new(0, L), new(1, L), new(1, 0), false); else Q(kv, ku, kt, O0, O1, I1, I0, Vector2.zero, new(0, L), new(1, L), new(1, 0), false);
                        Q(kv, ku, kt, new(i0.x, ya - .02f, i0.y), new(i1.x, yb - .02f, i1.y), I1, I0, Vector2.zero, new(L, 0), new(L, .2f), new(0, .2f), true);
                        Q(rv, ru, rt, O0, O1, O1 + Vector3.up * 1.1f, O0 + Vector3.up * 1.1f, Vector2.zero, new(L / 3f, 0), new(L / 3f, .37f), new(0, .37f), true);
                    }
                    Vector2 la = a + nrm * deck * .5f, ra = a - nrm * deck * .5f, lb = b2 + nrm * deck * .5f, rb = b2 - nrm * deck * .5f;
                    Q(sv, su, st, new(ra.x, ya - .9f, ra.y), new(rb.x, yb - .9f, rb.y), new(lb.x, yb - .9f, lb.y), new(la.x, ya - .9f, la.y), Vector2.zero, new(0, L), new(1, L), new(1, 0), false);
                    foreach (int sg in new[] { -1, 1 })
                    {
                        Vector2 e0 = a + nrm * sg * deck * .5f, e1 = b2 + nrm * sg * deck * .5f;
                        Q(sv, su, st, new(e0.x, ya - .9f, e0.y), new(e1.x, yb - .9f, e1.y), new(e1.x, yb + .17f, e1.y), new(e0.x, ya + .17f, e0.y), Vector2.zero, new(L, 0), new(L, 1), new(0, 1), true);
                    }
                }
                for (int i = 0; i < du.Count; i++) du[i] /= 6f;
                MapMesh(t, "T125" + V + "_Bridge_10-bridge_deck", dv, du, dt, asphalt ? asphalt : slab);
                MapMesh(t, "T125" + V + "_Bridge_10-bridge_kerbs", kv, ku, kt, kerbM);
                MapMesh(t, "T125" + V + "_Bridge_10-bridge_slab", sv, su, st, slab);
                MapMesh(t, "T125" + V + "_Bridge_10-bridge_parapets", rv, ru, rt, par);
                foreach (float z in new[] { -21f, 0f, 21f })
                {
                    var cube = GameObject.CreatePrimitive(PrimitiveType.Cube); cube.name = "T125" + V + "_Pier_10-bridge"; cube.transform.SetParent(t, false);
                    Object.DestroyImmediate(cube.GetComponent<Collider>());
                    float top = deckY - .9f, bottom = -3f;
                    cube.transform.localPosition = new Vector3(0, (top + bottom) / 2, z); cube.transform.localScale = new Vector3(deck - 1.5f, top - bottom, 1.6f);
                    cube.GetComponent<MeshRenderer>().sharedMaterial = pier;
                }
            }
        }

        // =========================================================================================== material sets for map renderers + props
        static void MapMaterials()
        {
            MapMats.Clear();
            // T89 port yard / loading apron (W85 Zone_*: UV world / 4 m, key concrete_SK3c)
            MapMat("T89a_yard", "slabs6", "C9C5BD", 4, 4, "Zone_06-yard, Zone_06-09-loading-apron (concrete_SK3c, tile 4)");
            MapMat("T89b_yard", "asph_light", "9C9C9A", 4, 4, "Zone_06-yard, Zone_06-09-loading-apron");
            MapMat("T89c_yard", "patched", "C2BDB2", 4, 4, "Zone_06-yard, Zone_06-09-loading-apron");
            // T90 port pier (W85 Pier(): deck UV world / 4, skirt UV 0..1 x 0..0.4)
            MapMat("T90a_pier", "conc", "C9C6BF", 4, 4, "Pier_06-pier (deck)"); MapMat("T90a_skirt", "conc", "B9B5AD", 1, 1, "PierSkirt_06-pier");
            MapMat("T90b_pier", "conc", "C4C0B8", 4, 4, "Pier_06-pier (deck)"); MapMat("T90b_skirt", "conc", "B5B1A9", 1, 1, "PierSkirt_06-pier");
            MapMat("T90c_pier", "aggregate", "B8B4AC", 4, 4, "Pier_06-pier (deck)"); MapMat("T90c_skirt", "aggregate", "A8A49C", 1, 1, "PierSkirt_06-pier");
            // T97 hedges (W85 Hedge_* cube primitives: UV 0..1 per face, ~3 x 1.8 x 0.9 m)
            MapMat("T97a_hedge", "hedge_box", null, 1.5f, 1f, "Hedge_07-V0*-plot cubes (lawn_hedge / W85_hedge)");
            MapMat("T97b_hedge", "hedge_laurel", null, 1.5f, 1f, "Hedge_07-V0*-plot cubes");
            MapMat("T97c_hedge", "hedge_bougain", null, 1.5f, 1f, "Hedge_07-V0*-plot cubes");
            // T98 pools / decks (W85 Zone_*: pool_tile tile 1, boards_SK5a tile 3)
            MapMat("T98a_pool", "mosaic", "7FD3D8", 1, 1, "Zone_07-V0*-pool (pool_tile, tile 1)"); MapMat("T98a_deck", "deck_teak", null, 3, 3, "Zone_07-V0*-deck (boards_SK5a, tile 3)");
            MapMat("T98b_pool", "mosaic", "A9DCE8", 1, 1, "Zone_07-V0*-pool"); MapMat("T98b_deck", "slab_lime", "EDE6D6", 3, 3, "Zone_07-V0*-deck");
            MapMat("T98c_pool", "mosaic", "3E6E80", 1, 1, "Zone_07-V0*-pool"); MapMat("T98c_deck", "setts_sand", "D8C9A8", 3, 3, "Zone_07-V0*-deck");
            // T100 Elite piers / T112 beach boards (boards_pier_SK5a_v02, tile 3; skirt 0..1)
            var keep = AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Map/W76Build/Generated/v01/Materials/W76_boards_pier_SK5a_v02.mat");
            if (keep) { MapMats["T100a_deck"] = (keep, "keep: existing W76_boards_pier_SK5a_v02"); MapMats["T112a_deck"] = (keep, "keep: existing W76_boards_pier_SK5a_v02"); }
            else Note("W76_boards_pier_SK5a_v02.mat missing - T100a / T112a fall back to own copy");
            if (!keep) { MapMat("T100a_deck", "planks_w", "B07A4A", 3, 3, "fallback"); MapMat("T112a_deck", "planks_w", "B07A4A", 3, 3, "fallback"); }
            MapMat("T100b_deck", "deck_teak", null, 3, 3, "Pier_07-pier-P1..P3 + PierSkirt_07-pier-*");
            MapMat("T100c_deck", "deck_bleached", null, 3, 3, "Pier_07-pier-P1..P3 + PierSkirt_07-pier-*");
            MapMat("T112b_deck", "deck_bleached", null, 3, 3, "Pier_09-pier, Pier_09-pier-head, PierSkirt_09-*, Boardwalk_09-*");
            MapMat("T112c_deck", "deck_teak", null, 3, 3, "Pier_09-pier, Pier_09-pier-head, PierSkirt_09-*, Boardwalk_09-*");
            // T113 pier square (plaza_M3, tile 8)
            var m3 = AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Map/W85Build/Generated/v01/Materials/W85_plaza_M3.mat");
            if (m3) MapMats["T113a_plaza"] = (m3, "keep: existing W85_plaza_M3"); else MapMat("T113a_plaza", "slab_grey", "BDBAB2", 8, 8, "fallback");
            MapMat("T113b_plaza", "terrazzo", "ECE6DA", 8, 8, "Zone_09-pier-square (plaza_M3, tile 8)");
            MapMat("T113c_plaza", "slab_grey", "C9C7C2", 8, 8, "Zone_09-pier-square");
            // XT1 Tramduro concrete zones (concrete_SK3c, tile 4)
            MapMat("XT1a_concrete", "slabs6", "C2BDB0", 4, 4, "Zone_10-concrete_yard, Zone_10-helipad, Zone_10-concrete_entry, Zone_10-garage_apron, Zone_10-aa_plinth*, Zone_10-missile_cluster");
            MapMat("XT1b_concrete", "asph_light", "8E8E8A", 4, 4, "same zones");
            MapMat("XT1c_concrete", "patched", "A8A494", 4, 4, "same zones");
            // T125 bridge (W85 BuildBridge: parapets UV L/3 x h/3, slab / kerbs 0..1 x L, piers cube primitives 0..1)
            MapMat("T125a_parapets", "board", "C9C3B6", 3, 3, "Bridge_10-bridge_parapets"); MapMat("T125a_slab", "conc", "BDB7AB", 1, 1, "Bridge_10-bridge_slab");
            MapMat("T125a_kerbs", "conc", "D0CBC0", 1, 1, "Bridge_10-bridge_kerbs"); MapMat("T125a_piers", "board", "B5AFA2", 3.6f, 5, "Pier_10-bridge_* cubes");
            MapMat("T125b_parapets", "plaster", "EEEAE2", 3, 3, "Bridge_10-bridge_parapets"); MapMat("T125b_slab", "conc", "C4BFB4", 1, 1, "Bridge_10-bridge_slab");
            MapMat("T125b_kerbs", "stone", "9A9A98", 1, 1, "Bridge_10-bridge_kerbs"); MapMat("T125b_piers", "rubble_grey", "B8B4AC", 3.3f, 4.5f, "Pier_10-bridge_* cubes");
            MapMat("T125c_parapets", "formwork", "9E9A8E", 3, 3, "Bridge_10-bridge_parapets"); MapMat("T125c_slab", "formwork", "A8A498", 1, 1, "Bridge_10-bridge_slab");
            MapMat("T125c_kerbs", "conc", "B5B0A4", 1, 1, "Bridge_10-bridge_kerbs"); MapMat("T125c_piers", "formwork", "9A968A", 3, 4, "Pier_10-bridge_* cubes");
            // T122 perimeter (material only, if the generator is not used: FenceMesh_10-perimeter, UV L/3 x h/3)
            MapMat("T122a_wall", "wallpanel", "BFB8A8", 3, 3, "FenceMesh_10-perimeter (metal_painted_SK6a, tile 3) - material only");
            // T106 waterfall rock (W85 box primitive 7 x 10 x 8; material only, if the rock generator is not used)
            MapMat("T106a_rock", "rockmacro", null, 1.2f, 1.6f, "box '<waterfall_to_sea id>' (cube) - material only");
            MapMat("T106b_rock", "rock_grey", null, 2, 2.5f, "box (cube) - material only");
            MapMat("T106c_rock", "rock_warm", null, 2, 2.5f, "box (cube) - material only");
            Note($"map materials: {MapMats.Count}");
        }

        // prop material sets: lifeguard towers [concrete, white, wood, dark wood, red], umbrellas [concrete, white, metal grey, canopy, stripe],
        // loungers [metal frame, bed]. One colour per instance (index / hash of the instance name).
        static readonly string[] UmbA = { "E8735E", "2FA3A8", "F2C14E", "8FD3B8", "EE8FA8" }, UmbB = { "B8352E", "2E4A78", "F2C14E" }, UmbC = { "2E4A78", "E8DCC2", "F4F2EC" };
        static Material[] UmbrellaSet(string code, int v, int k)
        {
            if (v == 0 && code == "T102") return new[] { MPm("MP_Concrete"), MPm("MP_White"), MPm("MP_Metal_Grey"), MPm("MP_Red"), MPm("MP_Fabric_Stripe") };
            if (code == "T102")
            {
                if (v == 1) return new[] { MPm("MP_Concrete"), PropMats["T102b_pole"], PropMats["T102b_pole"], PropMats["T102b_canopy"], PropMats["T102b_canopy2"] };
                return new[] { MPm("MP_Concrete"), PropMats["white"], PropMats["chrome"], PropMats["navy"], PropMats["white"] };
            }
            string[] set = v == 0 ? UmbA : v == 1 ? UmbB : UmbC;
            string col = set[k % set.Length];
            var canopy = PropMats["c_" + col];
            var stripe = v == 2 ? canopy : PropMats["white"];
            return new[] { MPm("MP_Concrete"), PropMats["white"], PropMats["chrome"], canopy, stripe };
        }
        static Material[] LoungerSet(string code, int v, int k)
        {
            if (v == 0 && code == "T102") return new[] { MPm("MP_Metal_Grey"), MPm("MP_Wood") };
            if (code == "T102") return v == 1 ? new[] { PropMats["T102b_frame"], PropMats["T102b_bed"] } : new[] { PropMats["white"], PropMats["white"] };
            if (v == 0) return new[] { MPm("MP_Metal_Grey"), MPm("MP_Wood") };
            if (v == 1) return new[] { PropMats["white"], k % 3 == 2 ? PropMats["c_2FA3A8"] : PropMats["white_plastic"] };
            return new[] { PropMats["chrome"], PropMats["teak"] };
        }
        static readonly string[] TowerTint = { "F4D35E", "9BD08A" };
        static Material[] TowerSet(int v, int k)
        {
            if (v == 0) return new[] { MPm("MP_Concrete"), MPm("MP_White"), MPm("MP_Wood"), MPm("MP_Wood_Dark"), MPm("MP_Red") };
            if (v == 1) return new[] { MPm("MP_Concrete"), PropMats["c_" + TowerTint[k]], PropMats["white"], PropMats["white"], PropMats["c_E8735E"] };
            return new[] { MPm("MP_Concrete"), PropMats["white"], PropMats["navy"], PropMats["navy"], PropMats["c_B8352E"] };
        }
        static void PropMaterials()
        {
            PropMats.Clear();
            foreach (var c in UmbA.Concat(UmbB).Concat(UmbC).Concat(TowerTint).Concat(new[] { "E8735E", "B8352E", "2FA3A8" }).Distinct()) PropMat("c_" + c, c, .15f);
            PropMat("white", "F4F2EC", .2f); PropMat("white_plastic", "EEEDE8", .35f); PropMat("navy", "2E4A78", .2f);
            PropMat("chrome", "C9CCCE", .65f, null, .8f); PropMat("teak", "B98A5E", .25f);
            PropMat("T102b_canopy", "F4F2EC", .1f); PropMat("T102b_canopy2", "EFE6D2", .1f); PropMat("T102b_pole", "8A6A4A", .3f);
            PropMat("T102b_frame", "F2F2EE", .3f); PropMat("T102b_bed", "B98A5E", .25f);
            // T114 palms: copies of the Leafy v04 palm materials with new colours + prefab copies using them
            string md = "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Materials/";
            var leaf = AssetDatabase.LoadAssetAtPath<Material>(md + "Palm_PalmLeaf_Wind_v04_03.mat");
            var leaf2 = AssetDatabase.LoadAssetAtPath<Material>(md + "Palm_Leaf_Wind_v04_03.mat");
            var bark = AssetDatabase.LoadAssetAtPath<Material>(md + "Palm_PalmBark_Wind_v04_03.mat");
            if (!leaf || !bark) { Note("palm materials missing - T114 skipped"); return; }
            foreach (var (v, lc, bc) in new[] { ("b", "5FAE4A", "A08A6A"), ("c", "3F8A5A", "8A7F72") })
            {
                Material Copy(Material src, string hex, string nm)
                {
                    if (!src) return null;
                    var m = new Material(src) { name = nm };
                    if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", X(hex));
                    AssetDatabase.CreateAsset(m, MatDir + "/Props/" + nm + ".mat");
                    return PropMats[nm] = m;
                }
                var l = Copy(leaf, lc, "T2P_T114" + v + "_PalmLeaf"); var l2 = Copy(leaf2, lc, "T2P_T114" + v + "_Leaf"); var bk = Copy(bark, bc, "T2P_T114" + v + "_PalmBark");
                foreach (string n in new[] { "Palm_A", "Palm_B", "Palm_C" })
                {
                    string src = $"Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/{n}_v04_03.prefab";
                    var pf = AssetDatabase.LoadAssetAtPath<GameObject>(src);
                    if (!pf) continue;
                    var inst = (GameObject)PrefabUtility.InstantiatePrefab(pf);
                    PrefabUtility.UnpackPrefabInstance(inst, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                    foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
                        r.sharedMaterials = r.sharedMaterials.Select(m => m == leaf ? l : m == leaf2 && l2 ? l2 : m == bark ? bk : m).ToArray();
                    PrefabUtility.SaveAsPrefabAsset(inst, $"{PrefabDir}/{n}_v04_03_T114{v}.prefab");
                    Object.DestroyImmediate(inst);
                }
            }
        }
    }
}
