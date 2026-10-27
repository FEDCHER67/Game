using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>Hill B v7 (Vadim 23.10): the pre-Fedya W19 hill (ridge with W19 falloff and noise, same footprint, two groves, the
    /// cornice to the port over a small headland) with Vadim's serpentine kept, a proper meeting plaza on the summit, and a curved
    /// round tunnel (graphite inside, light portals). Local W86 terrain + scene only; Restore() puts Fedya's terrain and scene back.</summary>
    static class VadimHillApply
    {
        const string Scene = "Assets/OnlyVolunteers/Scenes/Map/Map_W85_Play_v02.unity";
        const string Bak = @"C:\Users\chern_0eqkb03\VolunteersBuilds\backup_hill";
        const string Dir = "Assets/VadimLocal/Hill";
        const string Roads = "Assets/OnlyVolunteers/Map/W85Build/Data/v02/roads_v85.json";
        const float Plain = 5f, Pass = 41f, RoadW = 6.8f, SpurW = 5.6f, PlazaR = 12.5f;
        static readonly Vector2 PlazaC = new Vector2(878f, 585f);
        static readonly Vector2[] Main = { new(945, 671), new(944, 652), new(955, 636), new(982, 631), new(1006, 625), new(1017, 610), new(1006, 598), new(984, 595), new(968, 592), new(961, 582), new(956, 569), new(962, 557), new(978, 551), new(996, 550), new(1012, 550), new(1030, 543), new(1041, 531), new(1044, 518), new(1044, 510) };
        static readonly Vector2 PassAt = new Vector2(968, 592), SpurWant = new Vector2(976, 595);
        static Vector2 SpurFrom;
        static readonly Vector2[] SpurTail = { new(948, 614), new(926, 611), new(906, 603), new(892, 591) };
        static readonly Vector2[] NorthApp = { new(748, 671), new(748, 660), new(748, 649) };
        static readonly Vector2[] SouthApp = { new(822.6f, 548), new(827, 541), new(830, 533), new(831, 520), new(831, 502) };
        static readonly Vector2[] OldSerp = { new(945, 671), new(946, 664), new(949, 658), new(950, 655), new(947, 650), new(943, 644), new(942, 640), new(946, 634), new(955, 627), new(967, 620), new(983, 614), new(995, 608), new(1007, 597), new(1019, 581), new(1026, 569), new(1033, 559), new(1038, 552), new(1041, 544), new(1043, 536), new(1044, 510) };
        static readonly Vector2[] OldSpur = { new(997, 607), new(989, 598), new(979, 592), new(958, 580), new(942, 571), new(926, 563), new(911, 556), new(897, 552), new(882, 550), new(870, 550), new(860, 553), new(852, 559), new(845, 567), new(840, 574), new(832, 577), new(828, 582), new(826, 588), new(828, 594), new(832, 599), new(838, 602), new(854, 602), new(862, 604) };
        // hill B crest (x, z, height over the plain, half width): W19 footprint and heights, a saddle where the serpentine crosses,
        // the summit (meeting plaza) at x 878; the headland the cornice climbs over
        static readonly Vector4[] Ridge = { new(728, 560, 16, 46), new(765, 568, 28, 54), new(820, 578, 38, 60), new(878, 585, 43, 62), new(918, 590, 40, 62), new(948, 591, 38, 62), new(968, 592, 38, 62), new(995, 590, 39, 62), new(1032, 584, 37, 60), new(1072, 577, 33, 58), new(1112, 569, 27, 52), new(1150, 560, 19, 46), new(1182, 552, 12, 36) };
        static readonly Vector4[] Headland = { new(1190, 528, 8, 26), new(1206, 550, 10, 28), new(1220, 572, 5, 22) };
        // the cornice to the port (Vadim 23.10): on the very edge of the cliff over the bay, like before Fedya
        static readonly Vector2[] CornicePts = { new(1202, 494), new(1202, 504), new(1206, 513), new(1214, 521), new(1222, 530), new(1226, 541), new(1228, 553), new(1231, 564), new(1238, 574), new(1247, 583), new(1255, 594), new(1261, 607), new(1263, 620), new(1263, 633) };
        static Vector2[] OldCornice = new Vector2[0];
        static Vector4[] DescentRidge = new Vector4[0];
        // the tunnel: Fedya's portals, an S-bend between them (one portal is not visible from the other)
        static readonly Vector2[] TunnelPts = { new(748f, 648.99f), new(749, 632), new(756, 613), new(772, 595), new(792, 579), new(808, 566), new(818, 555), new(822.63f, 548.01f) };
        const float TunH0 = 6.23f, TunH1 = 7.85f, TunR = 5.0f, TunC = 1.6f;
        // retaining walls v2 (Vadim 25.10): one height (3.5 m over the road / sidewalk) everywhere, from the very street edge
        const float WallH = 3.5f, WallTh = .5f, WallCap = .15f, LowZ = 1.3f, DeckW = 2.6f;
        class WLine { public string name; public int kind; public bool openStart, openEnd; public List<Vector2> f = new(), m = new(); public List<float> b = new(), t = new(); }
        struct WHit { public bool ok; public float s, dist, e, b, t; public int kind; }
        static readonly List<WLine> WLines = new();
        static readonly List<List<Vector2>> FootFull = new();
        static readonly Dictionary<long, List<(int l, int k)>> WGrid = new();
        static readonly Rect Zone = new Rect(620, 470, 670, 232);
        static readonly HashSet<string> Rebuilt = new() { "serpentine_view_b", "view_b_spur", "cornice_view_c", "tunnel", "tunnel_north_approach", "tunnel_south_approach" };

        struct S { public Vector2 p, right; public float y, half, roadHalf, cut, wall, cliff; public int road; }

        public static void Run()
        {
            var scene = EditorSceneManager.OpenScene(Scene);
            var log = new StringBuilder();
            var terrain = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>();
            var td = terrain.terrainData; var tp = terrain.transform.position;
            string tdPath = AssetDatabase.GetAssetPath(td);
            Directory.CreateDirectory(Bak);
            if (!File.Exists(Path.Combine(Bak, "terrain_path.txt")))
            {
                File.Copy(tdPath, Path.Combine(Bak, Path.GetFileName(tdPath)), true);
                File.Copy(Scene, Path.Combine(Bak, Path.GetFileName(Scene)), true);
                File.WriteAllText(Path.Combine(Bak, "terrain_path.txt"), tdPath);
            }
            if (!AssetDatabase.IsValidFolder(Dir)) AssetDatabase.CreateFolder("Assets/VadimLocal", "Hill");

            // ---------------------------------------------------------------- roads
            float plazaY = Mathf.Round(Plain + HillAbove(PlazaC, false));
            float mainY0 = StreetY(Main[0], 5.86f) - .13f, mainY1 = StreetY(Main[Main.Length - 1], 5.06f) - .13f;
            var main = ProfilePeak(Main, mainY0, PassAt, Pass, mainY1);
            int ij = 0; for (int i = 1; i < main.Count; i++) if ((main[i].p - SpurWant).sqrMagnitude < (main[ij].p - SpurWant).sqrMagnitude) ij = i;
            SpurFrom = main[ij].p; float spurY0 = main[ij].y;
            Vector2 tan = (main[Mathf.Min(ij + 3, main.Count - 1)].p - main[Mathf.Max(ij - 3, 0)].p).normalized, nrm = new Vector2(-tan.y, tan.x);
            if (nrm.y < 0f) nrm = -nrm;     // to the north side, away from the city
            var spurPts = new List<Vector2> { SpurFrom + nrm * 2.2f, SpurFrom + nrm * 7f, SpurFrom + nrm * 12f + tan * 4f };
            spurPts.AddRange(SpurTail);
            {
                int ip = 0; for (int i = 1; i < main.Count; i++) if (main[i].y > main[ip].y) ip = i;
                var dr = new List<Vector4>(); float acc = 0f, Lrest = 0f;
                for (int i = ip + 1; i < main.Count; i++) Lrest += (main[i].p - main[i - 1].p).magnitude;
                for (int i = ip; i < main.Count; i++)
                {
                    if (i > ip) acc += (main[i].p - main[i - 1].p).magnitude;
                    if (i != ip && i != main.Count - 1 && ((int)acc) % 8 != 0) continue;
                    float extra = 4f * Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(0f, 28f, Lrest - acc));
                    dr.Add(new Vector4(main[i].p.x, main[i].p.y, main[i].y - Plain + extra, 32f));
                }
                DescentRidge = dr.ToArray();
            }
            var spur = Profile(spurPts.ToArray(), spurY0 - .02f, plazaY, 22);
            main = ExtendEnds(TrimToStreet(main, true, true, log, "serpentine"), true, true);
            var samples = new List<S>();
            AddRoad(samples, main, RoadW, 1, 3.5f, 3.5f); AddRoad(samples, spur, SpurW, 3, 4f, 0f);
            {   // earth walls along the serpentine (later faced with concrete): 4 m, lower over the first / last 30 m; 3 m along the spur
                float sm = 0f, Lm = 0f; for (int i = 1; i < main.Count; i++) Lm += (main[i].p - main[i - 1].p).magnitude;
                for (int i = 0, k = 0; i < samples.Count; i++)
                {
                    var q = samples[i];
                    if (q.road == 1) { if (k > 0) sm += (q.p - samples[i - 1].p).magnitude; k++; q.wall = 4f * Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(12f, 42f, sm)) * (1f - Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(Lm - 62f, Lm - 22f, sm))); }
                    if (q.road == 3) { float ds = (q.p - SpurFrom).magnitude, dp2 = (q.p - PlazaC).magnitude; q.wall = 3f * Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(10f, 22f, ds)) * Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(PlazaR + 3f, PlazaR + 14f, dp2)); }
                    samples[i] = q;
                }
            }
            var rj = MiniJson.Parse(File.ReadAllText(Roads)) as Dictionary<string, object>;
            OldCornice = PolyFromJson(rj, "cornice_view_c", out _);
            var cornice = TrimToStreet(CorniceProfile2(), true, true, log, "cornice");
            AddRoad(samples, cornice, 6.4f, 4, 3.5f, 3f);
            {   // the cliff section: the bay side of the road drops straight into the water
                int first = samples.FindIndex(x => x.road == 4);
                var cz = new float[cornice.Count];
                for (int i = 0; i < cornice.Count; i++) cz[i] = cornice[i].p.y;
                for (int i = 0; i < cornice.Count; i++)
                {
                    float z = cz[i], w = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(503f, 511f, z)) * (1f - Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(560f, 570f, z)));
                    var q = samples[first + i]; q.cliff = w; samples[first + i] = q;
                }
            }
            var napp = ExtendEnds(TrimToStreet(Profile(NorthApp, 5.03f, TunH0), true, false, log, "north approach"), true, false); var sapp = ExtendEnds(TrimToStreet(Profile(SouthApp, TunH1, 5.06f), false, true, log, "south approach"), false, true);
            var tunnelRoads = new List<S>();
            AddRoad(tunnelRoads, napp, RoadW, 5, 3.5f, 0f); AddRoad(tunnelRoads, sapp, RoadW, 6, 0f, 3.5f);
            var axis = Profile(TunnelPts, TunH0, TunH1, 6, false);
            float tunL = 0; var axS = new float[axis.Count]; for (int i = 1; i < axis.Count; i++) { tunL += (axis[i].p - axis[i - 1].p).magnitude; axS[i] = tunL; }
            for (int i = 0; i < tunnelRoads.Count; i++)
            {   // forecourts: the approach itself, wider and with a steeper cut over the last 22 m to each portal
                var q = tunnelRoads[i]; float dPortal = Mathf.Min((q.p - axis[0].p).magnitude, (q.p - axis[axis.Count - 1].p).magnitude);
                float k = Mathf.InverseLerp(0f, 22f, dPortal);
                q.half = Mathf.Lerp(TunR + 1.2f, 4.5f, k); q.cut = Mathf.Lerp(1.2f, .85f, k); tunnelRoads[i] = q;
            }
            var allRoads = samples.Concat(tunnelRoads).ToList();
            BuildWallLines(samples, tunnelRoads, log);
            // the other roads of the map keep their ground: no hill change within ~10-30 m of them
            var keepSegs = new List<(Vector2 a, Vector2 b)>();
            foreach (var ro in (List<object>)rj["roads"])
            {
                var r = (Dictionary<string, object>)ro; if (Rebuilt.Contains((string)r["id"])) continue;
                var pl = ((List<object>)r["points"]).Select(o => { var a = (List<object>)o; return new Vector2(System.Convert.ToSingle(a[0]), System.Convert.ToSingle(a[1])); }).ToList();
                for (int i = 0; i + 1 < pl.Count; i++)
                {
                    var bb = Rect.MinMaxRect(Mathf.Min(pl[i].x, pl[i + 1].x) - 40, Mathf.Min(pl[i].y, pl[i + 1].y) - 40, Mathf.Max(pl[i].x, pl[i + 1].x) + 40, Mathf.Max(pl[i].y, pl[i + 1].y) + 40);
                    if (bb.Overlaps(Zone)) keepSegs.Add((pl[i], pl[i + 1]));
                }
            }
            log.AppendLine($"plaza {PlazaC} at {plazaY:0} m; serpentine {Len(Main):0} m peak {main.Max(q => q.y):0.0} m grade {Grade(main):0}%, spur {spur.Count:0} m {Grade(spur):0}%, cornice peak {cornice.Max(q => q.y):0.0} m {Grade(cornice):0}%; tunnel {tunL:0} m; kept road segments {keepSegs.Count}");

            // ---------------------------------------------------------------- heights
            int R = td.heightmapResolution; float sx = td.size.x / (R - 1), sz = td.size.z / (R - 1), sy = td.size.y;
            int x0 = Mathf.FloorToInt((Zone.xMin - tp.x) / sx), x1 = Mathf.CeilToInt((Zone.xMax - tp.x) / sx);
            int z0 = Mathf.FloorToInt((Zone.yMin - tp.z) / sz), z1 = Mathf.CeilToInt((Zone.yMax - tp.z) / sz);
            int W = x1 - x0 + 1, Hh = z1 - z0 + 1;
            var h = td.GetHeights(x0, z0, W, Hh);
            var old = (float[,])h.Clone();
            Own = new float[Hh, W]; OX = x0; OZ = z0; OSX = sx; OSZ = sz; OTP = tp;
            var yT = new float[Hh, W]; var pin = new bool[Hh, W]; var pinY = new float[Hh, W]; var lb = new float[Hh, W];
            for (int j = 0; j < Hh; j++) for (int i = 0; i < W; i++)
            {
                var p = new Vector2(tp.x + (x0 + i) * sx, tp.z + (z0 + j) * sz);
                float y0 = tp.y + h[j, i] * sy;
                float hill = HillAbove(p, true);
                float own = Mathf.Max(Mathf.SmoothStep(0f, 1f, hill / 3f), Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(5.4f, 8f, y0)));
                own *= DistrictKeep(p) * EdgeFade(p) * Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(.8f, 3f, y0));
                float dKeep = 1e9f; foreach (var sg in keepSegs) dKeep = Mathf.Min(dKeep, SegDist(p, sg.a, sg.b));
                own *= Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(4f, 14f, dKeep));
                Own[j, i] = own;
                float y = Mathf.Lerp(y0, Plain + hill, own);
                lb[j, i] = -1e9f;
                var (ts, tdd, ty) = OnAxis(axis, axS, p);
                if (ts > -22f && ts < tunL + 22f)
                {   // the hill over the tube and around the portals: 1.2 m over the crown at the faces, 3.5 m deeper in, a broad lobe;
                    // in front of each face it goes on and slopes down, the approach cut (corridor) makes the trench to the portal
                    float faceDist = Mathf.Min(ts, tunL - ts), crown = ty + TunC + TunR;
                    float need = crown + Mathf.Lerp(1.2f, 3.5f, Mathf.InverseLerp(4f, 14f, faceDist)) - Mathf.Max(0f, tdd - (TunR + 2.5f)) * .32f - Mathf.Max(0f, -faceDist) * .55f;
                    y = Mathf.Max(y, need);
                    if (ts >= 0f && ts <= tunL && tdd < TunR + 2.5f) lb[j, i] = crown + 1f;
                }
                bool front = ts <= .5f || ts >= tunL - .5f;
                y = Corridor(y, p, samples);
                y = Corridor(y, p, tunnelRoads, front);
                // pins: the districts, other roads and the zone border keep their ground; the new roads, forecourts and the plaza their level
                if (own < .02f || dKeep < 4f || EdgeFade(p) < .04f) { pin[j, i] = true; pinY[j, i] = y0; }
                if (RoadPin(p, samples, out float ry) || front && RoadPin(p, tunnelRoads, out ry))
                {
                    if ((p - SpurFrom).sqrMagnitude < 196f) ry = Mathf.Min(ry, NearestY(p, samples, 1, out _, out _) - .3f);
                    pin[j, i] = true; pinY[j, i] = ry;
                }
                else if (CliffCut(p, samples, y0, out float cy)) { pin[j, i] = true; pinY[j, i] = cy; y = cy; }
                else if (FrontOfFoot(p, out float fy)) { pin[j, i] = true; pinY[j, i] = Mathf.Min(y0, fy); y = pinY[j, i]; }   // sidewalks / shoulder: flat
                else if (WallTerrain(p, out bool wPin, out float wY, out float wLb))
                {   // retaining walls: low ground in front of / under them, a bench under the deck, a lower bound behind
                    if (wPin) { pin[j, i] = true; pinY[j, i] = wY; y = wY; }
                    else { pin[j, i] = false; lb[j, i] = Mathf.Max(lb[j, i], wLb); y = Mathf.Max(y, wLb); }
                }
                float dp = (p - PlazaC).magnitude;
                if (dp < PlazaR + 1.5f) { pin[j, i] = true; pinY[j, i] = plazaY - .05f; y = plazaY - .05f; }
                else if (dp < PlazaR + 22f) y = Mathf.Lerp(plazaY - .05f, y, Mathf.SmoothStep(0f, 1f, (dp - PlazaR - 1.5f) / 20.5f));
                if (dp >= PlazaR + 1.5f && dp < PlazaR + 45f) { float ee = dp - PlazaR - 1.5f, sl = Mathf.Max(0f, ee - 6f); lb[j, i] = Mathf.Max(lb[j, i], plazaY - .05f - ee * .45f - sl * sl * .05f); }
                yT[j, i] = y;
            }
            // relaxation: everything between the pins flows smoothly (no creases where banks meet the hill, no cliffs);
            // never thinner than 1 m over the tube
            int rxx = Mathf.Max(1, Mathf.RoundToInt(4.5f / sx)), rzz = Mathf.Max(1, Mathf.RoundToInt(4.5f / sz));
            for (int it = 0; it < 9; it++)
            {
                yT = Blur(yT, rxx, rzz, 1);
                for (int j = 0; j < Hh; j++) for (int i = 0; i < W; i++) yT[j, i] = pin[j, i] ? pinY[j, i] : Mathf.Max(yT[j, i], lb[j, i]);
            }
            {
                var pm = new float[Hh, W];
                for (int j = 0; j < Hh; j++) for (int i = 0; i < W; i++) pm[j, i] = pin[j, i] ? 1f : 0f;
                pm = Blur(pm, Mathf.RoundToInt(7f / sx), Mathf.RoundToInt(7f / sz), 2);
                for (int j = 0; j < Hh; j++) for (int i = 0; i < W; i++)
                {
                    if (pin[j, i]) continue;
                    var p = new Vector2(tp.x + (x0 + i) * sx, tp.z + (z0 + j) * sz);
                    float free = Mathf.Clamp01(1f - pm[j, i] * 2.5f), above = Mathf.Clamp01((yT[j, i] - Plain - 2f) / 22f);
                    if (free <= 0f || above <= 0f) continue;
                    float rn1 = 1f - Mathf.Abs(2f * Mathf.PerlinNoise(p.x / 52f + 41.3f, p.y / 52f + 7.9f) - 1f);
                    float rn2 = 1f - Mathf.Abs(2f * Mathf.PerlinNoise(p.x / 23f - 13.1f, p.y / 23f + 29.4f) - 1f);
                    float spurs = (Smooth(rn1) - .5f) * 5.5f + (Smooth(rn2) - .5f) * 1.6f;
                    float tilt = (Mathf.PerlinNoise(p.x / 130f + 3.3f, p.y / 130f - 5.1f) - .5f) * 6f;
                    yT[j, i] = Mathf.Max(yT[j, i] + (spurs + tilt) * free * above, lb[j, i]);
                }
            }
            for (int j = 0; j < Hh; j++) for (int i = 0; i < W; i++) h[j, i] = Mathf.Clamp01((yT[j, i] - tp.y) / sy);
            td.SetHeights(x0, z0, h);
            {   // cliff check: steepness on a 2 m grid where the ground was changed (not on the pinned road surfaces)
                var bad = new List<(float st, Vector2 p)>(); int n40 = 0, n50 = 0;
                for (float qz = Zone.yMin + 3; qz < Zone.yMax - 3; qz += 2f) for (float qx = Zone.xMin + 3; qx < Zone.xMax - 3; qx += 2f)
                {
                    var q = new Vector2(qx, qz); if (OwnAt(q) < .05f || OnRoad(q, samples, out _)) continue;
                    float st = td.GetSteepness((qx - tp.x) / td.size.x, (qz - tp.z) / td.size.z);
                    if (st > 40f) n40++; if (st > 50f) { n50++; bad.Add((st, q)); }
                }
                log.AppendLine($"steepness: {n40} samples > 40 deg, {n50} > 50 deg; worst: " + string.Join("; ", bad.OrderByDescending(b2 => b2.st).Take(12).Select(b2 => $"{b2.p.x:0},{b2.p.y:0} {b2.st:0}")));
            }

            // holes: only the tunnel mouths (first 1.5 m inside each face)
            int hr = td.holesResolution; float hx = td.size.x / hr, hz = td.size.z / hr;
            int c0 = Mathf.FloorToInt((Zone.xMin - tp.x) / hx), c1 = Mathf.CeilToInt((Zone.xMax - tp.x) / hx), r0 = Mathf.FloorToInt((Zone.yMin - tp.z) / hz), r1 = Mathf.CeilToInt((Zone.yMax - tp.z) / hz);
            var holes = td.GetHoles(c0, r0, c1 - c0, r1 - r0); int opened = 0, closed = 0;
            for (int j = 0; j < r1 - r0; j++) for (int i = 0; i < c1 - c0; i++)
            {
                var hp = new Vector2(tp.x + (c0 + i + .5f) * hx, tp.z + (r0 + j + .5f) * hz);
                var (hs, hd, _) = OnAxis(axis, axS, hp);
                bool mouth = hd < TunR + .5f && (hs > -.2f && hs < 1.5f || hs > tunL - 1.5f && hs < tunL + .2f);
                bool nearTunnel = hd < 40f && hs > -30f && hs < tunL + 30f;
                if (mouth) { if (holes[j, i]) opened++; holes[j, i] = false; }
                else if (!holes[j, i] && nearTunnel) { holes[j, i] = true; closed++; }
            }
            td.SetHoles(c0, r0, holes);
            log.AppendLine($"holes: mouths {opened}, Fedya's portal holes closed {closed}");

            // ---------------------------------------------------------------- splat (blended, no seams)
            int A = td.alphamapResolution; float ax = td.size.x / A, az = td.size.z / A;
            int a0 = Mathf.FloorToInt((Zone.xMin - tp.x) / ax), a1 = Mathf.CeilToInt((Zone.xMax - tp.x) / ax);
            int b0 = Mathf.FloorToInt((Zone.yMin - tp.z) / az), b1 = Mathf.CeilToInt((Zone.yMax - tp.z) / az);
            var al = td.GetAlphamaps(a0, b0, a1 - a0, b1 - b0); int L = td.alphamapLayers; const int meadow = 0, worn = 1, dirtL = 2, forestL = 3, rockL = 7;
            var target = new float[L];
            for (int j = 0; j < b1 - b0; j++) for (int i = 0; i < a1 - a0; i++)
            {
                float nx = (a0 + i + .5f) / A, nz = (b0 + j + .5f) / A;
                var p = new Vector2(tp.x + nx * td.size.x, tp.z + nz * td.size.z);
                float own = OwnAt(p);
                float eNew = 1e9f; foreach (var q in allRoads) eNew = Mathf.Min(eNew, (q.p - p).magnitude - q.half);
                float dOld = Mathf.Min(Mathf.Min(PolyDist(p, OldSerp), PolyDist(p, OldSpur)), PolyDist(p, OldCornice));
                float wGrass = Mathf.Max(own, dOld < 9f && eNew > 3f ? 1f - Mathf.InverseLerp(6f, 9f, dOld) : 0f);
                if (wGrass > 0f)
                {
                    System.Array.Clear(target, 0, L);
                    float n = Mathf.PerlinNoise(p.x * .05f, p.y * .05f), grove = Grove(p);
                    target[meadow] = (.35f + .4f * n) * (1f - grove * .7f); target[worn] = (.65f - .4f * n) * (1f - grove * .7f); target[forestL] = grove * .7f;
                    for (int l = 0; l < L; l++) al[j, i, l] = Mathf.Lerp(al[j, i, l], target[l], wGrass);
                }
                float rock = Mathf.InverseLerp(40f, 55f, td.GetSteepness(nx, nz)) * Mathf.Max(own, .3f);
                float dirt = eNew < 2.5f ? 1f - Mathf.Clamp01(eNew / 2.5f) : 0f;
                if ((p - PlazaC).magnitude < PlazaR + 2f) dirt = Mathf.Max(dirt, .8f);
                if (rock > 0 || dirt > 0)
                {
                    for (int l = 0; l < L; l++) al[j, i, l] *= 1f - Mathf.Max(rock, dirt * .7f);
                    al[j, i, rockL] += rock; al[j, i, dirtL] += dirt * .7f * (1f - rock);
                }
                float sum = 0; for (int l = 0; l < L; l++) sum += al[j, i, l];
                for (int l = 0; l < L; l++) al[j, i, l] /= Mathf.Max(sum, 1e-4f);
            }
            td.SetAlphamaps(a0, b0, al);

            // ---------------------------------------------------------------- trees: snap, clear roads/plaza/steep, W19 groves
            var trees = td.treeInstances.ToList(); int removedT = 0;
            var protoCount = new Dictionary<int, int>();
            for (int k = trees.Count - 1; k >= 0; k--)
            {
                var ti = trees[k]; var p = new Vector2(tp.x + ti.position.x * td.size.x, tp.z + ti.position.z * td.size.z);
                if (!Zone.Contains(p)) continue;
                protoCount.TryGetValue(ti.prototypeIndex, out int pc); protoCount[ti.prototypeIndex] = pc + 1;
                bool kill = (p - PlazaC).magnitude < PlazaR + 6f || td.GetSteepness(ti.position.x, ti.position.z) > 42f || PolyDist(p, TunnelPts) < 10f && OwnAt(p) > .1f;
                if (!kill) foreach (var q in allRoads) if ((q.p - p).magnitude < q.half + 2.5f) { kill = true; break; }
                if (!kill && UnderWall(p, 1.5f)) kill = true;
                if (!kill && AtFootWall(p, 4f)) kill = true;   // no trees on the sidewalks / shoulders at the foot walls
                if (kill) { trees.RemoveAt(k); removedT++; continue; }
                ti.position.y = td.GetInterpolatedHeight(ti.position.x, ti.position.z) / sy; trees[k] = ti;
            }
            var protos = protoCount.OrderByDescending(kv => kv.Value).Take(3).Select(kv => kv.Key).ToArray();
            int added = 0; var rnd = new System.Random(19);
            if (protos.Length > 0)
                for (float gz = Zone.yMin; gz < Zone.yMax; gz += 4.4f) for (float gx = Zone.xMin; gx < Zone.xMax; gx += 4.4f)
                {
                    var p = new Vector2(gx + (float)rnd.NextDouble() * 3.4f - 1.7f, gz + (float)rnd.NextDouble() * 3.4f - 1.7f);
                    float hill = HillAbove(p, false); if (hill < 2.5f || OwnAt(p) < .4f) continue;
                    float dPl = (p - PlazaC).magnitude, keepP = dPl < 48f ? .86f : .42f;
                    float gr = Grove(p); if (gr < .28f ? rnd.NextDouble() > .02 : rnd.NextDouble() > keepP) continue;
                    if (dPl < 60f && p.y < PlazaC.y - 6f && rnd.NextDouble() < .75) continue;
                    if (p.x > 950f && p.x < 1065f && p.y < 598f && p.y > 515f) continue;            // the view from the serpentine down to the city stays open
                    if ((p - PlazaC).magnitude < PlazaR + 9f || PolyDist(p, TunnelPts) < 14f) continue;
                    if (allRoads.Any(q => (q.p - p).magnitude < q.half + 5f) || UnderWall(p, 2f)) continue;
                    float nx = (p.x - tp.x) / td.size.x, nz = (p.y - tp.z) / td.size.z;
                    if (td.GetSteepness(nx, nz) > 36f) continue;
                    float sc = .85f + (float)rnd.NextDouble() * .45f;
                    trees.Add(new TreeInstance
                    {
                        position = new Vector3(nx, td.GetInterpolatedHeight(nx, nz) / sy, nz), prototypeIndex = protos[rnd.Next(protos.Length)],
                        widthScale = sc, heightScale = sc * (.92f + (float)rnd.NextDouble() * .16f), rotation = (float)rnd.NextDouble() * 6.283f,
                        color = Color.white, lightmapColor = Color.white
                    });
                    added++;
                }
            td.SetTreeInstances(trees.ToArray(), true);
            log.AppendLine($"trees: removed {removedT}, groves added {added} (prototypes {string.Join(",", protos)})");

            // ---------------------------------------------------------------- baked tall grass onto the new ground
            var grass = Object.FindFirstObjectByType<OnlyVolunteers.Map.W85.W85GrassRenderer>(FindObjectsInactive.Include);
            if (grass && grass.data && grass.data.instances)
            {
                var src = grass.data; var bytes = (byte[])src.instances.bytes.Clone();
                var chunks = (OnlyVolunteers.Map.Grass.GrassPatchData24.Chunk[])src.chunks.Clone();
                int gMoved = 0, gHidden = 0; var wb = src.worldBounds;
                void Put(int o, float v) { var b4 = System.BitConverter.GetBytes(v); System.Buffer.BlockCopy(b4, 0, bytes, o, 4); }
                for (int c = 0; c < chunks.Length; c++)
                {
                    var ch = chunks[c];
                    if (!new Rect(ch.centre.x - ch.extents.x, ch.centre.z - ch.extents.z, ch.extents.x * 2f, ch.extents.z * 2f).Overlaps(Zone)) continue;
                    float ymin = 1e9f, ymax = -1e9f; bool touched = false;
                    for (uint k = ch.start; k < ch.start + ch.count && (k + 1) * 32 <= bytes.Length; k++)
                    {
                        int o = (int)k * 32;
                        float gx = System.BitConverter.ToSingle(bytes, o), gyOld = System.BitConverter.ToSingle(bytes, o + 4), gz = System.BitConverter.ToSingle(bytes, o + 8), gh = System.BitConverter.ToSingle(bytes, o + 12);
                        var p = new Vector2(gx, gz); float gy = gyOld;
                        if (Zone.Contains(p))
                        {
                            touched = true;
                            gy = terrain.SampleHeight(new Vector3(gx, 0, gz)) + tp.y;
                            if (Mathf.Abs(gy - gyOld) > .02f) { Put(o + 4, gy); gMoved++; }
                            bool kill = (p - PlazaC).magnitude < PlazaR + 1f || td.GetSteepness((gx - tp.x) / td.size.x, (gz - tp.z) / td.size.z) > 42f;
                            if (!kill) foreach (var q in allRoads) if ((q.p - p).magnitude < q.half + .3f) { kill = true; break; }
                            if (!kill && UnderWall(p, .4f)) kill = true;
                            if (kill && gh > 0f) { Put(o + 12, 0f); gh = 0f; gHidden++; }
                        }
                        ymin = Mathf.Min(ymin, gy); ymax = Mathf.Max(ymax, gy + gh);
                    }
                    if (touched && ymax > ymin) { ch.centre.y = (ymin + ymax) * .5f; ch.extents.y = (ymax - ymin) * .5f + .5f; chunks[c] = ch; wb.Encapsulate(new Vector3(ch.centre.x, ymin, ch.centre.z)); wb.Encapsulate(new Vector3(ch.centre.x, ymax, ch.centre.z)); }
                }
                string bp = Dir + "/Grass_W86_hill.bytes"; File.WriteAllBytes(bp, bytes); AssetDatabase.ImportAsset(bp, ImportAssetOptions.ForceUpdate);
                var nd = ScriptableObject.CreateInstance<OnlyVolunteers.Map.Grass.GrassPatchData24>();
                nd.instances = AssetDatabase.LoadAssetAtPath<TextAsset>(bp); nd.instanceCount = src.instanceCount; nd.worldBounds = wb; nd.chunks = chunks;
                nd.sourceScene = src.sourceScene; nd.sourceCommit = src.sourceCommit; nd.placementSummary = src.placementSummary + " | VadimHill v7: blades re-seated on hill B";
                string dp = Dir + "/GrassData_W86_hill.asset"; AssetDatabase.DeleteAsset(dp); AssetDatabase.CreateAsset(nd, dp);
                grass.data = nd; EditorUtility.SetDirty(grass);
                log.AppendLine($"grass: {gMoved} blades re-seated, {gHidden} hidden (roads, plaza, steep)");
            }

            // ---------------------------------------------------------------- materials, old objects off
            Material roadMat = null, corniceMat = null, tubeMat = null, deckMat = null, stoneMat = null, gravelMat = null; float tile = 6f; Transform roadsParent = null; int layer = 0;
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (r.name == "Road_serpentine_view_b") { roadMat = r.sharedMaterial; roadsParent = r.transform.parent; layer = r.gameObject.layer; var m = r.GetComponent<MeshFilter>()?.sharedMesh; if (m) { float mu = m.uv.Max(u => Mathf.Abs(u.x)); if (mu > 0) tile = 6.4f / mu; } }
                if (r.name == "Road_cornice_view_c") corniceMat = r.sharedMaterial;
                if (r.name == "Tunnel_shell") tubeMat = r.sharedMaterial;
                if (r.name == "Tunnel_road") deckMat = r.sharedMaterial;
                if (r.name.StartsWith("Parapet_view_b_spur_stone")) stoneMat = r.sharedMaterial;
            }
            var pocket = GameObject.Find("ViewPocket_view_b_spur");
            Transform benchT = null, lampT = null;
            if (pocket)
            {
                float bestA = 0;
                foreach (Transform ch in pocket.transform)
                {
                    if (ch.name.Contains("bench") && !benchT) benchT = ch;
                    if (ch.name.Contains("lamp")) lampT = ch;
                    var rr = ch.GetComponent<MeshRenderer>();
                    if (rr && !ch.name.Contains("bench") && !ch.name.Contains("lamp") && !ch.name.StartsWith("Parapet")) { float a = rr.bounds.size.x * rr.bounds.size.z; if (a > bestA) { bestA = a; gravelMat = rr.sharedMaterial; } }
                }
            }
            if (!stoneMat) foreach (var g in AssetDatabase.FindAssets("cobble t:Material")) { stoneMat = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(g)); if (stoneMat) break; }
            var root = GameObject.Find("Map_W85_v02").transform;
            foreach (var n in new[] { "Road_serpentine_view_b_up_v2", "Road_serpentine_view_b_down_v2", "Road_serpentine_view_b_v3", "Road_view_b_spur_v2", "Road_cornice_view_c_v2", "Road_tunnel_north_approach_v2", "Road_tunnel_south_approach_v2", "Road_cornice_parapet_v2", "Wall_route_v1", "Wall_foot_v1", "Wall_route_v2", "Wall_foot_v2", "Wall_deck_v2", "Wall_apron_v2", "VadimSidewalkFill", "Tunnel_v2", "VadimMeetPlaza", "VadimHillRocks" })
            { var e = GameObject.Find(n); if (e) Object.DestroyImmediate(e); }
            int off = 0;
            foreach (var tr in Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                string n = tr.name;
                bool oldRoad = (n.Contains("serpentine_view_b") || n.Contains("view_b_spur") || n.Contains("cornice_view_c")) && !n.Contains("_v2");
                bool oldTunnel = tr.parent && tr.parent.name == "Tunnel" || n == "Road_tunnel_north_approach" || n == "Road_tunnel_south_approach";
                bool tunnelWall = n.StartsWith("Wall_retaining_tunnel");
                if ((oldRoad || oldTunnel || tunnelWall) && tr.gameObject.activeSelf && (!tr.parent || !tr.parent.name.StartsWith("ViewPocket"))) { tr.gameObject.SetActive(false); off++; }
            }
            log.AppendLine($"old serpentine/spur/cornice/tunnel objects off: {off}");

            // Fedya's rock faces / outcrops / decals that no longer sit on the ground
            int rockCut = 0, decalCut = 0, meshes = 0;
            foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None))
            {
                if (!mf.sharedMesh) continue;
                bool rockFace = mf.transform.parent && mf.transform.parent.name == "RockFaces";
                bool decal = false; for (var q = mf.transform; q != null; q = q.parent) if (q.name.StartsWith("Decal")) { decal = true; break; }
                if (!rockFace && !decal) continue;
                var bnd = mf.GetComponent<Renderer>().bounds;
                if (!new Rect(bnd.min.x, bnd.min.z, bnd.size.x, bnd.size.z).Overlaps(Zone)) continue;
                var m = mf.sharedMesh; var v = m.vertices; var tri = m.triangles; var keep = new List<int>(); var l2w = mf.transform.localToWorldMatrix;
                for (int k = 0; k < tri.Length; k += 3)
                {
                    var c = l2w.MultiplyPoint3x4((v[tri[k]] + v[tri[k + 1]] + v[tri[k + 2]]) / 3f); var p = new Vector2(c.x, c.z);
                    bool bad = false;
                    if (Zone.Contains(p))
                    {
                        float gy = terrain.SampleHeight(c) + tp.y, eNew = 1e9f; foreach (var q in allRoads) eNew = Mathf.Min(eNew, (q.p - p).magnitude - q.half);
                        bad = rockFace ? OwnAt(p) > .02f || PolyDist(p, TunnelPts) < 30f || eNew < 10f || Mathf.Abs(c.y - gy) > .6f || AtFootWall(p, 1f)
                                       : eNew > 1f && (Mathf.Min(Mathf.Min(PolyDist(p, OldSerp), PolyDist(p, OldSpur)), PolyDist(p, OldCornice)) < 9f || Mathf.Abs(c.y - gy) > .35f || BehindFoot(p));
                    }
                    if (bad) { if (rockFace) rockCut++; else decalCut++; } else keep.AddRange(new[] { tri[k], tri[k + 1], tri[k + 2] });
                }
                if (keep.Count == tri.Length) continue;
                var nm = Object.Instantiate(m); nm.name = m.name + "_hill"; nm.SetTriangles(keep, 0); nm.RecalculateBounds();
                string path = Dir + "/clip_" + meshes + ".asset"; AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(nm, path);
                mf.sharedMesh = nm; meshes++;
            }
            int outcrops = 0;
            var oc = GameObject.Find("RockOutcrops");
            if (oc) foreach (Transform r in oc.transform)
            {
                var p = new Vector2(r.position.x, r.position.z); if (!Zone.Contains(p)) continue;
                bool kill = allRoads.Any(q => (q.p - p).magnitude < q.half + 4f) || (p - PlazaC).magnitude < PlazaR + 5f || PolyDist(p, TunnelPts) < 30f || AtFootWall(p, 3f);
                if (kill) { r.gameObject.SetActive(false); continue; }
                if (OwnAt(p) > .02f) { var pos = r.position; pos.y = terrain.SampleHeight(pos) + tp.y - .4f; r.position = pos; outcrops++; }
            }
            log.AppendLine($"rock faces cut {rockCut} tris, decals cut {decalCut} tris ({meshes} meshes); outcrops re-seated {outcrops}");

            int moved = 0, dropped = 0;
            foreach (Transform g in root)
            {
                if (g.name.StartsWith("District_") || g.name == "Tunnel" || g.name == "Roads" || g.name.StartsWith("ViewPocket") || g.name.StartsWith("Decal") || g.name.StartsWith("Rock") || g.name.StartsWith("Vadim") || g.GetComponent<Terrain>()) continue;
                foreach (Transform c in g)
                {
                    var p3 = c.position; var p = new Vector2(p3.x, p3.z);
                    if (!Zone.Contains(p) || !c.gameObject.activeSelf) continue;
                    int i = Mathf.Clamp(Mathf.RoundToInt((p.x - tp.x) / sx) - x0, 0, W - 1), j = Mathf.Clamp(Mathf.RoundToInt((p.y - tp.z) / sz) - z0, 0, Hh - 1);
                    float og = tp.y + old[j, i] * sy, ng = tp.y + h[j, i] * sy;
                    if (Mathf.Abs(p3.y - og) > 1.5f || Mathf.Abs(ng - og) < .05f) continue;
                    if (allRoads.Any(q => (q.p - p).magnitude < q.half + .5f) || (p - PlazaC).magnitude < PlazaR + 2f) { c.gameObject.SetActive(false); dropped++; continue; }
                    c.position = p3 + Vector3.up * (ng - og); moved++;
                }
            }
            log.AppendLine($"objects re-snapped {moved}, dropped {dropped}");

            // ---------------------------------------------------------------- rock outcrops on the slopes
            {
                var templates = new List<GameObject>();
                if (oc) foreach (Transform r in oc.transform) if (r.GetComponentInChildren<MeshRenderer>() && templates.Count < 8 && !templates.Any(x => x.name.Split(' ')[0] == r.name.Split(' ')[0])) templates.Add(r.gameObject);
                var rockParent = new GameObject("VadimHillRocks").transform; rockParent.SetParent(root, false);
                var rr = new System.Random(7); int clusters = 0, rocks = 0;
                for (int tries = 0; tries < 4000 && clusters < 34 && templates.Count > 0; tries++)
                {
                    var p = new Vector2(Zone.xMin + 40f + (float)rr.NextDouble() * (Zone.width - 80f), Zone.yMin + 30f + (float)rr.NextDouble() * (Zone.height - 60f));
                    if (OwnAt(p) < .6f || HillAbove(p, false) < 9f) continue;
                    float nx = (p.x - tp.x) / td.size.x, nz = (p.y - tp.z) / td.size.z, st = td.GetSteepness(nx, nz);
                    if (st < 14f || st > 40f) continue;
                    float crest = 1f - Mathf.Abs(2f * Mathf.PerlinNoise(p.x / 52f + 41.3f, p.y / 52f + 7.9f) - 1f);
                    if (crest < .55f && rr.NextDouble() > .25) continue;
                    if ((p - PlazaC).magnitude < PlazaR + 9f || PolyDist(p, TunnelPts) < 22f || allRoads.Any(q => (q.p - p).magnitude < q.half + 7f)) continue;
                    int n = 2 + rr.Next(3);
                    for (int k = 0; k < n; k++)
                    {
                        var q2 = p + new Vector2((float)rr.NextDouble() * 7f - 3.5f, (float)rr.NextDouble() * 7f - 3.5f);
                        if (allRoads.Any(q => (q.p - q2).magnitude < q.half + 5f)) continue;
                        var g = Object.Instantiate(templates[rr.Next(templates.Count)], rockParent); g.name = "HillRock_" + rocks; g.SetActive(true);
                        float sc = (k == 0 ? 2.2f : 1.3f) + (float)rr.NextDouble() * (k == 0 ? 1.6f : .9f);
                        g.transform.localScale = Vector3.one * sc;
                        g.transform.rotation = Quaternion.Euler((float)rr.NextDouble() * 14f - 7f, (float)rr.NextDouble() * 360f, (float)rr.NextDouble() * 14f - 7f);
                        var w = new Vector3(q2.x, 0, q2.y); w.y = terrain.SampleHeight(w) + tp.y;
                        var bnd = g.GetComponentInChildren<Renderer>().bounds; float hgt = Mathf.Max(.5f, bnd.size.y);
                        g.transform.position = w - Vector3.up * hgt * .35f;
                        rocks++;
                    }
                    clusters++;
                }
                log.AppendLine($"rock outcrops: {clusters} clusters, {rocks} rocks ({templates.Count} rock models)");
            }

            // ---------------------------------------------------------------- new roads, plaza, tunnel
            if (!roadsParent) roadsParent = root;
            var markMat = MarkingMaterial(roadMat);
            MakeRoad("Road_serpentine_view_b_v3", main, RoadW, tile, roadMat, roadsParent, layer, null, 3.5f, 3.5f);
            MakeRoad("Road_view_b_spur_v2", spur, SpurW, tile, roadMat, roadsParent, layer, null, 4f, 0f, (q, sq, yq) => JunctionY(q, sq, yq, samples));
            // where the new roads meet the streets: the sidewalks / kerbs under them are cut out
            int cut = 0;
            cut += CutSidewalks(main, RoadW, true) + CutSidewalks(main, RoadW, false) + CutSidewalks(cornice, 6.4f, true) + CutSidewalks(cornice, 6.4f, false);
            cut += CutSidewalks(napp, RoadW, true) + CutSidewalks(sapp, RoadW, false);
            log.AppendLine($"street joins: {cut} sidewalk/kerb triangles cut under the new roads");
            { var sbq = new StringBuilder("cornice start heights:"); for (float qz = 490; qz <= 530; qz += 5) { sbq.Append($" z{qz}:"); for (float qx = 1195; qx <= 1240; qx += 5) sbq.Append(" " + (terrain.SampleHeight(new Vector3(qx, 0, qz)) + tp.y).ToString("0")); } log.AppendLine(sbq.ToString()); }
            MakeRoad("Road_cornice_view_c_v2", cornice, 6.4f, tile, corniceMat ? corniceMat : roadMat, roadsParent, layer, markMat, 3.5f, 3f);
            MakeRoad("Road_tunnel_north_approach_v2", napp, RoadW, tile, roadMat, roadsParent, layer, markMat, 3.5f, 0f);
            MakeRoad("Road_tunnel_south_approach_v2", sapp, RoadW, tile, roadMat, roadsParent, layer, markMat, 0f, 3.5f);
            var wallMat = RetainingMaterial(tubeMat);
            SidewalkFill(root, layer, log);
            BuildWalls(terrain, wallMat, roadMat, roadsParent, layer, log);
            FixLamps(log);
            CorniceParapet(samples, stoneMat, roadsParent, layer, log);
            BuildPlaza(root, plazaY, gravelMat, stoneMat, benchT, lampT, layer, log);
            if (pocket) pocket.SetActive(false);
            var (wallG, portalG, archG) = TunnelMaterials(tubeMat);
            TunnelMarkMat = markMat;
            BuildTunnel(root, axis, wallG, roadMat ? roadMat : deckMat, portalG, archG, layer, log);
            BuildBorder(root, layer, roadMat, log);
            BuildTramduro(root, layer, log);
            BuildDowntownFixes(root, layer, roadMat, log);
            BuildValley(root, layer, log);
            BuildElite(root, layer, log);
            OneStone(log);
            DeepenShoals(log);
            NoFoamDecals(log);

            // haze 10 % earlier (Vadim 23.10)
            var night = Object.FindFirstObjectByType<OnlyVolunteers.VadimLocal.VadimNightCity>(FindObjectsInactive.Include);
            if (night) { night.hazeStart = 99f; night.hazeHalf = 342f; EditorUtility.SetDirty(night); log.AppendLine("haze 99 / 342 m"); }

            terrain.Flush();
            EditorUtility.SetDirty(td);
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Shots(axis, axS, tunL, plazaY);
            File.WriteAllText(@"C:\Users\chern_0eqkb03\VolunteersBuilds\hill_apply.txt", log.ToString());
        }

        /// <summary>What sits at the blue patch by Downtown's north-west corner (x 845-905, z 515-545).</summary>
        public static void Probe()
        {
            EditorSceneManager.OpenScene(Scene);
            var sb = new StringBuilder();
            foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None))
            {
                var r = mf.GetComponent<Renderer>(); if (!r || !mf.sharedMesh) continue;
                var b = r.bounds; if (b.SqrDistance(new Vector3(945, 5.2f, 667)) > 9f || b.size.magnitude > 600f) continue;
                string path = mf.name; for (var q = mf.transform.parent; q != null; q = q.parent) path = q.name + "/" + path;
                sb.AppendLine($"{path} b={b.center:F1} size={b.size:F1} mat={(r.sharedMaterial ? r.sharedMaterial.name : "-")} tris={mf.sharedMesh.triangles.Length / 3} col={(mf.GetComponent<Collider>() ? "yes" : "no")}");
            }
            File.WriteAllText(@"C:\Users\chern_0eqkb03\VolunteersBuilds\probe.txt", sb.ToString());
        }

        /// <summary>Reference shots for the retaining walls (GPT prompt) and a look at the cornice / tunnel approaches.</summary>
        public static void RefWalls()
        {
            EditorSceneManager.OpenScene(Scene);
            var sb = new StringBuilder();
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None))
            {
                var m = r.sharedMaterial; if (!m) continue;
                if (m.name.Contains("Sea") || m.name.Contains("sea") || r.name.Contains("Sea") || r.name.Contains("Water"))
                    sb.AppendLine($"WATER {r.name} mat={m.name} b={r.bounds.center:F1} size={r.bounds.size:F0}");
            }
            var ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); float ty = ter.transform.position.y;
            foreach (var z in new[] { 500f, 520f, 540f, 560f, 580f, 600f })
            {
                sb.Append($"cornice z{z}:");
                for (float x = 1180; x <= 1290; x += 10) sb.Append(" " + (ter.SampleHeight(new Vector3(x, 0, z)) + ty).ToString("0.0"));
                sb.AppendLine();
            }
            var app = new[] { new Vector2(822.6f, 548), new Vector2(827, 541), new Vector2(830, 533), new Vector2(831, 520), new Vector2(831, 502), new Vector2(748, 671), new Vector2(748, 660), new Vector2(748, 649) };
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None))
            {
                var c = r.bounds.center; var p = new Vector2(c.x, c.z);
                if (r.bounds.size.magnitude > 300f) continue;
                if (app.Any(a => (a - p).magnitude < 12f) && !r.name.StartsWith("B_") && !r.name.Contains("Parapet"))
                {
                    string path = r.name; for (var q = r.transform.parent; q != null; q = q.parent) path = q.name + "/" + path;
                    sb.AppendLine($"NEAR-APPROACH {path} active={r.gameObject.activeInHierarchy} b={c:F1} size={r.bounds.size:F1} mat={(r.sharedMaterial ? r.sharedMaterial.name : "-")}");
                }
            }
            File.WriteAllText(@"C:\Users\chern_0eqkb03\VolunteersBuilds\refwalls.txt", sb.ToString());
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("RefCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.clearFlags = CameraClearFlags.Skybox;
            string D = @"C:\Users\chern_0eqkb03\VolunteersBuilds\";
            cam.fieldOfView = 60;
            go.transform.position = new Vector3(905, 7.5f, 511); go.transform.LookAt(new Vector3(900, 14, 565)); Shot(cam, 1400, 800, D + "wall_ref_downtown.png");
            go.transform.position = new Vector3(1005, 7.5f, 511); go.transform.LookAt(new Vector3(990, 15, 570)); Shot(cam, 1400, 800, D + "wall_ref_downtown2.png");
            go.transform.position = new Vector3(946, 7.5f, 684); go.transform.LookAt(new Vector3(948, 12, 640)); Shot(cam, 1400, 800, D + "wall_ref_rough_exit.png");
            go.transform.position = new Vector3(960, 90, 430); go.transform.LookAt(new Vector3(940, 15, 560)); Shot(cam, 1400, 800, D + "wall_ref_overview.png");
            go.transform.position = new Vector3(1290, 30, 515); go.transform.LookAt(new Vector3(1215, 10, 560)); Shot(cam, 1200, 700, D + "cornice_persp.png");
            cam.orthographic = true; cam.orthographicSize = 75; go.transform.position = new Vector3(1225, 300, 565); go.transform.rotation = Quaternion.Euler(90, 0, 0);
            Shot(cam, 1200, 1000, D + "cornice_top.png");
            cam.orthographicSize = 28; go.transform.position = new Vector3(828, 300, 527); Shot(cam, 800, 800, D + "approach_s_top.png");
            go.transform.position = new Vector3(748, 300, 660); Shot(cam, 800, 800, D + "approach_n_top.png");
            Object.DestroyImmediate(go);
        }

        /// <summary>Reference shots: the beach in front of Downtown (transition city -> sand) and the Quiet Valley fence with the forest.</summary>
        public static void RefBeach()
        {
            EditorSceneManager.OpenScene(Scene);
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            foreach (var mb in Object.FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None))
                if (System.Text.RegularExpressions.Regex.IsMatch(mb.GetType().Name, "(?i)fog|aerial")) mb.enabled = false;
            var go = new GameObject("RefCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.clearFlags = CameraClearFlags.Skybox;
            string D = @"C:\Users\chern_0eqkb03\VolunteersBuilds\ref_";
            cam.orthographic = true; go.transform.rotation = Quaternion.Euler(90, 0, 0);
            cam.orthographicSize = 125; go.transform.position = new Vector3(1080, 300, 150); Shot(cam, 1800, 750, D + "beach_top.png");
            cam.orthographicSize = 75; go.transform.position = new Vector3(760, 300, 170); Shot(cam, 1200, 1000, D + "beach_sw_top.png");
            cam.orthographicSize = 110; go.transform.position = new Vector3(520, 300, 210); Shot(cam, 1200, 1000, D + "valley_top.png");
            cam.orthographic = false; cam.fieldOfView = 60;
            go.transform.position = new Vector3(1000, 55, 10); go.transform.LookAt(new Vector3(1000, 5, 175)); Shot(cam, 1400, 800, D + "beach_from_sea.png");
            go.transform.position = new Vector3(820, 45, 90); go.transform.LookAt(new Vector3(780, 6, 190)); Shot(cam, 1400, 800, D + "beach_sw_persp.png");
            go.transform.position = new Vector3(960, 8, 200); go.transform.LookAt(new Vector3(960, 2, 120)); Shot(cam, 1400, 800, D + "beach_street_end.png");
            go.transform.position = new Vector3(1150, 8, 200); go.transform.LookAt(new Vector3(1150, 2, 120)); Shot(cam, 1400, 800, D + "beach_street_end2.png");
            go.transform.position = new Vector3(470, 30, 300); go.transform.LookAt(new Vector3(535, 6, 250)); Shot(cam, 1400, 800, D + "valley_forest_edge.png");
            go.transform.position = new Vector3(600, 40, 110); go.transform.LookAt(new Vector3(545, 6, 200)); Shot(cam, 1400, 800, D + "valley_from_beach.png");
            go.transform.position = new Vector3(530, 4, 290); go.transform.LookAt(new Vector3(540, 3, 270)); Shot(cam, 1400, 800, D + "valley_fence_close.png");
            Object.DestroyImmediate(go);
        }

        public static void Restore()
        {
            string tdPath = File.ReadAllText(Path.Combine(Bak, "terrain_path.txt")).Trim();
            File.Copy(Path.Combine(Bak, Path.GetFileName(tdPath)), tdPath, true);
            File.Copy(Path.Combine(Bak, Path.GetFileName(Scene)), Scene, true);
            foreach (var f in Directory.GetFiles(Bak, "steppe_*"))
                foreach (var g in AssetDatabase.FindAssets(Path.GetFileNameWithoutExtension(f).Substring(7) + " t:TerrainData"))
                { var tp2 = AssetDatabase.GUIDToAssetPath(g); if (Path.GetFileName(tp2) == Path.GetFileName(f).Substring(7)) File.Copy(f, tp2, true); }
            AssetDatabase.Refresh();
        }

        // ------------------------------------------------------------------------------------------------ shape helpers

        static float[,] Own; static int OX, OZ; static float OSX, OSZ; static Vector3 OTP;
        static float OwnAt(Vector2 p)
        {
            if (Own == null) return 0f;
            int i = Mathf.RoundToInt((p.x - OTP.x) / OSX) - OX, j = Mathf.RoundToInt((p.y - OTP.z) / OSZ) - OZ;
            if (i < 0 || j < 0 || i >= Own.GetLength(1) || j >= Own.GetLength(0)) return 0f;
            return Own[j, i];
        }

        /// <summary>Hill height over the plain: W19 ridge falloff (smoothstep of 1 - d / half width) times W19's 45 m noise factor, plus
        /// small natural bumps; no noise factor right at the plaza so the summit stays where the meeting place is.</summary>
        static float HillAbove(Vector2 p, bool bumps)
        {
            float best = Mathf.Max(Mathf.Max(RidgeH(Ridge, p), RidgeH(Headland, p)), DescentRidge.Length > 1 ? RidgeH(DescentRidge, p) : 0f);
            if (best <= 0f) return 0f;
            float f = Mathf.Lerp(1f, .8f + .4f * Fbm(p.x / 45f, p.y / 45f, 2), Mathf.InverseLerp(20f, 60f, (p - PlazaC).magnitude));
            float hh = best * f;
            if (bumps) hh += ((Fbm(p.x / 18f + 7.1f, p.y / 18f - 3.3f, 2) - .5f) * 1.8f + (Mathf.PerlinNoise(p.x / 7f + 3.1f, p.y / 7f + 8.3f) - .5f) * .5f) * Mathf.Clamp01(hh / 8f);
            return Mathf.Max(0f, hh);
        }

        static float RidgeH(Vector4[] rg, Vector2 p)
        {
            float best = 0f;
            for (int i = 0; i + 1 < rg.Length; i++)
            {
                Vector2 a = rg[i], b = rg[i + 1], ab = b - a;
                float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude), d = (p - (a + ab * t)).magnitude;
                float top = Mathf.Lerp(rg[i].z, rg[i + 1].z, t), hw = Mathf.Lerp(rg[i].w, rg[i + 1].w, t);
                var cpt = a + ab * t; if (p.y > cpt.y) d *= hw / (hw + 18f); else d *= hw / (hw - 6f);   // the south foot reaches the plain before Downtown
                if (d < hw) best = Mathf.Max(best, top * Smooth(1f - d / hw));
            }
            return best;
        }

        /// <summary>Where the districts and the port keep their ground (0) and where the hill may change it (1).</summary>
        static float DistrictKeep(Vector2 p)
        {
            float rough = Mathf.Max(Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(670f, 660f, p.y)), 1f - Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(28f, 45f, (p - TunnelPts[0]).magnitude)));   // Fedya's portal banks go too
            float dtEast = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(519f, 525f, p.y)), dtWest = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(478f, 540f, p.y));
            float downtown = Mathf.Lerp(dtWest, dtEast, Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(765f, 800f, p.x)));
            float port = p.x > 1150f ? Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(597f, 584f, p.y)) : 1f;
            float build = 1f - (1f - Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(700f, 725f, p.x))) * (1f - Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(500f, 525f, p.y)));   // the construction site
            return rough * downtown * port * build;
        }

        static float EdgeFade(Vector2 p) => Mathf.Clamp01(Mathf.Min(Mathf.Min(p.x - Zone.xMin, Zone.xMax - p.x), Mathf.Min(p.y - Zone.yMin, Zone.yMax - p.y)) / 25f);

        /// <summary>W19-like groves: patches of 35-40 m, denser on the west and east masses.</summary>
        static float Grove(Vector2 p)
        {
            float g = Mathf.InverseLerp(.42f, .62f, Fbm(p.x / 38f + 5.3f, p.y / 38f + 1.7f, 2));
            float mass = Mathf.Max(Mathf.InverseLerp(980f, 930f, p.x), Mathf.InverseLerp(1040f, 1080f, p.x));
            return Mathf.Clamp01(g * (.45f + .55f * mass) + .15f * mass);
        }

        static float Smooth(float t) { t = Mathf.Clamp01(t); return t * t * (3f - 2f * t); }

        static float Fbm(float x, float y, int oct)
        {
            float s = 0f, a = .5f, f = 1f, norm = 0f;
            for (int o = 0; o < oct; o++) { s += a * Mathf.PerlinNoise(x * f + 31.7f * o, y * f + 17.3f * o); norm += a; a *= .5f; f *= 2f; }
            return s / norm;
        }

        static bool OnRoad(Vector2 p, List<S> roads, out float ry)
        {
            ry = 0f; float best = 1e9f; S nb = default;
            foreach (var q in roads) { float d = (q.p - p).sqrMagnitude; if (d < best) { best = d; nb = q; } }
            if (roads.Count == 0 || Mathf.Sqrt(best) > nb.half) return false;
            ry = nb.y - .12f; return true;
        }

        static float[,] Blur(float[,] src, int rx, int rz, int passes)
        {
            int H = src.GetLength(0), W = src.GetLength(1); var a = (float[,])src.Clone(); var b = new float[H, W];
            for (int it = 0; it < passes; it++)
            {
                for (int j = 0; j < H; j++) { float acc = 0; int n = 0; for (int i = -rx; i < W + rx; i++) { int add = i + rx, rem = i - rx - 1; if (add < W) { acc += a[j, add]; n++; } if (rem >= 0) { acc -= a[j, rem]; n--; } if (i >= 0 && i < W) b[j, i] = acc / n; } }
                for (int i = 0; i < W; i++) { float acc = 0; int n = 0; for (int j = -rz; j < H + rz; j++) { int add = j + rz, rem = j - rz - 1; if (add < H) { acc += b[add, i]; n++; } if (rem >= 0) { acc -= b[rem, i]; n--; } if (j >= 0 && j < H) a[j, i] = acc / n; } }
            }
            return a;
        }

        static float Corridor(float y, Vector2 p, List<S> roads, bool active = true)
        {
            if (!active || roads.Count == 0) return y;
            float best = 1e9f; S nb = default;
            foreach (var q in roads) { float d = (q.p - p).sqrMagnitude; if (d < best) { best = d; nb = q; } }
            float e = Mathf.Sqrt(best) - nb.half;
            if (e >= 80f) return y;
            float ry = nb.y - .12f;
            if (e <= 0) return ry;
            float far = Mathf.Max(0f, e - 10f); far *= far * .06f;
            y = Mathf.Clamp(y, ry - e * .6f - far, ry + e * nb.cut + far);
            return y;
        }

        static (float s, float d, float y) OnAxis(List<(Vector2 p, float y)> axis, float[] axS, Vector2 p)
        {
            float bd = 1e9f, bs = -1f, by = 0f;
            for (int i = 0; i + 1 < axis.Count; i++)
            {
                Vector2 a = axis[i].p, b = axis[i + 1].p, ab = b - a; float L2 = ab.sqrMagnitude; if (L2 < 1e-6f) continue;
                float tRaw = Vector2.Dot(p - a, ab) / L2, t = Mathf.Clamp01(tRaw);
                float d = (p - (a + ab * t)).magnitude;
                if (d < bd)
                {
                    bd = d; by = Mathf.Lerp(axis[i].y, axis[i + 1].y, t);
                    bs = axS[i] + Mathf.Sqrt(L2) * (i == 0 ? Mathf.Min(tRaw, 1f) : i == axis.Count - 2 ? Mathf.Max(tRaw, 0f) : t);
                }
            }
            return (bs, bd, by);
        }

        static float SegDist(Vector2 p, Vector2 a, Vector2 b) { var ab = b - a; float l2 = ab.sqrMagnitude; if (l2 < 1e-6f) return (p - a).magnitude; float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / l2); return (p - (a + ab * t)).magnitude; }
        static float PolyDist(Vector2 p, Vector2[] pl) { float d = 1e9f; for (int i = 0; i + 1 < pl.Length; i++) d = Mathf.Min(d, SegDist(p, pl[i], pl[i + 1])); return d; }

        static Vector2[] PolyFromJson(Dictionary<string, object> rj, string id, out float[] heights)
        {
            heights = null;
            foreach (var ro in (List<object>)rj["roads"])
            {
                var r = (Dictionary<string, object>)ro; if ((string)r["id"] != id) continue;
                heights = ((List<object>)r["heights"]).Select(o => System.Convert.ToSingle(o)).ToArray();
                return ((List<object>)r["points"]).Select(o => { var a = (List<object>)o; return new Vector2(System.Convert.ToSingle(a[0]), System.Convert.ToSingle(a[1])); }).ToArray();
            }
            return new Vector2[0];
        }

        /// <summary>The cornice to the port over the headland: Fedya's line, his heights at both ends, a 14 m crest at (1206, 556).</summary>
        static List<(Vector2 p, float y)> CorniceProfile(Vector2[] pl, float[] hs)
        {
            var pts = new List<Vector2> { pl[0] };
            for (int i = 0; i + 1 < pl.Length; i++)
            {
                float L = (pl[i + 1] - pl[i]).magnitude; int k = Mathf.Max(1, (int)(L / 2f));
                for (int j = 1; j <= k; j++) pts.Add(Vector2.Lerp(pl[i], pl[i + 1], j / (float)k));
            }
            var s = new float[pts.Count]; for (int i = 1; i < pts.Count; i++) s[i] = s[i - 1] + (pts[i] - pts[i - 1]).magnitude;
            int Near(Vector2 q) { int bi = 0; float bd = 1e9f; for (int i = 0; i < pts.Count; i++) { float d = (pts[i] - q).sqrMagnitude; if (d < bd) { bd = d; bi = i; } } return bi; }
            int iA = Near(new Vector2(1257, 598)), iP = Near(new Vector2(1206, 556)), iB = Near(new Vector2(1202, 506));
            float Orig(int i) => hs != null && hs.Length > 0 ? hs[Mathf.Clamp(i, 0, hs.Length - 1)] : 5f;
            const float peak = 14f;
            var outL = new List<(Vector2, float)>();
            for (int i = 0; i < pts.Count; i++)
            {
                float y;
                if (i <= Mathf.Min(iA, iB) || i >= Mathf.Max(iA, iB)) y = Orig(i);
                else
                {
                    bool firstHalf = iA < iB ? i <= iP : i >= iP;
                    int e0 = firstHalf ? iA : iB; float y0 = Orig(e0);
                    float u = Mathf.Abs(s[i] - s[e0]) / Mathf.Max(1f, Mathf.Abs(s[iP] - s[e0]));
                    y = Mathf.Lerp(y0, peak, Smooth(u) * .6f + u * .4f);
                }
                outL.Add((pts[i], y));
            }
            return outL;
        }

        static List<(Vector2 p, float y)> Profile(Vector2[] pl, float h0, float h1, int smooth = 8, bool roundEnds = true)
        {
            var pts = new List<Vector2> { pl[0] };
            for (int i = 0; i + 1 < pl.Length; i++)
            {
                int k = Mathf.Max(1, Mathf.RoundToInt((pl[i + 1] - pl[i]).magnitude));
                for (int j = 1; j <= k; j++) pts.Add(Vector2.Lerp(pl[i], pl[i + 1], j / (float)k));
            }
            for (int it = 0; it < smooth; it++)
            {
                var n = new List<Vector2>(pts);
                for (int i = 1; i + 1 < pts.Count; i++) n[i] = (pts[i - 1] + pts[i] * 2f + pts[i + 1]) * .25f;
                pts = n;
            }
            var s = new float[pts.Count]; for (int i = 1; i < pts.Count; i++) s[i] = s[i - 1] + (pts[i] - pts[i - 1]).magnitude;
            float Lt = s[s.Length - 1];
            float bnd = roundEnds ? Mathf.Min(.3f, 12f / Lt) : .001f, g = 1f / (1f - bnd);
            var ys = s.Select(v =>
            {
                float u = v / Lt;
                float f = u < bnd ? g * u * u / (2f * bnd) : u > 1f - bnd ? 1f - g * (1f - u) * (1f - u) / (2f * bnd) : g * (u - bnd * .5f);
                return Mathf.Lerp(h0, h1, f);
            }).ToArray();
            return pts.Select((p, i) => (p, ys[i])).ToList();
        }

        /// <summary>A road over a crest: resampled and smoothed line, rounded climb to the peak point, rounded descent after it.</summary>
        static List<(Vector2 p, float y)> ProfilePeak(Vector2[] pl, float h0, Vector2 peakAt, float hPeak, float h1)
        {
            var raw = Profile(pl, 0f, 1f, 45, false);
            var s = new float[raw.Count]; for (int i = 1; i < raw.Count; i++) s[i] = s[i - 1] + (raw[i].p - raw[i - 1].p).magnitude;
            int ip = 0; float bd = 1e9f; for (int i = 0; i < raw.Count; i++) { float d = (raw[i].p - peakAt).sqrMagnitude; if (d < bd) { bd = d; ip = i; } }
            float sP = s[ip], sE = s[s.Length - 1];
            float Ease(float u) { u = Mathf.Clamp01(u); return Smooth(u) * .25f + u * .75f; }
            return raw.Select((q, i) => (q.p, s[i] <= sP ? Mathf.Lerp(h0, hPeak, Ease(s[i] / sP)) : Mathf.Lerp(hPeak, h1, Ease((s[i] - sP) / (sE - sP))))).ToList();
        }

        static float Len(Vector2[] pl) { float l = 0; for (int i = 1; i < pl.Length; i++) l += (pl[i] - pl[i - 1]).magnitude; return l; }
        static float Grade(List<(Vector2 p, float y)> r) { float g = 0; for (int i = 1; i < r.Count; i++) { float d = (r[i].p - r[i - 1].p).magnitude; if (d > .3f) g = Mathf.Max(g, Mathf.Abs(r[i].y - r[i - 1].y) / d); } return g * 100f; }

        // ------------------------------------------------------------------------------------------------ meshes

        /// <summary>Quad with flat normals, winding chosen so the face points along n.</summary>
        static void Quad(List<Vector3> v, List<Vector2> uv, List<int> t, Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 n, float tile)
        {
            int i = v.Count; v.Add(a); v.Add(b); v.Add(c); v.Add(d);
            var right = (b - a).normalized; var upv = Vector3.Cross(n, right);
            foreach (var q in new[] { a, b, c, d }) uv.Add(new Vector2(Vector3.Dot(q - a, right), Vector3.Dot(q - a, upv)) / tile);
            if (Vector3.Dot(Vector3.Cross(b - a, c - a), n) >= 0) t.AddRange(new[] { i, i + 1, i + 2, i, i + 2, i + 3 });
            else t.AddRange(new[] { i, i + 2, i + 1, i, i + 3, i + 2 });
        }

        static Mesh Save(string name, List<Vector3> v, List<Vector2> uv, List<int> t, bool recalc = true)
        {
            var m = new Mesh { name = name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(t, 0);
            if (recalc) m.RecalculateNormals();
            m.RecalculateTangents(); m.RecalculateBounds();
            string path = Dir + "/" + name + ".asset"; AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static Mesh Build(string name, List<Vector3> v, List<Vector2> uv, List<int> t, System.Func<int, Vector3> wantNormal)
        {
            var m = new Mesh { name = name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(t, 0); m.RecalculateNormals();
            var nrm = m.normals; float votes = 0; for (int i = 0; i < nrm.Length; i += 7) votes += Vector3.Dot(nrm[i], wantNormal(i));
            if (votes < 0) { var r = new List<int>(t); for (int k = 0; k < r.Count; k += 3) { (r[k + 1], r[k + 2]) = (r[k + 2], r[k + 1]); } m.SetTriangles(r, 0); m.RecalculateNormals(); }
            m.RecalculateTangents(); m.RecalculateBounds();
            string path = Dir + "/" + name + ".asset"; AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static GameObject Go(string name, Transform parent, Mesh mesh, Material mat, int layer, bool collider)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false); go.layer = layer;
            go.AddComponent<MeshFilter>().sharedMesh = mesh; go.AddComponent<MeshRenderer>().sharedMaterial = mat;
            if (collider) go.AddComponent<MeshCollider>().sharedMesh = mesh;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI);
            return go;
        }

        /// <summary>Road ribbon (0.05 m over its line), side skirts 0.5 m down (no gap to the ground beside it), white markings: edge lines
        /// and a dashed centre line.</summary>
        static void MakeRoad(string name, List<(Vector2 p, float y)> pts, float w0, float tile, Material mat, Transform parent, int layer, Material markMat, float flareStart = 0f, float flareEnd = 0f, System.Func<Vector2, float, float, float> yAt = null)
        {
            var sAt = new float[pts.Count]; for (int i = 1; i < pts.Count; i++) sAt[i] = sAt[i - 1] + (pts[i].p - pts[i - 1].p).magnitude;
            float total = sAt[pts.Count - 1];
            float W(int i) => w0 + flareStart * (1f - Mathf.SmoothStep(0f, 1f, sAt[i] / 9f)) + flareEnd * (1f - Mathf.SmoothStep(0f, 1f, (total - sAt[i]) / 9f));
            float w = w0;
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var tri = new List<int>(); float acc = 0;
            var sv = new List<Vector3>(); var suv = new List<Vector2>(); var st = new List<int>();
            var mv = new List<Vector3>(); var muv = new List<Vector2>(); var mt = new List<int>();
            var L = new Vector3[pts.Count]; var Rr = new Vector3[pts.Count]; var N = new Vector3[pts.Count]; var C = new Vector3[pts.Count]; var acc2 = new float[pts.Count];
            for (int i = 0; i < pts.Count; i++)
            {
                Vector2 d = (pts[Mathf.Min(i + 1, pts.Count - 1)].p - pts[Mathf.Max(i - 1, 0)].p).normalized, n = new(-d.y, d.x);
                if (i > 0) acc += (pts[i].p - pts[i - 1].p).magnitude;
                float y = pts[i].y + .05f, wi = W(i); var l = pts[i].p + n * wi * .5f; var r = pts[i].p - n * wi * .5f;
                float yl = yAt != null ? yAt(l, acc, pts[i].y) + .05f : y, yr = yAt != null ? yAt(r, acc, pts[i].y) + .05f : y;
                L[i] = new Vector3(l.x, yl, l.y); Rr[i] = new Vector3(r.x, yr, r.y); N[i] = new Vector3(n.x, 0, n.y); C[i] = new Vector3(pts[i].p.x, y, pts[i].p.y); acc2[i] = acc;
                v.Add(L[i]); v.Add(Rr[i]);
                uv.Add(new Vector2((w0 - wi) * .5f / tile, acc / tile)); uv.Add(new Vector2((w0 + wi) * .5f / tile, acc / tile));
                if (i > 0) { int b = i * 2; tri.AddRange(new[] { b - 2, b, b + 1, b - 2, b + 1, b - 1 }); }
            }
            Go(name, parent, Build(name, v, uv, tri, _ => Vector3.up), mat, layer, true);
            var down = Vector3.up * .55f;
            for (int i = 1; i < pts.Count; i++)
            {
                Quad(sv, suv, st, L[i - 1], L[i], L[i] - down, L[i - 1] - down, (N[i - 1] + N[i]).normalized, 2f);
                Quad(sv, suv, st, Rr[i - 1], Rr[i], Rr[i] - down, Rr[i - 1] - down, -(N[i - 1] + N[i]).normalized, 2f);
            }
            Go(name + "_skirt", parent, Save(name + "_skirt", sv, suv, st), mat, layer, false);
            if (!markMat) return;
            const float lw = .14f, lift = .025f;
            for (int i = 1; i < pts.Count; i++)
            {
                var nn = (N[i - 1] + N[i]).normalized; var up2 = Vector3.up * lift;
                foreach (float side in new[] { 1f, -1f })
                {   // edge lines 0.3 m in from the edge
                    float o = (w * .5f - .3f) * side;
                    var a0 = C[i - 1] + N[i - 1] * o + up2; var a1 = C[i] + N[i] * o + up2;
                    Quad(mv, muv, mt, a0 - N[i - 1] * lw * .5f, a1 - N[i] * lw * .5f, a1 + N[i] * lw * .5f, a0 + N[i - 1] * lw * .5f, Vector3.up, 1f);
                }
                float m0 = acc2[i - 1] % 8f, m1 = m0 + (acc2[i] - acc2[i - 1]);
                if (m0 < 3f && w > 5.5f)
                {   // centre dashes 3 m on, 5 m off
                    var a0 = C[i - 1] + up2; var a1 = m1 <= 3f ? C[i] + up2 : Vector3.Lerp(C[i - 1], C[i], (3f - m0) / Mathf.Max(.01f, m1 - m0)) + up2;
                    Quad(mv, muv, mt, a0 - nn * lw * .5f, a1 - nn * lw * .5f, a1 + nn * lw * .5f, a0 + nn * lw * .5f, Vector3.up, 1f);
                }
            }
            if (mv.Count > 0) Go(name + "_marks", parent, Save(name + "_marks", mv, muv, mt), markMat, layer, false);
        }

        // ------------------------------------------------------------------------------------------ retaining walls v2
        static long WKey(int cx, int cz) => ((long)cx << 32) ^ (uint)cz;

        static List<(Vector2 p, float y)> ExtendEnds(List<(Vector2 p, float y)> r, bool atStart, bool atEnd)
        {
            var o = new List<(Vector2 p, float y)>(r);
            if (atStart && r.Count > 1) { var d = (r[0].p - r[1].p).normalized; o.Insert(0, (r[0].p + d * 2.5f, r[0].y - .03f)); }
            if (atEnd && r.Count > 1) { var d = (r[r.Count - 1].p - r[r.Count - 2].p).normalized; o.Add((r[r.Count - 1].p + d * 2.5f, r[r.Count - 1].y - .03f)); }
            return o;
        }

        static List<Vector2> Dense(IList<Vector2> pts, float step)
        {
            var o = new List<Vector2> { pts[0] };
            for (int i = 1; i < pts.Count; i++)
            {
                int n = Mathf.Max(1, Mathf.CeilToInt((pts[i] - pts[i - 1]).magnitude / step));
                for (int k = 1; k <= n; k++) o.Add(Vector2.Lerp(pts[i - 1], pts[i], k / (float)n));
            }
            return o;
        }

        static float RayY(Vector2 p, string key, float fallback)
        {
            float best = -1e9f;
            foreach (var h in Physics.RaycastAll(new Vector3(p.x, 200f, p.y), Vector3.down, 400f))
                if (h.collider.name.ToLowerInvariant().Contains(key) && h.point.y > best && h.point.y < 60f) best = h.point.y;
            return best > -1e8f ? best : fallback;
        }

        /// <summary>Height of road id at p (its line, interpolated), the distance to it and its half width.</summary>
        static float NearestY(Vector2 p, List<S> roads, int id, out float dist, out float roadHalf)
        {
            int k = -1; float best = 1e9f;
            for (int i = 0; i < roads.Count; i++) { if (roads[i].road != id) continue; float d = (roads[i].p - p).sqrMagnitude; if (d < best) { best = d; k = i; } }
            dist = 1e9f; roadHalf = 0f; if (k < 0) return 0f;
            float y = roads[k].y; dist = Mathf.Sqrt(best); roadHalf = roads[k].roadHalf;
            foreach (int j in new[] { k - 1, k + 1 })
            {
                if (j < 0 || j >= roads.Count || roads[j].road != id) continue;
                Vector2 a = roads[k].p, ab = roads[j].p - a; float l2 = ab.sqrMagnitude; if (l2 < 1e-6f) continue;
                float tt = Mathf.Clamp01(Vector2.Dot(p - a, ab) / l2), dd = (p - (a + ab * tt)).magnitude;
                if (dd < dist) { dist = dd; y = Mathf.Lerp(roads[k].y, roads[j].y, tt); }
            }
            return y;
        }

        /// <summary>The spur's first 10 m lie on the serpentine's own surface (2 cm under it where they overlap), so the junction
        /// has no step or crack, then ease into the spur's profile.</summary>
        static float JunctionY(Vector2 q, float s, float y, List<S> samples)
        {
            if (s >= 10f) return y;
            float sy = NearestY(q, samples, 1, out float d, out float rh);
            return Mathf.Lerp(d < rh ? sy - .02f : sy, y, Smooth(Mathf.Clamp01(s / 10f)));
        }

        /// <summary>Wall lines (Vadim 25.10): foot walls on Downtown's outer sidewalk edge and 1.5 m off the Rough ring / port road,
        /// open only where a road climbs the hill; route walls on both sides of the serpentine, the spur and the tunnel approaches,
        /// starting at the foot walls. Front = the open (road / street) side.</summary>
        static void BuildWallLines(List<S> samples, List<S> tunnelRoads, StringBuilder log)
        {
            WLines.Clear(); FootFull.Clear(); WGrid.Clear();
            Physics.SyncTransforms();
            var roads = samples.Concat(tunnelRoads).ToList();
            bool InRoad(Vector2 p, out bool cornice)
            {
                cornice = false;
                foreach (var q in roads) if ((q.p - p).sqrMagnitude < (q.half + .1f) * (q.half + .1f)) { cornice = q.road == 4; return true; }
                return false;
            }
            void Foot(string name, int kind, List<Vector2> f, System.Func<int, float> baseY)
            {
                FootFull.Add(f);
                int i = 0;
                while (i < f.Count)
                {
                    while (i < f.Count && InRoad(f[i], out _)) i++;
                    if (i >= f.Count) break;
                    bool c0 = false; if (i > 0) InRoad(f[i - 1], out c0);
                    var L = new WLine { name = name, kind = kind, openStart = i == 0 || c0 };
                    while (i < f.Count && !InRoad(f[i], out _)) { L.f.Add(f[i]); L.b.Add(baseY(i)); L.t.Add(baseY(i) + WallH); i++; }
                    bool c1 = false; if (i < f.Count) InRoad(f[i], out c1);
                    L.openEnd = i >= f.Count || c1;
                    if (L.f.Count < 2) continue;
                    Vector2 Nr(int a) { var d = (L.f[a + 1] - L.f[a]).normalized; return new Vector2(d.y, -d.x); }
                    for (int k = 0; k < L.f.Count; k++)
                    {   // mitred offsets: front = right of travel
                        if (k == 0) L.m.Add(Nr(0)); else if (k == L.f.Count - 1) L.m.Add(Nr(k - 1));
                        else { Vector2 a = Nr(k - 1), b = Nr(k); L.m.Add((a + b) / Mathf.Max(.2f, 1f + Vector2.Dot(a, b))); }
                    }
                    WLines.Add(L);
                }
            }
            // Downtown: the outer edge of the north sidewalks (with the jogs at Vn and Vc), west corner to the cornice
            float dtY = RayY(new Vector2(950f, 518.5f), "sidewalk", 5.3f); FootDtY = dtY;
            Foot("Wall_foot_downtown", 1, Dense(new[] { new Vector2(803, 513), new Vector2(872, 513), new Vector2(872, 521), new Vector2(1115, 521), new Vector2(1115, 505), new Vector2(1200, 505) }, 1f), _ => dtY);
            // Rough: ring + road to the port, travelled westwards, the face 4.7 m to its left (south); a 1.5 m earth shoulder
            var cen = Dense(new[] { new Vector2(1036, 674), new Vector2(1007, 675), new Vector2(999, 674), new Vector2(993, 674), new Vector2(989, 673), new Vector2(986, 672), new Vector2(982, 672), new Vector2(979, 671), new Vector2(976, 671), new Vector2(972, 671), new Vector2(730, 671) }, 1f);
            var rf = new List<Vector2>(); var ry = new List<float>();
            for (int i = 0; i < cen.Count; i++)
            {
                var d = (cen[Mathf.Min(i + 1, cen.Count - 1)] - cen[Mathf.Max(i - 1, 0)]).normalized;
                rf.Add(cen[i] + new Vector2(-d.y, d.x) * 4.7f); ry.Add(RayY(cen[i], "rough", 5.06f));
            }
            Foot("Wall_foot_rough", 2, rf, i => ry[i]);
            RoughBase.Clear(); RoughBase.AddRange(ry);

            float FootS(Vector2 p, out bool near)
            {
                near = false; float best = 1e9f, so = 0f;
                foreach (var f in FootFull) for (int k = 0; k + 1 < f.Count; k++)
                {
                    Vector2 a = f[k], d = f[k + 1] - a; float l2 = d.sqrMagnitude; if (l2 < 1e-6f) continue;
                    float u = Vector2.Dot(p - a, d) / l2; if (u < -.05f || u > 1.05f) continue;
                    var c = a + d * Mathf.Clamp01(u); float dist = (p - c).magnitude; if (dist > 12f || dist >= best) continue;
                    best = dist; so = Vector2.Dot(p - c, new Vector2(d.y, -d.x).normalized); near = true;
                }
                return so;
            }
            foreach (var (list, id) in new[] { (samples, 1), (samples, 3), (tunnelRoads, 5), (tunnelRoads, 6) })
                foreach (float side in new[] { 1f, -1f })
                {
                    var rs = list.Where(q => q.road == id).ToList();
                    WLine L = null; Vector2 pP = default; float pS = 0f, pY = 0f; bool pFront = false, pNear = false, has = false;
                    void Add(Vector2 P, Vector2 nF, float y) { L.f.Add(P); L.m.Add(nF); L.b.Add(y); L.t.Add(y + WallH); }
                    for (int i = 0; i < rs.Count; i++)
                    {
                        var q = rs[i]; var P = q.p + q.right * side * (q.half + .1f); var nF = -q.right * side;
                        float fs = FootS(P, out bool near); bool front = near && fs > 0f, blocked = false;
                        foreach (var o in roads)
                        {
                            if (o.road == id || o.road == 4) continue;
                            float r = o.half + (id == 3 ? .6f : .1f); if ((o.p - P).sqrMagnitude < r * r) { blocked = true; break; }
                        }
                        if (id == 3 && (q.p - PlazaC).magnitude < PlazaR + 22f) blocked = true;
                        if (!front && !blocked)
                        {
                            if (L == null)
                            {
                                bool cross = has && pFront && near && pNear;
                                L = new WLine { name = "route" + id, kind = 0, openStart = !cross };
                                if (cross) { float tt = pS / Mathf.Max(1e-4f, pS - fs); Add(Vector2.Lerp(pP, P, tt), nF, Mathf.Lerp(pY, q.y, tt)); }
                            }
                            Add(P, nF, q.y);
                        }
                        else if (L != null)
                        {
                            bool cross = front && near && pNear && !pFront;
                            if (cross) { float tt = -pS / Mathf.Max(1e-4f, fs - pS); Add(Vector2.Lerp(pP, P, tt), nF, Mathf.Lerp(pY, q.y, tt)); }
                            L.openEnd = !cross; if (L.f.Count >= 2) WLines.Add(L); L = null;
                        }
                        pP = P; pS = fs; pY = q.y; pFront = front; pNear = near; has = true;
                    }
                    if (L != null) { L.openEnd = true; if (L.f.Count >= 2) WLines.Add(L); }
                }
            for (int l = 0; l < WLines.Count; l++)
                for (int k = 0; k + 1 < WLines[l].f.Count; k++)
                {
                    Vector2 a = WLines[l].f[k], b = WLines[l].f[k + 1];
                    int x0 = Mathf.FloorToInt((Mathf.Min(a.x, b.x) - 15f) / 10f), x1 = Mathf.FloorToInt((Mathf.Max(a.x, b.x) + 15f) / 10f);
                    int z0 = Mathf.FloorToInt((Mathf.Min(a.y, b.y) - 15f) / 10f), z1 = Mathf.FloorToInt((Mathf.Max(a.y, b.y) + 15f) / 10f);
                    for (int cx = x0; cx <= x1; cx++) for (int cz = z0; cz <= z1; cz++)
                    {
                        long key = WKey(cx, cz); if (!WGrid.TryGetValue(key, out var lst)) WGrid[key] = lst = new List<(int l, int k)>();
                        lst.Add((l, k));
                    }
                }
            log.AppendLine($"wall lines: {string.Join(", ", WLines.Select(x => $"{x.name} {x.f.Count} {(x.openStart ? "o" : "a")}{(x.openEnd ? "o" : "a")}"))}; Downtown sidewalk {dtY:0.00}");
        }

        /// <summary>low: a wall whose face is within 1.3 m behind / 1.6 m in front of p; back: the nearest wall p is behind.</summary>
        static bool WallNear(Vector2 p, out WHit low, out WHit back)
        {
            low = default; back = default; back.dist = 1e9f; low.b = 1e9f;
            if (!WGrid.TryGetValue(WKey(Mathf.FloorToInt(p.x / 10f), Mathf.FloorToInt(p.y / 10f)), out var cand)) return false;
            foreach (var (l, k) in cand)
            {
                var L = WLines[l]; Vector2 a = L.f[k], d = L.f[k + 1] - a; float len2 = d.sqrMagnitude; if (len2 < 1e-6f) continue;
                float u = Vector2.Dot(p - a, d) / len2, uc = Mathf.Clamp01(u), len = Mathf.Sqrt(len2); var c = a + d * uc;
                var n = new Vector2(d.y, -d.x) / len; if (Vector2.Dot(n, L.m[k] + L.m[k + 1]) < 0f) n = -n;
                float s = Vector2.Dot(p - c, n), dist = (p - c).magnitude, e = 0f; bool end = false;
                if (u < 0f && k == 0) { e = -u * len; end = L.openStart; } else if (u > 1f && k == L.f.Count - 2) { e = (u - 1f) * len; end = L.openEnd; }
                float by = Mathf.Lerp(L.b[k], L.b[k + 1], uc), ty = Mathf.Lerp(L.t[k], L.t[k + 1], uc);
                if (e <= .01f && s > -LowZ && s < 1.6f && dist < 1.7f && by < low.b) low = new WHit { ok = true, s = s, dist = dist, b = by, t = ty, kind = L.kind };
                if (s < 0f && dist < 14f && dist < back.dist && (e <= .01f || end)) back = new WHit { ok = true, s = s, dist = dist, e = e, b = by, t = ty, kind = L.kind };
            }
            return low.ok || back.ok;
        }

        static bool WallTerrain(Vector2 p, out bool pinIt, out float pinY, out float lbY)
        {
            pinIt = false; pinY = 0f; lbY = -1e9f;
            if (!WallNear(p, out var low, out var bk)) return false;
            if (low.ok) { pinIt = true; pinY = low.b - (low.kind == 2 ? .05f : .3f); return true; }
            float depth = -bk.s;
            if (bk.e <= .01f)
            {
                if (depth <= DeckW + .4f) { pinIt = true; pinY = bk.t - .2f; return true; }
                lbY = bk.t - .2f - Mathf.Max(0f, depth - 5f) * .8f; return true;
            }
            lbY = bk.t - .2f - bk.e * 1.1f - Mathf.Max(0f, depth - 5f) * .8f; return true;
        }

        /// <summary>On Downtown's north sidewalks / the Rough shoulder in front of the foot walls, or on a wall and its deck.</summary>
        static bool AtFootWall(Vector2 p, float extra) => p.x > 795f && p.x < 1205f && p.y > 495f && p.y < 522f + extra || p.x > 725f && p.x < 1040f && p.y > 664f - extra && p.y < 682f || UnderWall(p, extra);

        static float FootDtY = 5.3f;
        static readonly List<float> RoughBase = new();
        /// <summary>In front of a foot wall (Downtown's sidewalks and streets up to 20 m, the Rough shoulder up to 6 m): the ground
        /// stays flat under them (no road banks rising through the sidewalk at the hill roads' mouths).</summary>
        static bool FrontOfFoot(Vector2 p, out float y)
        {
            y = 1e9f;
            for (int f = 0; f < FootFull.Count; f++)
            {
                var pl = FootFull[f]; float reach = f == 0 ? 20f : 14f;
                for (int k = 0; k + 1 < pl.Count; k++)
                {
                    Vector2 a = pl[k], d = pl[k + 1] - a; float l2 = d.sqrMagnitude; if (l2 < 1e-6f) continue;
                    float u = Vector2.Dot(p - a, d) / l2; if (u < 0f || u > 1f) continue;
                    var c = a + d * u; float sd = Vector2.Dot(p - c, new Vector2(d.y, -d.x).normalized);
                    if (sd >= 1.6f && sd < reach) { y = f == 0 ? FootDtY - .3f : (k < RoughBase.Count ? RoughBase[k] - .06f : 1e9f); return true; }
                }
            }
            return false;
        }

        static bool BehindFoot(Vector2 p)
        {
            foreach (var pl in FootFull)
                for (int k = 0; k + 1 < pl.Count; k++)
                {
                    Vector2 a = pl[k], d = pl[k + 1] - a; float l2 = d.sqrMagnitude; if (l2 < 1e-6f) continue;
                    float u = Vector2.Dot(p - a, d) / l2; if (u < 0f || u > 1f) continue;
                    var c = a + d * u; float sd = Vector2.Dot(p - c, new Vector2(d.y, -d.x).normalized);
                    if (sd < -.5f && sd > -40f) return true;
                }
            return false;
        }

        static bool UnderWall(Vector2 p, float extra) => WallNear(p, out var lw, out var bw) && (lw.ok || bw.ok && bw.e <= .01f && -bw.s < DeckW + extra);

        static void QuadU(List<Vector3> v, List<Vector2> uv, List<int> t, Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud, Vector3 n)
        {
            int i = v.Count; v.Add(a); v.Add(b); v.Add(c); v.Add(d); uv.Add(ua); uv.Add(ub); uv.Add(uc); uv.Add(ud);
            if (Vector3.Dot(Vector3.Cross(b - a, c - a), n) >= 0) t.AddRange(new[] { i, i + 1, i + 2, i, i + 2, i + 3 });
            else t.AddRange(new[] { i, i + 2, i + 1, i, i + 3, i + 2 });
        }

        /// <summary>The ground behind the walls: a strip with the terrain's own material and splat (same look), covering the 1.3 m
        /// the terrain has to stay low behind the face.</summary>
        static Material DeckMaterial(Terrain terrain)
        {   // URP Lit with the meadow layer in the terrain's own tiling (the Terrain/Lit shader renders black on a mesh)
            var td = terrain.terrainData; string path = Dir + "/Wall_deck_ground.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "Wall_deck_ground" }; AssetDatabase.CreateAsset(m, path); }
            m.shader = Shader.Find("Universal Render Pipeline/Lit");
            var l = td.terrainLayers[0];
            m.SetTexture("_BaseMap", l.diffuseTexture);
            m.SetTextureScale("_BaseMap", new Vector2(td.size.x / l.tileSize.x, td.size.z / l.tileSize.y));
            m.SetTextureOffset("_BaseMap", new Vector2(l.tileOffset.x / l.tileSize.x, l.tileOffset.y / l.tileSize.y));
            m.SetColor("_BaseColor", Color.white);
            File.AppendAllText("C:/Users/chern_0eqkb03/VolunteersBuilds/hill_deck_info.txt", $"deck: layer0 {l.name} tex {(l.diffuseTexture ? l.diffuseTexture.name : "null")} remapMax {l.diffuseRemapMax} remapMin {l.diffuseRemapMin} shader {m.shader.name}" + System.Environment.NewLine);
            m.SetFloat("_Smoothness", 0f); m.SetFloat("_Metallic", 0f); m.SetFloat("_SpecularHighlights", 0f); m.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
            m.SetFloat("_EnvironmentReflections", 0f); m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
            EditorUtility.SetDirty(m);
            return m;
        }

        /// <summary>Re-makes the deck material in place and renders three wall views (no terrain / scene rebuild).</summary>
        public static void DeckFix()
        {
            var scene = EditorSceneManager.OpenScene(Scene);
            DeckMaterial(GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>());
            AssetDatabase.SaveAssets();
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("HillShotCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.clearFlags = CameraClearFlags.Skybox; cam.fieldOfView = 60;
            string D = @"C:\Users\chern_0eqkb03\VolunteersBuilds\";
            go.transform.position = new Vector3(966, 49, 583); go.transform.LookAt(new Vector3(976, 41, 595)); Shot(cam, 1000, 600, D + "v17_junction.png");
            go.transform.position = new Vector3(895, 7.5f, 676); go.transform.LookAt(new Vector3(925, 8, 662)); Shot(cam, 1000, 600, D + "v17_rough.png");
            go.transform.position = new Vector3(1026, 7.5f, 511); go.transform.LookAt(new Vector3(1044, 9, 530)); Shot(cam, 1000, 600, D + "v17_dt_mouth.png");
            go.transform.position = new Vector3(1044, 34, 488); go.transform.LookAt(new Vector3(1044, 8, 528)); Shot(cam, 1000, 600, D + "v17_dt_mouth_hi.png");
            Object.DestroyImmediate(go);
        }

        static void BuildWalls(Terrain terrain, Material wallMat, Material apronMat, Transform parent, int layer, StringBuilder log)
        {
            {   // asphalt from the carriageway right up to the route walls (no dirt shoulder strip along the wall foot)
                var av = new List<Vector3>(); var auv = new List<Vector2>(); var at = new List<int>();
                foreach (var L in WLines.Where(x => x.kind == 0))
                    for (int k = 0; k + 1 < L.f.Count; k++)
                    {
                        Vector2 a = L.f[k] - L.m[k] * .05f, b = L.f[k + 1] - L.m[k + 1] * .05f, a1 = L.f[k] + L.m[k] * 3.2f, b1 = L.f[k + 1] + L.m[k + 1] * 3.2f;
                        Vector3 A(Vector2 q, float y) => new Vector3(q.x, y + .03f, q.y);
                        QuadU(av, auv, at, A(a, L.b[k]), A(b, L.b[k + 1]), A(b1, L.b[k + 1]), A(a1, L.b[k]), a / 6f, b / 6f, b1 / 6f, a1 / 6f, Vector3.up);
                    }
                if (av.Count > 0) Go("Wall_apron_v2", parent, Save("Wall_apron_v2", av, auv, at), apronMat, layer, true);
            }
            const float tile = 4f;
            var tp = terrain.transform.position; var size = terrain.terrainData.size;
            Vector3 P3(Vector2 q, float y) => new Vector3(q.x, y, q.y);
            Vector2 TUV(Vector2 q) => new Vector2((q.x - tp.x) / size.x, (q.y - tp.z) / size.z);
            var dv = new List<Vector3>(); var duv = new List<Vector2>(); var dt = new List<int>();
            float metres = 0f;
            foreach (bool route in new[] { true, false })
            {
                var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
                foreach (var L in WLines.Where(x => (x.kind == 0) == route))
                {
                    float acc = 0f; int n = L.f.Count;
                    for (int k = 0; k + 1 < n; k++)
                    {
                        Vector2 a = L.f[k], b = L.f[k + 1], ma = L.m[k], mb = L.m[k + 1]; float l = (b - a).magnitude;
                        float u0 = acc / tile, u1 = (acc + l) / tile, ba = L.b[k] - .6f, bb = L.b[k + 1] - .6f, ta = L.t[k] - WallCap, tb = L.t[k + 1] - WallCap, ca = L.t[k], cb = L.t[k + 1];
                        var nF = P3((ma + mb).normalized, 0f);
                        Vector2 a2 = a - ma * WallTh, b2 = b - mb * WallTh, af = a + ma * .1f, bf = b + mb * .1f, ak = a - ma * (WallTh + .1f), bk = b - mb * (WallTh + .1f);
                        QuadU(v, uv, t, P3(a, ba), P3(b, bb), P3(b, tb), P3(a, ta), new(u0, ba / tile), new(u1, bb / tile), new(u1, tb / tile), new(u0, ta / tile), nF);
                        QuadU(v, uv, t, P3(a2, ba), P3(b2, bb), P3(b2, tb), P3(a2, ta), new(u0, ba / tile), new(u1, bb / tile), new(u1, tb / tile), new(u0, ta / tile), -nF);
                        QuadU(v, uv, t, P3(af, ca), P3(bf, cb), P3(bk, cb), P3(ak, ca), new(u0, 0f), new(u1, 0f), new(u1, .175f), new(u0, .175f), Vector3.up);
                        QuadU(v, uv, t, P3(af, ta), P3(bf, tb), P3(bf, cb), P3(af, ca), new(u0, 0f), new(u1, 0f), new(u1, .04f), new(u0, .04f), nF);
                        QuadU(v, uv, t, P3(ak, ta), P3(bk, tb), P3(bk, cb), P3(ak, ca), new(u0, 0f), new(u1, 0f), new(u1, .04f), new(u0, .04f), -nF);
                        QuadU(v, uv, t, P3(a, ta), P3(b, tb), P3(bf, tb), P3(af, ta), new(u0, 0f), new(u1, 0f), new(u1, .03f), new(u0, .03f), Vector3.down);
                        // deck: from inside the wall to 2.6 m behind the face, then down into the ground
                        Vector2 d0a = a - ma * (WallTh - .05f), d0b = b - mb * (WallTh - .05f), d1a = a - ma * DeckW, d1b = b - mb * DeckW, d2a = a - ma * (DeckW + .4f), d2b = b - mb * (DeckW + .4f);
                        QuadU(dv, duv, dt, P3(d0a, ca - .1f), P3(d0b, cb - .1f), P3(d1b, cb - .1f), P3(d1a, ca - .1f), TUV(d0a), TUV(d0b), TUV(d1b), TUV(d1a), Vector3.up);
                        QuadU(dv, duv, dt, P3(d1a, ca - .1f), P3(d1b, cb - .1f), P3(d2b, cb - .6f), P3(d2a, ca - .6f), TUV(d1a), TUV(d1b), TUV(d2b), TUV(d2a), Vector3.up);
                        acc += l;
                    }
                    metres += acc;
                    foreach (bool start in new[] { true, false })
                    {   // ends: body, cap, deck skirt
                        int i0 = start ? 0 : n - 1, i1 = start ? 1 : n - 2;
                        Vector2 a = L.f[i0], ma = L.m[i0]; var o = P3((a - L.f[i1]).normalized, 0f);
                        float ba = L.b[i0] - .6f, ta = L.t[i0] - WallCap, ca = L.t[i0];
                        Vector2 a2 = a - ma * WallTh, af = a + ma * .1f, ak = a - ma * (WallTh + .1f), d0 = a - ma * (WallTh - .05f), d2 = a - ma * (DeckW + .4f);
                        QuadU(v, uv, t, P3(a, ba), P3(a2, ba), P3(a2, ta), P3(a, ta), new(0f, ba / tile), new(.125f, ba / tile), new(.125f, ta / tile), new(0f, ta / tile), o);
                        QuadU(v, uv, t, P3(af, ta), P3(ak, ta), P3(ak, ca), P3(af, ca), new(0f, 0f), new(.175f, 0f), new(.175f, .04f), new(0f, .04f), o);
                    }
                }
                if (v.Count > 0) Go(route ? "Wall_route_v2" : "Wall_foot_v2", parent, Save(route ? "Wall_route_v2" : "Wall_foot_v2", v, uv, t), wallMat, layer, true);
            }
            if (dv.Count > 0) Go("Wall_deck_v2", parent, Save("Wall_deck_v2", dv, duv, dt), DeckMaterial(terrain), layer, true);
            log.AppendLine($"walls v2: {metres:0} m (route + foot), one height {WallH} m");
        }

        /// <summary>Downtown's north sidewalks had holes opposite every T junction and at the corners: slabs of the same height,
        /// material and paving mapping fill them.</summary>
        static void SidewalkFill(Transform root, int layer, StringBuilder log)
        {
            var old = root.Find("VadimSidewalkFill"); if (old) Object.DestroyImmediate(old.gameObject);
            var parent = new GameObject("VadimSidewalkFill").transform; parent.SetParent(root, false);
            var all = Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None);
            var gaps = new (float x0, float z0, float x1, float z1, string rf)[]
            {
                (808, 508, 820, 513, "Sidewalk_05-street-N0w_L"), (870, 508, 877, 513, "Sidewalk_05-street-N0w_L"), (872, 513, 877, 516, "Sidewalk_05-street-N0w_L"),
                (877, 516, 889, 521, "Sidewalk_05-street-N0c_L"), (946, 516, 958, 521, "Sidewalk_05-street-N0c_L"), (1097, 516, 1110, 521, "Sidewalk_05-street-N0c_L"),
                (1110, 505, 1115, 516, "Sidewalk_05-street-N0e_L"), (1155, 500, 1168, 505, "Sidewalk_05-street-N0e_L"),
            };
            int made = 0;
            foreach (var g in gaps)
            {
                var r = all.FirstOrDefault(x => x.name == g.rf); if (!r) continue;
                var mesh = r.GetComponent<MeshFilter>().sharedMesh; float top = RayY(new Vector2(r.bounds.center.x, r.bounds.center.z), "sidewalk", r.bounds.max.y);
                Vector3 au = Vector3.zero, av = Vector3.zero; bool ok = false;
                if (mesh && mesh.isReadable)
                {   // the reference slab's planar paving mapping (u, v linear in x, z) from one top triangle
                    var vs = mesh.vertices; var us = mesh.uv; var ts = mesh.triangles;
                    float bestA = .2f; int bestK = -1;
                    for (int k = 0; k < ts.Length && us.Length == vs.Length; k += 3)
                    {
                        Vector3 q0 = r.transform.TransformPoint(vs[ts[k]]), q1 = r.transform.TransformPoint(vs[ts[k + 1]]), q2 = r.transform.TransformPoint(vs[ts[k + 2]]);
                        var cq = Vector3.Cross(q1 - q0, q2 - q0); if (Mathf.Abs(cq.normalized.y) > .95f && cq.magnitude > bestA) { bestA = cq.magnitude; bestK = k; }
                    }
                    for (int k = Mathf.Max(0, bestK); bestK >= 0 && k <= bestK && !ok; k += 3)
                    {
                        Vector3 p0 = r.transform.TransformPoint(vs[ts[k]]), p1 = r.transform.TransformPoint(vs[ts[k + 1]]), p2 = r.transform.TransformPoint(vs[ts[k + 2]]);
                        var cr = Vector3.Cross(p1 - p0, p2 - p0); if (cr.magnitude < .2f || Mathf.Abs(cr.normalized.y) < .95f) continue;
                        float det = p0.x * (p1.z - p2.z) - p0.z * (p1.x - p2.x) + (p1.x * p2.z - p2.x * p1.z); if (Mathf.Abs(det) < 1e-4f) continue;
                        Vector3 Solve(float f0, float f1, float f2) => new Vector3(
                            (f0 * (p1.z - p2.z) - p0.z * (f1 - f2) + (f1 * p2.z - f2 * p1.z)) / det,
                            (p0.x * (f1 - f2) - f0 * (p1.x - p2.x) + (p1.x * f2 - p2.x * f1)) / det,
                            (p0.x * (p1.z * f2 - p2.z * f1) - p0.z * (p1.x * f2 - p2.x * f1) + f0 * (p1.x * p2.z - p2.x * p1.z)) / det);
                        Vector2 q0 = us[ts[k]], q1 = us[ts[k + 1]], q2 = us[ts[k + 2]];
                        au = Solve(q0.x, q1.x, q2.x); av = Solve(q0.y, q1.y, q2.y); ok = true;
                    }
                }
                Vector2 UV(float x, float z) => ok ? new Vector2(au.x * x + au.y * z + au.z, av.x * x + av.y * z + av.z) : new Vector2(x, z) * .5f;
                var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
                Vector3 A = new(g.x0, top, g.z0), B = new(g.x1, top, g.z0), C = new(g.x1, top, g.z1), D = new(g.x0, top, g.z1), dn = Vector3.down * .4f;
                QuadU(v, uv, t, A, B, C, D, UV(g.x0, g.z0), UV(g.x1, g.z0), UV(g.x1, g.z1), UV(g.x0, g.z1), Vector3.up);
                QuadU(v, uv, t, A, B, B + dn, A + dn, UV(g.x0, g.z0), UV(g.x1, g.z0), UV(g.x1, g.z0 + .4f), UV(g.x0, g.z0 + .4f), Vector3.back);
                QuadU(v, uv, t, B, C, C + dn, B + dn, UV(g.x1, g.z0), UV(g.x1, g.z1), UV(g.x1 - .4f, g.z1), UV(g.x1 - .4f, g.z0), Vector3.right);
                QuadU(v, uv, t, C, D, D + dn, C + dn, UV(g.x1, g.z1), UV(g.x0, g.z1), UV(g.x0, g.z1 - .4f), UV(g.x1, g.z1 - .4f), Vector3.forward);
                QuadU(v, uv, t, D, A, A + dn, D + dn, UV(g.x0, g.z1), UV(g.x0, g.z0), UV(g.x0 + .4f, g.z0), UV(g.x0 + .4f, g.z1), Vector3.left);
                Go("SidewalkFill_" + made, parent, Save("SidewalkFill_" + made, v, uv, t), r.sharedMaterial, r.gameObject.layer, true);
                made++;
            }
            log.AppendLine($"sidewalk holes filled: {made} / {gaps.Length}");
        }

        /// <summary>The Downtown lamp model came in lying down (the FBX node's Z-up conversion was dropped): stand them up.</summary>
        static void FixLamps(StringBuilder log)
        {
            const string fbx = "Assets/VadimLocal/Lamps_v86/Lamps_v86.fbx";
            var nodes = AssetDatabase.LoadAllAssetsAtPath(fbx).OfType<GameObject>().SelectMany(g => g.GetComponentsInChildren<MeshFilter>(true)).ToList();
            int n = 0, extra = 0;
            foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (!mf.name.StartsWith("DowntownLamp_v01") || !mf.sharedMesh) continue;
                var src = nodes.FirstOrDefault(x => x.sharedMesh == mf.sharedMesh);
                var baseRot = src ? src.transform.rotation : Quaternion.identity;
                var par = mf.transform.parent; var f0 = par ? Vector3.ProjectOnPlane(par.forward, Vector3.up) : Vector3.forward; if (f0.sqrMagnitude < .01f) f0 = Vector3.forward;
                float sign = mf.sharedMesh.bounds.center.x >= 0 ? 1f : -1f;
                var yaw = Quaternion.Euler(0, Vector3.SignedAngle(Vector3.right * sign, new Vector3(f0.x, 0, f0.z), Vector3.up), 0);
                mf.transform.rotation = yaw * baseRot;
                var rr = mf.GetComponent<Renderer>();
                if (rr && rr.bounds.size.y < 2f) { mf.transform.rotation = yaw * Quaternion.Euler(-90f, 0f, 0f); extra++; }
                n++;
            }
            log.AppendLine($"Downtown lamps stood up: {n} (Z-up fallback {extra})");
        }

        // ------------------------------------------------------------------------------------------ border north of Rough (Vadim 25.10)
        const string BorderDir = "Assets/VadimLocal/Border";

        static Material BorderMat(string name, Color c, Texture tex = null, bool transparent = false)
        {
            string path = BorderDir + "/" + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(m, path); }
            m.shader = Shader.Find("Universal Render Pipeline/Lit");
            m.SetColor("_BaseColor", c); m.SetTexture("_BaseMap", tex); m.SetFloat("_Smoothness", .05f); m.SetFloat("_Metallic", 0f);
            if (transparent)
            {
                m.SetFloat("_Surface", 1f); m.SetFloat("_Blend", 0f); m.SetOverrideTag("RenderType", "Transparent");
                m.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                m.SetFloat("_ZWrite", 0f); m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); m.renderQueue = 3000;
                m.SetFloat("_SpecularHighlights", 0f); m.EnableKeyword("_SPECULARHIGHLIGHTS_OFF"); m.SetFloat("_EnvironmentReflections", 0f); m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
                m.SetFloat("_Cull", 0f);
            }
            EditorUtility.SetDirty(m); return m;
        }

        /// <summary>Boxes (centre, size, rotation) merged into one mesh.</summary>
        static Mesh Boxes(string name, List<(Vector3 c, Vector3 s, Quaternion r)> boxes)
        {
            var cube = Resources.GetBuiltinResource<Mesh>("Cube.fbx");
            var ci = boxes.Select(b => new CombineInstance { mesh = cube, transform = Matrix4x4.TRS(b.c, b.r, b.s) }).ToArray();
            var m = new Mesh { name = name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 }; m.CombineMeshes(ci, true, true);
            m.RecalculateBounds();
            string path = BorderDir + "/" + name + ".asset"; AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(m, path);
            return m;
        }

        /// <summary>The border north of the Rough district: the steppe made flat and short, a dust haze bank 200-500 m out (no hills
        /// on the horizon), a guard booth at the KPP gate, a double fence with barbed wire, concrete blocks, hedgehogs and signs,
        /// and the old road running on into the haze. No military vehicles.</summary>
        static void BuildBorder(Transform root, int layer, Material roadFallback, StringBuilder log)
        {
            var old = root.Find("VadimBorder"); if (old) Object.DestroyImmediate(old.gameObject);
            var parent = new GameObject("VadimBorder").transform; parent.SetParent(root, false);
            var main = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var mp = main.transform.position;
            var stepGo = GameObject.Find("SteppeBackdrop_v02"); var steppe = stepGo ? stepGo.GetComponent<Terrain>() : null;
            float Ground(float x, float z) => z < 947f || !steppe ? main.SampleHeight(new Vector3(x, 0, z)) + mp.y : steppe.SampleHeight(new Vector3(x, 0, z)) + steppe.transform.position.y;

            // 1. no steppe (Vadim 25.10: behind the dust only water): the backdrop terrain off, the map's north edge behind the Rough
            //    and its rocks slopes down into the sea right past the fence
            if (stepGo) stepGo.SetActive(false);
            {
                var mtd = main.terrainData; int MR = mtd.heightmapResolution; float msx = mtd.size.x / (MR - 1), msz = mtd.size.z / (MR - 1);
                int ex0 = Mathf.FloorToInt((520f - mp.x) / msx), ex1 = Mathf.CeilToInt((1160f - mp.x) / msx), ez0 = Mathf.FloorToInt((942f - mp.z) / msz), ez1 = MR - 1;
                var eh = mtd.GetHeights(ex0, ez0, ex1 - ex0 + 1, ez1 - ez0 + 1);
                for (int j = 0; j <= ez1 - ez0; j++) for (int i = 0; i <= ex1 - ex0; i++)
                {
                    float z = mp.z + (ez0 + j) * msz, x = mp.x + (ex0 + i) * msx;
                    float side = Smooth(Mathf.Min(x - 520f, 1160f - x) / 30f);
                    float shore = Mathf.Lerp(6f, -3.5f, Smooth((z - 943f) / 6.5f));
                    float y0 = mp.y + eh[j, i] * mtd.size.y, y = Mathf.Lerp(y0, Mathf.Min(y0, shore), side);
                    eh[j, i] = Mathf.Clamp01((y - mp.y) / mtd.size.y);
                }
                mtd.SetHeights(ex0, ez0, eh);
                FillSea("Sea_fill_border", Rect.MinMaxRect(500f, 930f, 1200f, 1152f), c => c.y > 951f || main.SampleHeight(new Vector3(c.x, 0, c.y)) + mp.y < .3f, log);
            }
            if (false && steppe)
            {
                var td = steppe.terrainData; string tdPath = AssetDatabase.GetAssetPath(td), bak = Path.Combine(Bak, "steppe_" + Path.GetFileName(tdPath));
                if (!File.Exists(bak)) File.Copy(tdPath, bak, true);
                int R = td.heightmapResolution; var bp = steppe.transform.position; var h = new float[R, R];
                for (int j = 0; j < R; j++) for (int i = 0; i < R; i++)
                {
                    float x = bp.x + i * td.size.x / (R - 1), z = bp.z + j * td.size.z / (R - 1);
                    // only a strip of land behind the Rough district (the road runs into the haze on it); the rest under the sea
                    float land = 5.4f + (Mathf.PerlinNoise(x * .018f + 3.1f, z * .018f + 7.7f) - .5f) * .8f;
                    float outside = Mathf.Max(Mathf.Max(620f - x, x - 1080f), z - 1230f);
                    float y = Mathf.Lerp(land, -8f, Smooth(outside / 50f));
                    if (z < 1010f && x >= 0f && x <= main.terrainData.size.x) y = Mathf.Lerp(main.SampleHeight(new Vector3(x, 0, 949f)) + mp.y, y, Smooth((z - 942f) / 60f));
                    h[j, i] = Mathf.Clamp01((y - bp.y) / td.size.y);
                }
                td.SetHeights(0, 0, h);
                int hr = td.holesResolution; var holes = new bool[hr, hr]; int cut = 0;
                for (int j = 0; j < hr; j++) for (int i = 0; i < hr; i++)
                {
                    float x = bp.x + (i + .5f) * td.size.x / hr, z = bp.z + (j + .5f) * td.size.z / hr;
                    bool keep = x > 560f && x < 1140f && z < 1290f;   // the strip behind the Rough district and its shore slopes
                    holes[j, i] = keep; if (!keep) cut++;
                }
                td.SetHoles(0, 0, holes); EditorUtility.SetDirty(td);
                log.AppendLine($"steppe: {cut} cells cut away, only the strip behind the Rough district left");
            }

            // 2. dust haze: five see-through banks, denser near the ground, the far ones higher
            var grad = new Texture2D(64, 128, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "Border_dust_grad" };
            for (int y = 0; y < 128; y++) for (int x = 0; x < 64; x++)
            {   // denser at the ground, gone at the top, soft at both ends
                float v = y / 127f, u = x / 63f, a = Mathf.Pow(1f - v, 1.6f) * Mathf.SmoothStep(0f, 1f, v * 12f + .35f) * Mathf.SmoothStep(0f, 1f, Mathf.Min(u, 1f - u) / .25f);
                grad.SetPixel(x, y, new Color(1, 1, 1, a));
            }
            grad.Apply(); string gp = BorderDir + "/Border_dust_grad.asset"; AssetDatabase.DeleteAsset(gp); AssetDatabase.CreateAsset(grad, gp);
            var dustMat = BorderMat("Border_dust", Color.white, grad, true);
            dustMat.shader = Shader.Find("VadimLocal/DustWall"); dustMat.SetTexture("_BaseMap", grad); dustMat.SetColor("_Color", new Color(.86f, .52f, .24f, 1f)); dustMat.renderQueue = 3050;
            foreach (var n in new[] { "Fence_04-border-fence1", "Fence_04-border-fence2" }) { var f = GameObject.Find(n); if (f) f.SetActive(false); }   // Fedya's 37 m chain-link veil
            if (false)
            {   // a strip of dry orange steppe from the fence to the dust
                var l2 = main.terrainData.terrainLayers.Length > 2 ? main.terrainData.terrainLayers[2] : null;
                var sandMat = BorderMat("Border_steppe_sand", new Color(1f, .82f, .58f), l2 ? l2.diffuseTexture : null);
                var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
                const float sx0 = 600f, sx1 = 1100f, sz0 = 943f, sz1 = 1060f, st = 5f; int nx = Mathf.RoundToInt((sx1 - sx0) / st), nz = Mathf.RoundToInt((sz1 - sz0) / st);
                for (int j = 0; j <= nz; j++) for (int i = 0; i <= nx; i++) { float x = sx0 + i * st, z = sz0 + j * st; v.Add(new Vector3(x, Ground(x, z) + .04f, z)); uv.Add(new Vector2(x, z) / 4f); }
                for (int j = 0; j < nz; j++) for (int i = 0; i < nx; i++) { int a = j * (nx + 1) + i; t.AddRange(new[] { a, a + nx + 1, a + 1, a + 1, a + nx + 1, a + nx + 2 }); }
                Go("Border_steppe_sand", parent, Save("Border_steppe_sand", v, uv, t), sandMat, layer, false);
            }
            {
                var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
                foreach (var (z, top) in new[] { (1000f, 45f), (1040f, 70f), (1100f, 100f) })
                    QuadU(v, uv, t, new Vector3(380f, -2f, z), new Vector3(1320f, -2f, z), new Vector3(1320f, top, z), new Vector3(380f, top, z), new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1), Vector3.back);
                // (25.10: no dust walls any more — the dust is a real fog in the haze pass, Hidden/VadimHaze)
            }

            // 3. KPP: guard booth beside the gate (east of the road, door to the road)
            float gy = Ground(868.5f, 929f);
            var white = BorderMat("Border_booth_white", new Color(.86f, .86f, .83f)); var glass = BorderMat("Border_glass", new Color(.13f, .16f, .19f));
            var roof = BorderMat("Border_roof", new Color(.32f, .33f, .34f)); var metal = BorderMat("Border_metal", new Color(.24f, .25f, .26f));
            var concrete = BorderMat("Border_concrete", new Color(.70f, .69f, .66f)); var rust = BorderMat("Border_rust", new Color(.35f, .22f, .15f));
            var booth = new GameObject("KPP_booth").transform; booth.SetParent(parent, false);
            Go("KPP_booth_body", booth, Boxes("KPP_booth_body", new() { (new Vector3(868.6f, gy + 1.3f, 928.8f), new Vector3(2.6f, 2.6f, 2.8f), Quaternion.identity), (new Vector3(868.6f, gy + .1f, 928.8f), new Vector3(3.0f, .2f, 3.2f), Quaternion.identity) }), white, layer, true);
            Go("KPP_booth_glass", booth, Boxes("KPP_booth_glass", new() { (new Vector3(868.6f, gy + 1.75f, 928.8f), new Vector3(2.64f, 1.0f, 2.84f), Quaternion.identity), (new Vector3(867.28f, gy + 1.0f, 928.2f), new Vector3(.06f, 2.0f, .9f), Quaternion.identity) }), glass, layer, false);
            Go("KPP_booth_roof", booth, Boxes("KPP_booth_roof", new() { (new Vector3(868.6f, gy + 2.72f, 928.8f), new Vector3(3.4f, .24f, 3.6f), Quaternion.identity) }), roof, layer, false);

            // 4. double fence with barbed wire across the north edge (rock to rock), open only on the road
            var posts = new List<(Vector3, Vector3, Quaternion)>();
            int runs = 0;
            foreach (float fz in new[] { 937f, 941.5f })
                foreach (var (x0, x1) in new[] { (640f, 855f), (865f, 1066f) })
                {
                    runs++;
                    int n = Mathf.CeilToInt((x1 - x0) / 3f);
                    for (int k = 0; k <= n; k++)
                    {
                        float x = Mathf.Lerp(x0, x1, k / (float)n), y = Ground(x, fz);
                        posts.Add((new Vector3(x, y + 1.45f, fz), new Vector3(.09f, 2.9f, .09f), Quaternion.identity));
                        posts.Add((new Vector3(x, y + 3.05f, fz - .22f), new Vector3(.05f, .55f, .05f), Quaternion.Euler(-40f, 0, 0)));   // barbed-wire arm leaning out
                        if (k == n) continue;
                        float xn = Mathf.Lerp(x0, x1, (k + 1) / (float)n), yn = Ground(xn, fz), xm = (x + xn) * .5f, len = xn - x;
                        float tilt = Mathf.Atan2(yn - y, len) * Mathf.Rad2Deg;
                        foreach (float hh in new[] { .3f, .8f, 1.3f, 1.8f, 2.3f, 2.8f })
                            posts.Add((new Vector3(xm, (y + yn) * .5f + hh, fz), new Vector3(len, .025f, .025f), Quaternion.Euler(0, 0, tilt)));
                        foreach (float off in new[] { .15f, .32f })
                            posts.Add((new Vector3(xm, (y + yn) * .5f + 2.95f + off * .8f, fz - off), new Vector3(len, .03f, .03f), Quaternion.Euler(0, 0, tilt)));
                    }
                    // no invisible wall here yet (Vadim 25.10: invisible walls go in at the very end)
                }
            Go("Border_fence", parent, Boxes("Border_fence", posts), metal, layer, false);

            // 5. the road on into the haze, closed by concrete blocks past the gate; hedgehogs in front of the fence
            Material oldAsphalt = roadFallback;
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None)) if (r.name.Contains("border_checkpoint_road")) { oldAsphalt = r.sharedMaterial; break; }
            var rp = new List<(Vector2 p, float y)>(); for (float z = 936f; z <= 944f; z += 2f) rp.Add((new Vector2(860f, z), Ground(860f, z) + .02f));
            MakeRoad("Border_road_on", rp, 6.4f, 6f, oldAsphalt, parent, layer, null);
            var blocks = new List<(Vector3, Vector3, Quaternion)>();
            foreach (var (bx, bz) in new[] { (856.2f, 943.2f), (858.8f, 943.6f), (861.4f, 943.2f), (864f, 943.6f) })
                blocks.Add((new Vector3(bx, Ground(bx, bz) + .5f, bz), new Vector3(2.4f, 1.0f, .7f), Quaternion.Euler(0, -4f, 0)));
            Go("Border_blocks", parent, Boxes("Border_blocks", blocks), concrete, layer, true);
            var hog = new List<(Vector3, Vector3, Quaternion)>(); var rnd = new System.Random(5);
            for (float x = 646f; x < 1062f; x += 7.5f)
            {
                if (x > 848f && x < 872f) continue;
                float z = 942.6f + (float)rnd.NextDouble() * 1.4f, y = Ground(x, z) + .55f, yaw = (float)rnd.NextDouble() * 90f;
                foreach (var e in new[] { new Vector3(45, 0, 0), new Vector3(0, 0, 45), new Vector3(-35, 90, 35) })
                    hog.Add((new Vector3(x, y, z), new Vector3(.14f, 1.7f, .14f), Quaternion.Euler(0, yaw, 0) * Quaternion.Euler(e)));
            }
            Go("Border_hedgehogs", parent, Boxes("Border_hedgehogs", hog), rust, layer, false);

            // 6. signs on the inner fence: «ВЫЕЗД ЗАПРЕЩЁН» by the gate, «МИНЫ» along the line
            var exitTex = AssetDatabase.LoadAssetAtPath<Texture2D>(BorderDir + "/Sign_exit_forbidden.png"); var minesTex = AssetDatabase.LoadAssetAtPath<Texture2D>(BorderDir + "/Sign_mines.png");
            var exitMat = BorderMat("Border_sign_exit", Color.white, exitTex); var minesMat = BorderMat("Border_sign_mines", Color.white, minesTex);
            void Sign(string name, float x, float z, Material mat, float w = 1.6f)
            {
                float y = Ground(x, z) + 1.5f, hgt = w * .5625f; var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
                QuadU(v, uv, t, new Vector3(x - w * .5f, y, z), new Vector3(x + w * .5f, y, z), new Vector3(x + w * .5f, y + hgt, z), new Vector3(x - w * .5f, y + hgt, z), new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1), Vector3.back);
                QuadU(v, uv, t, new Vector3(x - w * .5f, y, z + .02f), new Vector3(x + w * .5f, y, z + .02f), new Vector3(x + w * .5f, y + hgt, z + .02f), new Vector3(x - w * .5f, y + hgt, z + .02f), new Vector2(1, 0), new Vector2(0, 0), new Vector2(0, 1), new Vector2(1, 1), Vector3.forward);
                Go(name, parent, Save(name, v, uv, t), mat, layer, false);
            }
            Sign("Border_sign_exit_w", 852.4f, 936.85f, exitMat, 2.0f); Sign("Border_sign_exit_e", 867.6f, 936.85f, exitMat, 2.0f);
            int si = 0; for (float x = 680f; x < 1050f; x += 45f) { if (Mathf.Abs(x - 860f) < 25f) continue; Sign("Border_sign_mines_" + si++, x, 936.85f, minesMat); }

            log.AppendLine($"border: steppe {(steppe ? "flattened" : "missing")}, dust banks 5, booth, fence runs {runs} ({posts.Count} parts), blocks {blocks.Count}, hedgehogs {hog.Count / 3}, signs {2 + si}");
        }

        /// <summary>Only the border (no hill rebuild): for quick passes.</summary>
        public static void BorderOnly()
        {
            var scene = EditorSceneManager.OpenScene(Scene); var log = new StringBuilder();
            var root = GameObject.Find("Map_W85_v02").transform; int layer = 0; Material roadMat = null;
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None)) if (r.name == "Road_serpentine_view_b_v3") { roadMat = r.sharedMaterial; layer = r.gameObject.layer; }
            BuildBorder(root, layer, roadMat, log);
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            BorderShots();
            File.WriteAllText(@"C:\Users\chern_0eqkb03\VolunteersBuilds\border_apply.txt", log.ToString());
        }

        internal static void BorderShots()
        {
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("BorderShotCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 4000; cam.clearFlags = CameraClearFlags.Skybox; cam.fieldOfView = 60;
            string D = @"C:\Users\chern_0eqkb03\VolunteersBuilds\";
            go.transform.position = new Vector3(860, 7.5f, 905); go.transform.LookAt(new Vector3(860, 7f, 1000)); Shot(cam, 1000, 600, D + "border_kpp.png");
            go.transform.position = new Vector3(880, 3.2f, 924); go.transform.LookAt(new Vector3(864, 3.5f, 934)); Shot(cam, 1000, 600, D + "border_booth.png");
            go.transform.position = new Vector3(1300, 70f, 420); go.transform.LookAt(new Vector3(860, 20f, 1000)); Shot(cam, 1000, 600, D + "border_far.png");
            Object.DestroyImmediate(go);
        }

        // ------------------------------------------------------------------------------------------ Tramduro island (Vadim 25.10)
        const string TramDir = "Assets/VadimLocal/Tramduro";

        /// <summary>Built-in meshes (cube / cylinder) merged into one mesh in the given space.</summary>
        static Mesh MergePrims(string name, string dir, List<(string prim, Matrix4x4 m)> parts)
        {
            var ci = parts.Select(p => new CombineInstance { mesh = Resources.GetBuiltinResource<Mesh>(p.prim + ".fbx"), transform = p.m }).ToArray();
            var mesh = new Mesh { name = name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 }; mesh.CombineMeshes(ci, true, true); mesh.RecalculateBounds();
            string path = dir + "/" + name + ".asset"; AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(mesh, path);
            return mesh;
        }

        static Material TramMat(string name, Color c)
        {
            string path = TramDir + "/" + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(m, path); }
            m.SetColor("_BaseColor", c); m.SetFloat("_Smoothness", .1f); EditorUtility.SetDirty(m); return m;
        }

        /// <summary>Tramduro island: the perimeter fence and gate rebuilt on the ground, stationary air-defence guns with a turning
        /// turret instead of the rocket launchers, the three nuclear missiles on one small mound at one height.</summary>
        static void BuildTramduro(Transform root, int layer, StringBuilder log)
        {
            if (!AssetDatabase.IsValidFolder(TramDir)) AssetDatabase.CreateFolder("Assets/VadimLocal", "Tramduro");
            var old = root.Find("VadimTramduro"); if (old) Object.DestroyImmediate(old.gameObject);
            var parent = new GameObject("VadimTramduro").transform; parent.SetParent(root, false);
            var terrain = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var tp = terrain.transform.position;
            float G(float x, float z) => terrain.SampleHeight(new Vector3(x, 0, z)) + tp.y;
            var district = GameObject.Find("District_tramduro");
            Transform Child(string n) => district ? district.transform.Find(n) : null;
            var concrete = TramMat("Tram_concrete", new Color(.70f, .69f, .66f)); var post = TramMat("Tram_post", new Color(.50f, .50f, .49f));
            var wire = TramMat("Tram_wire", new Color(.22f, .23f, .24f)); var olive = TramMat("Tram_olive", new Color(.29f, .33f, .21f));
            var dark = TramMat("Tram_dark", new Color(.13f, .14f, .15f));

            // 1. perimeter fence: concrete panels 2.4 m on the ground, posts, three strands of barbed wire; open at the entry, swing gate
            var j = MiniJson.Parse(File.ReadAllText("Assets/OnlyVolunteers/Map/W85Build/Data/v02/districts/tramduro_v85.json")) as Dictionary<string, object>;
            List<Vector2> line = null;
            foreach (var zo in (List<object>)j["zones"])
            {
                var z = (Dictionary<string, object>)zo; if ((string)z["id"] != "10-perimeter") continue;
                line = ((List<object>)z["line"]).Select(o => { var a = (List<object>)o; return new Vector2(System.Convert.ToSingle(a[0]), System.Convert.ToSingle(a[1])); }).ToList();
            }
            var oldFence = Child("Fence_10-perimeter"); if (oldFence) oldFence.gameObject.SetActive(false);
            int panels = 0;
            if (line != null && line.Count > 1)
            {
                var pts = Dense(line, 3f);
                var pp = new List<(string, Matrix4x4)>(); var wp = new List<(string, Matrix4x4)>(); var cp = new List<(string, Matrix4x4)>();
                var cols = new GameObject("Tram_fence_colliders").transform; cols.SetParent(parent, false);
                for (int i = 0; i < pts.Count; i++)
                {
                    float gy = G(pts[i].x, pts[i].y);
                    pp.Add(("Cube", Matrix4x4.TRS(new Vector3(pts[i].x, gy + 1.15f, pts[i].y), Quaternion.identity, new Vector3(.3f, 2.9f, .3f))));
                    if (i + 1 >= pts.Count) continue;
                    Vector2 a = pts[i], b = pts[i + 1], m = (a + b) * .5f; float len = (b - a).magnitude, gb = G(b.x, b.y), gm = Mathf.Min(G(m.x, m.y), Mathf.Min(gy, gb));
                    var yaw = Quaternion.LookRotation(new Vector3(b.x - a.x, 0, b.y - a.y));
                    // the panel reaches 0.4 m into the ground at its lowest point, its top follows the slope
                    float top = (gy + gb) * .5f + 2.4f, bottom = gm - .4f;
                    cp.Add(("Cube", Matrix4x4.TRS(new Vector3(m.x, (top + bottom) * .5f, m.y), yaw, new Vector3(.18f, top - bottom, len))));
                    foreach (float h in new[] { 2.55f, 2.7f, 2.85f })
                        wp.Add(("Cube", Matrix4x4.TRS(new Vector3(m.x, (gy + gb) * .5f + h, m.y), yaw * Quaternion.Euler(-Mathf.Atan2(gb - gy, len) * Mathf.Rad2Deg, 0, 0), new Vector3(.03f, .03f, len))));
                    var bc = new GameObject("c").AddComponent<BoxCollider>(); bc.transform.SetParent(cols, false);
                    bc.transform.SetPositionAndRotation(new Vector3(m.x, (top + bottom) * .5f, m.y), yaw); bc.size = new Vector3(.3f, top - bottom + .6f, len);
                    panels++;
                }
                Go("Tram_fence_panels", parent, MergePrims("Tram_fence_panels", TramDir, cp), concrete, layer, false);
                Go("Tram_fence_posts", parent, MergePrims("Tram_fence_posts", TramDir, pp), post, layer, false);
                Go("Tram_fence_wire", parent, MergePrims("Tram_fence_wire", TramDir, wp), wire, layer, false);
                // the gate: two concrete pillars at the ends of the line, two steel leaves swung open inwards
                Vector2 e0 = line[line.Count - 1], e1 = line[0], gapDir = (e1 - e0).normalized; float gap = (e1 - e0).magnitude;
                Vector2 inward = new Vector2(gapDir.y, -gapDir.x); var island = new Vector2(1560f, 785f); if (Vector2.Dot(island - (e0 + e1) * .5f, inward) < 0f) inward = -inward;
                var gpParts = new List<(string, Matrix4x4)>();
                var gate = new GameObject("Tram_gate").transform; gate.SetParent(parent, false);
                var mid = (e0 + e1) * .5f; gate.position = new Vector3(mid.x, G(mid.x, mid.y), mid.y);
                var leaves = new List<Transform>(); var yaws = new List<float>();
                foreach (var (pe, sgn) in new[] { (e0, 1f), (e1, -1f) })
                {
                    float gy = G(pe.x, pe.y);
                    gpParts.Add(("Cube", Matrix4x4.TRS(new Vector3(pe.x, gy + 1.5f, pe.y), Quaternion.LookRotation(new Vector3(gapDir.x, 0, gapDir.y)), new Vector3(.7f, 3.4f, .7f))));
                    float lw = gap * .5f - .45f; var along = gapDir * sgn;
                    var hinge = new GameObject("leaf").transform; hinge.SetParent(gate, false);
                    var hp = pe + along * .4f; hinge.position = new Vector3(hp.x, Mathf.Min(gy, G(mid.x, mid.y)), hp.y);
                    hinge.rotation = Quaternion.FromToRotation(Vector3.right, new Vector3(along.x, 0, along.y));
                    var bars = new List<(string, Matrix4x4)>
                    {
                        ("Cube", Matrix4x4.TRS(new Vector3(lw * .5f, .2f, 0), Quaternion.identity, new Vector3(lw, .1f, .1f))),
                        ("Cube", Matrix4x4.TRS(new Vector3(lw * .5f, 2.5f, 0), Quaternion.identity, new Vector3(lw, .1f, .1f))),
                        ("Cube", Matrix4x4.TRS(new Vector3(lw * .5f, 1.35f, 0), Quaternion.identity, new Vector3(lw, .08f, .08f))),
                    };
                    for (int k = 0; k <= 10; k++) bars.Add(("Cube", Matrix4x4.TRS(new Vector3(lw * k / 10f, 1.35f, 0), Quaternion.identity, new Vector3(.06f, 2.4f, .06f))));
                    Go("bars", hinge, MergePrims("Tram_gate_leaf_" + (sgn > 0 ? "a" : "b"), TramDir, bars), wire, layer, false);
                    var bc = hinge.gameObject.AddComponent<BoxCollider>(); bc.center = new Vector3(lw * .5f, 1.35f, 0); bc.size = new Vector3(lw, 2.6f, .2f);
                    // open: the free end swings inwards (onto the island)
                    float yaw = Vector3.SignedAngle(new Vector3(along.x, 0, along.y), new Vector3(inward.x, 0, inward.y), Vector3.up);
                    leaves.Add(hinge); yaws.Add(yaw);
                }
                var vg = gate.gameObject.AddComponent<OnlyVolunteers.VadimLocal.VadimGate>(); vg.leaves = leaves.ToArray(); vg.openYaw = yaws.ToArray();
                Go("Tram_gate_pillars", parent, MergePrims("Tram_gate_pillars", TramDir, gpParts), concrete, layer, true);
                // the boom barrier goes; the guard booth stands outside, in front of the fence by the road
                var bar = Child("10-barrier"); if (bar) bar.gameObject.SetActive(false);
                {   // the entry: straight from the bridge end into the gate, on a concrete embankment (no step, no slanted pad)
                    var ent = Child("Zone_10-concrete_entry"); if (ent) ent.gameObject.SetActive(false);
                    Material asph = null; foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None)) if (r.name == "Bridge_bridge_tramduro_deck") { asph = r.sharedMaterial; break; }
                    float yb = 3.0f, yg = G(mid.x + 3f, mid.y);
                    var ep = new List<(Vector2 p, float y)>();
                    for (float x = 1445.6f; x <= 1470.01f; x += 1f) { float u = Mathf.InverseLerp(1446.4f, mid.x, x); ep.Add((new Vector2(x, Mathf.Lerp(781f, mid.y, Mathf.Clamp01(u))), Mathf.Lerp(yb, yg, Smooth(u)))); }
                    if (asph) MakeRoad("Tram_entry_road", ep, 8.8f, 6f, asph, parent, layer, null);
                    var emb = new List<(string, Matrix4x4)>();
                    for (int k = 0; k + 1 < ep.Count; k++)
                    {
                        var a = ep[k]; var c = (a.p + ep[k + 1].p) * .5f; float top = (a.y + ep[k + 1].y) * .5f - .02f, bot = Mathf.Min(G(c.x, c.y - 4f), G(c.x, c.y + 4f)) - .6f;
                        if (top - bot > .1f) emb.Add(("Cube", Matrix4x4.TRS(new Vector3(c.x, (top + bot) * .5f, c.y), Quaternion.identity, new Vector3(1.02f, top - bot, 9.2f))));
                    }
                    if (emb.Count > 0) Go("Tram_entry_embankment", parent, MergePrims("Tram_entry_embankment", TramDir, emb), concrete, layer, true);
                }
                var kpp = Child("B_10-07-kpp");
                if (kpp)
                {
                    var rs = kpp.GetComponentsInChildren<Renderer>(); var kb = rs[0].bounds; foreach (var r in rs) kb.Encapsulate(r.bounds);
                    var want = new Vector2(1458.2f, 789.6f);   // outside, beside the north gate pillar, on the driver's left
                    kpp.position += new Vector3(want.x - kb.center.x, G(want.x, want.y) - kb.min.y, want.y - kb.center.z);
                }
                log.AppendLine($"tramduro fence: {panels} panels on the ground, gate {gap:0.0} m between {e0} and {e1}");
            }

            // 2. air defence: the rocket launchers go; a stationary gun on a concrete plinth with a turning twin-barrel turret
            int aa = 0; Mesh aaBase = null, aaBody = null, aaGuns = null;
            for (int i = 1; i <= 4; i++)
            {
                var src = Child("10-aa" + i); if (!src) continue;
                var p = src.position; src.gameObject.SetActive(false);
                if (i == 2) continue;   // the one by the missile mound goes (Vadim 25.10)
                float gy = G(p.x, p.z);
                var g = new GameObject("Tram_AA_" + i).transform; g.SetParent(parent, false); g.position = new Vector3(p.x, gy, p.z);
                Go("base", g, aaBase ??= MergePrims("Tram_AA_base", TramDir, new()
                {
                    ("Cube", Matrix4x4.TRS(new Vector3(0, .15f, 0), Quaternion.identity, new Vector3(6f, .5f, 6f))),
                    ("Cylinder", Matrix4x4.TRS(new Vector3(0, 1.0f, 0), Quaternion.identity, new Vector3(2.2f, .7f, 2.2f))),
                }), concrete, layer, true).transform.localPosition = Vector3.zero;
                var tur = new GameObject("turret").transform; tur.SetParent(g, false); tur.localPosition = new Vector3(0, 1.7f, 0);
                tur.localRotation = Quaternion.Euler(0, (p.x < 1560f ? -90f : 90f) + i * 25f, 0);
                var bodyM = aaBody ??= MergePrims("Tram_AA_turret", TramDir, new()
                {
                    ("Cube", Matrix4x4.TRS(new Vector3(0, .55f, -.1f), Quaternion.identity, new Vector3(2.4f, 1.1f, 2.8f))),
                    ("Cube", Matrix4x4.TRS(new Vector3(0, .75f, 1.35f), Quaternion.Euler(-20f, 0, 0), new Vector3(1.5f, .8f, .6f))),
                    ("Cylinder", Matrix4x4.TRS(new Vector3(0, 1.45f, -1.1f), Quaternion.identity, new Vector3(.12f, .45f, .12f))),
                    ("Cube", Matrix4x4.TRS(new Vector3(0, 2.0f, -1.1f), Quaternion.Euler(-15f, 0, 0), new Vector3(1.2f, .7f, .08f))),
                });
                Go("body", tur, bodyM, olive, layer, false);
                var gunParts = new List<(string, Matrix4x4)>();
                foreach (float sx in new[] { -.35f, .35f })
                {
                    var dir = Quaternion.Euler(-35f, 0, 0) * Vector3.forward; var c = new Vector3(sx, .85f, 1.5f) + dir * 1.9f;
                    gunParts.Add(("Cylinder", Matrix4x4.TRS(c, Quaternion.FromToRotation(Vector3.up, dir), new Vector3(.17f, 1.9f, .17f))));
                    gunParts.Add(("Cylinder", Matrix4x4.TRS(new Vector3(sx, .85f, 1.5f) + dir * 3.75f, Quaternion.FromToRotation(Vector3.up, dir), new Vector3(.24f, .18f, .24f))));
                }
                Go("guns", tur, aaGuns ??= MergePrims("Tram_AA_guns", TramDir, gunParts), dark, layer, false);
                var t = g.gameObject.AddComponent<OnlyVolunteers.VadimLocal.VadimAaTurret>(); t.turret = tur;
                aa++; log.AppendLine($"aa {i} at {g.position}");
            }

            // 3. the missiles: one small mound with a concrete top at one height, a dark shaft ring under each missile
            {
                float x0 = 1610.2f, x1 = 1626.2f, z0 = 810.5f, z1 = 844.5f, top = 5.6f, foot = 2.0f, run = 3.4f;
                var grass = AssetDatabase.LoadAssetAtPath<Material>(Dir + "/Wall_deck_ground.mat") ?? concrete;
                var tv = new List<Vector3>(); var tuv = new List<Vector2>(); var tt = new List<int>();
                QuadU(tv, tuv, tt, new Vector3(x0, top, z0), new Vector3(x1, top, z0), new Vector3(x1, top, z1), new Vector3(x0, top, z1), new Vector2(x0, z0) / 4f, new Vector2(x1, z0) / 4f, new Vector2(x1, z1) / 4f, new Vector2(x0, z1) / 4f, Vector3.up);
                var sv = new List<Vector3>(); var suv = new List<Vector2>(); var st = new List<int>();
                Vector3[] T = { new(x0, top, z0), new(x1, top, z0), new(x1, top, z1), new(x0, top, z1) };
                Vector3[] B = { new(x0 - run, foot, z0 - run), new(x1 + run, foot, z0 - run), new(x1 + run, foot, z1 + run), new(x0 - run, foot, z1 + run) };
                for (int k = 0; k < 4; k++)
                {
                    int n = (k + 1) % 4; var mid = (T[k] + T[n] + B[k] + B[n]) * .25f; var outN = new Vector3(mid.x - (x0 + x1) * .5f, 0, mid.z - (z0 + z1) * .5f).normalized + Vector3.up;
                    Vector2 U(Vector3 q) => new Vector2(q.x + q.y * .3f, q.z) / 3f;
                    QuadU(sv, suv, st, T[k], T[n], B[n], B[k], U(T[k]), U(T[n]), U(B[n]), U(B[k]), outN);
                }
                var mound = Go("Tram_missile_mound_top", parent, Save("Tram_missile_mound_top", tv, tuv, tt), concrete, layer, true);
                Go("Tram_missile_mound_sides", parent, Save("Tram_missile_mound_sides", sv, suv, st), grass, layer, true);
                var rings = new List<(string, Matrix4x4)>();
                for (int i = 1; i <= 3; i++)
                {
                    var m = Child("10-missile" + i); if (!m) continue;
                    var rs = m.GetComponentsInChildren<Renderer>(); var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                    m.position += Vector3.up * (top - .05f - b.min.y);
                    rings.Add(("Cylinder", Matrix4x4.TRS(new Vector3(m.position.x, top + .03f, m.position.z), Quaternion.identity, new Vector3(Mathf.Max(b.size.x, b.size.z) * .8f, .03f, Mathf.Max(b.size.x, b.size.z) * .8f))));
                }
                if (rings.Count > 0) Go("Tram_missile_shafts", parent, MergePrims("Tram_missile_shafts", TramDir, rings), dark, layer, false);
                log.AppendLine($"tramduro: aa guns {aa}, missiles on a mound at {top} m ({rings.Count})");
            }
            // 4. the palace front (Vadim 25.10): Downtown's statue on the parade concrete a little right of the middle, a new
            // tribune on the left with its back to the palace, the same Tramduro flag everywhere, a proper helipad, tank barrels
            foreach (var n in new[] { "10-statue", "10-statue_pedestal", "Zone_10-statue_plaza", "10-speech_platform", "10-speech_lectern", "10-speech_steps", "Helipad_platform_XT1", "XT1helia", "Zone_10-helipad" })
            { var c = Child(n); if (c) c.gameObject.SetActive(false); }
            float yard = 4.72f;
            var mon = GameObject.Find("05-15-monument");
            if (mon)
            {
                var st = Object.Instantiate(mon, parent); st.name = "Tram_statue_from_downtown";
                st.transform.SetPositionAndRotation(new Vector3(1581f, yard, 792f), mon.transform.rotation);
            }
            var white = TramMat("Tram_marble", new Color(.92f, .92f, .89f)); var gold = TramMat("Tram_gold", new Color(.86f, .66f, .18f));
            var red = TramMat("Tram_carpet", new Color(.55f, .07f, .09f)); var wood = TramMat("Tram_wood", new Color(.32f, .18f, .10f));
            var flagMat = TramMat("Tram_flag", Color.white); flagMat.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(TramDir + "/Tram_flag.png")); flagMat.SetFloat("_Cull", 0f);
            {   // tribune: 8 x 5.5 m deck 1.2 m high, steps and carpet from the palace side, a big lectern facing the parade ground
                Vector3 C = new(1556.2f, yard, 797.5f); float deck = C.y + 1.2f;
                var body = new List<(string, Matrix4x4)>
                {
                    ("Cube", Matrix4x4.TRS(new Vector3(C.x, (deck + C.y - .4f) * .5f, C.z), Quaternion.identity, new Vector3(8f, deck - C.y + .4f, 5.5f))),
                };
                for (int k = 0; k < 4; k++)
                {   // four 0.24 m steps down from the deck on the palace side
                    float st = C.y + (4 - k) * .24f;
                    body.Add(("Cube", Matrix4x4.TRS(new Vector3(C.x, (st + C.y - .2f) * .5f, C.z + 2.95f + k * .4f), Quaternion.identity, new Vector3(3.2f, st - C.y + .2f, .4f))));
                }
                Go("Tram_tribune", parent, MergePrims("Tram_tribune", TramDir, body), white, layer, true);
                var trim = new List<(string, Matrix4x4)> { ("Cube", Matrix4x4.TRS(new Vector3(C.x, deck - .09f, C.z), Quaternion.identity, new Vector3(8.08f, .12f, 5.58f))) };
                Go("Tram_tribune_trim", parent, MergePrims("Tram_tribune_trim", TramDir, trim), gold, layer, false);
                var carpet = new List<(string, Matrix4x4)> { ("Cube", Matrix4x4.TRS(new Vector3(C.x, deck + .015f, C.z + .55f), Quaternion.identity, new Vector3(1.6f, .03f, 4.4f))) };
                for (int k = 0; k < 4; k++) carpet.Add(("Cube", Matrix4x4.TRS(new Vector3(C.x, C.y + (4 - k) * .24f + .015f, C.z + 2.95f + k * .4f), Quaternion.identity, new Vector3(1.6f, .03f, .42f))));
                Go("Tram_tribune_carpet", parent, MergePrims("Tram_tribune_carpet", TramDir, carpet), red, layer, false);
                var lec = new List<(string, Matrix4x4)>
                {
                    ("Cube", Matrix4x4.TRS(new Vector3(C.x, deck + .75f, C.z - 1.7f), Quaternion.identity, new Vector3(1.6f, 1.5f, .8f))),
                    ("Cube", Matrix4x4.TRS(new Vector3(C.x, deck + 1.55f, C.z - 1.75f), Quaternion.Euler(-18f, 0, 0), new Vector3(1.8f, .1f, 1.0f))),
                };
                Go("Tram_lectern", parent, MergePrims("Tram_lectern", TramDir, lec), wood, layer, true);
                var seal = new List<(string, Matrix4x4)>
                {
                    ("Cylinder", Matrix4x4.TRS(new Vector3(C.x, deck + .85f, C.z - 2.14f), Quaternion.Euler(90f, 0, 0), new Vector3(.8f, .02f, .8f))),
                    ("Cylinder", Matrix4x4.TRS(new Vector3(C.x - .25f, deck + 1.8f, C.z - 1.95f), Quaternion.Euler(-30f, 0, 0), new Vector3(.03f, .25f, .03f))),
                    ("Cylinder", Matrix4x4.TRS(new Vector3(C.x + .25f, deck + 1.8f, C.z - 1.95f), Quaternion.Euler(-30f, 0, 0), new Vector3(.03f, .25f, .03f))),
                };
                Go("Tram_lectern_seal", parent, MergePrims("Tram_lectern_seal", TramDir, seal), gold, layer, false);
                Flag("Tram_flag_tribune_w", new Vector3(C.x - 3.6f, deck, C.z + 2.3f), 4.2f);
                Flag("Tram_flag_tribune_e", new Vector3(C.x + 3.6f, deck, C.z + 2.3f), 4.2f);
            }
            Flag("Tram_flag_palace", new Vector3(1576.2f, 13.9f, 823.5f), 4.6f);
            void Flag(string name, Vector3 foot, float h)
            {
                Go(name + "_pole", parent, MergePrims(name + "_pole", TramDir, new() { ("Cylinder", Matrix4x4.TRS(foot + Vector3.up * h * .5f, Quaternion.identity, new Vector3(.09f, h * .5f, .09f))), ("Cube", Matrix4x4.TRS(foot + Vector3.up * (h + .06f), Quaternion.identity, Vector3.one * .16f)) }), gold, layer, false);
                var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
                Vector3 a = foot + new Vector3(.06f, h - 1.25f, 0), b = a + new Vector3(1.9f, 0, 0), c = b + new Vector3(0, 1.2f, 0), d = a + new Vector3(0, 1.2f, 0);
                QuadU(v, uv, t, a, b, c, d, new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1), Vector3.back);
                QuadU(v, uv, t, a, b, c, d, new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1), Vector3.forward);
                Go(name + "_cloth", parent, Save(name + "_cloth", v, uv, t), flagMat, layer, false);
            }
            {   // helipad: a 24 m square 0.6 m over the yard, dark top, yellow ring, white H, edge lights; the helicopter on it
                Vector3 P = new(1601.2f, yard, 737.5f); float top = P.y + .6f;
                Go("Tram_helipad", parent, MergePrims("Tram_helipad", TramDir, new() { ("Cube", Matrix4x4.TRS(new Vector3(P.x, (top + P.y - .5f) * .5f, P.z), Quaternion.identity, new Vector3(24f, top - P.y + .5f, 24f))) }), concrete, layer, true);
                Go("Tram_helipad_top", parent, MergePrims("Tram_helipad_top", TramDir, new() { ("Cube", Matrix4x4.TRS(new Vector3(P.x, top + .01f, P.z), Quaternion.identity, new Vector3(21f, .02f, 21f))) }), dark, layer, false);
                var ring = new List<(string, Matrix4x4)>();
                for (int k = 0; k < 40; k++) { float an = k * Mathf.PI * 2f / 40f; ring.Add(("Cube", Matrix4x4.TRS(new Vector3(P.x + Mathf.Cos(an) * 8f, top + .03f, P.z + Mathf.Sin(an) * 8f), Quaternion.Euler(0, -an * Mathf.Rad2Deg, 0), new Vector3(.5f, .02f, 1.3f)))); }
                for (int k = 0; k < 12; k++) { float u = -10.5f + k * 21f / 11f; foreach (var (dx, dz) in new[] { (u, -10.5f), (u, 10.5f), (-10.5f, u), (10.5f, u) }) ring.Add(("Cube", Matrix4x4.TRS(new Vector3(P.x + dx, top + .1f, P.z + dz), Quaternion.identity, Vector3.one * .25f))); }
                Go("Tram_helipad_ring", parent, MergePrims("Tram_helipad_ring", TramDir, ring), TramMat("Tram_yellow", new Color(.95f, .78f, .12f)), layer, false);
                Go("Tram_helipad_H", parent, MergePrims("Tram_helipad_H", TramDir, new()
                {
                    ("Cube", Matrix4x4.TRS(new Vector3(P.x - 2.2f, top + .03f, P.z), Quaternion.identity, new Vector3(1f, .02f, 7f))),
                    ("Cube", Matrix4x4.TRS(new Vector3(P.x + 2.2f, top + .03f, P.z), Quaternion.identity, new Vector3(1f, .02f, 7f))),
                    ("Cube", Matrix4x4.TRS(new Vector3(P.x, top + .03f, P.z), Quaternion.identity, new Vector3(4.4f, .02f, 1f))),
                }), white, layer, false);
                var heli = Child("10-helicopter");
                if (heli) { var rs = heli.GetComponentsInChildren<Renderer>(); var hb = rs[0].bounds; foreach (var r in rs) hb.Encapsulate(r.bounds); heli.position += new Vector3(P.x - hb.center.x, top + .05f - hb.min.y, P.z - hb.center.z); }
            }
            {   // hangar: concrete side walls 1.4 m between the arch feet, a back-wall stripe, six warm lamps under the roof
                var hb = Child("B_10-05-hangar");
                if (hb)
                {
                    var rs = hb.GetComponentsInChildren<Renderer>(); var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                    float fy = b.min.y; var walls = new List<(string, Matrix4x4)>(); var lamps = new List<(string, Matrix4x4)>();
                    foreach (float wx in new[] { b.min.x + .9f, b.max.x - .9f })
                        walls.Add(("Cube", Matrix4x4.TRS(new Vector3(wx, fy + .7f, b.center.z), Quaternion.identity, new Vector3(.5f, 1.4f, b.size.z - 1.5f))));
                    for (int k = 0; k < 6; k++)
                    {
                        float lz = Mathf.Lerp(b.min.z + 4f, b.max.z - 4f, k / 5f);
                        lamps.Add(("Cube", Matrix4x4.TRS(new Vector3(b.center.x, b.max.y - 1.6f, lz), Quaternion.identity, new Vector3(1.6f, .15f, .5f))));
                        lamps.Add(("Cylinder", Matrix4x4.TRS(new Vector3(b.center.x, b.max.y - .8f, lz), Quaternion.identity, new Vector3(.04f, .7f, .04f))));
                    }
                    Go("Tram_hangar_walls", parent, MergePrims("Tram_hangar_walls", TramDir, walls), concrete, layer, true);
                    var lampMat = TramMat("Tram_hangar_lamp", new Color(1f, .9f, .7f)); lampMat.EnableKeyword("_EMISSION"); lampMat.SetColor("_EmissionColor", new Color(1f, .82f, .55f) * 2.2f); lampMat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
                    Go("Tram_hangar_lamps", parent, MergePrims("Tram_hangar_lamps", TramDir, lamps), lampMat, layer, false);
                    foreach (float lz in new[] { b.min.z + b.size.z * .3f, b.min.z + b.size.z * .7f })
                    {
                        var l = new GameObject("Tram_hangar_light").AddComponent<Light>(); l.transform.SetParent(parent, false);
                        l.transform.position = new Vector3(b.center.x, b.max.y - 2.2f, lz); l.type = LightType.Point; l.range = 22f; l.intensity = 1.6f; l.color = new Color(1f, .85f, .6f); l.shadows = LightShadows.None;
                    }
                }
            }
            {   // tanks: the simplified LOD1 model has the barrel off the turret; the three tanks always show the full model
                int sleeves = 0;
                for (int i = 1; i <= 3; i++)
                {
                    var tk = Child("10-tank" + i); if (!tk) continue;
                    var lg = tk.GetComponentInChildren<LODGroup>(); if (lg) lg.enabled = false;
                    foreach (var r in tk.GetComponentsInChildren<MeshRenderer>(true)) r.enabled = !r.name.Contains("LOD1") && !r.name.Contains("LOD2");
                    sleeves++;
                }
                log.AppendLine($"tramduro: statue {(mon ? "copied" : "missing")}, tribune, 3 flags, helipad, tanks on the full model {sleeves}");
            }
        }

        /// <summary>The longest thin part of a mesh (welded parts) and the part behind it on the tank side: when a gap lies between
        /// them, the box that closes it (mesh space) and the barrel's submesh.</summary>
        static bool BarrelGap(Mesh mesh, out Vector3 centre, out Vector3 size, out int sub)
        {
            centre = size = Vector3.zero; sub = 0;
            var v = mesh.vertices; int n = v.Length; var up = new int[n]; for (int i = 0; i < n; i++) up[i] = i;
            int Find(int x) { while (up[x] != x) { up[x] = up[up[x]]; x = up[x]; } return x; }
            void Union(int a, int b) { a = Find(a); b = Find(b); if (a != b) up[a] = b; }
            var weld = new Dictionary<Vector3Int, int>();
            for (int i = 0; i < n; i++) { var k = Vector3Int.RoundToInt(v[i] * 1000f); if (weld.TryGetValue(k, out int o)) Union(i, o); else weld[k] = i; }
            var subOf = new int[n];
            for (int s = 0; s < mesh.subMeshCount; s++) { var t = mesh.GetTriangles(s); for (int k = 0; k < t.Length; k += 3) { Union(t[k], t[k + 1]); Union(t[k], t[k + 2]); subOf[t[k]] = subOf[t[k + 1]] = subOf[t[k + 2]] = s; } }
            var comps = new Dictionary<int, Bounds>(); var compSub = new Dictionary<int, int>();
            for (int i = 0; i < n; i++) { int r = Find(i); if (comps.TryGetValue(r, out var b)) { b.Encapsulate(v[i]); comps[r] = b; } else { comps[r] = new Bounds(v[i], Vector3.zero); compSub[r] = subOf[i]; } }
            int best = -1, axis = 2; float score = 0f;
            foreach (var kv in comps)
            {
                var s3 = kv.Value.size;
                foreach (int a in new[] { 0, 2 }) { float len = s3[a], other = Mathf.Max(s3[2 - a], s3.y); if (len > 1.2f && other > 1e-3f && len / other > 4f && len / other > score) { score = len / other; best = kv.Key; axis = a; } }
            }
            if (best < 0) return false;
            var bb = comps[best]; var mc = mesh.bounds.center; int o2 = 2 - axis;
            bool fromMin = Mathf.Abs(bb.min[axis] - mc[axis]) < Mathf.Abs(bb.max[axis] - mc[axis]);   // the barrel starts at its min end
            float start = fromMin ? bb.min[axis] : bb.max[axis], gapMin = 1e9f;
            foreach (var kv in comps)
            {
                if (kv.Key == best) continue; var b = kv.Value;
                if (b.min.y > bb.center.y || b.max.y < bb.center.y || b.min[o2] > bb.center[o2] || b.max[o2] < bb.center[o2]) continue;
                float gap = fromMin ? start - b.max[axis] : b.min[axis] - start;
                if (fromMin ? b.min[axis] < start : b.max[axis] > start) gapMin = Mathf.Min(gapMin, gap);
            }
            if (gapMin < .03f || gapMin > 2f) return false;
            float a0 = fromMin ? start - gapMin - .05f : start - .05f, a1 = fromMin ? start + .05f : start + gapMin + .05f;
            centre = bb.center; centre[axis] = (a0 + a1) * .5f;
            size = bb.size; size[axis] = a1 - a0;
            sub = compSub[best];
            return true;
        }

        /// <summary>Border + Tramduro in one pass (Vadim 25.10).</summary>
        public static void Fix25() { BorderOnly(); TramduroOnly(); }


        /// <summary>Only Tramduro island (no hill rebuild).</summary>
        public static void TramduroOnly()
        {
            var scene = EditorSceneManager.OpenScene(Scene); var log = new StringBuilder();
            var root = GameObject.Find("Map_W85_v02").transform; int layer = 0;
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None)) if (r.name == "Road_serpentine_view_b_v3") layer = r.gameObject.layer;
            BuildTramduro(root, layer, log);
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("TramShotCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.clearFlags = CameraClearFlags.Skybox; cam.fieldOfView = 60;
            string D = @"C:\Users\chern_0eqkb03\VolunteersBuilds\";
            go.transform.position = new Vector3(1480, 60, 650); go.transform.LookAt(new Vector3(1560, 5, 790)); Shot(cam, 1000, 600, D + "tram_over.png");
            go.transform.position = new Vector3(1652, 16, 796); go.transform.LookAt(new Vector3(1618, 9, 828)); Shot(cam, 1000, 600, D + "tram_missiles.png");
            go.transform.position = new Vector3(1483, 9, 815); go.transform.LookAt(new Vector3(1492.2f, 6, 825.5f)); Shot(cam, 1000, 600, D + "tram_aa.png");
            go.transform.position = new Vector3(1440, 9, 770); go.transform.LookAt(new Vector3(1468, 4, 785)); Shot(cam, 1000, 600, D + "tram_gate.png");
            Object.DestroyImmediate(go);
            File.WriteAllText(D + "tram_apply.txt", log.ToString());
        }

        // ------------------------------------------------------------------------------------------ Downtown fixes (Vadim 25.10)
        const string DtDir = "Assets/VadimLocal/Downtown";

        static Material DtMat(string name, Color c, bool emit = false)
        {
            string path = DtDir + "/" + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(m, path); }
            m.SetColor("_BaseColor", c); m.SetFloat("_Smoothness", .08f);
            if (emit) { m.EnableKeyword("_EMISSION"); m.SetColor("_EmissionColor", c * 2.4f); m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None; }
            EditorUtility.SetDirty(m); return m;
        }

        /// <summary>Removes the flat surface triangles (plaza, sidewalks, pads, decals) over a rect, so a ramp can go down there.</summary>
        static int CutSurface(Rect r, StringBuilder log)
        {
            int cut = 0, k0 = 0;
            foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None))
            {
                var mr = mf.GetComponent<MeshRenderer>(); if (!mr || !mf.sharedMesh) continue;
                var b = mr.bounds; if (!Rect.MinMaxRect(b.min.x, b.min.z, b.max.x, b.max.z).Overlaps(r) || b.min.y > 6.5f || b.max.y < 3.5f) continue;
                if (!mf.sharedMesh.isReadable) { log.AppendLine($"  not readable over the ramp: {mf.name}"); continue; }
                if (b.size.y > 4f && !mf.name.ToLowerInvariant().Contains("plaza")) continue;
                if (mf.name.StartsWith("Dt_") || mf.name.StartsWith("Road_")) continue;
                var m = mf.sharedMesh; var v = m.vertices; var l2w = mf.transform.localToWorldMatrix; bool changed = false;
                var nm = Object.Instantiate(m); nm.name = m.name + "_cut";
                for (int s = 0; s < m.subMeshCount; s++)
                {
                    var t = m.GetTriangles(s); var keep = new List<int>();
                    for (int k = 0; k < t.Length; k += 3)
                    {
                        var c = l2w.MultiplyPoint3x4((v[t[k]] + v[t[k + 1]] + v[t[k + 2]]) / 3f);
                        if (r.Contains(new Vector2(c.x, c.z)) && c.y > 3.5f && c.y < 6.5f) { cut++; changed = true; } else keep.AddRange(new[] { t[k], t[k + 1], t[k + 2] });
                    }
                    nm.SetTriangles(keep, s);
                }
                if (!changed) continue;
                string path = DtDir + "/cut_" + (k0++) + "_" + mf.name.Replace("/", "_") + ".asset"; AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(nm, path);
                mf.sharedMesh = nm; var mc = mf.GetComponent<MeshCollider>(); if (mc) mc.sharedMesh = nm;
            }
            log.AppendLine($"downtown: {cut} surface triangles cut over {r}");
            return cut;
        }

        /// <summary>Downtown (Vadim 25.10): street S1 no longer runs straight through the whole district — two houses close it on
        /// its west part (one from the south block, one from the north, tight to their neighbours); an underground car park under
        /// the tower podium (05-03) with a two-way ramp from street N2 (the flickering curb marks go).</summary>
        static void BuildDowntownFixes(Transform root, int layer, Material roadMat, StringBuilder log)
        {
            if (!AssetDatabase.IsValidFolder(DtDir)) AssetDatabase.CreateFolder("Assets/VadimLocal", "Downtown");
            var old = root.Find("VadimDowntown"); if (old) Object.DestroyImmediate(old.gameObject);
            var parent = new GameObject("VadimDowntown").transform; parent.SetParent(root, false);
            var terrain = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var tp = terrain.transform.position; var td = terrain.terrainData;

            // 1. S1 closed between Va2 (x 918) and Vp2 (x 946): copies of house 05-H000 (15.9 x 11.5 m), south and north half
            var src = GameObject.Find("B_05-H000");
            var block = Rect.MinMaxRect(924f, 218.5f, 940f, 241.5f);
            if (src)
            {
                var rs = src.GetComponentsInChildren<Renderer>(); var sb = rs[0].bounds; foreach (var r in rs) sb.Encapsulate(r.bounds);
                foreach (var (cz, yaw, n) in new[] { (224.25f, 0f, "Dt_S1_house_south"), (235.75f, 180f, "Dt_S1_house_north") })
                {
                    var h = Object.Instantiate(src, parent); h.name = n;
                    var piv = new Vector3(sb.center.x, src.transform.position.y, sb.center.z);
                    h.transform.position = src.transform.position; h.transform.rotation = src.transform.rotation;
                    h.transform.RotateAround(piv, Vector3.up, yaw);
                    h.transform.position += new Vector3(932f - sb.center.x, 0f, cz - sb.center.z);
                }
                // what stood on that bit of street goes (cars, lamps, hydrants, signs)
                int gone = 0;
                foreach (var tr in root.GetComponentsInChildren<Transform>(true))
                {
                    if (tr == root || tr.IsChildOf(parent) || !tr.gameObject.activeSelf) continue;
                    var rr = tr.GetComponent<Renderer>(); if (!rr && tr.childCount == 0) continue;
                    var p = new Vector2(tr.position.x, tr.position.z); if (!block.Contains(p)) continue;
                    if (tr.name.StartsWith("Street") || tr.name.StartsWith("Sidewalk") || tr.name.StartsWith("Decal") || tr.name.StartsWith("District")) continue;
                    if (rr && (rr.bounds.size.x > 30f || rr.bounds.size.z > 30f)) continue;
                    tr.gameObject.SetActive(false); gone++;
                }
                log.AppendLine($"downtown: S1 closed by 2 houses at x 924-940 ({gone} props removed)");
            }

            // 2. underground car park 05-03 under the podium: floor 1.0 m, ceiling 4.65 m, ramp from N2 down the plaza's west strip
            Rect park = Rect.MinMaxRect(965f, 410f, 1089f, 431.5f), ramp = Rect.MinMaxRect(965.8f, 431.5f, 973.5f, 452f);
            foreach (var n in new[] { "05-drop-ramp-N2", "05-drop-ramp-N3", "Zone_05-drop-ramp-N2", "Zone_05-drop-ramp-N3" })
                foreach (var tr in root.GetComponentsInChildren<Transform>(true)) if (tr.name.Contains(n)) tr.gameObject.SetActive(false);
            CutSurface(ramp, log);
            {   // terrain holes over the whole garage and the ramp
                int hr = td.holesResolution; float hx = td.size.x / hr, hz = td.size.z / hr;
                int c0 = Mathf.FloorToInt((park.xMin - tp.x) / hx), c1 = Mathf.CeilToInt((park.xMax - tp.x) / hx), r0 = Mathf.FloorToInt((park.yMin - tp.z) / hz), r1 = Mathf.CeilToInt((ramp.yMax - tp.z) / hz);
                var holes = td.GetHoles(c0, r0, c1 - c0, r1 - r0);
                for (int j = 0; j < r1 - r0; j++) for (int i = 0; i < c1 - c0; i++)
                {
                    var q = new Vector2(tp.x + (c0 + i + .5f) * hx, tp.z + (r0 + j + .5f) * hz);
                    if (park.Contains(q) || ramp.Contains(q)) holes[j, i] = false;
                }
                td.SetHoles(c0, r0, holes); EditorUtility.SetDirty(td);
            }
            const float floorY = 1.0f, ceil = 4.65f, top = 5.02f;
            var conc = DtMat("Dt_park_concrete", new Color(.62f, .62f, .6f)); var wallM = DtMat("Dt_park_wall", new Color(.78f, .77f, .74f));
            var yellow = DtMat("Dt_park_yellow", new Color(.95f, .78f, .15f)); var white = DtMat("Dt_park_white", new Color(.93f, .93f, .9f));
            var lamp = DtMat("Dt_park_lamp", new Color(1f, .93f, .8f), true);
            var shell = new List<(string, Matrix4x4)>
            {
                ("Cube", Matrix4x4.TRS(new Vector3(park.center.x, floorY - .2f, park.center.y), Quaternion.identity, new Vector3(park.width + 1f, .4f, park.height + 1f))),
                ("Cube", Matrix4x4.TRS(new Vector3(park.center.x, ceil + .15f, park.center.y), Quaternion.identity, new Vector3(park.width + 1f, .3f, park.height + 1f))),
                ("Cube", Matrix4x4.TRS(new Vector3(park.center.x, (floorY + ceil) * .5f, park.yMin - .2f), Quaternion.identity, new Vector3(park.width + 1f, ceil - floorY + .4f, .4f))),
                ("Cube", Matrix4x4.TRS(new Vector3(park.xMin - .2f, (floorY + ceil) * .5f, park.center.y), Quaternion.identity, new Vector3(.4f, ceil - floorY + .4f, park.height + 1f))),
                ("Cube", Matrix4x4.TRS(new Vector3(park.xMax + .2f, (floorY + ceil) * .5f, park.center.y), Quaternion.identity, new Vector3(.4f, ceil - floorY + .4f, park.height + 1f))),
                // north wall with the ramp opening
                ("Cube", Matrix4x4.TRS(new Vector3((ramp.xMax + park.xMax) * .5f, (floorY + ceil) * .5f, park.yMax + .2f), Quaternion.identity, new Vector3(park.xMax - ramp.xMax, ceil - floorY + .4f, .4f))),
            };
            for (float x = park.xMin + 8f; x < park.xMax - 2f; x += 8f) foreach (float z in new[] { 417f, 424.5f })
                shell.Add(("Cube", Matrix4x4.TRS(new Vector3(x, (floorY + ceil) * .5f, z), Quaternion.identity, new Vector3(.6f, ceil - floorY, .6f))));
            Go("Dt_park_shell", parent, MergePrims("Dt_park_shell", DtDir, shell), wallM, layer, true);
            var marks = new List<(string, Matrix4x4)>();
            for (float x = park.xMin + 2f; x < park.xMax - 1f; x += 2.6f) foreach (var (z0, z1) in new[] { (410.5f, 416.5f), (425f, 431f) })
                marks.Add(("Cube", Matrix4x4.TRS(new Vector3(x, floorY + .01f, (z0 + z1) * .5f), Quaternion.identity, new Vector3(.12f, .02f, z1 - z0))));
            Go("Dt_park_marks", parent, MergePrims("Dt_park_marks", DtDir, marks), white, layer, false);
            var stripe = new List<(string, Matrix4x4)>();
            for (float x = park.xMin + 3f; x < park.xMax - 1f; x += 8f) stripe.Add(("Cube", Matrix4x4.TRS(new Vector3(x, 1.4f, park.yMin + .02f), Quaternion.identity, new Vector3(4f, .35f, .04f))));
            Go("Dt_park_stripe", parent, MergePrims("Dt_park_stripe", DtDir, stripe), yellow, layer, false);
            var lamps = new List<(string, Matrix4x4)>();
            for (float x = park.xMin + 5f; x < park.xMax - 2f; x += 10f) lamps.Add(("Cube", Matrix4x4.TRS(new Vector3(x, ceil - .05f, 420.75f), Quaternion.identity, new Vector3(2.4f, .08f, .3f))));
            Go("Dt_park_lamps", parent, MergePrims("Dt_park_lamps", DtDir, lamps), lamp, layer, false);
            foreach (float x in new[] { 990f, 1030f, 1070f })
            {
                var l = new GameObject("Dt_park_light").AddComponent<Light>(); l.transform.SetParent(parent, false);
                l.transform.position = new Vector3(x, ceil - .6f, 420.75f); l.type = LightType.Point; l.range = 24f; l.intensity = 2f; l.color = new Color(1f, .92f, .78f); l.shadows = LightShadows.None;
            }
            // the ramp: 7.7 m wide, street level at the N2 kerb to the garage floor, side walls with a railing above ground
            var rp = new List<(Vector2 p, float y)>();
            for (float z = ramp.yMax + 1.5f; z >= park.yMax - 3f; z -= 1f)
            {
                float u = Mathf.InverseLerp(ramp.yMax - 1f, park.yMax + .5f, z);
                rp.Add((new Vector2(ramp.center.x, z), Mathf.Lerp(top - .03f, floorY + .02f, Smooth(u))));
            }
            if (roadMat) MakeRoad("Dt_park_ramp", rp, ramp.width, 6f, roadMat, parent, layer, null);
            var side = new List<(string, Matrix4x4)>();
            foreach (float x in new[] { ramp.xMin - .2f, ramp.xMax + .2f })
            {
                side.Add(("Cube", Matrix4x4.TRS(new Vector3(x, (floorY + top + .9f) * .5f - .3f, (ramp.yMin + ramp.yMax) * .5f), Quaternion.identity, new Vector3(.4f, top + .9f - floorY + .6f, ramp.height))));
            }
            side.Add(("Cube", Matrix4x4.TRS(new Vector3(ramp.center.x, (ceil + top - .04f) * .5f, ramp.yMin + .2f), Quaternion.identity, new Vector3(ramp.width + .8f, top - .04f - ceil, .4f))));   // lintel over the garage mouth
            Go("Dt_park_ramp_walls", parent, MergePrims("Dt_park_ramp_walls", DtDir, side), wallM, layer, true);
            log.AppendLine($"downtown: underground car park {park.width:0} x {park.height:0} m, ramp from N2");
        }

        public static void DowntownOnly()
        {
            var scene = EditorSceneManager.OpenScene(Scene); var log = new StringBuilder();
            var root = GameObject.Find("Map_W85_v02").transform; int layer = 0; Material roadMat = null;
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None)) if (r.name == "Road_serpentine_view_b_v3") { roadMat = r.sharedMaterial; layer = r.gameObject.layer; }
            BuildDowntownFixes(root, layer, roadMat, log);
            GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>().Flush();
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("DtCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 2000; cam.fieldOfView = 60;
            string D = @"C:\Users\chern_0eqkb03\VolunteersBuilds\";
            go.transform.position = new Vector3(932, 40, 195); go.transform.LookAt(new Vector3(932, 8, 232)); Shot(cam, 1000, 600, D + "dt_s1.png");
            go.transform.position = new Vector3(969.6f, 9, 466); go.transform.LookAt(new Vector3(969.6f, 2, 432)); Shot(cam, 1000, 600, D + "dt_ramp.png");
            go.transform.position = new Vector3(975, 3.2f, 421); go.transform.LookAt(new Vector3(1040, 2.6f, 420)); Shot(cam, 1000, 600, D + "dt_park.png");
            Object.DestroyImmediate(go);
            File.WriteAllText(D + "dt_apply.txt", log.ToString());
        }

        // ------------------------------------------------------------------------------------------ Quiet Valley (Vadim 25.10)
        // the river turns south sooner: a new gorge at x ~610 right beside the valley, the old one (x ~650) filled; a big ridge
        // between the valley and the river, a medium one beyond it; the valley's river side (lab compound, fence, paths) moves in
        static readonly Vector2[] ValleyRiver = { new(540, 304), new(560, 303), new(578, 300), new(592, 294), new(602, 284), new(607, 268), new(609, 240), new(610, 200), new(611, 160), new(611, 125), new(612, 104), new(612, 90) };
        const float ValleyShift = -14f, ValleyEdgeOld = 616f, ValleyEdgeNew = 589f;

        static float PolyInfo(Vector2 p, Vector2[] pl, out float along, out float side)
        {
            float best = 1e9f, acc = 0f; along = 0f; side = 0f;
            for (int i = 0; i + 1 < pl.Length; i++)
            {
                Vector2 a = pl[i], d = pl[i + 1] - a; float l2 = d.sqrMagnitude, l = Mathf.Sqrt(l2);
                float u = Mathf.Clamp01(Vector2.Dot(p - a, d) / l2); var c = a + d * u; float dd = (p - c).magnitude;
                if (dd < best) { best = dd; along = acc + u * l; side = Mathf.Sign(d.x * (p.y - a.y) - d.y * (p.x - a.x)); }
                acc += l;
            }
            return best;
        }

        /// <summary>Fedya's sea is a 4 m quad grid left out wherever the old ground was land: where land is now sea, the missing quads
        /// are added (same grid, same material) so the new water is real water.</summary>
        // Vadim 27.10: the shore foam is drawn wherever the sea is shallower than ~0.5 m, so underwater sandbars and shoals
        // away from land showed as white lines in open water. Deepen the sea floor that is shallow and more than ShoalKeep m
        // from dry land; the beach slope next to the shore stays as it is. Only cells under a sea mesh are touched.
        const float ShoalKeep = 6f, ShoalBlend = 8f, ShoalDepth = .9f;
        // Vadim 27.10: «white only where the water runs onto the sand». The static foam decals along the shore and on the
        // river (T134_*) were the second offshore band and the white blotches; the water shader draws the one shore band.
        public static void FoamOnly()
        {
            var scene = EditorSceneManager.OpenScene(Scene); var log = new StringBuilder();
            NoFoamDecals(log);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            Debug.Log("[VadimHill] " + log);
        }

        static void NoFoamDecals(StringBuilder log)
        {
            foreach (var n in new[] { "T134_shore_foam", "T134_river_foam" })
            {
                var go = GameObject.Find(n);
                if (!go) { log.AppendLine($"Foam: {n} not found"); continue; }
                log.AppendLine($"Foam: {n} off ({go.transform.childCount} decals)"); go.SetActive(false);
            }
        }

        public static void ShoalsOnly()
        {
            var scene = EditorSceneManager.OpenScene(Scene); var log = new StringBuilder();
            DeepenShoals(log);
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            Debug.Log("[VadimHill] " + log);
        }

        static void DeepenShoals(StringBuilder log)
        {
            var terrain = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>();
            var seaGo = GameObject.Find("Sea_dense_0m"); if (!seaGo) { log.AppendLine("Shoals: no Sea_dense_0m"); return; }
            var td = terrain.terrainData; Vector3 tp = terrain.transform.position; float H = td.size.y;
            int R = td.heightmapResolution; float cell = td.size.x / (R - 1);
            var cols = new List<MeshCollider>();
            foreach (var mf in seaGo.transform.parent.GetComponentsInChildren<MeshFilter>())
                if (mf.name.StartsWith("Sea")) { var mc = mf.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; cols.Add(mc); }
            Physics.SyncTransforms();
            int step = Mathf.Max(1, Mathf.RoundToInt(4f / cell)), C = (R + step - 1) / step;
            var under = new bool[C, C];
            for (int cz = 0; cz < C; cz++) for (int cx = 0; cx < C; cx++)
            {
                float wx = tp.x + (cx * step + step * .5f) * cell, wz = tp.z + (cz * step + step * .5f) * cell;
                var ray = new Ray(new Vector3(wx, 50f, wz), Vector3.down);
                foreach (var mc in cols) if (mc.Raycast(ray, out _, 100f)) { under[cz, cx] = true; break; }
            }
            foreach (var mc in cols) Object.DestroyImmediate(mc);
            var h = td.GetHeights(0, 0, R, R);
            var dist = new float[R, R]; const float Big = 1e6f; float d1 = cell, d2 = cell * 1.41421f;
            for (int z = 0; z < R; z++) for (int x = 0; x < R; x++) dist[z, x] = h[z, x] * H + tp.y > -.02f ? 0f : Big;
            for (int z = 0; z < R; z++) for (int x = 0; x < R; x++)
            {
                float d = dist[z, x]; if (d == 0f) continue;
                if (x > 0) d = Mathf.Min(d, dist[z, x - 1] + d1);
                if (z > 0) { d = Mathf.Min(d, dist[z - 1, x] + d1); if (x > 0) d = Mathf.Min(d, dist[z - 1, x - 1] + d2); if (x < R - 1) d = Mathf.Min(d, dist[z - 1, x + 1] + d2); }
                dist[z, x] = d;
            }
            for (int z = R - 1; z >= 0; z--) for (int x = R - 1; x >= 0; x--)
            {
                float d = dist[z, x]; if (d == 0f) continue;
                if (x < R - 1) d = Mathf.Min(d, dist[z, x + 1] + d1);
                if (z < R - 1) { d = Mathf.Min(d, dist[z + 1, x] + d1); if (x < R - 1) d = Mathf.Min(d, dist[z + 1, x + 1] + d2); if (x > 0) d = Mathf.Min(d, dist[z + 1, x - 1] + d2); }
                dist[z, x] = d;
            }
            int changed = 0;
            for (int z = 0; z < R; z++) for (int x = 0; x < R; x++)
            {
                float y = h[z, x] * H + tp.y; if (y >= -.02f || !under[z / step, x / step]) continue;
                float depth = -y, k = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(ShoalKeep, ShoalKeep + ShoalBlend, dist[z, x]));
                float want = Mathf.Lerp(depth, Mathf.Max(depth, ShoalDepth), k);
                if (want > depth + .005f) { h[z, x] = (-want - tp.y) / H; changed++; }
            }
            td.SetHeights(0, 0, h); terrain.Flush(); EditorUtility.SetDirty(td);
            log.AppendLine($"Shoals: {changed} sea-floor cells deepened to >= {ShoalDepth} m (more than {ShoalKeep} m from land)");
        }

        static void FillSea(string name, Rect r, System.Func<Vector2, bool> want, StringBuilder log)
        {
            var seaGo = GameObject.Find("Sea_dense_0m"); if (!seaGo) { log.AppendLine("FillSea: no Sea_dense_0m"); return; }
            var old = seaGo.transform.parent.Find(name); if (old) Object.DestroyImmediate(old.gameObject);
            var mc = seaGo.AddComponent<MeshCollider>(); mc.sharedMesh = seaGo.GetComponent<MeshFilter>().sharedMesh; Physics.SyncTransforms();
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            for (float z = -200f + Mathf.Floor((r.yMin + 200f) / 4f) * 4f; z < r.yMax; z += 4f)
                for (float x = -200f + Mathf.Floor((r.xMin + 200f) / 4f) * 4f; x < r.xMax; x += 4f)
                {
                    var c = new Vector2(x + 2f, z + 2f);
                    if (!want(c) || mc.Raycast(new Ray(new Vector3(c.x, 50f, c.y), Vector3.down), out _, 100f)) continue;
                    int n = v.Count;
                    v.Add(new Vector3(x, 0, z)); v.Add(new Vector3(x, 0, z + 4f)); v.Add(new Vector3(x + 4f, 0, z + 4f)); v.Add(new Vector3(x + 4f, 0, z));
                    uv.Add(new Vector2(x, z) / 10f); uv.Add(new Vector2(x, z + 4f) / 10f); uv.Add(new Vector2(x + 4f, z + 4f) / 10f); uv.Add(new Vector2(x + 4f, z) / 10f);
                    t.AddRange(new[] { n, n + 1, n + 2, n, n + 2, n + 3 });
                }
            Object.DestroyImmediate(mc);
            log.AppendLine($"{name}: {t.Count / 6} sea quads added");
            if (v.Count == 0) return;
            var m = new Mesh { name = name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 }; m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(t, 0); m.RecalculateNormals(); m.RecalculateBounds();
            string pth = Dir + "/" + name + ".asset"; AssetDatabase.DeleteAsset(pth); AssetDatabase.CreateAsset(m, pth);
            var go = new GameObject(name); go.transform.SetParent(seaGo.transform.parent, false); go.layer = seaGo.layer;
            go.AddComponent<MeshFilter>().sharedMesh = m; var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = seaGo.GetComponent<MeshRenderer>().sharedMaterial;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        }

        // ------------------------------------------------------------------ stone (Vadim 25.10): a mountain is one plain grey stone, nothing else
        const string RockDir = "Assets/VadimLocal/Rock";

        /// <summary>Seamless stylised grey stone, one solid rock (Vadim 25.10: no small stones joined together — one big mountain, like
        /// in simple games): soft large patches, a fine grain, gentle vertical weathering and a few long thin cracks.</summary>
        static Texture2D StoneTexture() =>   // Vadim 25.10: Fedya's rock macro (it fakes ledges and volume), only darker (tint below)
            AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/OnlyVolunteers/Map/W85Build/Generated/v02/Textures/Rock_Macro.png");
        static readonly Color StoneTint = new Color(.68f, .71f, .76f);   // dark grey stone (Vadim 25.10, option 3)

        /// <summary>A rock skin over terrain cells (1 m) the predicate picks: box-projected UVs, edges sunk into the ground. Terrain textures
        /// are projected from above and stretch on steep ground, so every steep rock surface gets a skin (Vadim 25.10).</summary>
        static int SkinOver(string name, RectInt R, System.Func<float, float, float, float, bool> on, Transform parent, int layer)
        {
            var ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var td = ter.terrainData; var tp = ter.transform.position;
            var mat = AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Map/W85Build/Generated/v02/Materials/W86_rock_face.mat");
            var flag = new bool[R.width + 2, R.height + 2];
            for (int x = R.xMin; x <= R.xMax; x++) for (int z = R.yMin; z <= R.yMax; z++)
            {
                float u = (x + .5f - tp.x) / td.size.x, v = (z + .5f - tp.z) / td.size.z;
                flag[x - R.xMin, z - R.yMin] = on(x + .5f, z + .5f, td.GetInterpolatedHeight(u, v) + tp.y, td.GetSteepness(u, v));
            }
            bool On(int x, int z) => x >= R.xMin && z >= R.yMin && x <= R.xMax && z <= R.yMax && flag[x - R.xMin, z - R.yMin];
            Vector3 Vt(int vx, int vz)
            {
                bool inner = On(vx - 1, vz - 1) && On(vx, vz - 1) && On(vx - 1, vz) && On(vx, vz);
                float u = (vx - tp.x) / td.size.x, v = (vz - tp.z) / td.size.z;
                return new Vector3(vx, td.GetInterpolatedHeight(u, v) + tp.y, vz) + td.GetInterpolatedNormal(u, v) * (inner ? .12f : -.3f);
            }
            var V = new List<Vector3>(); var UV = new List<Vector2>(); var T = new List<int>();
            void Tri(Vector3 a, Vector3 b, Vector3 c)
            {
                var n = Vector3.Cross(b - a, c - a); float ax = Mathf.Abs(n.x), ay = Mathf.Abs(n.y), az = Mathf.Abs(n.z);
                Vector2 Uv(Vector3 q) => ay >= ax && ay >= az ? new Vector2(q.x, q.z) / 7f : ax >= az ? new Vector2(q.z, q.y) / 7f : new Vector2(q.x, q.y) / 7f;
                if (n.y < 0) { var t0 = b; b = c; c = t0; }
                int k = V.Count; V.Add(a); V.Add(b); V.Add(c); UV.Add(Uv(a)); UV.Add(Uv(b)); UV.Add(Uv(c)); T.Add(k); T.Add(k + 1); T.Add(k + 2);
            }
            for (int x = R.xMin; x <= R.xMax; x++) for (int z = R.yMin; z <= R.yMax; z++)
            {
                if (!On(x, z)) continue;
                Vector3 p00 = Vt(x, z), p10 = Vt(x + 1, z), p01 = Vt(x, z + 1), p11 = Vt(x + 1, z + 1);
                Tri(p00, p01, p11); Tri(p00, p11, p10);
            }
            var old = parent.Find(name); if (old) Object.DestroyImmediate(old.gameObject);
            if (V.Count == 0 || !mat) return 0;
            var m = new Mesh { name = name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 }; m.SetVertices(V); m.SetUVs(0, UV); m.SetTriangles(T, 0); m.RecalculateNormals(); m.RecalculateBounds();
            string pth = Dir + "/" + name + ".asset"; AssetDatabase.DeleteAsset(pth); AssetDatabase.CreateAsset(m, pth);
            var go = new GameObject(name); go.transform.SetParent(parent, false); go.layer = layer; go.isStatic = true;
            go.AddComponent<MeshFilter>().sharedMesh = m; var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = mat; mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            return T.Count / 3;
        }

        public static void StonePreview()
        {   // just the texture, for Vadim to look at before a build
            var t = StoneTexture(); File.Copy(AssetDatabase.GetAssetPath(t), "C:/Users/chern_0eqkb03/VolunteersBuilds/stone_v02_tile.png", true);
        }

        /// <summary>Every rock skin (Fedya's rock faces, our ridge) and the terrain's rock layer get the same grey stone; the faces get smooth
        /// normals (no faceted chessboard).</summary>
        static void OneStone(StringBuilder log)
        {
            var tex = StoneTexture();
            string mp = RockDir + "/W86_rock_stone_v01.mat"; var mat = AssetDatabase.LoadAssetAtPath<Material>(mp);
            if (!mat) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "W86_rock_stone_v01", enableInstancing = true }; AssetDatabase.CreateAsset(mat, mp); }
            mat.SetTexture("_BaseMap", tex); mat.SetTextureScale("_BaseMap", Vector2.one); mat.SetColor("_BaseColor", StoneTint); mat.SetFloat("_Smoothness", .05f); EditorUtility.SetDirty(mat);   // skins are UV'd 7 m per unit: one texture over 20 m
            if (!AssetDatabase.IsValidFolder(RockDir + "/Smooth")) AssetDatabase.CreateFolder(RockDir, "Smooth");
            int n = 0;
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None))
            {
                if (!r.sharedMaterial || !r.sharedMaterial.name.StartsWith("W86_rock_face")) continue;
                r.sharedMaterial = mat; var mf = r.GetComponent<MeshFilter>(); var m = mf ? mf.sharedMesh : null; if (!m || !m.isReadable) continue;
                var v = m.vertices; var t3 = m.triangles; var acc = new Dictionary<Vector3Int, Vector3>();
                Vector3Int K(Vector3 q) => new Vector3Int(Mathf.RoundToInt(q.x * 50), Mathf.RoundToInt(q.y * 50), Mathf.RoundToInt(q.z * 50));
                for (int k = 0; k < t3.Length; k += 3)
                {
                    var nn = Vector3.Cross(v[t3[k + 1]] - v[t3[k]], v[t3[k + 2]] - v[t3[k]]);
                    for (int q = 0; q < 3; q++) { var key = K(v[t3[k + q]]); acc[key] = (acc.TryGetValue(key, out var a) ? a : Vector3.zero) + nn; }
                }
                var sm = Object.Instantiate(m); sm.name = m.name + "_stone"; sm.normals = v.Select(q => acc.TryGetValue(K(q), out var a2) && a2.sqrMagnitude > 0 ? a2.normalized : Vector3.up).ToArray();
                string pth = RockDir + "/Smooth/" + r.name + "_" + n + ".asset"; AssetDatabase.DeleteAsset(pth); AssetDatabase.CreateAsset(sm, pth); mf.sharedMesh = sm; n++;
            }
            int oc = 0;
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None))
                if (r.transform.parent && r.transform.parent.name == "RockOutcrops" || r.sharedMaterial && r.sharedMaterial.name.StartsWith("HK_Rock"))
                {   // the boulders: their own texture, tinted to the same grey as the stone (no white blobs, no dark holes)
                    string bp = RockDir + "/Boulder_stone_v01.mat"; var bm = AssetDatabase.LoadAssetAtPath<Material>(bp);
                    if (!bm) { bm = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "Boulder_stone_v01" }; AssetDatabase.CreateAsset(bm, bp); }
                    bm.SetColor("_BaseColor", new Color(.36f, .38f, .41f)); bm.SetFloat("_Smoothness", .05f); EditorUtility.SetDirty(bm);   // URP Lit: plain stone grey
                    r.sharedMaterials = r.sharedMaterials.Select(_ => bm).ToArray(); oc++;
                }
            log.AppendLine($"stone: {oc} outcrops re-textured");
            var ter = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var td = ter.terrainData; var ls = td.terrainLayers;
            string lp = RockDir + "/TL_rock_stone_v01.terrainlayer"; var tl = AssetDatabase.LoadAssetAtPath<TerrainLayer>(lp);
            if (!tl) { tl = new TerrainLayer(); AssetDatabase.CreateAsset(tl, lp); }
            tl.diffuseTexture = tex; tl.tileSize = new Vector2(7f, 7f); tl.diffuseRemapMin = Vector4.zero; tl.diffuseRemapMax = new Vector4(StoneTint.r, StoneTint.g, StoneTint.b, 1f); EditorUtility.SetDirty(tl);
            string was = ls.Length > 7 && ls[7] ? ls[7].name : "-";
            if (ls.Length > 7) { ls[7] = tl; td.terrainLayers = ls; }
            log.AppendLine($"stone: {n} rock skins re-textured and smoothed, terrain rock layer 7 ({was}) -> {tl.name}");
        }

        /// <summary>The city beach's own splat mix, sampled on its dry sand a little up from the water at x 780.</summary>
        static float[,,] CityBeachSand(Terrain t)
        {
            var td = t.terrainData; var tp = t.transform.position; float ax = td.size.x / td.alphamapResolution, az = td.size.z / td.alphamapResolution;
            float zz = 172f; for (float z = 110f; z < 260f; z += 1f) { float hq = t.SampleHeight(new Vector3(780f, 0, z)) + tp.y; if (hq > .9f) { zz = z + 8f; break; } }
            return td.GetAlphamaps(Mathf.FloorToInt((780f - tp.x) / ax), Mathf.FloorToInt((zz - tp.z) / az), 1, 1);
        }

        /// <summary>The sand / grass edge behind the east beach: follows the water line with a soft wobble, never a ruler line.</summary>
        static float BeachEdge(float x) => 39f + (Mathf.PerlinNoise(x * .045f, 2.7f) - .5f) * 14f;

        /// <summary>Index of the plain dry-sand terrain layer (by name), -1 if none.</summary>
        static int SandLayer(TerrainData td)
        {
            var ls = td.terrainLayers;
            for (int l = 0; l < ls.Length; l++) { string n = ls[l] ? ls[l].name.ToLower() : ""; if (n.Contains("sand") && !n.Contains("wet") && !n.Contains("dark")) return l; }
            return -1;
        }

        /// <summary>Beach rule (Vadim 25.10): a lounger always faces the sea — backrest away from the water, feet to it. Works out the
        /// backrest end from the mesh (the higher end of its long axis) and turns the object so that end points away from the sea.</summary>
        static void FaceSea(Transform t, Vector2 sea)
        {
            var mf = t.GetComponentInChildren<MeshFilter>(); Vector3 back = Vector3.forward;
            if (mf && mf.sharedMesh && mf.sharedMesh.isReadable)
            {
                var m = mf.sharedMesh; var bb = m.bounds; bool alongX = bb.size.x >= bb.size.z; float lo = alongX ? bb.min.x : bb.min.z, len = Mathf.Max(alongX ? bb.size.x : bb.size.z, 1e-3f);
                float hA = -1e9f, hB = -1e9f; foreach (var q in m.vertices) { float u = ((alongX ? q.x : q.z) - lo) / len; if (u < .25f) hA = Mathf.Max(hA, q.y); if (u > .75f) hB = Mathf.Max(hB, q.y); }
                var axis = alongX ? Vector3.right : Vector3.forward; back = hB >= hA ? axis : -axis;
                back = t.InverseTransformDirection(mf.transform.TransformDirection(back));
            }
            float want = Mathf.Atan2(-sea.x, -sea.y) * Mathf.Rad2Deg, have = Mathf.Atan2(back.x, back.z) * Mathf.Rad2Deg;
            t.rotation = Quaternion.Euler(0f, want - have, 0f);
        }

        /// <summary>East of the new river: the sea edge from the river mouth to the city beach (Vadim 25.10).</summary>
        static float EastWaterline(float x) => Mathf.Lerp(100f, 150f, Smooth(Mathf.InverseLerp(615f, 705f, x)));

        /// <summary>Vadim 25.10: the valley floor (inside the valley, beyond the big ridge) flat, not lumpy. Wide blur; the ground under
        /// roads, buildings and other solid things stays where it is (blended out over 4 m); paths / decals / fences on the ground and
        /// trees / grass follow the new ground.</summary>
        static void FlattenValleyFloor(Terrain terrain, StringBuilder log)
        {
            var td = terrain.terrainData; var tp = terrain.transform.position; int R = td.heightmapResolution; float sx = td.size.x / (R - 1), sz = td.size.z / (R - 1), sy = td.size.y;
            var F = Rect.MinMaxRect(466f, 116f, 598f, 302f);
            int x0 = Mathf.FloorToInt((F.xMin - tp.x) / sx), x1 = Mathf.CeilToInt((F.xMax - tp.x) / sx), z0 = Mathf.FloorToInt((F.yMin - tp.z) / sz), z1 = Mathf.CeilToInt((F.yMax - tp.z) / sz);
            int W = x1 - x0 + 1, H = z1 - z0 + 1; var h = td.GetHeights(x0, z0, W, H); var orig = (float[,])h.Clone();
            float G0(int j, int i) => tp.y + orig[j, i] * sy;
            // where it may change: the floor (1.5 .. 14 m, beyond the ridge), not under solid things
            var pin = new float[H, W]; Physics.SyncTransforms(); int pinned = 0;
            for (int j = 0; j < H; j++) for (int i = 0; i < W; i++)
            {
                var p = new Vector2(tp.x + (x0 + i) * sx, tp.z + (z0 + j) * sz); float y0 = G0(j, i);
                if (y0 < 1.5f || y0 > 14f || PolyInfo(p, ValleyRiver, out _, out _) < 24f) { pin[j, i] = 1f; continue; }
                foreach (var hit in Physics.RaycastAll(new Vector3(p.x, y0 + 30f, p.y), Vector3.down, 40f))
                    if (!(hit.collider is TerrainCollider) && hit.point.y < y0 + 3f && hit.point.y > y0 - 2f) { pin[j, i] = 1f; pinned++; break; }
            }
            int rp = Mathf.RoundToInt(4f / sx); var pinB = (float[,])pin.Clone();
            for (int j = 0; j < H; j++) for (int i = 0; i < W; i++)
            {   // grow the pins 4 m (soft)
                if (pin[j, i] >= 1f) continue; float best = 0f;
                for (int a = -rp; a <= rp; a++) for (int b = -rp; b <= rp; b++)
                {
                    int jj = j + a, ii = i + b; if (jj < 0 || ii < 0 || jj >= H || ii >= W || pin[jj, ii] < 1f) continue;
                    best = Mathf.Max(best, 1f - Mathf.Sqrt(a * a + b * b) / (rp + 1f));
                }
                pinB[j, i] = Smooth(best);
            }
            var bl = (float[,])h.Clone(); int rr = Mathf.RoundToInt(10f / sx);
            for (int pass = 0; pass < 2; pass++)
            {
                var tmp = new float[H, W];
                for (int j = 0; j < H; j++) for (int i = 0; i < W; i++) { float a = 0f; for (int k = -rr; k <= rr; k++) a += bl[j, Mathf.Clamp(i + k, 0, W - 1)]; tmp[j, i] = a / (2 * rr + 1); }
                for (int j = 0; j < H; j++) for (int i = 0; i < W; i++) { float a = 0f; for (int k = -rr; k <= rr; k++) a += tmp[Mathf.Clamp(j + k, 0, H - 1), i]; bl[j, i] = a / (2 * rr + 1); }
            }
            int changed = 0;
            for (int j = 0; j < H; j++) for (int i = 0; i < W; i++)
            {
                float wx = tp.x + (x0 + i) * sx, wz = tp.z + (z0 + j) * sz;
                float edge = Smooth(Mathf.Min(Mathf.Min(wx - F.xMin, F.xMax - wx), Mathf.Min(wz - F.yMin, F.yMax - wz)) / 12f);
                float k = .92f * edge * (1f - pinB[j, i]); if (k <= 0f) continue;
                h[j, i] = Mathf.Lerp(orig[j, i], bl[j, i], k); if (Mathf.Abs(h[j, i] - orig[j, i]) * sy > .03f) changed++;
            }
            td.SetHeights(x0, z0, h); terrain.Flush();
            float D(float x, float z)
            {   // how much the ground moved here
                int i = Mathf.Clamp(Mathf.RoundToInt((x - tp.x) / sx) - x0, 0, W - 1), j = Mathf.Clamp(Mathf.RoundToInt((z - tp.z) / sz) - z0, 0, H - 1);
                return F.Contains(new Vector2(x, z)) ? (h[j, i] - orig[j, i]) * sy : 0f;
            }
            // flat things lying on the ground (paths, decals, low fences, ground patches) follow it
            int meshes = 0;
            foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None))
            {
                var r = mf.GetComponent<Renderer>(); if (!r || !mf.sharedMesh || !mf.sharedMesh.isReadable) continue; var b = r.bounds;
                if (!F.Overlaps(Rect.MinMaxRect(b.min.x, b.min.z, b.max.x, b.max.z)) || b.size.x > 300f) continue;
                string n = mf.name.ToLower(), pn = mf.transform.parent ? mf.transform.parent.name.ToLower() : "";
                bool flat = pn.Contains("decal") || n.Contains("decal") || n.Contains("path") || n.Contains("fence") || n.Contains("grounds") || n.Contains("veg") || n.Contains("hedge");
                if (!flat) continue;
                var v = mf.sharedMesh.vertices; var l2w = mf.transform.localToWorldMatrix; var w2l = mf.transform.worldToLocalMatrix; bool any = false;
                for (int q = 0; q < v.Length; q++) { var wp = l2w.MultiplyPoint3x4(v[q]); float d = D(wp.x, wp.z); if (Mathf.Abs(d) < .01f) continue; wp.y += d; v[q] = w2l.MultiplyPoint3x4(wp); any = true; }
                if (!any) continue;
                var nm = Object.Instantiate(mf.sharedMesh); nm.name = mf.sharedMesh.name + "_floor"; nm.vertices = v; nm.RecalculateBounds();
                string pth = Dir + "/floor_" + mf.name.Replace(":", "_").Replace("/", "_") + "_" + meshes + ".asset"; AssetDatabase.DeleteAsset(pth); AssetDatabase.CreateAsset(nm, pth);
                mf.sharedMesh = nm; var mc = mf.GetComponent<MeshCollider>(); if (mc) mc.sharedMesh = nm; meshes++;
            }
            var trees = td.treeInstances; int tm = 0;
            for (int k = 0; k < trees.Length; k++)
            {
                var ti = trees[k]; float wx = tp.x + ti.position.x * td.size.x, wz = tp.z + ti.position.z * td.size.z; if (Mathf.Abs(D(wx, wz)) < .01f) continue;
                ti.position.y = td.GetInterpolatedHeight(ti.position.x, ti.position.z) / sy; trees[k] = ti; tm++;
            }
            td.treeInstances = trees;
            var grass = Object.FindFirstObjectByType<OnlyVolunteers.Map.W85.W85GrassRenderer>(FindObjectsInactive.Include); int gm = 0;
            if (grass && grass.data && grass.data.instances)
            {
                var bytes = (byte[])grass.data.instances.bytes.Clone();
                for (int o = 0; o + 32 <= bytes.Length; o += 32)
                {
                    float gx = System.BitConverter.ToSingle(bytes, o), gy = System.BitConverter.ToSingle(bytes, o + 4), gz = System.BitConverter.ToSingle(bytes, o + 8); float d = D(gx, gz); if (Mathf.Abs(d) < .01f) continue;
                    System.Buffer.BlockCopy(System.BitConverter.GetBytes(gy + d), 0, bytes, o + 4, 4); gm++;
                }
                string bp = Dir + "/Grass_W86_floor.bytes"; File.WriteAllBytes(bp, bytes); AssetDatabase.ImportAsset(bp, ImportAssetOptions.ForceUpdate);
                var nd = Object.Instantiate(grass.data); nd.instances = AssetDatabase.LoadAssetAtPath<TextAsset>(bp);
                string dpth = Dir + "/GrassData_W86_floor.asset"; AssetDatabase.DeleteAsset(dpth); AssetDatabase.CreateAsset(nd, dpth); grass.data = nd; EditorUtility.SetDirty(grass);
            }
            log.AppendLine($"valley floor: {changed} points flattened, {pinned} pinned under solid things, ground meshes followed {meshes}, trees {tm}, grass {gm}");
        }

        static void BuildValley(Transform root, int layer, StringBuilder log)
        {
            var old = root.Find("VadimValley"); if (old) Object.DestroyImmediate(old.gameObject);
            var parent = new GameObject("VadimValley").transform; parent.SetParent(root, false);
            var terrain = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var td = terrain.terrainData; var tp = terrain.transform.position;
            // surface of the river where the new course leaves the old one (from Fedya's water data)
            var wj = MiniJson.Parse(File.ReadAllText("Assets/OnlyVolunteers/Map/W85Build/Data/v02/water_v85.json")) as Dictionary<string, object>;
            var river = (Dictionary<string, object>)((List<object>)wj["bodies"]).First(o => (string)((Dictionary<string, object>)o)["id"] == "river");
            var oldAxis = ((List<object>)river["axis"]).Select(o => { var a = (List<object>)o; return new Vector2(System.Convert.ToSingle(a[0]), System.Convert.ToSingle(a[1])); }).ToArray();
            var surf = ((List<object>)river["surface_m"]).Select(o => System.Convert.ToSingle(o)).ToArray();
            int k0 = 0; for (int i = 1; i < oldAxis.Length; i++) if ((oldAxis[i] - ValleyRiver[1]).sqrMagnitude < (oldAxis[k0] - ValleyRiver[1]).sqrMagnitude) k0 = i;
            float s0 = surf[Mathf.Min(k0, surf.Length - 1)], total = 0f; for (int i = 1; i < ValleyRiver.Length; i++) total += (ValleyRiver[i] - ValleyRiver[i - 1]).magnitude;
            float Surf(float along) => along > total - 14f ? Mathf.Lerp(2.2f, .1f, Mathf.InverseLerp(total - 14f, total, along)) : Mathf.Lerp(s0, 2.2f, along / (total - 14f));
            var oldLower = oldAxis.Where(a => a.x > 584f && a.y < 312f).ToArray();
            var oldFill = new float[oldLower.Length];
            for (int q = 0; q < oldLower.Length; q++)
            {   // fill level of the old channel: the lower of its two banks 13 m to each side, 1 m under it
                var d = (oldLower[Mathf.Min(q + 1, oldLower.Length - 1)] - oldLower[Mathf.Max(q - 1, 0)]).normalized; var nrm = new Vector2(-d.y, d.x);
                float bl = terrain.SampleHeight(new Vector3(oldLower[q].x + nrm.x * 13f, 0, oldLower[q].y + nrm.y * 13f)), br = terrain.SampleHeight(new Vector3(oldLower[q].x - nrm.x * 13f, 0, oldLower[q].y - nrm.y * 13f));
                oldFill[q] = Mathf.Min(bl, br) + terrain.transform.position.y - 1f;
            }
            for (int pass = 0; pass < 4; pass++)
            {   // smooth along the channel: no steps between neighbouring points
                var f2 = (float[])oldFill.Clone();
                for (int q = 1; q + 1 < oldFill.Length; q++) f2[q] = (oldFill[q - 1] + oldFill[q] * 2f + oldFill[q + 1]) * .25f;
                oldFill = f2;
            }

            // 1. terrain: new channel and cliffs, the big ridge on the valley side, the medium ridge beyond, old gorge filled
            int R = td.heightmapResolution; float sx = td.size.x / (R - 1), sz = td.size.z / (R - 1), sy = td.size.y;
            var area = Rect.MinMaxRect(556f, 78f, 730f, 320f);
            int x0 = Mathf.FloorToInt((area.xMin - tp.x) / sx), x1 = Mathf.CeilToInt((area.xMax - tp.x) / sx), z0 = Mathf.FloorToInt((area.yMin - tp.z) / sz), z1 = Mathf.CeilToInt((area.yMax - tp.z) / sz);
            int W = x1 - x0 + 1, H = z1 - z0 + 1; var h = td.GetHeights(x0, z0, W, H); var orig = (float[,])h.Clone(); var pinned = new bool[H, W];
            int changed = 0;
            for (int j = 0; j < H; j++) for (int i = 0; i < W; i++)
            {
                var p = new Vector2(tp.x + (x0 + i) * sx, tp.z + (z0 + j) * sz);
                float y0 = tp.y + orig[j, i] * sy, y = y0;
                float dN = PolyInfo(p, ValleyRiver, out float along, out float side), sN = Surf(along);
                float dO = oldLower.Length > 1 ? PolyInfo(p, oldLower, out _, out _) : 1e9f;
                float coast = Smooth(Mathf.InverseLerp(88f, 112f, p.y)) * Smooth(Mathf.InverseLerp(292f, 256f, p.y));   // ridges come down to the sea in the south and to the bridge in the north
                bool west = side < 0f;                                                        // right of the downstream course = the valley side
                bool south = p.y < 292f;
                if (dN < 4.2f) { y = sN - 1.4f; pinned[j, i] = true; }
                else if (dN < 6f) { y = Mathf.Lerp(sN - 1.2f, sN + .6f, (dN - 4.2f) / 1.8f); pinned[j, i] = true; }
                else if (south && west)
                {   // big ridge: cliff to 27 m, crest ~7 m wide, steep drop to the valley floor at the new fence line
                    float crest = 27f + (Mathf.PerlinNoise(p.x * .05f, p.y * .05f) - .5f) * 4f;
                    float ridge = dN < 9f ? Mathf.Lerp(sN + .6f, crest, Smooth(Mathf.InverseLerp(6f, 9f, dN))) : dN < 16f ? crest : Mathf.Lerp(crest, y0, Smooth(Mathf.InverseLerp(16f, 21f, dN)));
                    if (dN < 21f) y = Mathf.Lerp(y0, ridge, coast);
                }
                else if (!west)
                {   // beyond the river (Vadim 25.10, 3rd): a narrow, high, ragged stone ridge along the river (a natural border), the flat
                    // field behind it, and the city beach carried on west to the river mouth in front of it
                    float w = p.y - EastWaterline(p.x);
                    float land = w < 0f ? Mathf.Min(y0, Mathf.Lerp(0f, -3f, Smooth(-w / 20f)))
                               : w < 30f ? Mathf.Lerp(.2f, 2.2f, w / 30f)
                               : Mathf.Lerp(2.2f, 7f, Smooth((w - 30f) / 40f));
                    float nose = Smooth(Mathf.InverseLerp(-10f, 16f, w)) * Smooth(Mathf.InverseLerp(298f, 272f, p.y));   // runs down to the sea at the end of the beach; ends at the bridge
                    float peaks = 1f - Mathf.Abs(Mathf.PerlinNoise(p.y * .03f, 5.3f) * 2f - 1f);                      // a row of summits
                    float crestD = 16f + (Mathf.PerlinNoise(p.y * .05f, 1.7f) - .5f) * 5f;                             // the crest line wanders
                    float hc = 15f + 9f * peaks;
                    float tri = Mathf.Clamp01(1f - Mathf.Abs(dN - crestD) / (dN < crestD ? crestD - 6f : 17f));        // straight flanks, a sharp crest
                    float bell = tri < .35f ? Smooth(tri / .35f) * .35f : tri;
                    float rag = (Mathf.PerlinNoise(p.x * .11f, p.y * .11f) - .5f) * 7f + (Mathf.PerlinNoise(p.x * .27f + 9f, p.y * .27f) - .5f) * 3f;   // broken rock
                    float spk = Mathf.Pow(1f - Mathf.Abs(Mathf.PerlinNoise(p.x * .045f + 2f, p.y * .032f) * 2f - 1f), 4f) * 6f * Mathf.PerlinNoise(p.y * .02f, 8.2f);   // a few pointed tops, uneven
                    float yy = land + Mathf.Max(0f, hc + rag + spk) * bell * nose;
                    if (bell * nose > .05f) pinned[j, i] = true;                                                  // no softening: keep it sharp
                    if (w > 0f) yy = Mathf.Max(Mathf.Lerp(sN + .6f, yy, Smooth(Mathf.InverseLerp(6f, 9f, dN))), sN + .6f - Mathf.Max(0f, dN - 6f) * .3f);   // the bank: never under the river
                    float fade = Smooth(Mathf.InverseLerp(318f, 304f, p.y)) * Smooth(Mathf.InverseLerp(730f, 712f, p.x));   // reaches past the old ridge's ends
                    y = Mathf.Lerp(y0, yy, fade);
                }
                if (Mathf.Abs(y - y0) > .02f) changed++;
                h[j, i] = Mathf.Clamp01((y - tp.y) / sy);
            }
            for (int pass = 0; pass < 3; pass++)
            {   // soften what changed (not the channel): three 3 x 3 passes
                var hb = (float[,])h.Clone();
                for (int j = 1; j < H - 1; j++) for (int i = 1; i < W - 1; i++)
                {
                    if (pinned[j, i] || Mathf.Abs(h[j, i] - orig[j, i]) * sy < .05f) continue; float s = 0f; for (int a = -1; a <= 1; a++) for (int b = -1; b <= 1; b++) s += h[j + a, i + b];
                    hb[j, i] = Mathf.Lerp(h[j, i], s / 9f, .6f);
                }
                h = hb;
            }
            td.SetHeights(x0, z0, h);
            {   // the plain between the new mountain and Downtown: bumps smoothed out (wide blur, faded in at the edges)
                var P = Rect.MinMaxRect(688f, 205f, 788f, 312f);
                int px0 = Mathf.FloorToInt((P.xMin - tp.x) / sx), px1 = Mathf.CeilToInt((P.xMax - tp.x) / sx), pz0 = Mathf.FloorToInt((P.yMin - tp.z) / sz), pz1 = Mathf.CeilToInt((P.yMax - tp.z) / sz);
                int PW = px1 - px0 + 1, PH = pz1 - pz0 + 1; var ph = td.GetHeights(px0, pz0, PW, PH); var pb = (float[,])ph.Clone();
                int rr = Mathf.RoundToInt(12f / sx);
                for (int pass = 0; pass < 2; pass++)
                {
                    var tmp = new float[PH, PW];
                    for (int j = 0; j < PH; j++) for (int i = 0; i < PW; i++) { float a = 0f; int n = 0; for (int k = -rr; k <= rr; k++) { int ii = Mathf.Clamp(i + k, 0, PW - 1); a += pb[j, ii]; n++; } tmp[j, i] = a / n; }
                    for (int j = 0; j < PH; j++) for (int i = 0; i < PW; i++) { float a = 0f; int n = 0; for (int k = -rr; k <= rr; k++) { int jj = Mathf.Clamp(j + k, 0, PH - 1); a += tmp[jj, i]; n++; } pb[j, i] = a / n; }
                }
                for (int j = 0; j < PH; j++) for (int i = 0; i < PW; i++)
                {
                    float wx = tp.x + (px0 + i) * sx, wz = tp.z + (pz0 + j) * sz;
                    float edge = Mathf.Min(Mathf.Min(wx - P.xMin, P.xMax - wx), Mathf.Min(wz - P.yMin, P.yMax - wz));
                    if (tp.y + ph[j, i] * sy < .5f) continue;                                   // the beach / water stay
                    ph[j, i] = Mathf.Lerp(ph[j, i], pb[j, i], .9f * Smooth(edge / 15f));
                }
                td.SetHeights(px0, pz0, ph);
            }
            FlattenValleyFloor(terrain, log);
            {   // the west end of the city beach too: plain sand from the water up to the field (no grass or dark patches mid-beach)
                int A = td.alphamapResolution; float ax = td.size.x / A, az = td.size.z / A; int L = td.alphamapLayers; var beachV = CityBeachSand(terrain);
                {
                    var B = Rect.MinMaxRect(612f, 80f, 760f, 215f);
                    int a0 = Mathf.FloorToInt((B.xMin - tp.x) / ax), a1 = Mathf.CeilToInt((B.xMax - tp.x) / ax), b0 = Mathf.FloorToInt((B.yMin - tp.z) / az), b1 = Mathf.CeilToInt((B.yMax - tp.z) / az);
                    var al = td.GetAlphamaps(a0, b0, a1 - a0, b1 - b0);
                    for (int j = 0; j < b1 - b0; j++) for (int i = 0; i < a1 - a0; i++)
                    {
                        float wx = tp.x + (a0 + i + .5f) * ax, wz = tp.z + (b0 + j + .5f) * az;
                        if (PolyInfo(new Vector2(wx, wz), ValleyRiver, out _, out float sb2) < 6f || sb2 < 0f) continue;
                        float hq = terrain.SampleHeight(new Vector3(wx, 0, wz)) + tp.y, wq = wz - EastWaterline(wx);
                        float be = BeachEdge(wx), k = (1f - Smooth(Mathf.InverseLerp(be - 5f, be + 5f, wq))) * (1f - Smooth(Mathf.InverseLerp(2.6f, 3.4f, hq))) * Smooth(Mathf.InverseLerp(760f, 735f, wx));
                        if (k <= 0f) continue;
                        for (int l = 0; l < L; l++) al[j, i, l] = Mathf.Lerp(al[j, i, l], beachV[0, 0, l], k);
                    }
                    td.SetAlphamaps(a0, b0, al);
                }
            }
            {   // terrain details (pebbles, reeds) that belonged to the old river and the old gorge: gone from the east side
                int DR = td.detailResolution, nd = 0; float dx = td.size.x / DR, dz = td.size.z / DR;
                int d0 = Mathf.FloorToInt((612f - tp.x) / dx), d1 = Mathf.CeilToInt((716f - tp.x) / dx), e0 = Mathf.FloorToInt((80f - tp.z) / dz), e1 = Mathf.CeilToInt((306f - tp.z) / dz);
                for (int layerD = 0; layerD < td.detailPrototypes.Length; layerD++)
                {
                    var dl = td.GetDetailLayer(d0, e0, d1 - d0, e1 - e0, layerD);
                    for (int j = 0; j < e1 - e0; j++) for (int i = 0; i < d1 - d0; i++)
                    {
                        if (dl[j, i] == 0) continue; var q = new Vector2(tp.x + (d0 + i + .5f) * dx, tp.z + (e0 + j + .5f) * dz);
                        if (PolyInfo(q, ValleyRiver, out _, out float sd3) < 5f || sd3 < 0f) continue;
                        dl[j, i] = 0; nd++;
                    }
                    td.SetDetailLayer(d0, e0, layerD, dl);
                }
                log.AppendLine($"valley east: {nd} detail cells cleared ({td.detailPrototypes.Length} detail layers)");
            }
            terrain.Flush();
            FillSea("Sea_fill_valley", Rect.MinMaxRect(596f, 60f, 716f, 170f), c => terrain.SampleHeight(new Vector3(c.x, 0, c.y)) + tp.y < .3f, log);
            {   // splat: rock on the steep new walls
                int A = td.alphamapResolution; float ax = td.size.x / A, az = td.size.z / A;
                int a0 = Mathf.FloorToInt((area.xMin - tp.x) / ax), a1 = Mathf.CeilToInt((area.xMax - tp.x) / ax), b0 = Mathf.FloorToInt((area.yMin - tp.z) / az), b1 = Mathf.CeilToInt((area.yMax - tp.z) / az);
                var al = td.GetAlphamaps(a0, b0, a1 - a0, b1 - b0); int L = td.alphamapLayers;
                var sandV = td.GetAlphamaps(Mathf.FloorToInt((715f - tp.x) / ax), Mathf.FloorToInt((172f - tp.z) / az), 1, 1);   // the city beach
                sandV = CityBeachSand(terrain);
                var fieldV = td.GetAlphamaps(Mathf.FloorToInt((748f - tp.x) / ax), Mathf.FloorToInt((262f - tp.z) / az), 1, 1);   // the field beyond, untouched
                log.AppendLine("valley beach sand: the city beach's own mix");
                for (int j = 0; j < b1 - b0; j++) for (int i = 0; i < a1 - a0; i++)
                {
                    float nx = (a0 + i + .5f) / A, nz = (b0 + j + .5f) / A; float st = td.GetSteepness(nx, nz);
                    var qe = new Vector2(tp.x + nx * td.size.x, tp.z + nz * td.size.z);
                    float dq = PolyInfo(qe, ValleyRiver, out _, out float sq);
                    bool eastQ = sq >= 0f && dq > 5f && qe.y < 318f && qe.x < 730f;
                    float wqe = qe.y - EastWaterline(qe.x), be = BeachEdge(qe.x);
                    float sd = eastQ ? (1f - Smooth(Mathf.InverseLerp(be - 5f, be + 5f, wqe))) * Smooth(Mathf.InverseLerp(745f, 730f, qe.x)) : 0f;
                    if (sd > 0f) { for (int l = 0; l < L; l++) al[j, i, l] = Mathf.Lerp(al[j, i, l], sandV[0, 0, l], sd); continue; }
                    var q = new Vector2(tp.x + nx * td.size.x, tp.z + nz * td.size.z);
                    int hi = Mathf.Clamp(Mathf.RoundToInt((q.x - tp.x) / sx) - x0, 0, W - 1), hj = Mathf.Clamp(Mathf.RoundToInt((q.y - tp.z) / sz) - z0, 0, H - 1);
                    bool reshaped = Mathf.Abs(h[hj, hi] - orig[hj, hi]) * sy > .5f && PolyInfo(q, ValleyRiver, out _, out _) > 5f;
                    if (eastQ)
                    {   // east field: the same grass as the field beyond, faded in from the edges (no painted rectangle)
                        float fk = Smooth(Mathf.InverseLerp(730f, 706f, q.x)) * Smooth(Mathf.InverseLerp(318f, 300f, q.y)) * Smooth(Mathf.InverseLerp(be + 3f, be + 9f, wqe));   // not on the beach
                        for (int l = 0; l < L; l++) al[j, i, l] = Mathf.Lerp(al[j, i, l], fieldV[0, 0, l], fk);
                    }
                    else if (reshaped)
                    {   // the new ridges and the filled old gorge: grass, worn on top, no old gorge gravel
                        float n = Mathf.PerlinNoise(q.x * .05f, q.y * .05f);
                        for (int l = 0; l < L; l++) al[j, i, l] = 0f; al[j, i, 0] = .45f + .3f * n; al[j, i, 1] = .55f - .3f * n;
                    }
                    float rock = Mathf.InverseLerp(38f, 52f, st);
                    if (eastQ && dq < 48f)
                    {   // the stone ridge: rock from 10 m up and on every steep bit, patches of grass in the hollows
                        float hq = td.GetInterpolatedHeight(nx, nz) + tp.y;
                        rock = Mathf.Max(rock, Mathf.Max(Smooth(Mathf.InverseLerp(10f, 14f, hq)), Mathf.InverseLerp(24f, 34f, st)) * (.7f + .3f * Mathf.PerlinNoise(qe.x * .2f, qe.y * .2f)));
                    }
                    if (rock <= 0f) continue;
                    for (int l = 0; l < L; l++) al[j, i, l] *= 1f - rock; al[j, i, 7] += rock;
                }
                td.SetAlphamaps(a0, b0, al);
            }
            float G(float x, float z) => terrain.SampleHeight(new Vector3(x, 0, z)) + tp.y;

            // 2. water: the old lower reach and the old waterfall go; a new reach along the new course, the waterfall at its mouth
            int cutW = 0;
            foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None))
            {
                if (mf.name != "Water_River_river" || !mf.sharedMesh || !mf.sharedMesh.isReadable) continue;
                var m = mf.sharedMesh; var v = m.vertices; var l2w = mf.transform.localToWorldMatrix; var nm = Object.Instantiate(m); nm.name = m.name + "_valley";
                for (int s = 0; s < m.subMeshCount; s++)
                {
                    var t = m.GetTriangles(s); var keep = new List<int>();
                    for (int k = 0; k < t.Length; k += 3)
                    {
                        var c = l2w.MultiplyPoint3x4((v[t[k]] + v[t[k + 1]] + v[t[k + 2]]) / 3f);
                        if (c.x > 578f && c.z < 315f) cutW++; else keep.AddRange(new[] { t[k], t[k + 1], t[k + 2] });
                    }
                    nm.SetTriangles(keep, s);
                }
                string pth = Dir + "/Water_River_river_valley.asset"; AssetDatabase.DeleteAsset(pth); AssetDatabase.CreateAsset(nm, pth); mf.sharedMesh = nm;
                var waterMat = mf.GetComponent<MeshRenderer>().sharedMaterial;
                var rp = new List<(Vector2 p, float y)>(); float acc = (ValleyRiver[1] - ValleyRiver[0]).magnitude + (ValleyRiver[2] - ValleyRiver[1]).magnitude;
                for (int i = 3; i < ValleyRiver.Length; i++)
                {
                    var a = ValleyRiver[i - 1]; var b = ValleyRiver[i]; float l = (b - a).magnitude; int n = Mathf.Max(1, Mathf.CeilToInt(l / 2f));
                    for (int k = (i == 3 ? 0 : 1); k <= n; k++) { var q = Vector2.Lerp(a, b, k / (float)n); rp.Add((q, Surf(acc + l * k / n) - .05f)); }
                    acc += l;
                }
                // (MakeRoad lifts its ribbon by 5 cm: the water sits at the surface)
                MakeRoad("Valley_river_new", rp, 7.4f, 6f, waterMat, parent, mf.gameObject.layer, null);
                var col = parent.Find("Valley_river_new")?.GetComponent<MeshCollider>(); if (col) Object.DestroyImmediate(col);
            }
            int moved = 0;
            foreach (var n in new[] { "Waterfall_waterfall_sea", "Foam_waterfall_sea", "Foam_waterfall_sea_outer", "FoamRing_waterfall_sea" })
            {
                var g = GameObject.Find(n); if (!g) continue;
                g.transform.position += new Vector3(ValleyRiver[ValleyRiver.Length - 1].x - 657f, -1f, ValleyRiver[ValleyRiver.Length - 1].y - 94f); moved++;
            }
            foreach (Transform tr in GameObject.Find("Water")?.transform ?? root)
                if (tr.name.StartsWith("Rock_") && tr.position.x > 640f && tr.position.z < 110f) tr.gameObject.SetActive(false);

            // 3. rocks: face triangles that no longer sit on the ground go; outcrops re-seated, the ones in the channel go
            int rockCut = 0, reseat = 0;
            foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None))
            {
                if (!mf.transform.parent || mf.transform.parent.name != "RockFaces" || !mf.sharedMesh || !mf.sharedMesh.isReadable) continue;
                var bnd = mf.GetComponent<Renderer>().bounds; if (!Rect.MinMaxRect(bnd.min.x, bnd.min.z, bnd.max.x, bnd.max.z).Overlaps(Rect.MinMaxRect(550f, 70f, 730f, 330f))) continue;
                var m = mf.sharedMesh; var v = m.vertices; var t = m.triangles; var keep = new List<int>(); var l2w = mf.transform.localToWorldMatrix;
                for (int k = 0; k < t.Length; k += 3)
                {
                    var c = l2w.MultiplyPoint3x4((v[t[k]] + v[t[k + 1]] + v[t[k + 2]]) / 3f);
                    float dc = PolyInfo(new Vector2(c.x, c.z), ValleyRiver, out _, out float sc);
                    bool bad = Rect.MinMaxRect(550f, 70f, 730f, 330f).Contains(new Vector2(c.x, c.z)) && Mathf.Abs(c.y - G(c.x, c.z)) > 1.2f
                            || area.Contains(new Vector2(c.x, c.z)) && (dc < 6f || sc >= 0f && c.z < 304f && c.x < 716f);
                    if (bad) rockCut++; else keep.AddRange(new[] { t[k], t[k + 1], t[k + 2] });
                }
                if (keep.Count == t.Length) continue;
                var nm = Object.Instantiate(m); nm.name = m.name + "_valley"; nm.SetTriangles(keep, 0); nm.RecalculateBounds();
                string pth = Dir + "/valley_" + mf.name + ".asset"; AssetDatabase.DeleteAsset(pth); AssetDatabase.CreateAsset(nm, pth); mf.sharedMesh = nm;
            }
            foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None))
            {   // the old river's foam decals lie on the field now (grey dashes): off
                if (!r.name.Contains("river_foam")) continue; var bc = r.bounds.center;
                if (bc.x > 625f && bc.x < 716f && bc.z > 80f && bc.z < 300f) r.gameObject.SetActive(false);
            }
            var oc = GameObject.Find("RockOutcrops");
            if (oc) foreach (Transform r in oc.transform)
            {
                var p = new Vector2(r.position.x, r.position.z); if (!area.Contains(p)) continue;
                if (PolyInfo(p, ValleyRiver, out _, out float so) < 7f || so >= 0f && p.y < 304f && p.x < 712f && G(p.x, p.y) < 12f) { r.gameObject.SetActive(false); continue; }   // east: rocks only up on the stone ridge
                var pos = r.position; pos.y = G(p.x, p.y) - .4f; r.position = pos; reseat++;
            }

            // 4. the valley's river side moves in: lab compound shifted, the fence / paths / lab road pulled to the new edge
            var dv = GameObject.Find("District_quiet_valley");
            var labRect = Rect.MinMaxRect(565f, 206f, 603f, 278f); int shifted = 0, warped = 0;
            float Warp(float x) => x <= 560f ? x : 560f + (x - 560f) * (ValleyEdgeNew - 560f) / (ValleyEdgeOld - 560f);
            void WarpMesh(MeshFilter mf, System.Func<float, float> fx)
            {
                var m = mf.sharedMesh; if (!m || !m.isReadable) return; var v = m.vertices; var l2w = mf.transform.localToWorldMatrix; var w2l = mf.transform.worldToLocalMatrix;
                for (int k = 0; k < v.Length; k++) { var wp = l2w.MultiplyPoint3x4(v[k]); wp.x = fx(wp.x); wp.y = Mathf.Max(wp.y, wp.y); v[k] = w2l.MultiplyPoint3x4(wp); }
                var nm = Object.Instantiate(m); nm.name = m.name + "_valley"; nm.vertices = v; nm.RecalculateBounds();
                string pth = Dir + "/valley_w_" + mf.name.Replace(":", "_") + ".asset"; AssetDatabase.DeleteAsset(pth); AssetDatabase.CreateAsset(nm, pth);
                mf.sharedMesh = nm; var mc = mf.GetComponent<MeshCollider>(); if (mc) mc.sharedMesh = nm; warped++;
            }
            if (dv)
                foreach (Transform c in dv.transform)
                {
                    string n = c.name;
                    var rs = c.GetComponentsInChildren<Renderer>(true); if (rs.Length == 0) continue; var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                    if (n.Contains("08_01_lab") || n.Contains("base5")) { c.position += new Vector3(ValleyShift, 0, 0); shifted++; }
                    else if (n.Contains("fence") || n.Contains("footpath") || n.Contains("grounds") || n.Contains("veg")) foreach (var mf in c.GetComponentsInChildren<MeshFilter>(true)) WarpMesh(mf, Warp);
                    else if (b.center.x > 565f && labRect.Contains(new Vector2(b.center.x, b.center.z))) { c.position += new Vector3(ValleyShift, 0, 0); shifted++; }
                }
            var spur = GameObject.Find("Road_valley_lab_spur");
            if (spur) foreach (var mf in spur.GetComponentsInChildren<MeshFilter>(true)) WarpMesh(mf, x => x - (-ValleyShift) * Smooth(Mathf.InverseLerp(548f, 557f, x)));
            foreach (var tr in root.GetComponentsInChildren<Transform>(true))
            {   // props by the lab (details, NPC spots): with the lab
                if (!tr.parent || tr.IsChildOf(parent) || dv && tr.IsChildOf(dv.transform)) continue;
                if (!(tr.parent.name.StartsWith("Details") || tr.parent.name.StartsWith("Patrol") || tr.parent.name.StartsWith("Marker"))) continue;
                if (labRect.Contains(new Vector2(tr.position.x, tr.position.z))) { tr.position += new Vector3(ValleyShift, 0, 0); shifted++; }
            }
            // 5. trees and grass that are now in the air / under ground / in the river
            var trees = td.treeInstances.ToList(); int tk = 0;
            for (int k = trees.Count - 1; k >= 0; k--)
            {
                var ti = trees[k]; var p = new Vector2(tp.x + ti.position.x * td.size.x, tp.z + ti.position.z * td.size.z); if (!area.Contains(p)) continue;
                if (PolyInfo(p, ValleyRiver, out _, out float st2) < 8f || td.GetSteepness(ti.position.x, ti.position.z) > 40f || st2 >= 0f && p.y - EastWaterline(p.x) < 46f) { trees.RemoveAt(k); tk++; continue; }
                ti.position.y = td.GetInterpolatedHeight(ti.position.x, ti.position.z) / sy; trees[k] = ti;
            }
            td.SetTreeInstances(trees.ToArray(), true);
            int gm = 0;
            var grass = Object.FindFirstObjectByType<OnlyVolunteers.Map.W85.W85GrassRenderer>(FindObjectsInactive.Include);
            if (grass && grass.data && grass.data.instances)
            {
                var bytes = (byte[])grass.data.instances.bytes.Clone();
                void Put(int o, float val) { var b4 = System.BitConverter.GetBytes(val); System.Buffer.BlockCopy(b4, 0, bytes, o, 4); }
                for (int o = 0; o + 32 <= bytes.Length; o += 32)
                {
                    float gx = System.BitConverter.ToSingle(bytes, o), gz = System.BitConverter.ToSingle(bytes, o + 8); var p = new Vector2(gx, gz); if (!area.Contains(p)) continue;
                    if (PolyInfo(p, ValleyRiver, out _, out float sg) < 6f || td.GetSteepness((gx - tp.x) / td.size.x, (gz - tp.z) / td.size.z) > 42f || sg >= 0f && gz - EastWaterline(gx) < 46f || sg >= 0f && gx < 704f && gz < 304f && G(gx, gz) > 8.5f
                        || oldLower.Length > 1 && PolyInfo(p, oldLower, out _, out _) < 8f) Put(o + 12, 0f);   // also the old river's reeds
                    else Put(o + 4, G(gx, gz)); gm++;
                }
                string bp = Dir + "/Grass_W86_valley.bytes"; File.WriteAllBytes(bp, bytes); AssetDatabase.ImportAsset(bp, ImportAssetOptions.ForceUpdate);
                var nd = Object.Instantiate(grass.data); nd.instances = AssetDatabase.LoadAssetAtPath<TextAsset>(bp);
                var ch = (OnlyVolunteers.Map.Grass.GrassPatchData24.Chunk[])nd.chunks.Clone();
                for (int c = 0; c < ch.Length; c++) if (area.Overlaps(new Rect(ch[c].centre.x - ch[c].extents.x, ch[c].centre.z - ch[c].extents.z, ch[c].extents.x * 2f, ch[c].extents.z * 2f))) ch[c].extents.y += 20f;
                nd.chunks = ch;
                string dpth = Dir + "/GrassData_W86_valley.asset"; AssetDatabase.DeleteAsset(dpth); AssetDatabase.CreateAsset(nd, dpth); grass.data = nd; EditorUtility.SetDirty(grass);
            }
            int skinTris = 0;
            {   // the east ridge reads as stone: a rock skin on it (Fedya's W86 rock-face technique and material)
                var rmat = AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Map/W85Build/Generated/v02/Materials/W86_rock_face.mat");
                bool On(int x, int z)
                {
                    var q = new Vector2(x + .5f, z + .5f); float d = PolyInfo(q, ValleyRiver, out _, out float sd); if (sd < 0f || d < 6.8f) return false;
                    float u = (q.x - tp.x) / td.size.x, v = (q.y - tp.z) / td.size.z, hq = td.GetInterpolatedHeight(u, v) + tp.y;
                    float wq = q.y - EastWaterline(q.x);
                    float baseY = wq < 0f ? 0f : wq < 30f ? Mathf.Lerp(.2f, 2.2f, wq / 30f) : Mathf.Lerp(2.2f, 7f, Smooth((wq - 30f) / 40f));   // the beach / field under the ridge
                    return d < 46f && (hq > Mathf.Max(.4f, baseY + 2.5f) || hq > baseY + .6f && td.GetSteepness(u, v) > 20f);   // the ridge down to where it flattens into the field / sand
                }
                int X0 = 612, X1 = 706, Z0 = 80, Z1 = 300; var on = new bool[X1 - X0 + 2, Z1 - Z0 + 2];
                for (int x = X0; x <= X1; x++) for (int z = Z0; z <= Z1; z++) on[x - X0, z - Z0] = On(x, z);
                bool IsOn(int x, int z) => x >= X0 && z >= Z0 && x <= X1 && z <= Z1 && on[x - X0, z - Z0];
                Vector3 Vt(int vx, int vz)
                {
                    bool inner = IsOn(vx - 1, vz - 1) && IsOn(vx, vz - 1) && IsOn(vx - 1, vz) && IsOn(vx, vz);
                    float u = (vx - tp.x) / td.size.x, v = (vz - tp.z) / td.size.z;
                    return new Vector3(vx, td.GetInterpolatedHeight(u, v) + tp.y, vz) + td.GetInterpolatedNormal(u, v) * (inner ? .12f : -.25f);
                }
                var sv = new List<Vector3>(); var suv = new List<Vector2>(); var st3 = new List<int>();
                void Tri(Vector3 a1, Vector3 b1, Vector3 c1)
                {
                    var n = Vector3.Cross(b1 - a1, c1 - a1); float ax = Mathf.Abs(n.x), ay = Mathf.Abs(n.y), az = Mathf.Abs(n.z);
                    Vector2 Uv(Vector3 q) => ay >= ax && ay >= az ? new Vector2(q.x, q.z) / 7f : ax >= az ? new Vector2(q.z, q.y) / 7f : new Vector2(q.x, q.y) / 7f;
                    if (n.y < 0) { var t0 = b1; b1 = c1; c1 = t0; }
                    int k = sv.Count; sv.Add(a1); sv.Add(b1); sv.Add(c1); suv.Add(Uv(a1)); suv.Add(Uv(b1)); suv.Add(Uv(c1)); st3.Add(k); st3.Add(k + 1); st3.Add(k + 2);
                }
                for (int x = X0; x <= X1; x++) for (int z = Z0; z <= Z1; z++)
                {
                    if (!IsOn(x, z)) continue;
                    Vector3 p00 = Vt(x, z), p10 = Vt(x + 1, z), p01 = Vt(x, z + 1), p11 = Vt(x + 1, z + 1);
                    Tri(p00, p01, p11); Tri(p00, p11, p10); skinTris += 2;
                }
                if (sv.Count > 0 && rmat)
                {
                    var m = new Mesh { name = "RockSkin_valley_east", indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 }; m.SetVertices(sv); m.SetUVs(0, suv); m.SetTriangles(st3, 0); m.RecalculateNormals(); m.RecalculateBounds();
                    string pth = Dir + "/RockSkin_valley_east.asset"; AssetDatabase.DeleteAsset(pth); AssetDatabase.CreateAsset(m, pth);
                    var go = new GameObject("RockSkin_valley_east"); go.transform.SetParent(parent, false); go.layer = layer; go.isStatic = true;
                    go.AddComponent<MeshFilter>().sharedMesh = m; var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = rmat; mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                }
            }
            terrain.Flush(); EditorUtility.SetDirty(td);
            log.AppendLine($"valley: {changed} terrain points, rock skin {skinTris} tris, old water tris cut {cutW}, waterfall parts moved {moved}, rock tris cut {rockCut}, outcrops re-seated {reseat}, lab compound pieces shifted {shifted}, meshes warped {warped}, trees removed {tk}, grass blades {gm}");
        }


        static void BuildElite(Transform root, int layer, StringBuilder log)
        {   // Vadim 25.10: the Elite marina under the cliff. A sand strip along the cliff foot from the south beach past the three
            // piers (the piers start on it, the cove loungers come down onto it from the cliff face); the land bumps that stuck
            // out of the sea under the yachts and the two little islands go under water; yachts by the beach moved off the sand.
            var terrain = GameObject.Find("Terrain_W85_v02").GetComponent<Terrain>(); var td = terrain.terrainData; var tp = terrain.transform.position;
            int R = td.heightmapResolution; float sx = td.size.x / (R - 1), sz = td.size.z / (R - 1), sy = td.size.y;
            float G(float x, float z) => terrain.SampleHeight(new Vector3(x, 0, z)) + tp.y;
            var area = Rect.MinMaxRect(1495f, 222f, 1615f, 362f);
            // the cliff foot: going west from the sea, where the ground first reaches 3 m (clamped, smoothed along the shore)
            var foot = new float[121];
            for (int k = 0; k <= 120; k++)
            {
                float z = 225f + k, fx = 1513f;
                for (float x = 1535f; x >= 1495f; x -= .5f) if (G(x, z) >= 3f) { fx = x; break; }
                foot[k] = Mathf.Clamp(fx, 1513f, 1522f);
            }
            var fs = new float[121]; for (int k = 0; k <= 120; k++) { float a = 0f; int n = 0; for (int q = -5; q <= 5; q++) { a += foot[Mathf.Clamp(k + q, 0, 120)]; n++; } fs[k] = a / n; }
            float Foot(float z) { float t = Mathf.Clamp(z - 225f, 0f, 120f); int k = Mathf.Min((int)t, 119); return Mathf.Lerp(fs[k], fs[k + 1], t - k); }
            float Wob(float z) => (Mathf.PerlinNoise(z * .07f, 3.1f) - .5f) * 2f;
            float Wid(float z) => Mathf.Max(0f, 17f * Smooth((348f - z) / 88f) + Wob(z) * Smooth((338f - z) / 30f));   // the south beach carried on, narrowing into the cliff
            float Band(float z) => Smooth(Mathf.InverseLerp(220f, 246f, z)) * Smooth(Mathf.InverseLerp(350f, 334f, z));
            float Flat(float z) => Mathf.Max(Wid(z) - 4f, 0f);
            float WL(float z) => Foot(z) + Wid(z) - .7f;                                       // the waterline
            const float top = 1.15f;                                                             // one level with the pier decks (1.2)

            // what moves: the piers start on the flat sand (decks flush with it), their yachts with them; the loungers in a row under the cliff
            var de = GameObject.Find("District_elite"); int piers = 0;
            var tmpl = new Transform[0]; var offs = new (Vector3 d, float up)[0];
            if (de)
            {
                float Root(float z) => WL(z) - .5f;                                                // the pier starts where the sand ends (Vadim 25.10)
                var pierDx = new Dictionary<string, float> { ["P1"] = Root(304f) - 1518f, ["P2"] = Root(278.5f) - 1518f, ["P3"] = Root(256f) - 1517f };
                foreach (Transform c in de.transform)
                    foreach (var kv in pierDx) if (c.name.EndsWith("07-pier-" + kv.Key)) { c.position += new Vector3(kv.Value, 0, 0); piers++; }
                void Yacht(string n, float dx) { var t = de.transform.Find(n); if (t) t.position += new Vector3(dx, 0, 0); }
                Yacht("07-yacht0", WL(298f) + 4f - 1521f);
                var y3 = de.transform.Find("07-yacht3");                                           // left (south) of P2 like the others, not on its north side
                if (y3) y3.position += new Vector3(WL(272f) + 5f - 1529f, 0, 272f - 285.5f);
                Yacht("07-yacht1", pierDx["P2"]); Yacht("07-yacht2", pierDx["P2"]); Yacht("07-yacht4", pierDx["P3"]);
                var y2 = de.transform.Find("07-yacht2"); if (y2) y2.position += new Vector3(0, 0, -3.5f);   // yachts 1 and 2 overlapped by 1.5 m
                tmpl = new[] { "07-cove-umbrella0", "07-cove-lounger00", "07-cove-lounger01" }.Select(n => de.transform.Find(n)).Where(t => t).ToArray();
                if (tmpl.Length == 3) offs = tmpl.Select(t => (t.position - tmpl[0].position, t.position.y - G(t.position.x, t.position.z))).ToArray();
            }

            // 1. terrain
            int x0 = Mathf.FloorToInt((area.xMin - tp.x) / sx), x1 = Mathf.CeilToInt((area.xMax - tp.x) / sx), z0 = Mathf.FloorToInt((area.yMin - tp.z) / sz), z1 = Mathf.CeilToInt((area.yMax - tp.z) / sz);
            int W = x1 - x0 + 1, H = z1 - z0 + 1; var h = td.GetHeights(x0, z0, W, H); var orig = (float[,])h.Clone(); int changed = 0;
            for (int j = 0; j < H; j++) for (int i = 0; i < W; i++)
            {
                float x = tp.x + (x0 + i) * sx, z = tp.z + (z0 + j) * sz, y0 = tp.y + h[j, i] * sy, y = y0;
                float edge = Smooth(Mathf.Min(Mathf.Min(x - area.xMin, area.xMax - x), Mathf.Min(z - area.yMin, area.yMax - z)) / 10f);
                float u = x - Foot(z), b = Band(z), wide = Wid(z), flat = Flat(z);
                float sea0 = Mathf.Lerp(24f, wide + 4f, b);
                float bed = -1.6f - 2.6f * Smooth((u - sea0) / 25f);
                if (u >= -3f && u < 0f) y = Mathf.Lerp(y0, Mathf.Min(y0, Mathf.Lerp(top, y0, Smooth(-u / 3f))), b);                    // the cliff toe meets the sand
                else if (u >= 0f && u <= wide + 4f)                                                                                     // flat sand, then down into the water
                {
                    float prof = u <= flat ? top : Mathf.Lerp(top, -1.6f, Smooth((u - flat) / 8f));
                    y = Mathf.Lerp(y0, prof, b);
                    if (u > flat && b > 0f) y = Mathf.Min(y, prof + .3f);                                                            // no old sand spikes left in the shallows
                }
                if (u > sea0) y = Mathf.Min(y, Mathf.Lerp(y0, Mathf.Min(y0, bed), edge));
                if (z >= 222f && u < wide - 3f && y < .5f) y = Mathf.Lerp(y, .5f, b);                                                    // no sea puddles on the beach
                if (u > -4f && u < Mathf.Min(3f, flat))
                {   // scree at the cliff foot: the rock runs down into the sand on a slope, not a 90-degree wall
                    float apron = top + Mathf.Max(0f, 2.5f - u) * 1.05f + (Mathf.PerlinNoise(x * .3f, z * .3f) - .5f) * .5f;
                    y = Mathf.Lerp(y, Mathf.Max(y, apron), b);
                }                                              // the marina floor: nothing above the water
                if (Mathf.Abs(y - y0) > .02f) changed++;
                h[j, i] = Mathf.Clamp01((y - tp.y) / sy);
            }
            for (int pass = 0; pass < 2; pass++)
                for (int j = 1; j < H - 1; j++) for (int i = 1; i < W - 1; i++)
                {   // single-cell spikes near the water line (old sand cones in the shallows) go
                    float yc = tp.y + h[j, i] * sy; if (yc < -2.5f || yc > 2.5f) continue;
                    float avg = (h[j - 1, i] + h[j + 1, i] + h[j, i - 1] + h[j, i + 1] + h[j - 1, i - 1] + h[j - 1, i + 1] + h[j + 1, i - 1] + h[j + 1, i + 1]) / 8f;
                    if ((h[j, i] - avg) * sy > .3f) { h[j, i] = avg + .3f / sy; changed++; }
                }
            td.SetHeights(x0, z0, h);
            {   // splat: white sand like the south beach on everything that changed
                int A = td.alphamapResolution; float ax = td.size.x / A, az = td.size.z / A; int L = td.alphamapLayers;
                var sand = td.GetAlphamaps(Mathf.FloorToInt((1508f - tp.x) / ax), Mathf.FloorToInt((228f - tp.z) / az), 1, 1);
                int a0 = Mathf.FloorToInt((area.xMin - tp.x) / ax), a1 = Mathf.CeilToInt((area.xMax - tp.x) / ax), b0 = Mathf.FloorToInt((area.yMin - tp.z) / az), b1 = Mathf.CeilToInt((area.yMax - tp.z) / az);
                var al = td.GetAlphamaps(a0, b0, a1 - a0, b1 - b0);
                for (int j = 0; j < b1 - b0; j++) for (int i = 0; i < a1 - a0; i++)
                {
                    float wx = tp.x + (a0 + i + .5f) * ax, wz = tp.z + (b0 + j + .5f) * az;
                    int hi = Mathf.Clamp(Mathf.RoundToInt((wx - tp.x) / sx) - x0, 0, W - 1), hj = Mathf.Clamp(Mathf.RoundToInt((wz - tp.z) / sz) - z0, 0, H - 1);
                    float st = td.GetSteepness((wx - tp.x) / td.size.x, (wz - tp.z) / td.size.z), hq = tp.y + h[hj, hi] * sy;
                    float rk = hq > 1.6f && wx < 1545f ? Mathf.InverseLerp(30f, 42f, st) : 0f;                                    // the cliff is rock, not sand
                    if (rk > 0f) { for (int l = 0; l < L; l++) al[j, i, l] *= 1f - rk; al[j, i, 7] += rk; continue; }
                    if (Mathf.Abs(h[hj, hi] - orig[hj, hi]) * sy < .25f) continue;
                    for (int l = 0; l < L; l++) al[j, i, l] = sand[0, 0, l];
                }
                td.SetAlphamaps(a0, b0, al);
            }
            {   // the mountain stays rock down to the beach: no sand painted up its lower slopes
                int A = td.alphamapResolution; float ax = td.size.x / A, az = td.size.z / A; int L = td.alphamapLayers;
                var M = Rect.MinMaxRect(1430f, 185f, 1545f, 362f);
                int a0 = Mathf.FloorToInt((M.xMin - tp.x) / ax), a1 = Mathf.CeilToInt((M.xMax - tp.x) / ax), b0 = Mathf.FloorToInt((M.yMin - tp.z) / az), b1 = Mathf.CeilToInt((M.yMax - tp.z) / az);
                var al = td.GetAlphamaps(a0, b0, a1 - a0, b1 - b0);
                for (int j = 0; j < b1 - b0; j++) for (int i = 0; i < a1 - a0; i++)
                {
                    float nx = (a0 + i + .5f) / A, nz = (b0 + j + .5f) / A, st = td.GetSteepness(nx, nz), hq = td.GetInterpolatedHeight(nx, nz) + tp.y;
                    float wzq = tp.z + nz * td.size.z, hill = wzq > 228f || hq > 8f ? 1f : 0f;                                                // the south beach dunes stay sand
                    float rk = Mathf.Max(hill * Mathf.InverseLerp(10f, 16f, st) * Mathf.InverseLerp(1.6f, 2.6f, hq) * Mathf.InverseLerp(39.5f, 37.5f, hq),
                                         Mathf.InverseLerp(25f, 32f, st) * Mathf.InverseLerp(1.3f, 1.8f, hq)); if (rk <= 0f) continue;   // the cliff is stone, one colour
                    for (int l = 0; l < L; l++) al[j, i, l] *= 1f - rk; al[j, i, 7] += rk;
                }
                td.SetAlphamaps(a0, b0, al);
            }
            terrain.Flush();

            // 2. beach rules (Vadim 25.10): loungers in pairs side by side, feet to the sea, an umbrella at the head between them,
            //    groups evenly along the beach with only a little jitter; a few palms at the cliff foot
            int lg = 0; var rnd = new System.Random(25);
            float J(float a) => ((float)rnd.NextDouble() * 2f - 1f) * a;
            if (tmpl.Length == 3)
            {
                foreach (var (gz, k) in new[] { 236f, 243f, 263f, 270f, 287f, 294f }.Select((zz, kk) => (zz, kk)))
                {
                    float fx = Foot(gz);
                    for (int q = 0; q < 3; q++)
                    {
                        string nm = q == 0 ? "07-cove-umbrella" + k : "07-cove-lounger" + k + (q - 1);
                        var t = de.transform.Find(nm); if (!t) { t = Object.Instantiate(tmpl[q].gameObject, de.transform).transform; t.name = nm; }
                        var pos = q == 0 ? new Vector3(fx + 3.0f + J(.1f), 0, gz + J(.1f)) : new Vector3(fx + 4.4f + J(.15f), 0, gz + (q == 1 ? -.95f : .95f) + J(.1f));
                        pos.y = G(pos.x, pos.z) + offs[q].up; t.position = pos;
                        if (q == 0) t.rotation = tmpl[0].rotation; else { FaceSea(t, Vector2.right); t.rotation *= Quaternion.Euler(0, J(3f), 0); }
                        lg++;
                    }
                }
                // Fedya's loungers on the south beach (09e) were scattered over the dune: in pairs, feet downhill to the water, each pair with an umbrella
                var db = GameObject.Find("District_beach");
                if (db)
                    for (int k = 0; k < 10; k++)
                    {
                        var a = db.transform.Find($"09e-lounger-0{k}-0"); var b2 = db.transform.Find($"09e-lounger-0{k}-1"); if (!a) continue;
                        var at = new Vector2(a.position.x, a.position.z);
                        var grad = new Vector2(G(at.x + 3f, at.y) - G(at.x - 3f, at.y), G(at.x, at.y + 3f) - G(at.x, at.y - 3f));
                        var sea = grad.sqrMagnitude > 1e-4f ? -grad.normalized : new Vector2(.4f, -.9f).normalized; var along = new Vector2(-sea.y, sea.x);
                        float up0 = a.position.y - G(at.x, at.y);
                        foreach (var (t, side) in new[] { (a, -1f), (b2, 1f) })
                        {
                            if (!t) continue; var c = at + along * (.95f * side);
                            t.position = new Vector3(c.x, G(c.x, c.y) + up0, c.y); FaceSea(t, sea); lg++;
                        }
                        var u = de.transform.Find("07-beach-umbrella" + k); if (!u) { u = Object.Instantiate(tmpl[0].gameObject, de.transform).transform; u.name = "07-beach-umbrella" + k; }
                        var uc = at - sea * 1.4f; u.position = new Vector3(uc.x, G(uc.x, uc.y) + offs[0].up, uc.y); u.rotation = tmpl[0].rotation; lg++;
                    }
            }
            {   // palms at the cliff foot, clear of the lounger groups and the pier roots
                var protos = td.treePrototypes; var palmIdx = Enumerable.Range(0, protos.Length).Where(k => protos[k].prefab && protos[k].prefab.name.ToLower().Contains("palm")).ToArray();
                if (palmIdx.Length > 0)
                {
                    var ptrees = td.treeInstances.ToList(); int n = 0;
                    foreach (var pz in new[] { 231f, 252.5f, 278.5f, 300f })
                    {
                        float px = Foot(pz) + 1.4f; var ti = new TreeInstance
                        {
                            position = new Vector3((px - tp.x) / td.size.x, (G(px, pz) - tp.y) / sy, (pz - tp.z) / td.size.z),
                            prototypeIndex = palmIdx[n % palmIdx.Length], widthScale = .95f + .1f * (n % 2), heightScale = .9f + .08f * n, rotation = n * 1.7f,
                            color = Color.white, lightmapColor = Color.white
                        };
                        ptrees.Add(ti); n++;
                    }
                    td.SetTreeInstances(ptrees.ToArray(), true);
                }
            }

            // 3. rock faces that no longer sit on the ground (the toe and the bumps out in the water) go; outcrops re-seated
            int rockCut = 0, reseat = 0;
            foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None))
            {
                if (!mf.transform.parent || mf.transform.parent.name != "RockFaces" || !mf.sharedMesh || !mf.sharedMesh.isReadable) continue;
                var bnd = mf.GetComponent<Renderer>().bounds; if (!Rect.MinMaxRect(bnd.min.x, bnd.min.z, bnd.max.x, bnd.max.z).Overlaps(area)) continue;
                var m = mf.sharedMesh; var v = m.vertices; var t = m.triangles; var keep = new List<int>(); var l2w = mf.transform.localToWorldMatrix;
                for (int k = 0; k < t.Length; k += 3)
                {
                    var c = l2w.MultiplyPoint3x4((v[t[k]] + v[t[k + 1]] + v[t[k + 2]]) / 3f);
                    bool bad = area.Contains(new Vector2(c.x, c.z)) && c.x - Foot(c.z) > -3.5f && Mathf.Abs(c.y - G(c.x, c.z)) > 1f
                            || c.z > 222f && c.z < 345f && c.x > 1490f && c.y < 7.5f && c.x - Foot(c.z) > -7f;   // the low wall: the scree slope shows instead                    // shards poking out of the sand
                    if (bad) rockCut++; else keep.AddRange(new[] { t[k], t[k + 1], t[k + 2] });
                }
                if (keep.Count == t.Length) continue;
                var nm = Object.Instantiate(m); nm.name = m.name + "_elite"; nm.SetTriangles(keep, 0); nm.RecalculateBounds();
                string pth = Dir + "/elite_" + mf.name + ".asset"; AssetDatabase.DeleteAsset(pth); AssetDatabase.CreateAsset(nm, pth); mf.sharedMesh = nm;
                var mc = mf.GetComponent<MeshCollider>(); if (mc) mc.sharedMesh = nm;
            }
            var oc = GameObject.Find("RockOutcrops");
            if (oc) foreach (Transform r in oc.transform)
            {
                var p = r.position; if (!Rect.MinMaxRect(1430f, 185f, 1615f, 362f).Contains(new Vector2(p.x, p.z))) continue;
                float g = G(p.x, p.z); if (g < 3.5f) { r.gameObject.SetActive(false); continue; }                                  // no boulders lying on the sand
                if (p.x - Foot(p.z) < -2f) continue;
                p.y = g - .4f; r.position = p; reseat++;
            }

            // 4. trees and grass over the water / on the reshaped strip
            var trees = td.treeInstances.ToList(); int tk = 0;
            for (int k = trees.Count - 1; k >= 0; k--)
            {
                var ti = trees[k]; var p = new Vector2(tp.x + ti.position.x * td.size.x, tp.z + ti.position.z * td.size.z); if (!area.Contains(p) || p.x - Foot(p.y) < -3f) continue;
                if (G(p.x, p.y) < .5f) { trees.RemoveAt(k); tk++; continue; }
                ti.position.y = td.GetInterpolatedHeight(ti.position.x, ti.position.z) / sy; trees[k] = ti;
            }
            td.SetTreeInstances(trees.ToArray(), true);
            int gm = 0;
            var grass = Object.FindFirstObjectByType<OnlyVolunteers.Map.W85.W85GrassRenderer>(FindObjectsInactive.Include);
            if (grass && grass.data && grass.data.instances)
            {
                var bytes = (byte[])grass.data.instances.bytes.Clone();
                void Put(int o, float val) { var b4 = System.BitConverter.GetBytes(val); System.Buffer.BlockCopy(b4, 0, bytes, o, 4); }
                for (int o = 0; o + 32 <= bytes.Length; o += 32)
                {
                    float gx = System.BitConverter.ToSingle(bytes, o), gz = System.BitConverter.ToSingle(bytes, o + 8); if (!area.Contains(new Vector2(gx, gz)) || gx - Foot(gz) < -3f) continue;
                    Put(o + 12, 0f); gm++;                                                                                              // sand / water: no grass
                }
                string bp = Dir + "/Grass_W86_elite.bytes"; File.WriteAllBytes(bp, bytes); AssetDatabase.ImportAsset(bp, ImportAssetOptions.ForceUpdate);
                var nd = Object.Instantiate(grass.data); nd.instances = AssetDatabase.LoadAssetAtPath<TextAsset>(bp);
                string dpth = Dir + "/GrassData_W86_elite.asset"; AssetDatabase.DeleteAsset(dpth); AssetDatabase.CreateAsset(nd, dpth); grass.data = nd; EditorUtility.SetDirty(grass);
            }
            EditorUtility.SetDirty(td);
            int eskin = SkinOver("RockSkin_elite_foot", new RectInt(1488, 222, 60, 124), (x, z, hq, st) => hq > 1.4f && hq < 7.6f && st > 22f, root, layer);   // the low band where the old faces were cut
            log.AppendLine($"elite foot rock skin {eskin} tris");
            log.AppendLine($"elite marina: {changed} terrain points, piers moved {piers}, lounger pieces {lg}, rock tris cut {rockCut}, outcrops re-seated {reseat}, trees removed {tk}, grass blades hidden {gm}; waterline z250 {WL(250):0.0} z278 {WL(278):0.0} z304 {WL(304):0.0} z325 {WL(325):0.0}");
        }

        public static void EliteOnly()
        {
            var scene = EditorSceneManager.OpenScene(Scene); var log = new StringBuilder();
            var root = GameObject.Find("Map_W85_v02").transform; int layer = 0;
            BuildElite(root, layer, log);
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            File.WriteAllText(@"C:\Users\chern_0eqkb03\VolunteersBuilds\elite_apply.txt", log.ToString());
        }

        public static void ValleyOnly()
        {
            var scene = EditorSceneManager.OpenScene(Scene); var log = new StringBuilder();
            var root = GameObject.Find("Map_W85_v02").transform; int layer = 0;
            foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None)) if (r.name == "Road_serpentine_view_b_v3") layer = r.gameObject.layer;
            BuildValley(root, layer, log);
            AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false; Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("VCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.fieldOfView = 60; cam.clearFlags = CameraClearFlags.Skybox;
            string D = @"C:\Users\chern_0eqkb03\VolunteersBuilds\";
            go.transform.position = new Vector3(555, 70, 360); go.transform.LookAt(new Vector3(585, 5, 200)); Shot(cam, 1000, 600, D + "valley_view.png");
            cam.orthographic = true; cam.orthographicSize = 140; cam.aspect = 300f / 280f; go.transform.position = new Vector3(580, 400, 210); go.transform.rotation = Quaternion.Euler(90, 0, 0);
            Shot(cam, 1000, 933, D + "valley_top_new.png");
            Object.DestroyImmediate(go);
            File.WriteAllText(D + "valley_apply.txt", log.ToString());
        }

        static Material RetainingMaterial(Material template)
        {
            string path = Dir + "/Wall_retaining_concrete.mat";
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/OnlyVolunteers/Art/MapTextures_W86/T1/Textures/T1_concrete_bridge_albedo.png");
            var m = template ? new Material(template) : new Material(Shader.Find("Universal Render Pipeline/Lit"));
            m.name = "Wall_retaining_concrete";
            foreach (var p in new[] { "_BaseMap", "_MainTex" }) if (m.HasProperty(p)) { m.SetTexture(p, tex); m.SetTextureScale(p, Vector2.one); }
            foreach (var p in new[] { "_BumpMap", "_DetailAlbedoMap", "_DetailNormalMap", "_EmissionMap" }) if (m.HasProperty(p)) m.SetTexture(p, null);
            m.DisableKeyword("_NORMALMAP"); m.DisableKeyword("_EMISSION");
            foreach (var p in new[] { "_BaseColor", "_Color" }) if (m.HasProperty(p)) m.SetColor(p, new Color(.88f, .88f, .87f)); // Vadim's pick Е: bridge concrete
            if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", .08f);
            AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(m, path);
            return m;
        }

        /// <summary>Concrete retaining walls (Vadim's pick, GPT variant 5) on both sides of the serpentine and the spur, standing at the
        /// shoulder edge in front of the earth walls, as high as those (+0.25 m), with a cap; open where the spur leaves.</summary>
        static void RouteWalls(List<S> roads, Material mat, Transform parent, int layer, StringBuilder log)
        {
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>(); float metres = 0f;
            const float th = .5f, cap = .15f, tile = 4f;
            foreach (int id in new[] { 1, 3 })
                foreach (float side in new[] { 1f, -1f })
                {
                    float acc = 0f; S prev = default; bool has = false;
                    foreach (var q in roads)
                    {
                        if (q.road != id) continue;
                        bool open = q.wall < .4f;
                        var basePt = q.p + q.right * side * (q.half + .1f);
                        foreach (var o in roads) if (o.road != id && (o.road == 1 || o.road == 3) && (o.p - basePt).magnitude < o.half + 1.5f) { open = true; break; }
                        if (open) { has = false; continue; }
                        if (has)
                        {
                            Vector3 P(S s0, float off, float yy) { var pp = s0.p + s0.right * side * off; return new Vector3(pp.x, yy, pp.y); }
                            float l = (q.p - prev.p).magnitude, a0 = prev.half + .1f, a1 = a0 + th;
                            float b0 = prev.y - .6f, b1 = q.y - .6f, t0 = prev.y + prev.wall + .25f, t1 = q.y + q.wall + .25f;
                            var inward = new Vector3(-q.right.x, 0, -q.right.y) * side;
                            // face to the road, top, back
                            Quad(v, uv, t, P(prev, a0, b0), P(q, a0, b1), P(q, a0, t1), P(prev, a0, t0), inward, tile);
                            int k = uv.Count - 4; uv[k] = new Vector2(acc / tile, b0 / tile); uv[k + 1] = new Vector2((acc + l) / tile, b1 / tile); uv[k + 2] = new Vector2((acc + l) / tile, t1 / tile); uv[k + 3] = new Vector2(acc / tile, t0 / tile);
                            Quad(v, uv, t, P(prev, a0 - .1f, t0 + cap), P(q, a0 - .1f, t1 + cap), P(q, a1 + .1f, t1 + cap), P(prev, a1 + .1f, t0 + cap), Vector3.up, 1f);
                            Quad(v, uv, t, P(prev, a0 - .1f, t0), P(q, a0 - .1f, t1), P(q, a0 - .1f, t1 + cap), P(prev, a0 - .1f, t0 + cap), inward, 1f);
                            Quad(v, uv, t, P(prev, a1, b0), P(q, a1, b1), P(q, a1, t1), P(prev, a1, t0), -inward, tile);
                            metres += l; acc += l;
                        }
                        prev = q; has = true;
                    }
                }
            if (v.Count > 0) Go("Wall_route_v1", parent, Save("Wall_route_v1", v, uv, t), mat, layer, true);
            log.AppendLine($"route walls: {metres:0} m of concrete wall");
        }

        /// <summary>A retaining wall along the foot of the hill over Downtown's north street, open for the tunnel approach and the
        /// serpentine; at least 2.6 m over the sidewalk, as high as the slope behind it.</summary>
        static void FootWall(Terrain terrain, Vector3 tp, Material mat, Transform parent, int layer, StringBuilder log)
        {
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>(); float metres = 0f;
            const float z = 523.5f, th = .6f, cap = .15f, tile = 4f;
            var gaps = new[] { new Vector2(817f, 843f), new Vector2(1031f, 1057f) };
            float H(float x) => terrain.SampleHeight(new Vector3(x, 0, z + 2.5f)) + tp.y;
            for (float x = 792f; x < 1150f; x += 2f)
            {
                float x1 = Mathf.Min(x + 2f, 1150f);
                if (gaps.Any(g => x1 > g.x && x < g.y)) continue;
                float b = 4.6f, t0 = Mathf.Max(H(x) + .3f, 7.6f), t1 = Mathf.Max(H(x1) + .3f, 7.6f);
                Vector3 A(float xx, float zz, float yy) => new Vector3(xx, yy, zz);
                Quad(v, uv, t, A(x, z, b), A(x1, z, b), A(x1, z, t1), A(x, z, t0), Vector3.back, tile);
                int k = uv.Count - 4; uv[k] = new Vector2(x / tile, b / tile); uv[k + 1] = new Vector2(x1 / tile, b / tile); uv[k + 2] = new Vector2(x1 / tile, t1 / tile); uv[k + 3] = new Vector2(x / tile, t0 / tile);
                Quad(v, uv, t, A(x, z - .1f, t0 + cap), A(x1, z - .1f, t1 + cap), A(x1, z + th + .1f, t1 + cap), A(x, z + th + .1f, t0 + cap), Vector3.up, 1f);
                Quad(v, uv, t, A(x, z - .1f, t0), A(x1, z - .1f, t1), A(x1, z - .1f, t1 + cap), A(x, z - .1f, t0 + cap), Vector3.back, 1f);
                Quad(v, uv, t, A(x, z + th, b), A(x1, z + th, b), A(x1, z + th, t1), A(x, z + th, t0), Vector3.forward, tile);
                bool gapLeft = gaps.Any(g => Mathf.Abs(x - g.y) < .01f) || x == 792f, gapRight = gaps.Any(g => Mathf.Abs(x1 - g.x) < 1.01f) || x1 >= 1150f;
                if (gapLeft) Quad(v, uv, t, A(x, z, b), A(x, z, t0), A(x, z + th, t0), A(x, z + th, b), Vector3.left, 1f);
                if (gapRight) Quad(v, uv, t, A(x1, z, b), A(x1, z + th, b), A(x1, z + th, t1), A(x1, z, t1), Vector3.right, 1f);
                metres += x1 - x;
            }
            if (v.Count > 0) Go("Wall_foot_v1", parent, Save("Wall_foot_v1", v, uv, t), mat, layer, true);
            log.AppendLine($"foot wall over Downtown: {metres:0} m");
        }

        static Material MarkingMaterial(Material template)
        {
            string path = Dir + "/Road_marking_white.mat";
            var m = template ? new Material(template) : new Material(Shader.Find("Universal Render Pipeline/Lit"));
            m.name = "Road_marking_white";
            foreach (var p in new[] { "_BaseMap", "_MainTex", "_BumpMap", "_DetailAlbedoMap", "_DetailNormalMap" }) if (m.HasProperty(p)) m.SetTexture(p, null);
            m.DisableKeyword("_NORMALMAP");
            foreach (var p in new[] { "_BaseColor", "_Color" }) if (m.HasProperty(p)) m.SetColor(p, new Color(.9f, .9f, .86f));
            if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", .1f);
            AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static void AddRoad(List<S> list, List<(Vector2 p, float y)> pts, float roadW, int id, float flareStart = 0f, float flareEnd = 0f)
        {
            var sAt = new float[pts.Count]; for (int i = 1; i < pts.Count; i++) sAt[i] = sAt[i - 1] + (pts[i].p - pts[i - 1].p).magnitude;
            float total = sAt[pts.Count - 1];
            for (int i = 0; i < pts.Count; i++)
            {
                Vector2 d = (pts[Mathf.Min(i + 1, pts.Count - 1)].p - pts[Mathf.Max(i - 1, 0)].p).normalized;
                float extra = .5f * (flareStart * (1f - Mathf.SmoothStep(0f, 1f, sAt[i] / 9f)) + flareEnd * (1f - Mathf.SmoothStep(0f, 1f, (total - sAt[i]) / 9f)));
                list.Add(new S { p = pts[i].p, y = pts[i].y, right = new Vector2(d.y, -d.x), roadHalf = roadW * .5f + extra, half = roadW * .5f + 1.5f + extra, cut = .75f, road = id });
            }
        }

        /// <summary>Cuts a road back to the edge of the street it joins (the part over the street goes) and lands it flush with the street
        /// there (1 cm over it), easing the heights over the last 9 m.</summary>
        static List<(Vector2 p, float y)> TrimToStreet(List<(Vector2 p, float y)> road, bool atStart, bool atEnd, StringBuilder log, string name)
        {
            float Hit(Vector2 p)
            {
                float top = -1e9f;
                foreach (var h in Physics.RaycastAll(new Vector3(p.x, 400f, p.y), Vector3.down, 800f))
                {
                    if (h.collider is TerrainCollider || h.point.y > 60f) continue;
                    string n = h.collider.name.ToLowerInvariant();
                    if (n.Contains("serpentine_view_b") || n.Contains("view_b_spur") || n.Contains("cornice_view_c") || n.Contains("tunnel") || n.Contains("portal")) continue;
                    if (n.Contains("street") || n.StartsWith("road_") || n.Contains("junction") || n.Contains("crossing")) top = Mathf.Max(top, h.point.y);
                }
                return top;
            }
            var o = new List<(Vector2 p, float y)>(road); var msg = new StringBuilder();
            foreach (bool start in new[] { true, false })
            {
                if (start ? !atStart : !atEnd) continue;
                if (!start) o.Reverse();
                int cut = 0; float streetY = -1e9f;
                while (o.Count > 10) { float hy = Hit(o[0].p); if (hy < -1e8f) break; streetY = hy; o.RemoveAt(0); cut++; }
                if (streetY > -1e8f)
                {   // a point exactly on the street edge, then ease the heights in over 9 m
                    Vector2 inside = o[0].p, dir = (o[0].p - o[1].p).normalized; Vector2 edge = inside;
                    for (float s = .1f; s < 3f; s += .1f) { if (Hit(inside + dir * s) > -1e8f) break; edge = inside + dir * s; }
                    o.Insert(0, (edge, streetY - .04f));
                    float acc = 0f;
                    for (int i = 1; i < o.Count && acc < 9f; i++)
                    {
                        acc += (o[i].p - o[i - 1].p).magnitude;
                        o[i] = (o[i].p, Mathf.Lerp(streetY - .04f, o[i].y, Mathf.SmoothStep(0f, 1f, acc / 9f)));
                    }
                }
                msg.Append($" {(start ? "start" : "end")}: {cut} pts over the street cut, street {streetY:0.00};");
                if (!start) o.Reverse();
            }
            log.AppendLine($"street join {name}:{msg}");
            return o;
        }

        /// <summary>Ground under a road: 0.3 m under the surface (interpolated along the road, not the nearest sample), easing to 0.08 m
        /// at the outer edge of the shoulder.</summary>
        /// <summary>Earth walls beside the serpentine and the spur: from the shoulder edge up to the wall height over 1.8 m, a 3.5 m crest,
        /// then down to the hill over 9 m (the uphill side is higher anyway). A lower bound for the ground.</summary>
        static float EarthWall(Vector2 p, List<S> roads)
        {
            float best = 1e9f; int k = -1;
            for (int i = 0; i < roads.Count; i++) { if (roads[i].wall <= .01f) continue; float d = (roads[i].p - p).sqrMagnitude; if (d < best) { best = d; k = i; } }
            if (k < 0) return -1e9f;
            var nb = roads[k]; float e = Mathf.Sqrt(best) - nb.half;
            if (e < 0f || e > 45f) return -1e9f;
            foreach (var q in roads) if (q.road != nb.road && (q.p - p).magnitude < q.half + .5f) return -1e9f;     // the spur cuts through
            // the outer face goes down at 0.8 until it meets the hill (no step where the bound ends)
            return e < 1.8f ? nb.y + nb.wall * Mathf.SmoothStep(0f, 1f, e / 1.8f) : e < 5.3f ? nb.y + nb.wall : nb.y + nb.wall - (e - 5.3f) * .8f;
        }

        /// <summary>Height of the street (any non-terrain collider) at a point, for the road ends.</summary>
        static List<(Vector2 p, float y)> Aprons(List<(Vector2 p, float y)> road, StringBuilder log, string name)
        {
            var o = new List<(Vector2 p, float y)>(road); int side = 0, street = 0; var seen = new HashSet<string>();
            var walkTris = new List<(Vector3 a, Vector3 b, Vector3 c)>();
            foreach (var endP in new[] { road[0].p, road[road.Count - 1].p })
                foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None))
                {
                    string mn = mf.name.ToLowerInvariant();
                    if (!mf.sharedMesh || !(mn.Contains("sidewalk") || mn.Contains("kerb") || mn.Contains("curb"))) continue;
                    var rb = mf.GetComponent<Renderer>(); if (!rb || rb.bounds.SqrDistance(new Vector3(endP.x, rb.bounds.center.y, endP.y)) > 35f * 35f) continue;
                    var mv = mf.sharedMesh.vertices; var mt = mf.sharedMesh.triangles; var l2w = mf.transform.localToWorldMatrix;
                    for (int k = 0; k < mt.Length; k += 3) walkTris.Add((l2w.MultiplyPoint3x4(mv[mt[k]]), l2w.MultiplyPoint3x4(mv[mt[k + 1]]), l2w.MultiplyPoint3x4(mv[mt[k + 2]])));
                }
            foreach (bool atStart in new[] { true, false })
            {
                float acc = 0f;
                for (int k = 0; k < o.Count && acc < 28f; k++)
                {
                    int i = atStart ? k : o.Count - 1 - k, prev = atStart ? i - 1 : i + 1;
                    if (k > 0) acc += (o[i].p - o[prev].p).magnitude;
                    float top = -1e9f; string what = null;
                    foreach (var h in Physics.RaycastAll(new Vector3(o[i].p.x, 400f, o[i].p.y), Vector3.down, 800f))
                    {
                        if (h.collider is TerrainCollider || h.point.y > 60f || h.point.y <= top) continue;
                        string n = h.collider.name.ToLowerInvariant();
                        if (n.Contains("serpentine_view_b") || n.Contains("view_b_spur") || n.Contains("cornice_view_c") || n.Contains("tunnel")) continue;
                        if (k < 2) seen.Add(h.collider.name);
                        if (n.Contains("sidewalk") || n.Contains("kerb") || n.Contains("curb")) { top = h.point.y; what = "side"; }
                        else if (n.Contains("street") || n.StartsWith("road_") || n.Contains("asphalt") || n.Contains("junction") || n.Contains("crossing")) { top = h.point.y; what = "street"; }
                    }
                    float walk = WalkTop(o[i].p, walkTris, RoadW * .5f);
                    if (walk > top + .02f) { top = walk; what = "side"; }
                    if (what == "side") { o[i] = (o[i].p, Mathf.Max(o[i].y, top - .03f)); side++; }
                    else if (what == "street") { o[i] = (o[i].p, Mathf.Min(o[i].y, top - .13f)); street++; }
                }
            }
            log.AppendLine($"aprons {name}: {side} points over sidewalks, {street} under the street surface; end hits: {string.Join(", ", seen)}");
            return o;
        }

        /// <summary>Highest sidewalk surface under a road point (also checked half a road width to each side, the kerb line).</summary>
        static float WalkTop(Vector2 p, List<(Vector3 a, Vector3 b, Vector3 c)> tris, float half)
        {
            float best = -1e9f;
            foreach (var (a, b, c) in tris)
            {
                if (Mathf.Abs(a.y - b.y) > .6f || Mathf.Abs(a.y - c.y) > .6f) continue;     // top faces only
                Vector2 A = new(a.x, a.z), B = new(b.x, b.z), C = new(c.x, c.z);
                float d = (B.y - C.y) * (A.x - C.x) + (C.x - B.x) * (A.y - C.y); if (Mathf.Abs(d) < 1e-6f) continue;
                float l1 = ((B.y - C.y) * (p.x - C.x) + (C.x - B.x) * (p.y - C.y)) / d, l2 = ((C.y - A.y) * (p.x - C.x) + (A.x - C.x) * (p.y - C.y)) / d, l3 = 1f - l1 - l2;
                if (l1 < -.01f || l2 < -.01f || l3 < -.01f) continue;
                best = Mathf.Max(best, a.y * l1 + b.y * l2 + c.y * l3);
            }
            return best;
        }

        static float StreetY(Vector2 p, float fallback)
        {
            float best = -1e9f;
            foreach (var h in Physics.RaycastAll(new Vector3(p.x, 400f, p.y), Vector3.down, 800f))
                if (!(h.collider is TerrainCollider) && h.point.y > best && h.point.y < 60f) best = h.point.y;
            return best > -1e8f ? best : fallback;
        }

        /// <summary>Removes the sidewalk / kerb triangles that lie under the first (or last) 30 m of a new road.</summary>
        static int CutSidewalks(List<(Vector2 p, float y)> road, float w, bool atStart)
        {
            var end = atStart ? road[0].p : road[road.Count - 1].p;
            var seg = new List<Vector2>(); float acc = 0f;
            for (int k = 0; k < road.Count; k++)
            {
                int i = atStart ? k : road.Count - 1 - k;
                if (k > 0) acc += (road[i].p - seg[seg.Count - 1]).magnitude;
                seg.Add(road[i].p); if (acc > 30f) break;
            }
            var arr = seg.ToArray(); int cut = 0;
            foreach (var mf in Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None))
            {
                string n = mf.name.ToLowerInvariant();
                if (!mf.sharedMesh || !(n.Contains("sidewalk") || n.Contains("kerb") || n.Contains("curb"))) continue;
                var r = mf.GetComponent<Renderer>(); if (!r) continue;
                var b = r.bounds; if (b.SqrDistance(new Vector3(end.x, b.center.y, end.y)) > 40f * 40f) continue;
                var m = mf.sharedMesh; var v = m.vertices; var keep = new List<int>(); var l2w = mf.transform.localToWorldMatrix; int before = 0;
                var subs = new List<int[]>();
                for (int s = 0; s < m.subMeshCount; s++)
                {
                    var tri = m.GetTriangles(s); var kept = new List<int>();
                    for (int k = 0; k < tri.Length; k += 3)
                    {
                        var c = l2w.MultiplyPoint3x4((v[tri[k]] + v[tri[k + 1]] + v[tri[k + 2]]) / 3f);
                        if (PolyDist(new Vector2(c.x, c.z), arr) < w * .5f + .5f) { cut++; before++; continue; }
                        kept.AddRange(new[] { tri[k], tri[k + 1], tri[k + 2] });
                    }
                    subs.Add(kept.ToArray());
                }
                if (before == 0) continue;
                var nm = Object.Instantiate(m); nm.name = m.name + "_cut";
                for (int s = 0; s < subs.Count; s++) nm.SetTriangles(subs[s], s);
                nm.RecalculateBounds();
                string path = Dir + "/sidewalk_cut_" + Mathf.Abs(mf.GetHashCode()) + "_" + (atStart ? "a" : "b") + ".asset"; AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(nm, path);
                var col = mf.GetComponent<MeshCollider>(); if (col && col.sharedMesh == m) col.sharedMesh = nm;
                mf.sharedMesh = nm;
            }
            return cut;
        }

        static bool RoadPin(Vector2 p, List<S> roads, out float ry)
        {
            ry = 0f; if (roads.Count == 0) return false;
            int k = 0; float best = 1e9f;
            for (int i = 0; i < roads.Count; i++) { float d = (roads[i].p - p).sqrMagnitude; if (d < best) { best = d; k = i; } }
            var nb = roads[k]; if (Mathf.Sqrt(best) > nb.half + 1f) return false;
            float y = nb.y, dist = Mathf.Sqrt(best);
            foreach (int j in new[] { k - 1, k + 1 })
            {
                if (j < 0 || j >= roads.Count || roads[j].road != nb.road) continue;
                Vector2 a = roads[k].p, b = roads[j].p, ab = b - a; float l2 = ab.sqrMagnitude; if (l2 < 1e-6f) continue;
                float tt = Mathf.Clamp01(Vector2.Dot(p - a, ab) / l2), dd = (p - (a + ab * tt)).magnitude;
                if (dd < dist) { dist = dd; y = Mathf.Lerp(roads[k].y, roads[j].y, tt); }
            }
            if (dist > nb.half) return false;
            float e = dist - nb.roadHalf;
            ry = y - (e <= .2f ? .3f : Mathf.Lerp(.3f, .08f, (e - .2f) / Mathf.Max(.1f, nb.half - nb.roadHalf - .2f)));
            return true;
        }

        /// <summary>The cornice cliff: on the bay side of the cliff section the ground falls from the road edge into the water.</summary>
        static bool CliffCut(Vector2 p, List<S> roads, float y0, out float cy)
        {
            cy = 0f; float best = 1e9f; int k = -1;
            for (int i = 0; i < roads.Count; i++) { if (roads[i].road != 4 || roads[i].cliff <= 0f) continue; float d = (roads[i].p - p).magnitude; if (d < best) { best = d; k = i; } }
            if (k < 0) return false;
            var nb = roads[k]; float side = Vector2.Dot(p - nb.p, nb.right);
            if (side <= nb.roadHalf + 1.2f || best > 45f || y0 < -3.4f || p.y < 504f || p.y > 572f) return false;
            float u = Mathf.SmoothStep(0f, 1f, (side - nb.roadHalf - 1.2f) / 4f);
            cy = Mathf.Lerp(y0, Mathf.Lerp(nb.y - .3f, -3.5f, u), nb.cliff);
            return true;
        }

        /// <summary>Low stone parapet on the bay side of the cliff section.</summary>
        static void CorniceParapet(List<S> roads, Material stone, Transform parent, int layer, StringBuilder log)
        {
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>(); int segs = 0;
            S prev = default; bool has = false;
            foreach (var q in roads)
            {
                if (q.road != 4 || q.cliff < .5f) { has = false; continue; }
                if (has)
                {
                    Vector3 P(S s0, float off, float yy) { var o = s0.p + s0.right * off; return new Vector3(o.x, s0.y + yy, o.y); }
                    float i0 = prev.roadHalf + .2f, o0 = prev.roadHalf + .65f; const float hgt = .85f;
                    var r3 = new Vector3(q.right.x, 0, q.right.y);
                    Quad(v, uv, t, P(prev, i0, -.3f), P(q, i0, -.3f), P(q, i0, hgt), P(prev, i0, hgt), -r3, 1.5f);
                    Quad(v, uv, t, P(prev, o0, -1.2f), P(q, o0, -1.2f), P(q, o0, hgt), P(prev, o0, hgt), r3, 1.5f);
                    Quad(v, uv, t, P(prev, i0, hgt), P(q, i0, hgt), P(q, o0, hgt), P(prev, o0, hgt), Vector3.up, 1.5f);
                    segs++;
                }
                prev = q; has = true;
            }
            if (segs > 0) Go("Road_cornice_parapet_v2", parent, Save("Road_cornice_parapet_v2", v, uv, t), stone, layer, true);
            log.AppendLine($"cornice parapet: {segs} m");
        }

        /// <summary>The cornice line (Downtown NE entry -> cliff edge over the bay -> port) with a 11 m crest over the cliff.</summary>
        static List<(Vector2 p, float y)> CorniceProfile2()
        {
            var raw = Profile(CornicePts, 0f, 1f, 30, false);
            var s = new float[raw.Count]; for (int i = 1; i < raw.Count; i++) s[i] = s[i - 1] + (raw[i].p - raw[i - 1].p).magnitude;
            int Near(Vector2 q) { int bi = 0; float bd = 1e9f; for (int i = 0; i < raw.Count; i++) { float d = (raw[i].p - q).sqrMagnitude; if (d < bd) { bd = d; bi = i; } } return bi; }
            float sP = s[Near(new Vector2(1227, 549))], sB = s[Near(new Vector2(1255, 594))], sE = s[s.Length - 1];
            float Ease(float u) { u = Mathf.Clamp01(u); return Smooth(u) * .6f + u * .4f; }
            var outL = new List<(Vector2 p, float y)>();
            for (int i = 0; i < raw.Count; i++)
            {
                float si = s[i], y;
                if (si < 12f) y = 5.06f;
                else if (si < sP) y = Mathf.Lerp(5.06f, 11f, Ease((si - 12f) / (sP - 12f)));
                else if (si < sB) y = Mathf.Lerp(11f, 3.15f, Ease((si - sP) / (sB - sP)));
                else y = Mathf.Lerp(3.15f, 2.56f, (si - sB) / Mathf.Max(1f, sE - sB));
                outL.Add((raw[i].p, y));
            }
            return outL;
        }

        /// <summary>The meeting place: a round gravel plaza on the summit, a low stone wall on the view side (south), three benches
        /// along it facing the view, two lamps by the entrance and the far side.</summary>
        static void BuildPlaza(Transform root, float y, Material gravel, Material stone, Transform bench, Transform lamp, int layer, StringBuilder log)
        {
            var parent = new GameObject("VadimMeetPlaza").transform; parent.SetParent(root, false);
            var c = new Vector3(PlazaC.x, y, PlazaC.y);
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            const int N = 48;
            v.Add(c + Vector3.up * .04f); uv.Add(Vector2.zero);
            for (int k = 0; k <= N; k++) { float a = k * Mathf.PI * 2f / N; var q = new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a)) * PlazaR; v.Add(c + q + Vector3.up * .04f); uv.Add(new Vector2(q.x, q.z) / 4f); if (k > 0) t.AddRange(new[] { 0, k + 1, k }); }
            var disc = Save("Plaza_gravel", v, uv, t);
            if (disc.normals[0].y < 0) { t.Reverse(); disc = Save("Plaza_gravel", v, uv, t); }
            Go("Plaza_gravel", parent, disc, gravel ? gravel : stone, layer, true);
            // low wall 0.6 m, 0.5 m thick, from 195 to 345 degrees (south half: city, bay)
            var wv = new List<Vector3>(); var wuv = new List<Vector2>(); var wt = new List<int>();
            float rIn = PlazaR - .1f, rOut = PlazaR + .4f, hgt = .6f; int seg = 0;
            for (float deg = 195f; deg < 345f; deg += 7.5f, seg++)
            {
                float a = deg * Mathf.Deg2Rad, b = Mathf.Min(deg + 7.5f, 345f) * Mathf.Deg2Rad;
                Vector3 da = new(Mathf.Cos(a), 0, Mathf.Sin(a)), db = new(Mathf.Cos(b), 0, Mathf.Sin(b)), dm = (da + db).normalized, upv = Vector3.up * hgt;
                Vector3 ia = c + da * rIn, ib = c + db * rIn, oa = c + da * rOut, ob = c + db * rOut;
                Quad(wv, wuv, wt, oa, ob, ob + upv, oa + upv, dm, 1.5f);
                Quad(wv, wuv, wt, ib, ia, ia + upv, ib + upv, -dm, 1.5f);
                Quad(wv, wuv, wt, ia + upv, ib + upv, ob + upv, oa + upv, Vector3.up, 1.5f);
                if (deg == 195f) Quad(wv, wuv, wt, ia, oa, oa + upv, ia + upv, Vector3.Cross(Vector3.up, da), 1.5f);
                if (deg + 7.5f >= 345f) Quad(wv, wuv, wt, ob, ib, ib + upv, ob + upv, -Vector3.Cross(Vector3.up, db), 1.5f);
            }
            for (int k = 0; k < wv.Count; k++) wv[k] -= Vector3.up * .15f;      // sunk a little into the ground
            Go("Plaza_wall", parent, Save("Plaza_wall", wv, wuv, wt), stone, layer, true);
            int benches = 0;
            if (bench)
            {   // Fedya's benches faced the view (0.7, -0.8): keep the same model offset, face outward over the wall
                float offset = bench.eulerAngles.y - Mathf.Atan2(.7f, -.8f) * Mathf.Rad2Deg;
                foreach (float deg in new[] { 235f, 270f, 305f })
                {
                    var d = new Vector3(Mathf.Cos(deg * Mathf.Deg2Rad), 0, Mathf.Sin(deg * Mathf.Deg2Rad));
                    var b = Object.Instantiate(bench.gameObject, parent); b.name = "Plaza_bench_" + benches;
                    b.transform.position = c + d * (PlazaR - 2.2f);
                    b.transform.rotation = Quaternion.Euler(0, Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg + offset, 0);
                    b.SetActive(true); benches++;
                }
            }
            if (lamp)
                foreach (float deg in new[] { 20f, 160f })
                {
                    var d = new Vector3(Mathf.Cos(deg * Mathf.Deg2Rad), 0, Mathf.Sin(deg * Mathf.Deg2Rad));
                    var l = Object.Instantiate(lamp.gameObject, parent); l.name = "Plaza_lamp_" + deg;
                    l.transform.position = c + d * (PlazaR - .8f); l.SetActive(true);
                }
            log.AppendLine($"plaza: R {PlazaR} m at {y:0} m, wall 150 deg, {benches} benches, lamps {(lamp ? 2 : 0)}");
        }

        /// <summary>Vadim's choice Г: graphite concrete inside, light concrete portal, a slightly darker arch band. No stripes.</summary>
        static (Material wall, Material portal, Material arch) TunnelMaterials(Material template)
        {
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/OnlyVolunteers/Art/MapTextures_W86/T1/Textures/T1_concrete_light_albedo.png");
            Material Make(string name, Color col)
            {
                string path = Dir + "/" + name + ".mat";
                var m = template ? new Material(template) : new Material(Shader.Find("Universal Render Pipeline/Lit"));
                m.name = name;
                foreach (var p in new[] { "_BaseMap", "_MainTex" }) if (m.HasProperty(p)) { m.SetTexture(p, tex); m.SetTextureScale(p, Vector2.one); m.SetTextureOffset(p, Vector2.zero); }
                foreach (var p in new[] { "_BumpMap", "_DetailAlbedoMap", "_DetailNormalMap", "_EmissionMap" }) if (m.HasProperty(p)) m.SetTexture(p, null);
                m.DisableKeyword("_NORMALMAP"); m.DisableKeyword("_EMISSION");
                foreach (var p in new[] { "_BaseColor", "_Color" }) if (m.HasProperty(p)) m.SetColor(p, col);
                if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", .12f);
                AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(m, path);
                return m;
            }
            return (Make("Tunnel_G_wall", new Color(.40f, .41f, .43f)), Make("Tunnel_G_portal", new Color(.86f, .85f, .82f)), Make("Tunnel_G_arch", new Color(.72f, .71f, .69f)));
        }

        static Material TunnelMarkMat;
        static void BuildTunnel(Transform root, List<(Vector2 p, float y)> axis, Material wallMat, Material deckMat, Material portalMat, Material archMat, int layer, StringBuilder log)
        {
            var parent = new GameObject("Tunnel_v2").transform; parent.SetParent(root, false);
            float a0 = -Mathf.Asin(TunC / TunR), a1 = Mathf.PI - a0; const int N = 28;
            float half = Mathf.Sqrt(TunR * TunR - TunC * TunC), arcStep = TunR * (a1 - a0) / N;
            var tv = new List<Vector3>(); var tuv = new List<Vector2>(); var tt = new List<int>();
            var dv = new List<Vector3>(); var duv = new List<Vector2>(); var dt = new List<int>();
            float acc = 0;
            for (int i = 0; i < axis.Count; i++)
            {
                Vector2 d = (axis[Mathf.Min(i + 1, axis.Count - 1)].p - axis[Mathf.Max(i - 1, 0)].p).normalized, n = new(-d.y, d.x);
                if (i > 0) acc += (axis[i].p - axis[i - 1].p).magnitude;
                var right = new Vector3(n.x, 0, n.y); var c = new Vector3(axis[i].p.x, axis[i].y + TunC, axis[i].p.y);
                for (int k = 0; k <= N; k++)
                {
                    float a = Mathf.Lerp(a0, a1, k / (float)N);
                    tv.Add(c + right * (TunR * Mathf.Cos(a)) + Vector3.up * (TunR * Mathf.Sin(a)));
                    tuv.Add(new Vector2(k * arcStep / 4f, acc / 4f));
                }
                var deckC = new Vector3(axis[i].p.x, axis[i].y + .03f, axis[i].p.y);
                dv.Add(deckC + right * half); dv.Add(deckC - right * half);
                duv.Add(new Vector2(0, acc / 6f)); duv.Add(new Vector2(2 * half / 6f, acc / 6f));
                if (i > 0)
                {
                    int q0 = (i - 1) * (N + 1), q1 = i * (N + 1);
                    for (int k = 0; k < N; k++) tt.AddRange(new[] { q0 + k, q1 + k, q1 + k + 1, q0 + k, q1 + k + 1, q0 + k + 1 });
                    int b = i * 2; dt.AddRange(new[] { b - 2, b, b + 1, b - 2, b + 1, b - 1 });
                }
            }
            var tube = Build("Tunnel_v2_tube", tv, tuv, tt, i => { int ring = i / (N + 1); var q = axis[ring]; return new Vector3(q.p.x, q.y + TunC, q.p.y) - tv[i]; });
            Go("Tunnel_v2_tube", parent, tube, wallMat, layer, true);
            var ttOut = new List<int>(); for (int k = 0; k < tt.Count; k += 3) ttOut.AddRange(new[] { tt[k], tt[k + 2], tt[k + 1] });
            var tubeOut = Build("Tunnel_v2_tube_out", new List<Vector3>(tv), tuv, ttOut, i => { int ring = i / (N + 1); var q = axis[ring]; return tv[i] - new Vector3(q.p.x, q.y + TunC, q.p.y); });
            Go("Tunnel_v2_tube_out", parent, tubeOut, wallMat, layer, false);
            {   // the road inside: 6.8 m carriageway with markings, raised walkways (0.18 m, kerb faces) to the wall
                var road = axis.Select(q => (q.p, q.y - .02f)).ToList();
                MakeRoad("Tunnel_v2_road", road, RoadW, 6f, deckMat, parent, layer, TunnelMarkMat);
                var wv = new List<Vector3>(); var wuv = new List<Vector2>(); var wt = new List<int>();
                for (int i = 1; i < axis.Count; i++)
                {
                    foreach (float side in new[] { 1f, -1f })
                    {
                        Vector3 At(int k2, float off, float yy) { Vector2 d2 = (axis[Mathf.Min(k2 + 1, axis.Count - 1)].p - axis[Mathf.Max(k2 - 1, 0)].p).normalized; var n2 = new Vector2(-d2.y, d2.x) * side; var o = axis[k2].p + n2 * off; return new Vector3(o.x, axis[k2].y + yy, o.y); }
                        Vector2 dd = (axis[i].p - axis[i - 1].p).normalized; var nside = new Vector3(-dd.y, 0, dd.x) * side;
                        Quad(wv, wuv, wt, At(i - 1, RoadW * .5f, .18f), At(i, RoadW * .5f, .18f), At(i, half + .3f, .18f), At(i - 1, half + .3f, .18f), Vector3.up, 2f);
                        Quad(wv, wuv, wt, At(i - 1, RoadW * .5f, -.1f), At(i, RoadW * .5f, -.1f), At(i, RoadW * .5f, .18f), At(i - 1, RoadW * .5f, .18f), -nside, 2f);
                    }
                }
                foreach (int iEnd in new[] { 0, axis.Count - 1 })
                    foreach (float side in new[] { 1f, -1f })
                    {
                        Vector2 d2 = (axis[Mathf.Min(iEnd + 1, axis.Count - 1)].p - axis[Mathf.Max(iEnd - 1, 0)].p).normalized, n2 = new Vector2(-d2.y, d2.x) * side;
                        Vector3 E(float off, float yy) { var o = axis[iEnd].p + n2 * off; return new Vector3(o.x, axis[iEnd].y + yy, o.y); }
                        var outward = new Vector3(d2.x, 0, d2.y) * (iEnd == 0 ? -1f : 1f);
                        Quad(wv, wuv, wt, E(RoadW * .5f, -1.5f), E(half + .3f, -1.5f), E(half + .3f, .18f), E(RoadW * .5f, .18f), outward, 2f);
                    }
                Go("Tunnel_v2_walkways", parent, Save("Tunnel_v2_walkways", wv, wuv, wt), portalMat, layer, true);
            }
            for (int e = 0; e < 2; e++)
            {
                var p0 = e == 0 ? axis[0] : axis[axis.Count - 1]; var p1 = e == 0 ? axis[1] : axis[axis.Count - 2];
                Vector2 inward = (p1.p - p0.p).normalized, nn = new(-inward.y, inward.x);
                var right = new Vector3(nn.x, 0, nn.y); var c = new Vector3(p0.p.x, p0.y + TunC, p0.p.y);
                float hw = TunR + 4.5f, bot = -TunC - .6f;
                var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
                for (int k = 0; k <= N; k++)
                {
                    float a = Mathf.Lerp(a0, a1, k / (float)N); var dir = new Vector2(Mathf.Cos(a), Mathf.Sin(a));
                    var inner = dir * TunR; float sc = TunR + .3f;
                    while (sc < 40f)
                    {
                        var q = dir * sc; float coverTop = TunR + 1.6f - Mathf.Max(0f, Mathf.Abs(q.x) - (TunR + 2.5f)) * .45f;
                        if (Mathf.Abs(q.x) >= hw || q.y <= bot || q.y >= coverTop) break;
                        sc += .1f;
                    }
                    var outer = dir * sc;
                    v.Add(c + right * inner.x + Vector3.up * inner.y); v.Add(c + right * outer.x + Vector3.up * outer.y);
                    uv.Add(inner / 4f); uv.Add(outer / 4f);
                    if (k > 0) { int b = k * 2; t.AddRange(new[] { b - 2, b - 1, b + 1, b - 2, b + 1, b }); }
                }
                foreach (int side in new[] { 1, -1 })
                {
                    var deckEnd = new Vector2(side * half, -TunC); int bi = v.Count;
                    v.Add(c + right * deckEnd.x + Vector3.up * deckEnd.y); v.Add(c + right * (side * hw) + Vector3.up * deckEnd.y);
                    v.Add(c + right * (side * hw) + Vector3.up * bot); v.Add(c + right * deckEnd.x + Vector3.up * bot);
                    uv.Add(deckEnd / 4f); uv.Add(new Vector2(side * hw, deckEnd.y) / 4f); uv.Add(new Vector2(side * hw, bot) / 4f); uv.Add(new Vector2(deckEnd.x, bot) / 4f);
                    t.AddRange(new[] { bi, bi + 1, bi + 2, bi, bi + 2, bi + 3 });
                }
                int nf = v.Count; var back = new Vector3(inward.x, 0, inward.y) * .8f;
                for (int k = 0; k < nf; k++) { v.Add(v[k] + back); uv.Add(uv[k]); }
                int tf = t.Count; for (int k = 0; k < tf; k += 3) t.AddRange(new[] { t[k] + nf, t[k + 2] + nf, t[k + 1] + nf });
                var outward = new Vector3(-inward.x, 0, -inward.y);
                Go("Tunnel_v2_portal_" + e, parent, Build("Tunnel_v2_portal_" + e, v, uv, t, i => i < nf ? outward : -outward), portalMat, layer, true);
                var rv = new List<Vector3>(); var ruv = new List<Vector2>(); var rt = new List<int>(); var proud = outward * .35f;
                for (int k = 0; k <= N; k++)
                {
                    float a = Mathf.Lerp(a0, a1, k / (float)N); var dir = new Vector3(0, Mathf.Sin(a), 0) + right * Mathf.Cos(a);
                    rv.Add(c + dir * TunR); rv.Add(c + dir * TunR + proud); rv.Add(c + dir * (TunR + .8f) + proud); rv.Add(c + dir * (TunR + .8f));
                    float u = k / (float)N * 4f; ruv.Add(new Vector2(u, -.12f)); ruv.Add(new Vector2(u, 0)); ruv.Add(new Vector2(u, .27f)); ruv.Add(new Vector2(u, .38f));
                    if (k > 0) { int b = k * 4, pb = b - 4; for (int s2 = 0; s2 < 3; s2++) rt.AddRange(new[] { pb + s2, b + s2, b + s2 + 1, pb + s2, b + s2 + 1, pb + s2 + 1 }); }
                }
                Go("Tunnel_v2_arch_" + e, parent, Build("Tunnel_v2_arch_" + e, rv, ruv, rt, i => (i % 4 == 1 || i % 4 == 2) ? outward : (i % 4 == 3 ? (rv[i] - c).normalized : (c - rv[i]).normalized)), archMat, layer, true);
            }
            // lamps on the crown every 12 m, warm point lights every 24 m (the old ones followed Fedya's straight axis)
            var old = GameObject.Find("Tunnel_lights"); if (old) old.SetActive(false);
            var lampMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Art/MapTextures_W86/T1/Materials/T1_tunnel_lamp.mat");
            float total = 0; var cum = new float[axis.Count]; for (int i = 1; i < axis.Count; i++) { total += (axis[i].p - axis[i - 1].p).magnitude; cum[i] = total; }
            int lamps = 0, lights = 0;
            for (float sAt = 6f; sAt < total - 4f; sAt += 12f)
            {
                int i = System.Array.FindIndex(cum, x => x >= sAt); if (i <= 0) i = 1;
                float u = (sAt - cum[i - 1]) / Mathf.Max(.01f, cum[i] - cum[i - 1]);
                var p = Vector2.Lerp(axis[i - 1].p, axis[i].p, u); float y = Mathf.Lerp(axis[i - 1].y, axis[i].y, u);
                var d = (axis[i].p - axis[i - 1].p).normalized;
                var box = GameObject.CreatePrimitive(PrimitiveType.Cube); Object.DestroyImmediate(box.GetComponent<Collider>());
                box.name = "Tunnel_v2_lamp"; box.transform.SetParent(parent, false);
                box.transform.position = new Vector3(p.x, y + TunC + TunR - .12f, p.y);
                box.transform.rotation = Quaternion.LookRotation(new Vector3(d.x, 0, d.y)); box.transform.localScale = new Vector3(.35f, .12f, 1.6f);
                if (lampMat) box.GetComponent<MeshRenderer>().sharedMaterial = lampMat;
                lamps++;
                if (lamps % 2 == 1)
                {
                    var l = new GameObject("Tunnel_v2_light").AddComponent<Light>(); l.transform.SetParent(parent, false);
                    l.transform.position = new Vector3(p.x, y + TunC + TunR - .6f, p.y);
                    l.type = LightType.Point; l.range = 16f; l.intensity = 2.2f; l.color = new Color(1f, .84f, .62f); l.shadows = LightShadows.None;
                    lights++;
                }
            }
            log.AppendLine($"tunnel v2: S-bend {total:0} m, round R {TunR} m, deck {2 * half:0.0} m, {lamps} lamps, {lights} lights");
        }

        // ------------------------------------------------------------------------------------------------ check shots

        static void Shots(List<(Vector2 p, float y)> axis, float[] axS, float tunL, float plazaY)
        {
            foreach (var c in Object.FindObjectsByType<Camera>(FindObjectsSortMode.None)) c.enabled = false;
            RenderSettings.fog = false;
            Shader.SetGlobalVector("_VadimHaze", new Vector4(99, 342, 0, 1));
            var go = new GameObject("HillShotCam"); var cam = go.AddComponent<Camera>(); cam.farClipPlane = 3000; cam.clearFlags = CameraClearFlags.Skybox;
            string D = @"C:\Users\chern_0eqkb03\VolunteersBuilds\";
            cam.orthographic = true; cam.orthographicSize = 140; go.transform.position = new Vector3(955, 400, 582); go.transform.rotation = Quaternion.Euler(90, 0, 0);
            Shot(cam, 1800, 900, D + "v7_top.png");
            cam.orthographic = false; cam.fieldOfView = 60;
            go.transform.position = new Vector3(965, 70, 430); go.transform.LookAt(new Vector3(930, 25, 595)); Shot(cam, 1200, 650, D + "v7_south.png");
            go.transform.position = new Vector3(PlazaC.x + 20, plazaY + 9, PlazaC.y - 24); go.transform.LookAt(new Vector3(PlazaC.x, plazaY + 1, PlazaC.y)); Shot(cam, 1000, 600, D + "v7_plaza.png");
            var n0 = axis[0]; var dirN = (axis[0].p - axis[3].p).normalized;
            go.transform.position = new Vector3(n0.p.x + dirN.x * 24f, n0.y + 4f, n0.p.y + dirN.y * 24f); go.transform.LookAt(new Vector3(n0.p.x, n0.y + 3f, n0.p.y)); Shot(cam, 1000, 600, D + "v7_portal_n.png");
            var s0 = axis[axis.Count - 1]; var dirS = (axis[axis.Count - 1].p - axis[axis.Count - 4].p).normalized;
            go.transform.position = new Vector3(s0.p.x + dirS.x * 24f, s0.y + 4f, s0.p.y + dirS.y * 24f); go.transform.LookAt(new Vector3(s0.p.x, s0.y + 3f, s0.p.y)); Shot(cam, 1000, 600, D + "v7_portal_s.png");
            var a = axis[Mathf.Min(6, axis.Count - 1)]; var b = axis[Mathf.Min(40, axis.Count - 1)];
            go.transform.position = new Vector3(a.p.x, a.y + 2.2f, a.p.y); go.transform.LookAt(new Vector3(b.p.x, b.y + 2.2f, b.p.y)); Shot(cam, 1000, 600, D + "v7_inside.png");
            go.transform.position = new Vector3(1292, 34, 652); go.transform.LookAt(new Vector3(1205, 12, 552)); Shot(cam, 1000, 600, D + "v7_cornice.png");
            go.transform.position = new Vector3(776, 10, 674); go.transform.LookAt(new Vector3(748, 9, 646)); Shot(cam, 1000, 600, D + "v7_portal_n_side.png");
            go.transform.position = new Vector3(930, 9, 684); go.transform.LookAt(new Vector3(948, 12, 640)); Shot(cam, 1000, 600, D + "v8_exit.png");
            go.transform.position = new Vector3(962, 26, 628); go.transform.LookAt(new Vector3(950, 8, 676)); Shot(cam, 1000, 600, D + "v8_northflank.png");
            go.transform.position = new Vector3(760, 85, 720); go.transform.LookAt(new Vector3(900, 18, 585)); Shot(cam, 1000, 600, D + "v8_nw.png");
            go.transform.position = new Vector3(1110, 75, 470); go.transform.LookAt(new Vector3(950, 22, 600)); Shot(cam, 1000, 600, D + "v8_se.png");
            go.transform.position = new Vector3(858, 38, 566); go.transform.LookAt(new Vector3(824, 8, 540)); Shot(cam, 1000, 600, D + "v8_trench_s.png");
            go.transform.position = new Vector3(1060, 60, 650); go.transform.LookAt(new Vector3(985, 25, 595)); Shot(cam, 1000, 600, D + "v8_ne.png");
            go.transform.position = new Vector3(675, 30, 455); go.transform.LookAt(new Vector3(745, 12, 515)); Shot(cam, 1000, 600, D + "v8_sw.png");
            go.transform.position = new Vector3(1290, 28, 515); go.transform.LookAt(new Vector3(1222, 9, 556)); Shot(cam, 1000, 600, D + "v12_cornice_bay.png");
            go.transform.position = new Vector3(1222, 14, 520); go.transform.LookAt(new Vector3(1232, 11, 560)); Shot(cam, 1000, 600, D + "v12_cornice_road.png");
            go.transform.position = new Vector3(831, 8, 505); go.transform.LookAt(new Vector3(823, 9, 548)); Shot(cam, 1000, 600, D + "v12_approach_s.png");
            go.transform.position = new Vector3(748, 8, 674); go.transform.LookAt(new Vector3(748, 8, 645)); Shot(cam, 1000, 600, D + "v12_approach_n.png");
            go.transform.position = new Vector3(990, 30, 640); go.transform.LookAt(new Vector3(975, 22, 620)); Shot(cam, 1000, 600, D + "v12_road_close.png");
            go.transform.position = new Vector3(1004, 32, 616); go.transform.LookAt(new Vector3(985, 41, 596)); Shot(cam, 1000, 600, D + "v13_eye_up.png");
            go.transform.position = new Vector3(962, 45, 580); go.transform.LookAt(new Vector3(980, 42, 595)); Shot(cam, 1000, 600, D + "v13_eye_pass.png");
            go.transform.position = new Vector3(936, 9, 684); go.transform.LookAt(new Vector3(946, 7, 662)); Shot(cam, 1000, 600, D + "v14_end_north.png");
            go.transform.position = new Vector3(900, 7, 512); go.transform.LookAt(new Vector3(930, 9, 530)); Shot(cam, 1000, 600, D + "v15_footwall.png");
            go.transform.position = new Vector3(SpurFrom.x - 10, 49, SpurFrom.y - 12); go.transform.LookAt(new Vector3(SpurFrom.x, 41, SpurFrom.y)); Shot(cam, 1000, 600, D + "v15_junction.png");
            go.transform.position = new Vector3(895, 7.5f, 676); go.transform.LookAt(new Vector3(925, 8, 662)); Shot(cam, 1000, 600, D + "v17_rough.png");
            go.transform.position = new Vector3(1044, 34, 488); go.transform.LookAt(new Vector3(1044, 8, 528)); Shot(cam, 1000, 600, D + "v17_dt_mouth_hi.png");
            go.transform.position = new Vector3(1034, 10, 500); go.transform.LookAt(new Vector3(1044, 8, 522)); Shot(cam, 1000, 600, D + "v14_end_south.png");
            go.transform.position = new Vector3(1196, 9, 486); go.transform.LookAt(new Vector3(1204, 8, 506)); Shot(cam, 1000, 600, D + "v14_end_cornice.png");
            cam.orthographic = true; cam.orthographicSize = 55; go.transform.position = new Vector3(980, 300, 590); go.transform.rotation = Quaternion.Euler(90, 0, 0); Shot(cam, 1000, 1000, D + "v13_junction_top.png"); cam.orthographic = false;
            go.transform.position = new Vector3(PlazaC.x + 2, plazaY + 1.7f, PlazaC.y + 4); go.transform.LookAt(new Vector3(PlazaC.x + 40, plazaY - 14, PlazaC.y - 120)); Shot(cam, 1000, 600, D + "v11_plaza_view_s.png");
            go.transform.position = new Vector3(PlazaC.x - 3, plazaY + 1.7f, PlazaC.y - 2); go.transform.LookAt(new Vector3(PlazaC.x + 30, plazaY - 20, PlazaC.y + 120)); Shot(cam, 1000, 600, D + "v11_plaza_view_n.png");
            go.transform.position = new Vector3(848, 30, 545); go.transform.LookAt(new Vector3(878, 40, 585)); Shot(cam, 1000, 600, D + "v8_plaza_low.png");
            go.transform.position = new Vector3(720, 10, 672); go.transform.LookAt(new Vector3(750, 9, 646)); Shot(cam, 1000, 600, D + "v7_portal_n_side2.png");
            Object.DestroyImmediate(go);
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
