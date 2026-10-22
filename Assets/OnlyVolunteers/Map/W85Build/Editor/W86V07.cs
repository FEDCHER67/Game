using System.Collections.Generic;
using System.Linq;
using OnlyVolunteers.Map.W76;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W85
{
    // W86 integration (B2, 22.10): Fedya's v07 texture choices rolled out on the map (DECISIONS_FEDYA.md):
    //  O1 offices (travertine stone grid, bronze frames), DS1 on 80 % of the ordinary Downtown houses + DS2 / DS3 on 20 %, DC3 square
    //  (cool grey), Port P1 containers + P3 buildings / fence / masts, Elite E2 (villas, garages, FBI, booth, high fence, stone road),
    //  Construction C2 (frame, core, scaffold, hoist, slab, cabins, workshop, fence, tower crane), Quiet Valley Q3 (lab, casino with a
    //  BLANK lit sign panel - no text at all, low board fence). Geometry = ports of TextureTestHousesV07 (Art/TextureTest_v01/Editor),
    //  fitted to the map footprints; materials = Built_v07/Materials/TT7_* (Palette19, colour = vertex colour, read only).
    public static partial class W85Builder
    {
        const string TT7Dir = "Assets/OnlyVolunteers/Art/TextureTest_v01/Built_v07/Materials/";
        static readonly HashSet<string> RNoShadow = new();
        static readonly Dictionary<string, float> T7Tile = new()
        {
            ["travertine"] = 2.4f, ["conc"] = 2.4f, ["panel"] = 2.4f, ["board"] = 2f, ["formwork"] = 2.4f, ["aggregate"] = 1.4f, ["slab_warm"] = 2f, ["slab_grey"] = 2f,
            ["slab_lime"] = 2f, ["stone"] = 1f, ["mosaic"] = 1.5f, ["setts"] = 1.15f, ["setts_sand"] = 1.2f, ["rubble_grey"] = 2.2f, ["rubble_warm"] = 2.2f,
            ["asph_light"] = 3f, ["ashlar"] = 2.4f, ["trapez"] = 1.5f, ["wave"] = 1.2f, ["shutter"] = 2f, ["planks"] = 1.4f, ["planks_w"] = 1.6f, ["teak"] = 1.2f,
            ["larch"] = 1.2f, ["osb"] = 1.22f, ["brick_roman"] = 1.2f, ["container"] = 1f, ["plaster"] = 3f, ["brick_d4"] = 3f, ["cinder"] = 3f, ["roof_flat"] = 4f,
            ["chain_P3"] = .8f, ["net_orange"] = 1f,
        };
        static int v07Count;
        static readonly Dictionary<string, int> V07Log = new();
        static void V07Note(string what) => V07Log[what] = V07Log.TryGetValue(what, out int n) ? n + 1 : 1;

        // TT7 surface as a rollout surface ("t7:<key>"), loaded on first use
        static string T7(string key)
        {
            string k = "t7:" + key;
            if (RS.ContainsKey(k)) return k;
            var m = AssetDatabase.LoadAssetAtPath<Material>(TT7Dir + "TT7_" + key + ".mat");
            if (!m) { RolloutIssue("TT7 material missing: " + key); m = RS["flat"].M; }
            float tu = T7Tile.TryGetValue(key, out var t) ? t : 1f;
            RS[k] = RSurfOf(m, tu, tu);
            if (key.StartsWith("glass") || key.StartsWith("water") || key.StartsWith("net") || key.StartsWith("chain")) RNoShadow.Add(k);
            return k;
        }

        // any material as a rollout surface (T1 / T2 / own emissive), tile tu
        static string RSurfKey(string key, Material m, float tu = 1f, bool noShadow = false)
        {
            if (RS.ContainsKey(key)) return key;
            RS[key] = RSurfOf(m, tu, tu);
            if (noShadow) RNoShadow.Add(key);
            return key;
        }

        static Color T7Own(string key) => RS[T7(key)].Own;
        static Color CK(string key, string hex) => hex == null ? T7Own(key) : RX(hex);

        // map-ready copy of a Palette19 material for meshes WITHOUT vertex colour (texture colour as is) and another UV unit:
        // _TintRef 1 (else the texture mean maps to white) and _BaseMap_ST = old tile / new tile
        static readonly Dictionary<string, Material> MapReadyCache = new();
        static Material MapReady(Material m, float scale)
        {
            if (!m) return null;
            string key = m.name + "_" + scale.ToString("0.###");
            if (MapReadyCache.TryGetValue(key, out var c) && c) return c;
            var cp = new Material(m) { name = "MR_" + key, enableInstancing = true };
            if (cp.HasProperty("_TintRef")) cp.SetVector("_TintRef", Vector4.one);
            if (cp.HasProperty("_BaseMap")) cp.SetTextureScale("_BaseMap", new Vector2(scale, scale));
            if (cp.HasProperty("_BumpMap")) cp.SetTextureScale("_BumpMap", new Vector2(scale, scale));
            Folder(Gen + "/Materials/W86");
            AssetDatabase.CreateAsset(cp, Gen + "/Materials/W86/" + Safe(cp.name) + ".mat"); created++;
            return MapReadyCache[key] = cp;
        }
        static Material MapReadyT7(string key, float oldTile) => MapReady(AssetDatabase.LoadAssetAtPath<Material>(TT7Dir + "TT7_" + key + ".mat"), oldTile / (T7Tile.TryGetValue(key, out var t) ? t : 1f));

        // ================================================================== geometry helpers (ports of the v07 test helpers)
        static void RBoxMM(RBatch b, string key, RFr f, Vector3 mn, Vector3 mx, Color col, int mask = RALL6) => RBox(b, key, f, (mn + mx) / 2, mx - mn, col, mask);

        static readonly Vector3[] RDirs = { Vector3.right, Vector3.left, Vector3.forward, Vector3.back, Vector3.up, Vector3.down };
        static void ROBox(RBatch b, string key, Vector3 c, Vector3 Xa, Vector3 Ya, Vector3 Za, Vector3 size, Color col, bool bottom = true)
        {
            var s = RS[key];
            foreach (var n in RDirs)
            {
                if (n == Vector3.down && !bottom) continue;
                Vector3 ua = Mathf.Abs(n.y) > .5f ? Vector3.forward : Vector3.up, ra = Vector3.Cross(n, ua);
                float hw = RExt(size, ra) / 2, hh = RExt(size, ua) / 2;
                Vector3 fc = n * RExt(size, n) / 2;
                Vector3 Lp(Vector3 p) => c + Xa * p.x + Ya * p.y + Za * p.z;
                Vector3 wa = Xa * ra.x + Ya * ra.y + Za * ra.z, wu = Xa * ua.x + Ya * ua.y + Za * ua.z;
                Vector3 a = Lp(fc - ra * hw - ua * hh), bb = Lp(fc - ra * hw + ua * hh), cc = Lp(fc + ra * hw + ua * hh), d = Lp(fc + ra * hw - ua * hh);
                Vector2 Uv(Vector3 p) => new(Vector3.Dot(p, wa) / s.TU, Vector3.Dot(p, wu) / s.TV);
                b[key].Quad(a, bb, cc, d, Uv(a), Uv(bb), Uv(cc), Uv(d), col);
            }
        }

        static void RBeam(RBatch b, string key, Vector3 p0, Vector3 p1, float w, float h, Color col)
        {
            Vector3 d = p1 - p0; float L = d.magnitude; if (L < 1e-4f) return;
            Vector3 Za = d / L, up = Mathf.Abs(Za.y) > .95f ? Vector3.forward : Vector3.up;
            Vector3 Xa = Vector3.Cross(up, Za).normalized, Ya = Vector3.Cross(Za, Xa);
            ROBox(b, key, (p0 + p1) / 2, Xa, Ya, Za, new Vector3(w, h, L), col);
        }

        static void RCylF(RBatch b, string key, Vector3 c, Vector3 Xa, Vector3 Ya, Vector3 Za, float r, float h, int n, Color col, bool top = true, bool bottom = false, float r2 = -1f)
        {
            if (r2 < 0) r2 = r;
            var s = RS[key]; var mb = b[key];
            float circ = 2 * Mathf.PI * r;
            Vector3 D(float a) => Xa * Mathf.Sin(a) + Za * Mathf.Cos(a);
            Vector3 tc = c + Ya * h;
            for (int i = 0; i < n; i++)
            {
                float a0 = 2 * Mathf.PI * i / n, a1 = 2 * Mathf.PI * (i + 1) / n;
                Vector3 b0 = c + D(a0) * r, b1 = c + D(a1) * r, t0 = tc + D(a0) * r2, t1 = tc + D(a1) * r2;
                float u0 = circ * i / n / s.TU, u1 = circ * (i + 1) / n / s.TU, v1 = h / s.TV;
                mb.Quad(b1, t1, t0, b0, new(u1, 0), new(u1, v1), new(u0, v1), new(u0, 0), col);
                if (top) { int k = mb.V.Count; mb.V.Add(tc); mb.V.Add(t0); mb.V.Add(t1); mb.U.Add(new(.5f, .5f)); mb.U.Add(new(.5f, .6f)); mb.U.Add(new(.6f, .5f)); mb.C.Add(col); mb.C.Add(col); mb.C.Add(col); mb.T.Add(k); mb.T.Add(k + 1); mb.T.Add(k + 2); }
                if (bottom) { int k = mb.V.Count; mb.V.Add(c); mb.V.Add(b1); mb.V.Add(b0); mb.U.Add(new(.5f, .5f)); mb.U.Add(new(.5f, .6f)); mb.U.Add(new(.6f, .5f)); mb.C.Add(col); mb.C.Add(col); mb.C.Add(col); mb.T.Add(k); mb.T.Add(k + 1); mb.T.Add(k + 2); }
            }
        }
        static void RCyl(RBatch b, string key, Vector3 c, float r, float h, int n, Color col, bool top = true, float r2 = -1f) => RCylF(b, key, c, Vector3.right, Vector3.up, Vector3.forward, r, h, n, col, top, false, r2);
        static void RCylAx(RBatch b, string key, Vector3 c, Vector3 axis, float r, float len, int n, Color col)
        {
            Vector3 Ya = axis.normalized, Xa = Vector3.Cross(Ya, Mathf.Abs(Ya.y) > .9f ? Vector3.right : Vector3.up).normalized, Za = Vector3.Cross(Xa, Ya);
            RCylF(b, key, c - Ya * len / 2, Xa, Ya, Za, r, len, n, col, true, true);
        }

        // glass pane with one cell of the 4 x 4 office glass atlas (v07 Pane)
        static void RPane(RBatch b, string key, RFr w, Rect o, float z, int cell)
        {
            int cx = cell % 4, cy = (cell / 4) % 4; const float e = .012f;
            var uv = Rect.MinMaxRect(cx / 4f + e, cy / 4f + e, (cx + 1) / 4f - e, (cy + 1) / 4f - e);
            b[key].Quad(w.P(o.xMin, o.yMin, z), w.P(o.xMin, o.yMax, z), w.P(o.xMax, o.yMax, z), w.P(o.xMax, o.yMin, z),
                new(uv.xMin, uv.yMin), new(uv.xMin, uv.yMax), new(uv.xMax, uv.yMax), new(uv.xMax, uv.yMin), Color.white);
        }
        static int RCell(string id) => (int)(RHash(id, 5) * 16) % 16;

        // office window (v07 OfficeWindow): atlas glass, frame profile t, mullions, transom, optional sill
        static void ROfficeWin(RBatch b, RFr w, Rect o, float r, string glass, Color frame, string id, int mull, float transom, Color? sill, float t = .06f)
        {
            RPane(b, glass, w, o, r + .005f, RCell(id));
            float zc = r - .03f; string fm = T7("flat_metal");
            RBox(b, fm, w, new Vector3(o.center.x, o.yMin + t / 2, zc), new Vector3(o.width, t, .07f), frame, RALL6);
            RBox(b, fm, w, new Vector3(o.center.x, o.yMax - t / 2, zc), new Vector3(o.width, t, .07f), frame, RALL6);
            RBox(b, fm, w, new Vector3(o.xMin + t / 2, o.center.y, zc), new Vector3(t, o.height, .07f), frame, RALL6);
            RBox(b, fm, w, new Vector3(o.xMax - t / 2, o.center.y, zc), new Vector3(t, o.height, .07f), frame, RALL6);
            for (int k = 1; k <= mull; k++) RBox(b, fm, w, new Vector3(o.xMin + o.width * k / (mull + 1), o.center.y, zc), new Vector3(t * .9f, o.height, .08f), frame, RALL6);
            if (transom > 0) RBox(b, fm, w, new Vector3(o.center.x, o.yMin + o.height * transom, zc), new Vector3(o.width, t * .9f, .08f), frame, RALL6);
            if (sill.HasValue) RBox(b, T7("flat"), w, new Vector3(o.center.x, o.yMin - .03f, (r - .07f) / 2), new Vector3(o.width + .12f, .06f, r + .07f), sill.Value, RALL6);
        }

        // ================================================================== building frame (front = entrance side = local -Z)
        struct BFr { public RFr F; public float W, D, Y0, Base, Top, H, Tl; public Vector2 C; }
        static BFr BFrameOf(Dictionary<string, object> b, List<Vector2> fp, float? facing = null, float? height = null)
        {
            Frame(fp, new Dictionary<string, object>(), out Vector2 c, out Vector2 ax, out Vector2 ay, out float hx, out float hy);
            var e0 = Arr(Get(b, "entrances")).Select(Obj).FirstOrDefault(e => e != null && Get(e, "facing_deg") != null);
            float fdeg = facing ?? (e0 != null ? F(Get(e0, "facing_deg")) : 270f);
            Vector2 dir = new(Mathf.Cos(fdeg * Mathf.Deg2Rad), Mathf.Sin(fdeg * Mathf.Deg2Rad));
            Vector2 front = new[] { ax, -ax, ay, -ay }.OrderByDescending(v => Vector2.Dot(v, dir)).First();
            bool alongX = Mathf.Abs(Vector2.Dot(front, ax)) > .5f;
            float W = alongX ? 2 * hy : 2 * hx, D = alongX ? 2 * hx : 2 * hy;
            float yaw = Mathf.Atan2(-front.x, -front.y) * Mathf.Rad2Deg;
            float g0 = fp.Min(q => Height(q.x, q.y));
            float H = height ?? F(Get(b, "height_m"), 3f);
            return new BFr { F = RFr.Yaw(new Vector3(c.x, g0, c.y), yaw), W = W, D = D, Y0 = g0, Base = g0 - .25f, Top = g0 - .25f + H, H = H, Tl = H - .25f, C = c };
        }

        static Vector2[] LocalRect(float W, float D) => new[] { new Vector2(-W / 2, -D / 2), new Vector2(W / 2, -D / 2), new Vector2(W / 2, D / 2), new Vector2(-W / 2, D / 2) };

        // entrance positions on a face (local s along the face), by facing / nearest face
        static List<(float s, Dictionary<string, object> e)> EntsOnFace(Dictionary<string, object> b, BFr bf, Vector2 a, Vector2 e2)
        {
            var o = new List<(float, Dictionary<string, object>)>();
            Vector3 A = bf.F.P(a.x, 0, a.y), E = bf.F.P(e2.x, 0, e2.y);
            Vector2 A2 = new(A.x, A.z), E2 = new(E.x, E.z); float L = (E2 - A2).magnitude;
            foreach (var en in Arr(Get(b, "entrances")).Select(Obj).Where(x => x != null && Get(x, "pos") != null))
            {
                Vector2 p = V2(Get(en, "pos"));
                float s = Vector2.Dot(p - A2, (E2 - A2) / L), off = Mathf.Abs(Cross(A2, E2, p)) / L;
                if (s > -.5f && s < L + .5f && off < 1.2f) o.Add((Mathf.Clamp(s, 0f, L), en));
            }
            return o;
        }

        // keep the W85 colliders (+ roof test entry), drop the generic visuals
        static void StripVisuals(Transform go, params string[] keep)
        {
            foreach (Transform c in go.Cast<Transform>().ToList())
                if (c.name != "colliders" && !keep.Contains(c.name)) Object.DestroyImmediate(c.gameObject);
            var lod = go.GetComponent<LODGroup>(); if (lod) Object.DestroyImmediate(lod);
            foreach (var r in go.GetComponents<Renderer>()) Object.DestroyImmediate(r);
        }

        static void FlushInto(Transform go, RBatch body, RBatch det, string name)
        {
            var bodyT = go.Find("body") ?? new GameObject("body").transform; bodyT.SetParent(go, false);
            var details = go.Find("details") ?? new GameObject("details").transform; details.SetParent(go, false);
            RFlush(body, bodyT, name);
            if (det != null) RFlush(det, details, name + "_det");
            RolloutLod(go.gameObject, details);
        }

        // ================================================================== DS1 / DS2 / DS3 (Fedya: DS1 on 80 % of ordinary houses, DS2 / DS3 20 %)
        static string DsOf(string id) { float h = RHash(id, 71); return h < .8f ? "DS1" : h < .9f ? "DS2" : "DS3"; }
        static readonly Dictionary<string, int> DsCount = new();

        static void ApplyDs(SepP sp, string id, int floors)
        {
            string ds = DsOf(id);
            DsCount[ds] = DsCount.TryGetValue(ds, out int n) ? n + 1 : 1;
            sp.Ds = ds; sp.On = true;
            int i = (int)(RHash(id, 72) * 7);
            if (ds == "DS1")
            {   // own corner pilasters (stone) or quoins + own cornice height / profile: a visible break at every party wall
                sp.Quoins = i % 2 == 1; sp.PilW = sp.Quoins ? 0f : .55f; sp.PilP = .12f; sp.PilTone = "stone";
                int cor = new[] { 2, 3, 1, 2, 3, 2, 1 }[i];
                sp.Cornice = cor == 2 ? "stepped" : cor == 3 ? "dentil" : "flat_band"; sp.CorniceH = cor == 2 ? .75f : cor == 3 ? .7f : .4f; sp.CorniceP = cor == 2 ? .5f : cor == 3 ? .45f : .35f;
                sp.Break = true; sp.CorCol = new[] { "DCD4C4", "E2DBCD", "CFC7B6", "D8D1C3", "BDB5A5", "E4DDD0", "D2CBBB" }[i];
                sp.PilCol = new[] { "D8D0C0", "D9D2C4", "CBC3B2", "DAD3C6", "B9B2A3", "E0D9CB", "C9C1B0" }[i];
            }
            else if (ds == "DS2")
            {   // alternating building line, recessed shadow gaps at the party walls, downpipes, plain / no cornice
                sp.Setback = RHash(id, 73) < .5f ? 1f : 0f; sp.JointW = .6f; sp.Downpipe = true; sp.PilW = 0f; sp.Quoins = false;
                sp.Cornice = RHash(id, 74) < .5f ? "flat_band" : "none"; sp.CorniceH = .4f; sp.CorniceP = .35f; sp.CorCol = "D3CCBE"; sp.Break = true;
            }
            else
            {   // different base (rusticated), string course, window types, trim colours, cornice per house, downpipe
                sp.Rustic = i % 2 == 1; sp.StringCol = new[] { "E4DCCB", "CFC6B3", "D9D0BD", "C7BFAE", "E9E2D3", "BFB6A4", "DED6C6" }[i];
                sp.StringFl = i % 2 == 0 ? 1 : 2; int wt = new[] { 3, 1, 0, 2, 3, 1, 0 }[i];
                sp.Paired = wt == 1; sp.Hood = wt == 3; sp.Lintel = wt == 2 || sp.Lintel;
                int cor = new[] { 2, 1, 3, 0, 2, 3, 1 }[i];
                sp.Cornice = cor == 2 ? "stepped" : cor == 3 ? "dentil" : cor == 1 ? "flat_band" : "none"; sp.CorniceH = cor == 2 ? .75f : cor == 3 ? .7f : .4f; sp.CorniceP = .4f; sp.CorCol = sp.StringCol;
                sp.FrameCol = new[] { "E4DFD3", "2F3437", "E9E4D8", "33463D", "E4DFD3", "4A3A30", "2F3437" }[i];
                sp.JointW = Mathf.Max(sp.JointW, .14f); sp.Downpipe = true; sp.Break = true; sp.PilW = 0f; sp.Quoins = false;
            }
        }

        // ================================================================== O1 offices (stone grid: travertine, bronze frames, dark granite base)
        static bool RolloutOfficeO1(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id, string district)
        {
            var roof = Obj(Get(b, "roof")) ?? new Dictionary<string, object> { ["type"] = "flat" };
            int floors = Mathf.Clamp((int)F(Get(b, "floors"), 6f), 2, 12);
            float Fh = 3.6f, Gf = 4.5f, H = Gf + (floors - 1) * Fh;
            var ents = Arr(Get(b, "entrances")).Select(Obj).Where(e => e != null && Get(e, "pos") != null).ToList();
            var kinds = D4Faces(fp, id, ents, out float floor0);
            float baseY = Mathf.Min(fp.Min(q => Height(q.x, q.y)) - .25f, floor0 - .4f);
            float top = floor0 + H, yb = baseY - floor0, tl = H;
            string clad = T7("travertine"), stoneK = T7("stone"), fm = T7("flat_metal"), glass = T7("glass_o1");
            Color cl = RX("E2D8C6"), frame = RX("4B4239"), sill = RX("D6CDBD"), dk = RX("4A4B4E");
            var body = new RBatch(); var det = new RBatch();
            var f = RFr.Yaw(new Vector3(0, floor0, 0), 0);
            var mainDoor = ents.FirstOrDefault(e => (S(Get(e, "role"), "") ?? "").Contains("main")) ?? ents.FirstOrDefault();
            for (int i = 0; i < 4; i++)
            {
                Vector2 p0 = fp[i], p1 = fp[(i + 1) % 4];
                var w = f.Wall(p0, p1); float L = (p1 - p0).magnitude;
                if (kinds[i] == 2 || L < 3f) { RWall(body, clad, w, 0, L, yb, tl + .9f, cl); continue; }
                bool street = kinds[i] == 1;
                int bays = Mathf.Max(1, Mathf.RoundToInt(L / 3.2f)); float bw = L / bays;
                float Bay(int k) => bw * (k + .5f);
                float hw = Mathf.Min(1.15f, bw / 2 - .33f);
                var holes = new List<Rect>();
                for (int fl = 1; fl < floors; fl++) { float yf = Gf + (fl - 1) * Fh; for (int k = 0; k < bays; k++) holes.Add(Rect.MinMaxRect(Bay(k) - hw, yf + .85f, Bay(k) + hw, yf + 3.15f)); }
                ROpenings(body, clad, w, L, Gf, tl + .9f, cl, holes, .32f);
                int n = 0; foreach (var o in holes) ROfficeWin(det, w, o, .32f, glass, frame, id + i + "_" + n++, 1, .72f, sill);
                for (int k = 0; k <= bays; k++) { float s = k * bw; RWallBox(det, clad, w, Mathf.Max(0, s - .33f), Mathf.Min(L, s + .33f), Gf, tl + .9f, .14f, cl); }
                for (int fl = 1; fl < floors; fl++) RWallBox(det, clad, w, 0, L, Gf + (fl - 1) * Fh - .12f, Gf + (fl - 1) * Fh + .12f, .06f, cl);
                // base: dark granite, tall glazing on the street (recessed entrance with a canopy), smaller windows elsewhere
                float sDoor = -1f;
                if (mainDoor != null && street)
                {
                    Vector2 dp = V2(Get(mainDoor, "pos")); float s = Vector2.Dot(dp - p0, (p1 - p0) / L);
                    if (s > -.2f && s < L + .2f && Mathf.Abs(Cross(p0, p1, dp)) / L < 1.2f) sDoor = Mathf.Clamp(s, 3f, L - 3f);
                }
                var gh = new List<Rect>();
                for (int k = 0; k < bays; k++)
                {
                    float cx = Bay(k);
                    if (sDoor >= 0f && Mathf.Abs(cx - sDoor) < 3.2f) continue;
                    if (street) gh.Add(Rect.MinMaxRect(cx - Mathf.Min(1.3f, bw / 2 - .25f), .35f, cx + Mathf.Min(1.3f, bw / 2 - .25f), 3.95f));
                    else if (k % 2 == 0) gh.Add(Rect.MinMaxRect(cx - Mathf.Min(1f, bw / 2 - .3f), 1.1f, cx + Mathf.Min(1f, bw / 2 - .3f), 3.4f));
                }
                if (sDoor >= 0f) gh.Add(Rect.MinMaxRect(sDoor - 2.9f, 0f, sDoor + 2.9f, 3.95f));
                ROpenings(body, stoneK, w, L, yb, Gf, dk, gh, .3f);
                n = 0;
                foreach (var o in gh)
                {
                    bool door = o.yMin < .01f;
                    ROfficeWin(det, w, o, door ? 1.2f : .3f, glass, frame, id + "g" + i + "_" + n++, door ? 3 : 1, door ? .7f : .75f, null, .08f);
                    if (door)
                    {   // recess reveals + soffit, canopy
                        foreach (float s in new[] { o.xMin, o.xMax }) RBox(body, stoneK, w, new Vector3(s, Gf / 2 - .2f, .6f), new Vector3(.02f, Gf - .4f, 1.2f), dk, RALL6);
                        RBox(body, T7("flat"), w, new Vector3(o.center.x, o.yMax + .005f, .6f), new Vector3(o.width, .01f, 1.2f), RX("D9D4CA"), RALL6);
                        RWallBox(det, fm, w, o.center.x - 4f, o.center.x + 4f, Gf - .3f, Gf - .05f, 2.4f, RX("3A3C3F"));
                    }
                }
                RWallBox(det, fm, w, -.02f, L + .02f, tl + .9f, tl + 1.05f, .2f, RX("8C8478"));           // coping
            }
            // party walls rise to the coping; roof, plant room
            Frame(fp, new Dictionary<string, object>(), out Vector2 rc, out Vector2 rax, out Vector2 ray, out float rhx, out float rhy);
            var rf = RFr.Yaw(new Vector3(rc.x, floor0, rc.y), Mathf.Atan2(ray.x, ray.y) * Mathf.Rad2Deg);
            RPlane(body, "roof_flat", rf, -rhx, -rhy, rhx, rhy, tl, RS["roof_flat"].Own);
            RBox(body, T7("trapez"), rf, new Vector3(rhx * .3f, tl + 1.6f, rhy * .25f), new Vector3(Mathf.Min(10f, rhx), 3.2f, Mathf.Min(6f, rhy)), RX("A8ADB0"), RALL5);
            FlushInto(go, body, det, "B_" + id + "_O1");
            Colliders(go, id, fp, baseY, top, "flat", roof, new List<Arch>());
            Built.Add(new BInfo { Go = go.gameObject, Id = district + "/" + id, Fp = fp, Base = baseY, Top = top, Type = "flat", Roof = roof });
            rolledO++;
            return true;
        }

        // ================================================================== DC3 square (cool grey): plaza band, pool, bollards, tall lamps, flags, pavilions
        static readonly Color DcBand = new(.227f, .239f, .259f), DcCop = new(.827f, .824f, .804f);
        static Material dcPaving;
        static Material DcPaving() => dcPaving ? dcPaving : dcPaving = MapReadyT7("slab_grey", Tile("plaza_M3"));

        // dark 0.5 m band along a polygon edge (inside), on top of a flat surface at y
        static void DcBandRing(RBatch b, Vector2[] poly, float y, float w)
        {
            var pts = poly.ToList(); if (Area(pts) < 0) pts.Reverse();
            string k = T7("stone");
            var f = RFr.Yaw(Vector3.zero, 0);
            for (int i = 0; i < pts.Count; i++)
            {
                Vector2 a = pts[i], c = pts[(i + 1) % pts.Count], d = (c - a).normalized, n = new(-d.y, d.x);     // CCW: left = inside
                Vector2 a2 = a + n * w, c2 = c + n * w;
                b[k].Quad(new Vector3(a.x, y, a.y), new Vector3(a2.x, y, a2.y), new Vector3(c2.x, y, c2.y), new Vector3(c.x, y, c.y), a, a2, c2, c, DcBand);
            }
        }

        static void DcTallLamp(RBatch b, Vector3 at, Color col, Color banner, bool east)
        {
            string fm = T7("flat_metal");
            RCyl(b, fm, at, .14f, .5f, 12, col);
            RCyl(b, fm, at, .09f, 6.2f, 12, col);
            float sx = east ? -1 : 1;
            RBeam(b, fm, at + new Vector3(0, 5.9f, 0), at + new Vector3(sx * 1.1f, 6.15f, 0), .07f, .07f, col);
            var g = RFr.Yaw(Vector3.zero, 0);
            RBox(b, fm, g, at + new Vector3(sx * 1.15f, 6.05f, 0), new Vector3(.55f, .16f, .3f), col, RALL6);
            RBox(b, T7("flat_gloss"), g, at + new Vector3(sx * 1.15f, 5.95f, 0), new Vector3(.45f, .04f, .22f), RX("F3EFE2"), RALL6);
            RBox(b, T7("flat"), g, at + new Vector3(-sx * .32f, 4.2f, 0), new Vector3(.5f, 1.8f, .03f), banner, RALL6);
            RBox(b, fm, g, at + new Vector3(-sx * .32f, 5.13f, 0), new Vector3(.62f, .04f, .04f), col, RALL6);
        }

        // DC3 pavilion on a footprint: glass panes between thin dark mullions, dark roof slab with a light trim, plinth
        static void DcPavilion(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id)
        {
            var bf = BFrameOf(b, fp);
            float H = Mathf.Clamp(bf.Tl, 3.2f, 4.2f);
            var body = new RBatch(); var det = new RBatch();
            string gk = T7("glass_dc_D6D4CE"), fm = T7("flat_metal");
            Color kc = RX("383C40"), trim = RX("D6D4CE");
            var rect = LocalRect(bf.W, bf.D);
            RBox(body, T7("flat"), bf.F, new Vector3(0, -.05f, 0), new Vector3(bf.W + .4f, .3f, bf.D + .4f), DcCop, RALL5);
            for (int i = 0; i < 4; i++)
            {
                var w = bf.F.Wall(rect[i], rect[(i + 1) % 4]); float L = (rect[(i + 1) % 4] - rect[i]).magnitude;
                int n = Mathf.Max(1, Mathf.RoundToInt(L / 1.5f)); float pw = L / n;
                for (int k = 0; k < n; k++) RPane(body, gk, w, Rect.MinMaxRect(k * pw, .2f, (k + 1) * pw, H), .02f, RCell(id + i + k));
                for (int k = 0; k <= n; k++) RBox(det, fm, w, new Vector3(k * pw, H / 2 + .1f, 0), new Vector3(.08f, H - .2f, .1f), kc, RALL6);
                RBox(det, fm, w, new Vector3(L / 2, 1f, 0), new Vector3(L, .06f, .08f), kc, RALL6);
            }
            RBox(body, fm, bf.F, new Vector3(0, H + .25f, 0), new Vector3(bf.W + 1.4f, .5f, bf.D + 1.4f), kc, RALL6);
            RBox(det, fm, bf.F, new Vector3(0, H + .02f, 0), new Vector3(bf.W + 1.5f, .06f, bf.D + 1.5f), trim, RALL6);
            FlushInto(go, body, det, "B_" + id + "_DC3");
            V07Note("DC3 pavilion");
        }

        // ================================================================== Port P3 (buildings), P1 containers, P3 masts / fence
        static void PortP3(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id, string kind)
        {
            var bf = BFrameOf(b, fp);
            float H = bf.Tl, ph = .6f, band = H > 6f ? 4.8f : Mathf.Max(1.6f, H * .6f);
            bool pitched = (S(Get(Obj(Get(b, "roof")), "type"), "flat") ?? "flat") != "flat";
            var body = new RBatch(); var det = new RBatch();
            string fm = T7("flat_metal"), wave = T7("wave"), trapez = T7("trapez"), conc = T7("conc");
            Color wallC = RX("B9BEC0"), upC = RX("5E8E86"), trim = RX("F0F0EC"), shut = RX("EEEEEA"), plin = RX("C4C0B8");
            var rect = LocalRect(bf.W, bf.D);
            float yb = -.25f;
            for (int i = 0; i < 4; i++)
            {
                Vector2 a = rect[i], e = rect[(i + 1) % 4];
                var w = bf.F.Wall(a, e); float L = (e - a).magnitude;
                var holes = new List<Rect>();
                foreach (var (s, en) in EntsOnFace(b, bf, a, e))
                {
                    string k = S(Get(en, "kind"), "door") ?? "door";
                    bool big = k.Contains("roll") || k.Contains("garage");
                    float hw = big ? 2.5f : .5f, hh = big ? Mathf.Min(5.2f, H - 1f) : 2.2f;
                    float sc = Mathf.Clamp(s, hw + .3f, L - hw - .3f);
                    holes.Add(Rect.MinMaxRect(sc - hw, 0, sc + hw, hh));
                }
                if (i == 0 && holes.Count == 0 && L > 2.4f) holes.Add(Rect.MinMaxRect(L / 2 - .5f, 0, L / 2 + .5f, Mathf.Min(2.2f, H - .4f)));
                if (i == 0 && kind == "warehouse" && holes.Count > 0) { var h0 = holes[0]; if (h0.width > 3f && h0.xMax + 1.6f < L) holes.Add(Rect.MinMaxRect(h0.xMax + .9f, 0, h0.xMax + 1.9f, 2.2f)); }
                var plinthHoles = holes.Where(h => h.yMin < ph).Select(h => Rect.MinMaxRect(h.xMin, yb, h.xMax, Mathf.Min(h.yMax, ph))).ToList();
                ROpenings(body, conc, w, L, yb, ph, plin, plinthHoles, .1f);
                ROpenings(body, wave, w, L, ph, Mathf.Min(band, H), wallC, holes, .1f);
                if (H > band + .2f) ROpenings(body, trapez, w, L, band, H, upC, holes, .1f);
                RWallBox(det, fm, w, 0, L, band - .1f, band + .25f, .08f, trim);
                if (H > 7f && (i == 0 || i == 2)) for (float s = 3f; s < L - 3f; s += 6f) { RBox(det, T7("flat_gloss"), w, new Vector3(s + 1.5f, H - 2f, -.02f), new Vector3(3.6f, .9f, .04f), RX("C9D3D6"), RALL6); RBox(det, fm, w, new Vector3(s + 1.5f, H - 2f, -.03f), new Vector3(3.8f, 1.1f, .02f), trim, RALL6); }
                else if (H <= 7f && i != 0 && L > 2.5f) { RBox(det, T7("flat_gloss"), w, new Vector3(L / 2, Mathf.Min(1.9f, H - .7f), -.02f), new Vector3(Mathf.Min(1.4f, L - 1f), .8f, .04f), RX("C9D3D6"), RALL6); RBox(det, fm, w, new Vector3(L / 2, Mathf.Min(1.9f, H - .7f), -.03f), new Vector3(Mathf.Min(1.6f, L - .8f), 1f, .02f), trim, RALL6); }
                foreach (var h in holes)
                {
                    bool big = h.width > 3f;
                    RBox(det, big ? T7("shutter") : fm, w, new Vector3(h.center.x, h.center.y, .12f), new Vector3(h.width, h.height, .02f), big ? shut : RX("5C6266"), RALL6);
                    RWallBox(det, fm, w, h.xMin - .2f, h.xMin, 0, h.yMax + .2f, .1f, trim);
                    RWallBox(det, fm, w, h.xMax, h.xMax + .2f, 0, h.yMax + .2f, .1f, trim);
                    RWallBox(det, fm, w, h.xMin - .2f, h.xMax + .2f, h.yMax, h.yMax + .2f, .1f, trim);
                    if (big) RWallBox(det, fm, w, h.xMin - .3f, h.xMax + .3f, h.yMax + .2f, h.yMax + .7f, .45f, trim);
                }
                RWallBox(det, fm, w, -.15f, .15f, yb, H + .3f, .15f, trim);
                if (!pitched) RWallBox(det, fm, w, -.1f, L + .1f, H, H + .35f, .12f, trim);
            }
            if (!pitched) RPlane(body, wave, bf.F, -bf.W / 2, -bf.D / 2, bf.W / 2, bf.D / 2, H + .02f, RX("A9AEB0"));
            FlushInto(go, body, det, "B_" + id + "_P3");
            V07Note("P3 " + kind);
        }

        // ISO container 20 / 40 ft (v07 Container): one atlas material, vertex tint; door end +X
        static void RContainer(RBatch b, Vector3 at, bool forty, float yaw, Color col, Vector3 size)
        {
            float L = size.x > 1f ? size.x : forty ? 12.19f : 6.06f, W = size.z > 1f ? size.z : 2.44f, H = size.y > 1f ? size.y : 2.59f;
            var f = RFr.Yaw(at, yaw);
            string ck = T7("container");
            var mb = b[ck];
            int reps = L > 9f ? 4 : 2; float seg = L / reps;
            void Face(Vector3 a, Vector3 bb, Vector3 c, Vector3 d, float u0, float u1) => mb.Quad(f.P(a), f.P(bb), f.P(c), f.P(d), new(u0, 0), new(u0, 1), new(u1, 1), new(u1, 0), col);
            for (int k = 0; k < reps; k++)
            {
                float x0 = -L / 2 + k * seg, x1 = x0 + seg;
                Face(new(x0, 0, -W / 2), new(x0, H, -W / 2), new(x1, H, -W / 2), new(x1, 0, -W / 2), 0f, .5f);
                Face(new(x1, 0, W / 2), new(x1, H, W / 2), new(x0, H, W / 2), new(x0, 0, W / 2), 0f, .5f);
                mb.Quad(f.P(x0, H, -W / 2), f.P(x0, H, W / 2), f.P(x1, H, W / 2), f.P(x1, H, -W / 2), new(0, .1f), new(0, .9f), new(.5f, .9f), new(.5f, .1f), col);
            }
            Face(new(L / 2, 0, -W / 2), new(L / 2, H, -W / 2), new(L / 2, H, W / 2), new(L / 2, 0, W / 2), .5f, .75f);
            Face(new(-L / 2, 0, W / 2), new(-L / 2, H, W / 2), new(-L / 2, H, -W / 2), new(-L / 2, 0, -W / 2), .75f, 1f);
            Color dk = col * .55f; dk.a = 1;
            foreach (float x in new[] { -L / 2 + .09f, L / 2 - .09f }) foreach (float z in new[] { -W / 2 + .09f, W / 2 - .09f }) foreach (float y in new[] { .06f, H - .06f })
                RBox(b, T7("flat_metal"), f, new Vector3(x, y, z), new Vector3(.19f, .13f, .19f), dk, RALL6);
        }
        static readonly string[] P1Colours = { "A8473A", "3E6A9A", "4E7A52", "C8743A", "D9D7D0", "8A6A4A" };

        // P3 light mast: tapered pole 20 m, head with three lamps
        static void P3Mast(RBatch b, Vector3 at, float h)
        {
            string fm = T7("flat_metal"); Color c = RX("D9DBDC");
            RCyl(b, fm, at, .28f, h, 12, c, true, .18f);
            var g = RFr.Yaw(Vector3.zero, 0);
            RBox(b, fm, g, at + new Vector3(0, h + .3f, 0), new Vector3(2.6f, .5f, .5f), c, RALL6);
            for (int k = -1; k <= 1; k++) RBox(b, T7("flat_gloss"), g, at + new Vector3(k * .8f, h - .1f, -.2f), new Vector3(.6f, .4f, .2f), RX("EDEBE2"), RALL6);
        }

        // ================================================================== Elite E2
        static readonly Color E2Villa = new(.937f, .902f, .839f), E2Upper = new(.914f, .863f, .776f), E2Frame = new(.231f, .192f, .157f), E2Gate = new(.29f, .227f, .173f), E2Cap = new(.788f, .769f, .729f);

        static void EliteVilla(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id, bool garage)
        {
            var bf = BFrameOf(b, fp);
            float H = bf.Tl, g1 = garage ? H : Mathf.Min(3.4f, H * .5f);
            var body = new RBatch(); var det = new RBatch();
            string pl = T7("plaster"), fm = T7("flat_metal"), gk = T7("glass_villa");
            var f0 = RFr.Yaw(new Vector3(0, bf.Y0, 0), 0);
            var poly = fp.ToList(); if (Area(poly) < 0) poly.Reverse();
            Vector3 frontW = bf.F.F * -1f;                                          // entrance side outward (world)
            for (int lvl = 0; lvl < (garage ? 1 : 2); lvl++)
            {
                float y0 = lvl == 0 ? -.25f : g1, y1 = lvl == 0 ? g1 : H;   // H = roof level (generic collider top)
                Color col = lvl == 0 ? E2Villa : E2Upper;
                var fl = RFr.Yaw(new Vector3(0, bf.Y0 + y0, 0), 0);
                for (int i = 0; i < poly.Count; i++)
                {
                    Vector2 a = poly[i], e = poly[(i + 1) % poly.Count];
                    var w = fl.Wall(a, e); float L = (e - a).magnitude, h = y1 - y0;
                    if (L < .3f) continue;
                    Vector3 outN = w.Out;
                    float facing = Vector3.Dot(outN, frontW);
                    var holes = new List<Rect>();
                    if (garage)
                    {
                        if (facing > .7f && L > 4f) holes.Add(Rect.MinMaxRect(L / 2 - 2.6f, .25f, L / 2 + 2.6f, Mathf.Min(2.75f, h - .3f)));
                    }
                    else if (facing < -.3f && L > 4f)
                    {   // garden side: big glazing (ground floor to the floor, upper ribbon)
                        float pane = lvl == 0 ? 3f : 2.2f, sill = lvl == 0 ? .25f : .55f, gh = lvl == 0 ? Mathf.Min(3f, h - .4f) : Mathf.Min(2.5f, h - .7f);
                        int n = Mathf.FloorToInt((L - 1.6f) / pane);
                        if (n > 0) { float st = (L - n * pane) / 2; holes.Add(Rect.MinMaxRect(st, sill, st + n * pane, sill + gh)); }
                    }
                    else if (L > 5f)
                    {
                        float hw = Mathf.Min(1f, L / 6f);
                        holes.Add(Rect.MinMaxRect(L * .3f - hw, lvl == 0 ? .6f : .7f, L * .3f + hw, lvl == 0 ? 2.6f : 2.6f));
                        if (L > 10f) holes.Add(Rect.MinMaxRect(L * .7f - hw, lvl == 0 ? .6f : .7f, L * .7f + hw, 2.6f));
                    }
                    ROpenings(body, pl, w, L, 0, h, col, holes, .15f);
                    foreach (var o in holes)
                    {
                        if (garage) { RBox(det, T7("shutter"), w, new Vector3(o.center.x, o.center.y, .12f), new Vector3(o.width, o.height, .02f), RX("7A7C7E"), RALL6); continue; }
                        int n = Mathf.Max(1, Mathf.RoundToInt(o.width / 3f)); float pw = o.width / n;
                        for (int j = 0; j < n; j++) RPane(body, gk, w, Rect.MinMaxRect(o.xMin + j * pw, o.yMin, o.xMin + (j + 1) * pw, o.yMax), .155f, RCell(id + lvl + i + j));
                        for (int j = 0; j <= n; j++) RBox(det, fm, w, new Vector3(o.xMin + j * pw, o.center.y, .1f), new Vector3(.07f, o.height, .1f), E2Frame, RALL6);
                        RBox(det, fm, w, new Vector3(o.center.x, o.yMin + .035f, .1f), new Vector3(o.width, .07f, .1f), E2Frame, RALL6);
                        RBox(det, fm, w, new Vector3(o.center.x, o.yMax - .035f, .1f), new Vector3(o.width, .07f, .1f), E2Frame, RALL6);
                    }
                    // louvres over the upper garden glazing, rubble feature wall + teak door at the entrance
                    if (!garage && lvl == 1 && facing < -.3f && holes.Count > 0)
                    {
                        var o = holes[0];
                        for (float x = o.center.x; x < o.xMax - .1f; x += .38f) RBox(det, T7("teak"), w, new Vector3(x, (o.yMin + o.yMax) / 2 + .15f, -.35f), new Vector3(.07f, o.height + .3f, .3f), T7Own("teak"), RALL6);
                    }
                    if (!garage && lvl == 0 && facing > .7f && L > 6f)
                    {
                        float s0 = L * .5f - 2.1f;
                        RWallBox(det, T7("rubble_grey"), w, s0, s0 + 4.2f, -.25f, h, .42f, T7Own("rubble_grey"));
                        RBox(det, T7("teak"), w, new Vector3(s0 + 5.2f, 1.25f, -.03f), new Vector3(1.6f, 2.5f, .06f), T7Own("teak"), RALL6);
                    }
                }
                // roof slab (top level) and a thin projecting fascia over each level
                string fl2 = T7("flat");
                if (lvl == (garage ? 0 : 1)) {
                var cap = Fill("tmp", poly.ToArray(), q => 0f, Vector2.zero, false);
                var vs = cap.vertices; var tr = cap.triangles; Object.DestroyImmediate(cap);
                var mb = body[fl2]; int o0 = mb.V.Count;
                foreach (var v in vs) { mb.V.Add(new Vector3(v.x, bf.Y0 + y1 + .02f, v.z)); mb.U.Add(new Vector2(v.x, v.z)); mb.C.Add(RX("F4F2EC")); }
                for (int t = 0; t + 2 < tr.Length; t += 3) { mb.T.Add(o0 + tr[t]); mb.T.Add(o0 + tr[t + 1]); mb.T.Add(o0 + tr[t + 2]); }
                }
                for (int i = 0; i < poly.Count; i++)
                {
                    Vector2 a = poly[i], e = poly[(i + 1) % poly.Count];
                    var w = fl.Wall(a, e); float L = (e - a).magnitude; if (L < .3f) continue;
                    RWallBox(det, fl2, w, -.4f, L + .4f, y1 - y0 - .3f, y1 - y0 + .03f, .4f, RX("F4F2EC"));
                }
            }
            FlushInto(go, body, det, "B_" + id + "_E2");
            V07Note(garage ? "E2 garage" : "E2 villa");
        }

        static void EliteFbi(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id, bool booth)
        {
            var bf = BFrameOf(b, fp);
            var body = new RBatch(); var det = new RBatch();
            string pn = T7("panel"), fm = T7("flat_metal"), gk = T7("glass_fbi");
            Color col = RX("4A5563"), fr = RX("2A2E33");
            float H = bf.Tl;
            var rect = LocalRect(bf.W, bf.D);
            if (booth)
            {
                RBox(body, pn, bf.F, new Vector3(0, (H - .25f) / 2, 0), new Vector3(bf.W, H + .25f, bf.D), col, RALL5);
                RBox(det, T7("flat_gloss"), bf.F, new Vector3(0, 1.75f, -bf.D / 2 - .01f), new Vector3(bf.W - 1.4f, 1.1f, .02f), RX("3A4652"), RALL6);
                RBox(det, T7("flat_gloss"), bf.F, new Vector3(bf.W / 2 + .01f, 1.75f, 0), new Vector3(.02f, 1.1f, bf.D - 1.7f), RX("3A4652"), RALL6);
                RBox(det, fm, bf.F, new Vector3(0, H + .1f, 0), new Vector3(bf.W + 1f, .3f, bf.D + 1f), fr, RALL6);
            }
            else
            {
                for (int i = 0; i < 4; i++)
                {
                    var w = bf.F.Wall(rect[i], rect[(i + 1) % 4]); float L = (rect[(i + 1) % 4] - rect[i]).magnitude;
                    var holes = new List<Rect>();
                    foreach (float y in new[] { .9f, H * .63f }) holes.Add(Rect.MinMaxRect(1.2f, y, L - 1.2f, y + 1.5f));
                    if (i == 0)
                    {
                        holes[0] = Rect.MinMaxRect(1.2f, .9f, L / 2 - 2.2f, 2.4f);
                        holes.Add(Rect.MinMaxRect(L / 2 + 2.2f, .9f, L - 1.2f, 2.4f));
                        holes.Add(Rect.MinMaxRect(L / 2 - 1.6f, 0, L / 2 + 1.6f, 3f));
                    }
                    ROpenings(body, pn, w, L, -.25f, H + .6f, col, holes, .2f);
                    int k = 0;
                    foreach (var o in holes)
                    {
                        int n = Mathf.Max(1, Mathf.RoundToInt(o.width / 1.5f)); float pw = o.width / n;
                        for (int j = 0; j < n; j++) RPane(body, gk, w, Rect.MinMaxRect(o.xMin + j * pw, o.yMin, o.xMin + (j + 1) * pw, o.yMax), .205f, RCell("fbi" + id + i + k + j));
                        for (int j = 0; j <= n; j++) RBox(det, fm, w, new Vector3(o.xMin + j * pw, o.center.y, .16f), new Vector3(.08f, o.height, .1f), fr, RALL6);
                        k++;
                    }
                    RWallBox(det, fm, w, -.05f, L + .05f, H + .6f, H + .75f, .1f, fr);
                }
                var fw = bf.F.Wall(rect[0], rect[1]);
                RWallBox(det, fm, fw, bf.W / 2 - 3f, bf.W / 2 + 3f, 3.1f, 3.4f, 2.2f, fr);
                RPlane(body, "roof_flat", bf.F, -bf.W / 2, -bf.D / 2, bf.W / 2, bf.D / 2, H + .02f, RS["roof_flat"].Own);
                RBox(det, fm, bf.F, new Vector3(-bf.W / 2 + .3f, 5.2f, -bf.D / 2 - .3f), new Vector3(.25f, .2f, .35f), RX("2A2C2E"), RALL6);
                RBox(det, fm, bf.F, new Vector3(bf.W / 2 - .3f, 5.2f, -bf.D / 2 - .3f), new Vector3(.25f, .2f, .35f), RX("2A2C2E"), RALL6);
            }
            FlushInto(go, body, det, "B_" + id + "_E2");
            V07Note(booth ? "E2 booth" : "E2 FBI");
        }

        // E2 lamp on the stone road: dark post, lantern head with a warm glass
        static void E2Lamp(RBatch b, Vector3 at)
        {
            string fm = T7("flat_metal");
            RCyl(b, fm, at, .07f, 3.4f, 8, E2Gate);
            var g = RFr.Yaw(Vector3.zero, 0);
            RBox(b, fm, g, at + new Vector3(0, 3.55f, 0), new Vector3(.36f, .5f, .36f), E2Gate, RALL6);
            RBox(b, T7("flat_gloss"), g, at + new Vector3(0, 3.5f, 0), new Vector3(.3f, .34f, .38f), RX("F1EBD8"), RALL6);
        }

        // ================================================================== Construction C2
        static readonly Color C2Frame = new(.796f, .761f, .698f), C2Tube = new(.784f, .275f, .227f), C2Rail = new(.886f, .702f, .18f), C2Rail2 = new(.165f, .173f, .18f);

        static void C2Building(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id, string kind)
        {
            var bf = BFrameOf(b, fp, 270f);
            var body = new RBatch(); var det = new RBatch();
            string board = T7("board"), fm = T7("flat_metal");
            float H = kind == "concrete_frame" ? bf.H : bf.Tl, W = bf.W, D = bf.D;
            switch (kind)
            {
                case "concrete_frame":
                {
                    int floors = Mathf.Max(1, (int)F(Get(b, "floors"), 5f)); float fh = H / floors;
                    int nx = Mathf.Max(2, Mathf.RoundToInt(W / 4.8f) + 1), nz = Mathf.Max(2, Mathf.RoundToInt(D / 7f) + 1);
                    RBoxMM(body, board, bf.F, new Vector3(-W / 2 - .2f, -.25f, -D / 2 - .2f), new Vector3(W / 2 + .2f, .3f, D / 2 + .2f), C2Frame);
                    var cols = new GameObject("colliders_frame").transform; cols.SetParent(go, false);
                    for (int fl = 1; fl <= floors; fl++)
                    {
                        float y = fl * fh;
                        RBoxMM(body, board, bf.F, new Vector3(-W / 2 - .2f, y - .25f, -D / 2 - .2f), new Vector3(W / 2 + .2f, y, D / 2 + .2f), C2Frame);
                        for (int ix = 0; ix < nx; ix++) for (int iz = 0; iz < nz; iz++)
                            {
                                float x = Mathf.Lerp(-W / 2, W / 2, ix / (float)(nx - 1)), z = Mathf.Lerp(-D / 2 + .4f, D / 2 - .4f, iz / (float)(nz - 1));
                                RBoxMM(body, board, bf.F, new Vector3(x - .2f, y - fh + (fl == 1 ? .3f : 0), z - .2f), new Vector3(x + .2f, y - .25f, z + .2f), C2Frame);
                            }
                        if (fl < floors)
                        {
                            for (float x = -W / 2; x <= W / 2 + .01f; x += 2f) RBox(det, fm, bf.F, new Vector3(x, y + .55f, -D / 2 - .05f), new Vector3(.05f, 1.1f, .05f), C2Rail2, RALL6);
                            foreach (float yy in new[] { .5f, 1.05f }) RBox(det, T7("flat"), bf.F, new Vector3(0, y + yy, -D / 2 - .05f), new Vector3(W, .08f, .03f), yy > 1f ? C2Rail : C2Rail2, RALL6);
                        }
                        AddBoxLocal(cols, bf.F, new Vector3(0, y - .125f, 0), new Vector3(W + .4f, .25f, D + .4f));
                    }
                    for (int ix = 0; ix < nx; ix++) for (int iz = 0; iz < nz; iz++)
                        {
                            float x = Mathf.Lerp(-W / 2, W / 2, ix / (float)(nx - 1)), z = Mathf.Lerp(-D / 2 + .4f, D / 2 - .4f, iz / (float)(nz - 1));
                            AddBoxLocal(cols, bf.F, new Vector3(x, H / 2, z), new Vector3(.4f, H, .4f));
                        }
                    AddBoxLocal(cols, bf.F, new Vector3(0, .025f, 0), new Vector3(W + .4f, .55f, D + .4f));
                    // brick infill in progress on the back bays of floors 1-2
                    for (int fl = 0; fl < Mathf.Min(2, floors); fl++)
                    {
                        float x0 = fl == 0 ? -W * .1f : W * .1f, x1 = W / 2 - .2f, y0 = fl * fh + .3f;
                        var w = bf.F.Wall(new Vector2(x0, D / 2 - .2f), new Vector2(x1, D / 2 - .2f));
                        RWall(body, T7("brick_roman"), w, 0, x1 - x0, y0, y0 + fh - .25f, T7Own("brick_roman"));
                        RWall(body, T7("brick_roman"), bf.F.Wall(new Vector2(x1, D / 2 - .2f), new Vector2(x0, D / 2 - .2f)), 0, x1 - x0, y0, y0 + fh - .25f, T7Own("brick_roman"));
                    }
                    // the generic box collider would fill the open frame: slabs + columns instead
                    var gen = go.Find("colliders"); if (gen) Object.DestroyImmediate(gen.gameObject);
                    cols.name = "colliders";
                    break;
                }
                case "stair_lift_core":
                {
                    var rect = LocalRect(W, D);
                    for (int i = 0; i < 4; i++)
                    {
                        var w = bf.F.Wall(rect[i], rect[(i + 1) % 4]); float L = (rect[(i + 1) % 4] - rect[i]).magnitude;
                        var holes = new List<Rect>();
                        if (i == 0) for (int fl = 0; fl < Mathf.FloorToInt(H / 3f); fl++) holes.Add(Rect.MinMaxRect(L / 2 - .5f, fl * 3f + .3f, L / 2 + .5f, fl * 3f + 2.4f));
                        ROpenings(body, board, w, L, -.25f, H, C2Frame, holes, .2f);
                    }
                    RPlane(body, board, bf.F, -W / 2, -D / 2, W / 2, D / 2, H, C2Frame);
                    break;
                }
                case "scaffold":
                {
                    float x0 = -W / 2, x1 = W / 2, z0 = -D / 2 + .1f, z1 = D / 2 - .1f;
                    for (float x = x0; x <= x1 + .01f; x += 2.4f) foreach (float z in new[] { z0, z1 }) RBox(body, fm, bf.F, new Vector3(x, H / 2, z), new Vector3(.05f, H, .05f), C2Tube, RALL6);
                    for (float y = 2f; y <= H; y += 2f)
                    {
                        foreach (float z in new[] { z0, z1 }) { RBox(body, fm, bf.F, new Vector3(0, y, z), new Vector3(W, .05f, .05f), C2Tube, RALL6); RBox(body, fm, bf.F, new Vector3(0, y + 1f, z), new Vector3(W, .045f, .045f), C2Tube, RALL6); }
                        for (float x = x0; x <= x1 + .01f; x += 2.4f) RBox(body, fm, bf.F, new Vector3(x, y, 0), new Vector3(.05f, .05f, z1 - z0), C2Tube, RALL6);
                        RBoxMM(body, T7("planks"), bf.F, new Vector3(x0, y + .03f, z0 + .05f), new Vector3(x1, y + .08f, z1 - .05f), T7Own("planks"));
                        RBoxMM(body, T7("planks"), bf.F, new Vector3(x0, y + .08f, z0 - .02f), new Vector3(x1, y + .26f, z0 + .02f), T7Own("planks"));
                    }
                    for (float x = x0; x < x1 - .1f; x += 4.8f) for (float y = 0f; y < H - 1f; y += 4f) RBeam(body, fm, bf.F.P(x, y, z0 - .06f), bf.F.P(Mathf.Min(x + 4.8f, x1), y + 4f, z0 - .06f), .045f, .045f, C2Tube);
                    string nk = T7("net_orange");
                    var w = bf.F.Wall(new Vector2(x0 + W * .3f, z0 - .15f), new Vector2(x1 - W * .1f, z0 - .15f));
                    RWall(det, nk, w, 0, W * .6f, 2f, H, Color.white);
                    break;
                }
                case "cargo_hoist":
                {
                    Color cr = RX("C8463A");
                    for (int k = 0; k < 4; k++) RBox(body, fm, bf.F, new Vector3((k % 2 - .5f) * 1.1f, H / 2, (k / 2 - .5f) * 1.1f), new Vector3(.08f, H, .08f), cr, RALL6);
                    for (float y = 1f; y < H; y += 1.5f) RBoxMM(body, fm, bf.F, new Vector3(-.6f, y, -.6f), new Vector3(.6f, y + .06f, .6f), cr);
                    RBoxMM(body, T7("trapez"), bf.F, new Vector3(-W / 2, -.25f, -D / 2), new Vector3(W / 2, 2.4f, D / 2), cr);
                    break;
                }
                case "foundation_slab":
                    RBoxMM(body, board, bf.F, new Vector3(-W / 2, -.25f, -D / 2), new Vector3(W / 2, H, D / 2), C2Frame, RALL5);
                    for (float x = -W / 2 + 1f; x < W / 2; x += 2f) RBox(det, fm, bf.F, new Vector3(x, H + .4f, 0), new Vector3(.03f, .8f, .03f), RX("6E5A4A"), RALL6);   // starter bars
                    break;
                case "van_workshop":
                {
                    var rect = LocalRect(W, D);
                    for (int i = 0; i < 4; i++)
                    {
                        Vector2 a = rect[i], e = rect[(i + 1) % 4];
                        var w = bf.F.Wall(a, e); float L = (e - a).magnitude;
                        var holes = new List<Rect>();
                        foreach (var (s, en) in EntsOnFace(b, bf, a, e)) { float sc = Mathf.Clamp(s, 3f, L - 3f); holes.Add(Rect.MinMaxRect(sc - 2.8f, 0, sc + 2.8f, Mathf.Min(4f, H - .6f))); }
                        float mid = Mathf.Min(2.4f, H * .5f);
                        ROpenings(body, T7("brick_roman"), w, L, -.25f, mid, T7Own("brick_roman"), holes.Select(h => Rect.MinMaxRect(h.xMin, -.25f, h.xMax, mid)).ToList(), .1f);
                        ROpenings(body, T7("wave"), w, L, mid, H, RX("B9BEC0"), holes, .1f);
                        foreach (var h in holes) { RBox(det, T7("shutter"), w, new Vector3(h.center.x, h.center.y, .12f), new Vector3(h.width, h.height, .02f), RX("C8463A"), RALL6); RWallBox(det, fm, w, h.xMin - .15f, h.xMax + .15f, h.yMax, h.yMax + .4f, .3f, RX("5C6266")); }
                        RWallBox(det, fm, w, -.05f, L + .05f, H, H + .2f, .12f, RX("8E9294"));
                    }
                    RPlane(body, T7("wave"), bf.F, -W / 2, -D / 2, W / 2, D / 2, H + .02f, RX("A9AEB0"));
                    break;
                }
                default:
                {   // site cabins, canteen, shower, foreman office, guard booth: block containers in trapezoid sheet
                    Color col = RX(S(Get(b, "tint")) ?? new[] { "8FA9B8", "A47E62", "C8BFA8", "A9C0CC" }[(int)(RHash(id, 81) * 4) % 4]);
                    Color trim = RX("E8E6DF");
                    float Hc = H;
                    RBoxMM(body, T7("trapez"), bf.F, new Vector3(-W / 2, .2f, -D / 2), new Vector3(W / 2, Hc, D / 2), col);
                    foreach (float x in new[] { -W / 2, W / 2 }) foreach (float z in new[] { -D / 2, D / 2 }) RBoxMM(det, fm, bf.F, new Vector3(x - .07f, -.25f, z - .07f), new Vector3(x + .07f, Hc + .05f, z + .07f), trim);
                    RBoxMM(det, fm, bf.F, new Vector3(-W / 2 - .07f, Hc - .1f, -D / 2 - .07f), new Vector3(W / 2 + .07f, Hc + .1f, D / 2 + .07f), trim);
                    float dx = W > 3f ? -W * .25f : 0f;
                    RBoxMM(det, T7("flat"), bf.F, new Vector3(dx - .45f, .25f, -D / 2 - .04f), new Vector3(dx + .45f, 2.2f, -D / 2 + .01f), RX("5A5F63"));
                    if (W > 3f) RBoxMM(det, T7("flat_gloss"), bf.F, new Vector3(W * .1f, 1.0f, -D / 2 - .03f), new Vector3(W * .1f + .8f, 1.9f, -D / 2 + .01f), RX("4F6470"));
                    RBoxMM(det, fm, bf.F, new Vector3(dx - .6f, -.25f, -D / 2 - .7f), new Vector3(dx + .6f, .22f, -D / 2), RX("6E7376"));
                    RBoxMM(det, T7("flat_gloss"), bf.F, new Vector3(W / 2 - .01f, 1.1f, -D * .2f), new Vector3(W / 2 + .03f, 1.9f, D * .1f), RX("4F6470"));
                    break;
                }
            }
            FlushInto(go, body, det, "B_" + id + "_C2");
            V07Note("C2 " + kind);
        }

        static void AddBoxLocal(Transform parent, RFr f, Vector3 c, Vector3 size)
        {
            var g = new GameObject("box"); g.transform.SetParent(parent, false);
            g.transform.SetPositionAndRotation(f.P(c), Quaternion.LookRotation(f.F, Vector3.up));
            g.AddComponent<BoxCollider>().size = size;
        }

        // v07 TowerCrane (C2 red / white), at a prop position, jib along the prop heading
        static void TowerCrane(RBatch b, Vector3 at, float yaw, Color paint, Color dark, float H = 36f, float L = 40f, float CL = 12f)
        {
            var f = RFr.Yaw(at, yaw);
            const float m = 1.6f;
            string fm = T7("flat_metal");
            RBoxMM(b, T7("conc"), f, new Vector3(-2.5f, -.3f, -2.5f), new Vector3(2.5f, .8f, 2.5f), RX("B9B5AD"));
            for (int k = 0; k < 4; k++) RBox(b, fm, f, new Vector3((k % 2 - .5f) * m, H / 2 + .8f, (k / 2 - .5f) * m), new Vector3(.14f, H, .14f), paint, RALL6);
            for (float y = .8f; y < H; y += 2f)
                foreach (var (a, e) in new[] { (new Vector3(-m / 2, 0, -m / 2), new Vector3(m / 2, 0, -m / 2)), (new Vector3(m / 2, 0, -m / 2), new Vector3(m / 2, 0, m / 2)), (new Vector3(m / 2, 0, m / 2), new Vector3(-m / 2, 0, m / 2)), (new Vector3(-m / 2, 0, m / 2), new Vector3(-m / 2, 0, -m / 2)) })
                {
                    RBeam(b, fm, f.P(a + Vector3.up * y), f.P(e + Vector3.up * y), .08f, .08f, paint);
                    RBeam(b, fm, f.P(a + Vector3.up * y), f.P(e + Vector3.up * (y + 2f)), .06f, .06f, paint);
                }
            float top = H + .8f;
            RBoxMM(b, fm, f, new Vector3(-1.2f, top, -1.2f), new Vector3(1.2f, top + 1.2f, 1.2f), dark);
            RBoxMM(b, fm, f, new Vector3(.9f, top - .2f, -2.2f), new Vector3(2.5f, top + 1.6f, -.6f), paint);
            RBoxMM(b, T7("flat_gloss"), f, new Vector3(2.5f, top + .4f, -2.1f), new Vector3(2.53f, top + 1.4f, -.7f), RX("4F6470"));
            Vector3 j0 = new(1.2f, top + 1.2f, 0);
            for (float s = 0; s < L; s += 2f)
            {
                Vector3 a = j0 + new Vector3(s, 0, 0), e = j0 + new Vector3(s + 2f, 0, 0);
                foreach (float z in new[] { -.6f, .6f }) RBeam(b, fm, f.P(a + new Vector3(0, 0, z)), f.P(e + new Vector3(0, 0, z)), .1f, .1f, paint);
                RBeam(b, fm, f.P(a + new Vector3(0, 1.4f, 0)), f.P(e + new Vector3(0, 1.4f, 0)), .1f, .1f, paint);
                foreach (float z in new[] { -.6f, .6f }) RBeam(b, fm, f.P(a + new Vector3(0, 0, z)), f.P(e + new Vector3(-1f, 1.4f, 0)), .06f, .06f, paint);
            }
            for (float s = 0; s < CL; s += 2f) foreach (float z in new[] { -.8f, .8f }) RBeam(b, fm, f.P(new Vector3(-1.2f - s, top + 1.2f, z)), f.P(new Vector3(-3.2f - s, top + 1.2f, z)), .12f, .12f, paint);
            for (int k = 0; k < 3; k++) RBoxMM(b, T7("conc"), f, new Vector3(-CL - .6f + k * 1.1f, top - .8f, -.9f), new Vector3(-CL + .4f + k * 1.1f, top + 1.2f, .9f), RX("BDB9B1"));
            RBeam(b, fm, f.P(new Vector3(0, top + 1.2f, 0)), f.P(new Vector3(0, top + 7f, 0)), .4f, .4f, paint);
            RBeam(b, fm, f.P(new Vector3(0, top + 7f, 0)), f.P(j0 + new Vector3(L * .55f, 1.4f, 0)), .05f, .05f, dark);
            RBeam(b, fm, f.P(new Vector3(0, top + 7f, 0)), f.P(new Vector3(-CL, top + 1.3f, 0)), .05f, .05f, dark);
            float tr = L * .45f;
            RBoxMM(b, fm, f, j0 + new Vector3(tr, -.4f, -.7f), j0 + new Vector3(tr + 1.4f, 0, .7f), dark);
            RBeam(b, fm, f.P(j0 + new Vector3(tr + .7f, -.4f, 0)), f.P(j0 + new Vector3(tr + .7f, -H * .5f, 0)), .03f, .03f, dark);
            RBoxMM(b, fm, f, j0 + new Vector3(tr + .3f, -H * .5f - .8f, -.3f), j0 + new Vector3(tr + 1.1f, -H * .5f, .3f), RX("E2B32E"));
        }

        // ================================================================== Quiet Valley Q3: lab + casino (blank lit sign, NO text)
        static void ValleyLabQ3(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id)
        {
            var bf = BFrameOf(b, fp);
            var body = new RBatch(); var det = new RBatch();
            string pn = T7("panel"), fm = T7("flat_metal"), gk = T7("glass_Q3"), conc = T7("conc");
            Color lc = RX("3C4045"), uc = RX("E2E0DA"), fr = RX("1E2022"), fin = RX("2B2D30");
            float H = bf.Tl, G = Mathf.Clamp(H * .52f, 3.2f, 4f), W = bf.W, D = bf.D;
            var rect = LocalRect(W, D);
            for (int lvl = 0; lvl < 2; lvl++)
            {
                float y0 = lvl == 0 ? -.25f : G, y1 = lvl == 0 ? G : H;
                var fl = RFr.Yaw(bf.F.O + Vector3.up * y0, 0); fl.R = bf.F.R; fl.F = bf.F.F;
                for (int i = 0; i < 4; i++)
                {
                    Vector2 a = rect[i], e = rect[(i + 1) % 4];
                    var w = fl.Wall(a, e); float L = (e - a).magnitude, h = y1 - y0;
                    var holes = new List<Rect>(); var doors = new List<bool>();
                    if (lvl == 0)
                    {
                        foreach (var (s, en) in EntsOnFace(b, bf, a, e))
                        {
                            string k = S(Get(en, "kind"), "door") ?? "door";
                            float hw = k.Contains("small") ? 1.6f : k.Contains("garage") ? 2.4f : 1.6f;
                            float sc = Mathf.Clamp(s, hw + .4f, L - hw - .4f);
                            if (holes.Any(o => o.xMin < sc + hw + .3f && o.xMax > sc - hw - .3f)) continue;
                            holes.Add(Rect.MinMaxRect(sc - hw, .25f, sc + hw, Mathf.Min(3.6f, h - .3f))); doors.Add(k.Contains("garage"));
                        }
                        if (L > 8f && holes.Count == 0) { holes.Add(Rect.MinMaxRect(3f, 2.4f, L - 3f, Mathf.Min(3.5f, h - .2f))); doors.Add(false); }
                    }
                    else if (L > 6f) { holes.Add(Rect.MinMaxRect(i % 2 == 0 ? 2f : 3f, .7f, L - (i % 2 == 0 ? 2f : 3f), Mathf.Min(3f, h - .3f))); doors.Add(false); }
                    ROpenings(body, lvl == 0 ? pn : conc, w, L, 0, h + (lvl == 1 ? .25f : 0f), lvl == 0 ? lc : uc, holes, .2f);
                    for (int j = 0; j < holes.Count; j++)
                    {
                        var o = holes[j];
                        if (doors[j]) { RBox(det, T7("shutter"), w, new Vector3(o.center.x, o.center.y, .22f), new Vector3(o.width, o.height, .02f), lc, RALL6); RWallBox(det, fm, w, o.xMin - .1f, o.xMax + .1f, o.yMax, o.yMax + .15f, .1f, fr); continue; }
                        int n = Mathf.Max(1, Mathf.RoundToInt(o.width / 1.6f)); float pw = o.width / n;
                        for (int q = 0; q < n; q++) RPane(body, gk, w, Rect.MinMaxRect(o.xMin + q * pw, o.yMin, o.xMin + (q + 1) * pw, o.yMax), .205f, RCell(id + lvl + i + q));
                        for (int q = 0; q <= n; q++)
                        {
                            RBox(det, fm, w, new Vector3(o.xMin + q * pw, o.center.y, .15f), new Vector3(.06f, o.height, .1f), fr, RALL6);
                            if (lvl == 1 && i == 0) RWallBox(det, T7("flat"), w, o.xMin + q * pw - .06f, o.xMin + q * pw + .06f, o.yMin - .3f, o.yMax + .3f, .55f, fin);
                        }
                        RBox(det, fm, w, new Vector3(o.center.x, o.yMax - .04f, .15f), new Vector3(o.width, .08f, .1f), fr, RALL6);
                    }
                    if (lvl == 1) RWallBox(det, fm, w, -.05f, L + .05f, h + .25f, h + .4f, .1f, fr);
                }
            }
            RPlane(body, "roof_flat", bf.F, -W / 2, -D / 2, W / 2, D / 2, H + .02f, RS["roof_flat"].Own);
            // entrance canopy on slim columns at the main door
            var main = Arr(Get(b, "entrances")).Select(Obj).FirstOrDefault(e => S(Get(e, "kind")) == "door");
            if (main != null)
            {
                var (s, _) = EntsOnFace(b, bf, rect[0], rect[1]).FirstOrDefault(t => t.e == main);
                float cx = -W / 2 + s;
                RBoxMM(det, T7("flat"), bf.F, new Vector3(cx - 4f, G - .3f, -D / 2 - 4f), new Vector3(cx + 4f, G, -D / 2), fin);
                RBoxMM(det, T7("teak"), bf.F, new Vector3(cx - 3.9f, G - .31f, -D / 2 - 3.9f), new Vector3(cx + 3.9f, G - .3f, -D / 2), T7Own("teak"));
                foreach (float x in new[] { cx - 3.3f, cx + 3.3f }) RCyl(det, fm, bf.F.P(x, -.25f, -D / 2 - 3.4f), .12f, G - .05f, 10, fr);
            }
            FlushInto(go, body, det, "B_" + id + "_Q3");
            V07Note("Q3 lab");
        }

        static void CasinoQ3(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id)
        {
            var bf = BFrameOf(b, fp);
            var body = new RBatch(); var det = new RBatch();
            string pl = T7("plaster"), fm = T7("flat_metal"), gk = T7("glass_casino");
            Color cc = RX("7A2E36"), trim = RX("C9A44C"), canopy = RX("1E2022");
            float W = bf.W, D = bf.D, CH = bf.Tl;
            var rect = LocalRect(W, D);
            for (int i = 0; i < 4; i++)
            {
                var w = bf.F.Wall(rect[i], rect[(i + 1) % 4]); float L = (rect[(i + 1) % 4] - rect[i]).magnitude;
                var holes = new List<Rect>();
                if (i == 0) { for (float s = 3f; s < L - 2f; s += 4f) if (Mathf.Abs(s + 1f - L / 2) > 4f) holes.Add(Rect.MinMaxRect(s, .9f, s + 2f, CH - 1.5f)); holes.Add(Rect.MinMaxRect(L / 2 - 2.2f, 0, L / 2 + 2.2f, 3.6f)); }
                if (i == 1 || i == 3) for (float s = 3f; s < L - 2f; s += 4.5f) holes.Add(Rect.MinMaxRect(s, .9f, s + 2f, CH - 1.5f));
                ROpenings(body, pl, w, L, -.25f, CH + .8f, cc, holes, .25f);
                int k = 0;
                foreach (var o in holes)
                {
                    ROfficeWin(det, w, o, .25f, gk, trim, id + "c" + i + k++, 1, .75f, trim, .07f);
                    RWallBox(det, fm, w, o.xMin - .18f, o.xMax + .18f, o.yMax, o.yMax + .22f, .1f, trim);
                }
                RWallBox(det, T7("stone"), w, 0, L, -.25f, .6f, .06f, RX("D9D2C4"));
                RWallBox(det, fm, w, -.05f, L + .05f, CH - .2f, CH + .15f, .25f, trim);
                RWallBox(det, T7("flat"), w, -.05f, L + .05f, CH + .8f, CH + .95f, .12f, RX("844149"));
            }
            RPlane(body, "roof_flat", bf.F, -W / 2, -D / 2, W / 2, D / 2, CH + .02f, RS["roof_flat"].Own);
            // portico canopy on four gold columns over the door
            RBoxMM(det, fm, bf.F, new Vector3(-7f, 3.9f, -D / 2 - 5.5f), new Vector3(7f, 4.4f, -D / 2), canopy);
            RBoxMM(det, fm, bf.F, new Vector3(-7.1f, 4.3f, -D / 2 - 5.6f), new Vector3(7.1f, 4.45f, -D / 2 + .1f), trim);
            foreach (float x in new[] { -6.4f, -2.5f, 2.5f, 6.4f }) RCyl(det, fm, bf.F.P(x, -.25f, -D / 2 - 4.9f), .22f, 4.15f, 12, trim);
            // the sign: a BLANK lit panel (Fedya 22.10: no text at all, no "CASINO", no name) - black fascia, warm lit face, bulb row
            string glow = RSurfKey("w86:casino_sign_glow", W86Mat("W86_casino_sign_blank_glow", new Color(1f, .86f, .62f), .3f, 0f, new Color(1.6f, 1.25f, .75f)), 1f, true);
            string bulb = RSurfKey("w86:casino_bulb", W86Mat("W86_casino_sign_bulb", new Color(1f, .93f, .78f), .4f, 0f, new Color(2.2f, 1.9f, 1.3f)), 1f, true);
            var fw = bf.F.Wall(rect[0], rect[1]);
            float sx = W / 2, sy = CH + .2f;
            RWallBox(det, fm, fw, sx - 6f, sx + 6f, sy, sy + 2.4f, .35f, RX("17181A"));
            RBox(det, glow, fw, new Vector3(sx, sy + 1.2f, -.37f), new Vector3(11f, 1.7f, .02f), Color.white, RZN);
            for (float s = sx - 5.7f; s <= sx + 5.71f; s += .5f) foreach (float y in new[] { sy + .15f, sy + 2.25f })
                    RBox(det, bulb, fw, new Vector3(s, y, -.38f), new Vector3(.12f, .12f, .06f), Color.white, ROUT);
            RWallBox(det, fm, fw, sx - 6.05f, sx + 6.05f, sy - .05f, sy, .4f, trim);
            FlushInto(go, body, det, "B_" + id + "_Q3");
            V07Note("Q3 casino (blank sign)");
        }

        // ================================================================== styled fences (E2 high stone wall, C2 blue site fence, Q3 dark boards, P3 chain-link)
        // visuals only; the W85 Fence() box colliders stay
        static void StyledFence(Transform parent, string id, Vector2[] line, bool closed, float h, List<(Vector2 c, float w)> gaps, string style)
        {
            var pts = line.ToList(); if (closed) pts.Add(line[0]);
            var b = new RBatch();
            Material netM = style == "p3" ? AssetDatabase.LoadAssetAtPath<Material>(T1Mat + "T1_T31b_net.mat") : null;
            string net = netM ? RSurfKey("t1:T31b_net", netM, 1f, true) : null;
            float acc = 0f, postStep = style == "e2" ? 6f : style == "q3" ? 2.4f : 3f, nextPost = 0f;
            for (int i = 1; i < pts.Count; i++)
            {
                Vector2 a = pts[i - 1], c = pts[i];
                int k = Mathf.Max(1, Mathf.CeilToInt((c - a).magnitude / 2f));
                for (int j = 0; j < k; j++)
                {
                    Vector2 p0 = Vector2.Lerp(a, c, j / (float)k), p1 = Vector2.Lerp(a, c, (j + 1) / (float)k), m = (p0 + p1) * .5f;
                    float L = (p1 - p0).magnitude;
                    bool gap = gaps != null && gaps.Any(g => (g.c - m).magnitude < g.w * .5f);
                    float y0 = Mathf.Min(Height(p0.x, p0.y), Height(p1.x, p1.y)) - .3f;
                    var f = RFr.Yaw(new Vector3(0, y0, 0), 0);
                    var w = f.Wall(p0, p1); var wb = f.Wall(p1, p0);
                    if (!gap)
                        switch (style)
                        {
                            case "e2":
                                RWall(b, T7("rubble_grey"), w, 0, L, 0, h + .3f, T7Own("rubble_grey"));
                                RWall(b, T7("rubble_grey"), f.Wall(p1 - Perp(p0, p1) * .3f, p0 - Perp(p0, p1) * .3f), 0, L, 0, h + .3f, T7Own("rubble_grey"));
                                RBox(b, T7("stone"), w, new Vector3(L / 2, h + .36f, .15f), new Vector3(L + .02f, .12f, .46f), E2Cap, RALL6);
                                foreach (float y in new[] { h + .65f, h + .85f }) RBox(b, T7("flat_metal"), w, new Vector3(L / 2, y, -.05f), new Vector3(L, .02f, .02f), RX("4A4C4E"), RALL6);
                                break;
                            case "c2":
                                RWall(b, T7("trapez"), w, 0, L, 0, h + .3f, RX("6F9AC8"));
                                RWall(b, T7("trapez"), wb, 0, L, 0, h + .3f, RX("6F9AC8") * .92f);
                                RWallBox(b, T7("flat_metal"), w, 0, L, h + .22f, h + .34f, .05f, RX("F2F2EE"));
                                break;
                            case "q3":
                                RWall(b, T7("planks_w"), w, 0, L, 0, h + .3f, RX("4A4038"));
                                RWall(b, T7("planks_w"), wb, 0, L, 0, h + .3f, RX("4A4038"));
                                RBox(b, T7("planks_w"), w, new Vector3(L / 2, h + .33f, .02f), new Vector3(L, .06f, .14f), RX("554A40"), RALL6);
                                break;
                            default:
                                if (net != null) { RWall(b, net, w, 0, L, .25f, h + .3f, Color.white); }
                                RBox(b, T7("flat_metal"), w, new Vector3(L / 2, h + .3f, 0), new Vector3(L, .05f, .05f), RX("3A3F3F"), RALL6);
                                break;
                        }
                    // posts on the post grid (also at the gap ends)
                    while (nextPost <= acc + L + 1e-3f)
                    {
                        float s = nextPost - acc; Vector2 q = Vector2.Lerp(p0, p1, Mathf.Clamp01(s / Mathf.Max(L, 1e-3f)));
                        bool inGap = gaps != null && gaps.Any(g => (g.c - q).magnitude < g.w * .5f - .2f);
                        if (!inGap)
                        {
                            float gy = Height(q.x, q.y) - .3f;
                            var pf = RFr.Yaw(new Vector3(q.x, gy, q.y), -Mathf.Atan2(p1.y - p0.y, p1.x - p0.x) * Mathf.Rad2Deg);
                            switch (style)
                            {
                                case "e2": RBox(b, T7("stone"), pf, new Vector3(0, (h + .5f) / 2, .15f), new Vector3(.6f, h + .5f, .7f), E2Cap, RALL5);
                                    RBox(b, T7("flat_metal"), pf, new Vector3(0, h + .55f, -.1f), new Vector3(.3f, .2f, .3f), RX("2A2C2E"), RALL6);
                                    RBox(b, T7("flat_gloss"), pf, new Vector3(0, h + .45f, -.26f), new Vector3(.22f, .14f, .04f), RX("EDEAE0"), RALL6); break;
                                case "c2": RBox(b, T7("flat_metal"), pf, new Vector3(0, (h + .4f) / 2, .1f), new Vector3(.08f, h + .4f, .08f), RX("8E9294"), RALL5); break;
                                case "q3": RBox(b, T7("planks_w"), pf, new Vector3(0, (h + .35f) / 2, .08f), new Vector3(.12f, h + .35f, .12f), RX("4A4038"), RALL5); break;
                                default: RBox(b, T7("conc"), pf, new Vector3(0, (h + .5f) / 2, 0), new Vector3(.2f, h + .5f, .2f), RX("C2BEB6"), RALL5); break;
                            }
                        }
                        nextPost += postStep;
                    }
                    acc += L;
                }
            }
            var holder = new GameObject("FenceStyled_" + id).transform; holder.SetParent(parent, false);
            RFlush(b, holder, "Fence_" + id + "_" + style);
            foreach (Transform t in holder) { var mr = t.GetComponent<MeshRenderer>(); if (mr && t.name.Contains("T31b")) mr.shadowCastingMode = ShadowCastingMode.Off; }
            V07Note("fence " + style);
        }
        static Vector2 Perp(Vector2 a, Vector2 b) { Vector2 d = (b - a).normalized; return new Vector2(d.y, -d.x); }
    }
}
