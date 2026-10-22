using System.Collections.Generic;
using System.IO;
using System.Linq;
using OnlyVolunteers.Map.W76;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W85
{
    // W86 integration (B2, 22.10): smaller pieces of the T1 / v07 rollout that hook into the W85 steps (terrain layers, tunnel, alley
    // plugs, DC3 pool + band) and the build summary.
    public static partial class W85Builder
    {
        static bool T2Available() => t2Ok != false;

        // ------------------------------------------------------------------ terrain layers: T21 b fields, T132 b steppe, bank bands
        static readonly Dictionary<string, string> LayerSwap = new()
        {
            ["L09_field_plowed"] = "T1_L09b_field_plowed", ["L10_field_stubble"] = "T1_L10b_field_stubble",
        };
        static TerrainLayer SwappedLayer(string key)
        {
            if (!IsV2 || !LayerSwap.TryGetValue(key, out string n)) return null;
            var l = AssetDatabase.LoadAssetAtPath<TerrainLayer>(T1Layers + n + ".terrainlayer");
            if (l) Done("T21 field layers (" + n + ")");
            return l;
        }

        // T129 / T131 c pebble bank band (river, mountain lake, plunge pool) as a 12th terrain layer (still 3 passes); T06 / T22 b mud band
        // (forest lake, Hamlet pond, swamp) painted into the existing L03 dirt layer (a 13th layer would cost one more terrain pass)
        static float[,,] W86BankBands(float[,,] a, List<string> keys, ref TerrainLayer[] layers)
        {
            var peb = AssetDatabase.LoadAssetAtPath<TerrainLayer>(T1Layers + "T1_L_bank_pebbles.terrainlayer");
            int AR = a.GetLength(0), L = keys.Count, dirt = keys.IndexOf("L03_dirt_SK1b");
            if (!peb || !File.Exists(Data + "/water_v85.json")) return a;
            var wj = Obj(Json.Parse(File.ReadAllText(Data + "/water_v85.json")));
            var dPeb = new float[AR, AR]; var dMud = new float[AR, AR];
            for (int j = 0; j < AR; j++) for (int i = 0; i < AR; i++) { dPeb[j, i] = 99f; dMud[j, i] = 99f; }
            void Stamp(float[,] d, Vector2 p0, Vector2 p1, float hw, float band)
            {
                float r = hw + band + 1f;
                int i0 = Mathf.Max(0, (int)((Mathf.Min(p0.x, p1.x) - r) / W * AR)), i1 = Mathf.Min(AR - 1, (int)((Mathf.Max(p0.x, p1.x) + r) / W * AR) + 1);
                int j0 = Mathf.Max(0, (int)((Mathf.Min(p0.y, p1.y) - r) / Hh * AR)), j1 = Mathf.Min(AR - 1, (int)((Mathf.Max(p0.y, p1.y) + r) / Hh * AR) + 1);
                for (int j = j0; j <= j1; j++)
                    for (int i = i0; i <= i1; i++)
                    {
                        var q = new Vector2((i + .5f) / AR * W, (j + .5f) / AR * Hh);
                        float dd = Mathf.Abs(DistSeg(q, p0, p1) - hw);                 // distance to the water line
                        if (dd < d[j, i]) d[j, i] = dd;
                    }
            }
            int nb = 0;
            foreach (var b in Arr(Get(wj, "bodies")).Select(Obj))
            {
                string kind = S(Get(b, "kind")), id = S(Get(b, "id"), "");
                if (kind == "river")
                {
                    var ax = V2s(Get(b, "axis")); var wd = Arr(Get(b, "width_m")).Select(x => F(x)).ToArray();
                    var under = Arr(Get(b, "underground_spans")).Select(o => Arr(o)).Where(o => o.Count >= 2).Select(o => ((int)F(o[0]), (int)F(o[1]))).ToList();
                    for (int k = 1; k < ax.Length; k++)
                    {
                        if (under.Any(u => k >= u.Item1 && k <= u.Item2 + 1)) continue;
                        float hw = ((k < wd.Length ? wd[k] : 6f) + (k - 1 < wd.Length ? wd[k - 1] : 6f)) * .25f;
                        Stamp(dPeb, ax[k - 1], ax[k], hw, 3.5f);
                    }
                    nb++;
                }
                else if (kind == "lake" || kind == "pond" || kind == "swamp")
                {
                    var o = V2s(Get(b, "outline")); if (o.Length < 3) continue;
                    bool rocky = id.Contains("mountain") || id.Contains("plunge");
                    for (int k = 0; k < o.Length; k++) Stamp(rocky ? dPeb : dMud, o[k], o[(k + 1) % o.Length], 0f, 3.5f);
                    nb++;
                }
            }
            var o2 = new float[AR, AR, L + 1];
            int painted = 0;
            for (int j = 0; j < AR; j++)
                for (int i = 0; i < AR; i++)
                {
                    float wp = Mathf.Clamp01((3.5f - dPeb[j, i]) / 1.2f), wm = Mathf.Clamp01((3f - dMud[j, i]) / 1.2f) * .85f;
                    float keep = 1f - wp;
                    for (int l = 0; l < L; l++) o2[j, i, l] = a[j, i, l] * keep;
                    o2[j, i, L] = wp;
                    if (wm > 0f && dirt >= 0)
                    {
                        float rest = 1f - wp, md = Mathf.Min(wm, rest);
                        float s = 0f; for (int l = 0; l < L; l++) s += o2[j, i, l];
                        if (s > 1e-4f) for (int l = 0; l < L; l++) o2[j, i, l] *= (s - md) / s;
                        o2[j, i, dirt] += md;
                    }
                    if (wp > 0f || wm > 0f) painted++;
                }
            layers = layers.Concat(new[] { peb }).ToArray();
            Note($"bank bands: {nb} water bodies, {painted} splat texels (T129 / T131 pebbles = layer {L + 1}, T06 / T22 mud -> L03 dirt)");
            Done("T06 / T22 / T129 / T131 bank bands");
            return o2;
        }

        static TerrainLayer SteppeLayerT132(string key)
        {
            if (key != "L02_worn_grass") return null;
            var l = AssetDatabase.LoadAssetAtPath<TerrainLayer>(T1Layers + "T1_L_steppe_b.terrainlayer");
            if (l) Done("T132 steppe backdrop layer");
            return l;
        }

        // ------------------------------------------------------------------ T128 tunnel: lamp strips every 6 m at 4.9 m, kerbs 0.8 m
        static void TunnelExtrasT128(Transform parent, List<Vector2> pts, float total, float h0, float h1, float width, float clear)
        {
            var lampM = T1M("T1_tunnel_lamp");
            var b = new RBatch();
            string lamp = lampM ? RSurfKey("t1:tunnel_lamp", lampM, 1f, true) : null;
            string kerb = RSurfKey("w86:tunnel_kerb", MapReady(AssetDatabase.LoadAssetAtPath<Material>(TT7Dir + "TT7_conc.mat"), 1f / 2.4f) ?? Mat("concrete_SK3c"), 1f);
            int n = 0;
            for (float s = 3f; s < total - 1f; s += 6f)
            {
                Vector2 q = PointAt(pts, s), q2 = PointAt(pts, Mathf.Min(total, s + .5f)), d = (q2 - q).normalized, nrm = new(-d.y, d.x);
                float y = Mathf.Lerp(h0, h1, s / total);
                foreach (int sg in new[] { -1, 1 })
                {
                    if (lamp == null) break;
                    Vector2 c = q + nrm * sg * (width * .5f - .08f);
                    var f = RFr.Yaw(new Vector3(c.x, y, c.y), Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg);
                    RBox(b, lamp, f, new Vector3(0, Mathf.Min(4.9f, clear - .6f), 0), new Vector3(.1f, .14f, 1.4f), Color.white, RALL6);
                    n++;
                }
            }
            var road = new MB();
            for (int i = 1; i < pts.Count; i++)
            {
                float sa = 0f; for (int k = 1; k < i; k++) sa += (pts[k] - pts[k - 1]).magnitude;
                Vector2 a = pts[i - 1], c = pts[i], d = (c - a).normalized, nrm = new(-d.y, d.x);
                float L = (c - a).magnitude, ya = Mathf.Lerp(h0, h1, sa / total) + .15f, yc = Mathf.Lerp(h0, h1, (sa + L) / total) + .15f;
                foreach (int sg in new[] { -1, 1 })
                {
                    Vector2 o0 = a + nrm * sg * width * .5f, o1 = c + nrm * sg * width * .5f, i0 = a + nrm * sg * (width * .5f - .8f), i1 = c + nrm * sg * (width * .5f - .8f);
                    Vector3 O0 = new(o0.x, ya, o0.y), O1 = new(o1.x, yc, o1.y), I0 = new(i0.x, ya, i0.y), I1 = new(i1.x, yc, i1.y);
                    if (sg > 0) road.Quad(I0, O0, O1, I1, i0, o0, o1, i1); else road.Quad(O0, I0, I1, O1, o0, i0, i1, o1);
                    var dn = Vector3.down * .17f;
                    if (sg > 0) road.Quad(I0 + dn, I0, I1, I1 + dn, Vector2.zero, new(0, .17f), new(L, .17f), new(L, 0)); else road.Quad(I1 + dn, I1, I0, I0 + dn, Vector2.zero, new(0, .17f), new(L, .17f), new(L, 0));
                }
            }
            var kg = MeshGo("Tunnel_kerbs", parent, road.Build("Tunnel_kerbs"), RS[kerb].M, true);
            if (lamp != null) RFlush(b, parent, "Tunnel_lamps");
            Note($"T128 tunnel: {n} lamp strips, kerbs 0.8 m, ceiling UV v 0.6-1");
            Done("T128 tunnel lamps / kerbs / ceiling UVs");
        }

        // ------------------------------------------------------------------ T67 b alley end plugs: D4 brick, a real door, lintel, downpipe
        static void AlleyPlugT67(GameObject plug, List<Vector2> pw, string id, Vector2[] alley)
        {
            if (pw.Count < 3) return;
            var mr = plug.GetComponent<MeshRenderer>(); var mf = plug.GetComponent<MeshFilter>();
            Vector3 c3 = plug.transform.position, s = plug.transform.localScale; float yaw = plug.transform.eulerAngles.y;
            var f = RFr.Yaw(new Vector3(c3.x, c3.y - s.y / 2, c3.z), yaw);
            var b = new RBatch(); Color brick = RX("6A4034");
            RBox(b, "brick_paint", f, new Vector3(0, s.y / 2, 0), s, brick, RALL5);
            // door on the face that looks into the alley
            Vector2 cen = alley.Length >= 3 ? alley.Aggregate(Vector2.zero, (a, q) => a + q) / alley.Length : new Vector2(c3.x, c3.z) - new Vector2(f.F.x, f.F.z);
            Vector2 toAlley = (cen - new Vector2(c3.x, c3.z)).normalized;
            Vector3[] outs = { -f.F, f.F, f.R, -f.R }; float[] half = { s.z / 2, s.z / 2, s.x / 2, s.x / 2 }; float[] len = { s.x, s.x, s.z, s.z };
            int best = Enumerable.Range(0, 4).OrderByDescending(k => Vector2.Dot(new Vector2(outs[k].x, outs[k].z), toAlley)).First();
            Vector3 o = outs[best];
            var wf = RFr.Yaw(new Vector3(c3.x, c3.y - s.y / 2, c3.z) + o * half[best], Mathf.Atan2(-o.x, -o.z) * Mathf.Rad2Deg);
            Color fr = RX("33463D"), stone = RX("D1C8B6");
            if (len[best] > 2.2f)
            {
                RBox(b, "flat", wf, new Vector3(0, 1.15f + .2f, -.0f), new Vector3(1.2f, 2.3f, .02f), fr, RZN);
                RBox(b, "flat", wf, new Vector3(0, 1.35f, -.05f), new Vector3(1.4f, 2.5f, .08f), RX("2A2E2C"), ROUT);
                RBox(b, "flat", wf, new Vector3(0, 2.75f, -.06f), new Vector3(1.7f, .25f, .14f), stone, RALL6);
                RCylF(b, "flat", wf.P(len[best] / 2 - .25f, .2f, -.1f), Vector3.right, Vector3.up, Vector3.forward, .055f, s.y - .2f, 8, RX("4A4E50"), false);
            }
            Object.DestroyImmediate(mr); Object.DestroyImmediate(mf);
            RFlush(b, plug.transform.parent, "AlleyPlug_" + id + "_T67");
            Done("T67 alley plugs (brick + door)");
        }

        // ------------------------------------------------------------------ DC3 mirror pool: mosaic floor, light coping ring, dark band
        static void DcPool(Transform parent, string id, Vector2[] poly, Vector2[] edge, float baseH)
        {
            var rim = parent.Find("PoolRim_" + id);
            if (rim) { var r = rim.GetComponent<MeshRenderer>(); if (r) Object.DestroyImmediate(r); }
            var b = new RBatch();
            var pts = poly.ToList(); if (Area(pts) < 0) pts.Reverse();
            string mos = T7("mosaic"), cop = T7("conc");
            var flr = Fill("tmp", pts.ToArray(), q => baseH + .02f, Vector2.zero, false);
            var vs = flr.vertices; var tr = flr.triangles; Object.DestroyImmediate(flr);
            int o0 = b[mos].V.Count;
            foreach (var v in vs) { b[mos].V.Add(v); b[mos].U.Add(new Vector2(v.x, v.z) / 1.5f); b[mos].C.Add(RX("47B4C6")); }
            for (int t = 0; t + 2 < tr.Length; t += 3) { b[mos].T.Add(o0 + tr[t]); b[mos].T.Add(o0 + tr[t + 1]); b[mos].T.Add(o0 + tr[t + 2]); }
            var f0 = RFr.Yaw(new Vector3(0, baseH, 0), 0);
            for (int i = 0; i < pts.Count; i++)
            {
                Vector2 a = pts[i], c = pts[(i + 1) % pts.Count]; float L = (c - a).magnitude;
                var w = f0.Wall(a, c);                                                     // outward (CCW)
                RWallBox(b, cop, w, -.3f, L + .3f, -.05f, .36f, .3f, DcCop);               // coping ring outside the water line
                RWall(b, mos, f0.Wall(c, a), 0, L, 0f, .34f, RX("47B4C6"));             // inner face
            }
            if (edge != null && edge.Length >= 3) DcBandRing(b, edge.Reverse().ToArray(), baseH + .05f, .5f);
            RFlush(b, parent, "DC3_pool_" + id);
            Done("DC3 pool (mosaic + coping + band)");
        }

        static void DcPlazaBand(Transform parent, Vector2[] poly)
        {
            if (poly.Length < 3) return;
            float y = poly.Average(q => Height(q.x, q.y)) + .046f;
            var b = new RBatch();
            DcBandRing(b, poly, y, .5f);
            RFlush(b, parent, "DC3_plaza_band");
            Done("DC3 plaza edge band");
        }

        // ------------------------------------------------------------------ T43 / T45 accent kinds on non-rect footprints (police 05-11,
        // rotunda, diner): the D4 look per polygon edge (brick / plaster, recessed windows, storefront glass, band + letters, cornice)
        static void PolyD4(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id, string kind)
        {
            var poly = fp.ToList(); if (Area(poly) < 0) poly.Reverse();
            float baseY = poly.Min(q => Height(q.x, q.y)) - .25f, H = F(Get(b, "height_m"), 8f), floor0 = baseY + .25f, tl = H - .25f;
            int floors = Mathf.Max(1, (int)F(Get(b, "floors"), Mathf.Max(1f, Mathf.Round(H / 3.4f))));
            bool shop = kind == "diner" || kind == "van_shop" || kind == "gas_shop";
            string wallK = shop ? "acg_plaster" : "brick_paint"; Color wc = shop ? RX("C6BBA3") : RX("7A4437"), stone = RX("D1C8B6"), frame = RX("2F3437");
            Color band = kind.StartsWith("police") ? RX("2E4A7A") : kind == "taxi_depot" ? RX("E1B53A") : RX("A33A33");
            float Gf = floors == 1 ? tl : 4.4f, Fh = floors > 1 ? (tl - Gf) / (floors - 1) : 3.4f;
            var body = new RBatch(); var det = new RBatch();
            var f = RFr.Yaw(new Vector3(0, floor0, 0), 0);
            var ents = Arr(Get(b, "entrances")).Select(Obj).Where(e => e != null && Get(e, "pos") != null).ToList();
            int longest = Enumerable.Range(0, poly.Count).OrderByDescending(i => (poly[(i + 1) % poly.Count] - poly[i]).magnitude).First();
            int signFace = ents.Count > 0 ? Enumerable.Range(0, poly.Count).OrderBy(i => DistSeg(V2(Get(ents[0], "pos")), poly[i], poly[(i + 1) % poly.Count])).First() : longest;
            for (int i = 0; i < poly.Count; i++)
            {
                Vector2 a = poly[i], c = poly[(i + 1) % poly.Count]; float L = (c - a).magnitude;
                if (L < .05f) continue;
                var w = f.Wall(a, c);
                var holes = new List<Rect>();
                if (L > 2.2f)
                {
                    int bays = Mathf.Max(1, Mathf.RoundToInt(L / 3.2f)); float bw = L / bays;
                    for (int k = 0; k < bays; k++)
                    {
                        float x = bw * (k + .5f), hw = Mathf.Min(shop ? 1.35f : .7f, bw / 2 - .3f);
                        if (hw < .3f) continue;
                        if (shop) holes.Add(Rect.MinMaxRect(x - hw, .5f, x + hw, Mathf.Min(3f, Gf - .9f)));
                        else holes.Add(Rect.MinMaxRect(x - hw, 1f, x + hw, 2.6f));
                        for (int fl = 1; fl < floors; fl++) { float yf = Gf + (fl - 1) * Fh; if (!shop) holes.Add(Rect.MinMaxRect(x - Mathf.Min(.7f, hw), yf + .8f, x + Mathf.Min(.7f, hw), yf + Mathf.Min(2.75f, Fh - .5f))); }
                    }
                }
                ROpenings(body, wallK, w, L, -.25f, tl, wc, holes, .22f);
                foreach (var o in holes)
                {
                    if (shop && o.yMin < 1f) RShopUnit(body, det, w, o, .22f, false);
                    else RWindowUnit(body, det, w, o, .22f, false, frame, stone, !shop);
                }
                if (floors > 1) RWallBox(det, "trim", w, 0, L, Gf, Gf + .4f, .1f, RS["trim"].Own);
                RWallBox(det, "flat", w, -.02f, L + .02f, tl - .45f, tl, .3f, stone);                          // cornice
                RWallBox(det, "flat", w, 0, L, -.25f, .45f, .07f, stone);                                        // plinth
                if (i == signFace && L > 3f)
                {
                    float y = floors > 1 ? Gf + .7f : Gf - .6f;
                    RWallBox(det, "flat", w, .2f, L - .2f, y - .32f, y + .32f, .12f, band);
                    int row = kind.StartsWith("police") ? 0 : kind == "taxi_depot" ? 1 : kind == "gas_shop" ? 2 : kind == "diner" ? 3 : kind == "van_shop" ? 4 : -1;
                    if (row >= 0) SignWord(det, w, row, L / 2, y, .42f, .15f);
                }
            }
            var cap = Fill("tmp", poly.ToArray(), q => floor0 + tl, Vector2.zero, false);
            var vs = cap.vertices; var tr = cap.triangles; Object.DestroyImmediate(cap);
            var mb = body["roof_flat"]; int o0 = mb.V.Count;
            foreach (var v in vs) { mb.V.Add(v); mb.U.Add(new Vector2(v.x, v.z) / 4f); mb.C.Add(RS["roof_flat"].Own); }
            for (int t = 0; t + 2 < tr.Length; t += 3) { mb.T.Add(o0 + tr[t]); mb.T.Add(o0 + tr[t + 1]); mb.T.Add(o0 + tr[t + 2]); }
            FlushInto(go, body, det, "B_" + id + "_D4poly");
            Done("T1 accent (polygon D4) " + kind);
        }

        // ------------------------------------------------------------------ build summary
        static string W86Summary()
        {
            var sb = new System.Text.StringBuilder("W86 integration: ");
            sb.Append(string.Join(", ", W86Done.OrderBy(k => k.Key).Select(k => $"{k.Key} {k.Value}")));
            if (V07Log.Count > 0) sb.Append("; v07: " + string.Join(", ", V07Log.OrderBy(k => k.Key).Select(k => $"{k.Key} {k.Value}")));
            if (DsCount.Count > 0) sb.Append("; Downtown separation: " + string.Join(" ", DsCount.OrderBy(k => k.Key).Select(k => $"{k.Key} {k.Value}")));
            if (W86Missing.Count > 0) sb.Append("; MISSING assets: " + string.Join(", ", W86Missing));
            return sb.ToString();
        }
    }
}
