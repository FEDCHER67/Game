using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using OnlyVolunteers.Map.W76;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using SRandom = System.Random;

namespace OnlyVolunteers.Map.W85
{
    // W86 decals (B3, 22.10; Fedya: "all decals on the map - markings, cracks, manholes, stains, oil, shore foam - from the ready textures").
    // Batched mesh decals filled into the DecalHooks_W86 groups the integration left, one renderer per group / material / chunk:
    //  - T123 markings (T1 b atlas, worn T1 c on the Rough ring / KPP road / Rough east road), asphalt only: never the Elite stone road,
    //    dirt roads, the Hamlet or roads the district data marks "markings": false. Rural asphalt 6.4 m: dashed centre (3 m / 6 m) + edge
    //    lines 0.3 m in; Downtown 12 m streets: dashed centre (solid for 12 m behind a stop line), parking-lane lines 2.3 m off each kerb
    //    (the parked cars stand in that strip), stop lines on the minor leg of "stop" junctions and on every leg of traffic-light
    //    junctions, zebras exactly where the Downtown legend has crosswalks, a few lane arrows before traffic lights, BUS at the bus stop,
    //    stall lines where the data has parking markings, the KPP stop line. Nothing inside junction boxes (a point inside another
    //    carriageway; continuations of one road excepted). Lines follow the road: 1 m stations raycast on the road's own collider, +2.5 cm.
    //  - T124 wear (T1 b atlas + GPT StreetUtility / RoadWear / OilTar): cracks, patches, tar seams, manholes off the wheel tracks, drains
    //    at the kerbs, oil; density by district (Rough old asphalt most: cold-mix, alligator, sunk manholes, gravel, puddles, broken edges;
    //    Downtown / Elite clean); oil at fuel pumps, garage gates, vehicles, the port yard / apron / drums, parking lots, the beach oil
    //    spill + film on the water (data zones); puddles / mud on dirt (Construction puddles, Hamlet / Rough / forest ruts, Hamlet mud).
    //  - T134 foam (T1 b strip): along the sea shoreline (0 m contour of the sea that touches the map edge; port quay excluded) and
    //    across / along the river at the cascades, the pool outlet and in the rapids.
    // Draw calls: chunks of 64 m (small decals, LODGroup cull ~150 m / manholes ~120 m) or 128 m (lines, foam: no cull); materials are
    // copies of the T1 picks with fixed queues inside the transparent range: wear < oil < markings < utility < (water 3000) < foam.
    public static partial class W85Builder
    {
        const float DLift = .025f, DFov = 70f;
        const string GM = "T123_road_markings", GW = "T124_road_wear", GU = "T124_street_utility", GO = "T124_oil", GG = "T124_ground",
            GFilm = "T124_oil_film", GF = "T134_shore_foam", GR = "T134_river_foam";
        static readonly Dictionary<string, Material> DMats = new();
        static readonly Dictionary<(string g, string m, int cx, int cz), MB> DBat = new();
        static readonly Dictionary<string, (Transform t, float chunk, float cull)> DGrp = new();
        static readonly Dictionary<string, int> DCnt = new();
        static readonly HashSet<Collider> DSurf = new();
        static readonly List<DCw> DCws = new();
        static readonly List<(string a, string b, Vector2 node)> DConts = new();
        static readonly List<Vector2[]> DNoMark = new();
        static readonly List<Vector2[]> DDrives = new();
        static readonly List<Vector2[]> DFoot = new();
        static Vector2[] DPortPad = new Vector2[0];
        static readonly Rect DHamlet = Rect.MinMaxRect(200f, 370f, 450f, 610f);

        sealed class DCw { public string Id; public Vector2[] Pl; public float W; public Rect Box; }
        sealed class DLeg { public Vector2 Dir; public string Street; public bool Stop, Zebra; public float TStop, Cut, Len; }
        sealed class DJn { public Vector2 Pos; public string Control, Type; public readonly List<DLeg> Legs = new(); public List<Dictionary<string, object>> Walks = new(); }
        readonly struct DEl
        {
            public readonly string M; public readonly Rect Uv; public readonly float W, H;
            public DEl(string m, Rect uv, float w, float h) { M = m; Uv = uv; W = w; H = h; }
            public DEl As(string m) => new(m, Uv, W, H);
        }

        static void DC(string what, int n = 1) { if (n > 0) DCnt[what] = DCnt.TryGetValue(what, out int k) ? k + n : n; }
        static int DSeed(string s) => (int)(Hash(s, 86) * 1e9f);

        // ------------------------------------------------------------------ atlas elements
        // T1 4 x 4 atlases (2048 px, 512 px cells): px box inside the cell (y down) -> uv rect (Unity, bottom-left origin)
        static Rect DCell(int row, int col, float x0 = 0, float y0 = 0, float x1 = 512, float y1 = 512) =>
            Rect.MinMaxRect(col * .25f + x0 / 2048f, 1f - row * .25f - y1 / 2048f, col * .25f + x1 / 2048f, 1f - row * .25f - y0 / 2048f);
        static DEl WearEl(int r, int c, float x0, float y0, float x1, float y1) => new("wear", DCell(r, c, x0, y0, x1, y1), (x1 - x0) / 205f, (y1 - y0) / 205f);

        static readonly DEl[] DCracks = { WearEl(0, 0, 0, 0, 512, 512), WearEl(0, 1, 78, 201, 448, 440), WearEl(0, 2, 40, 67, 233, 512), WearEl(0, 3, 0, 0, 512, 512) };
        static readonly DEl[] DPatches = { WearEl(1, 0, 49, 33, 435, 377), WearEl(1, 1, 86, 51, 486, 465) };
        static readonly DEl[] DOilSoft = { WearEl(1, 2, 109, 79, 415, 436), WearEl(1, 3, 35, 83, 383, 415) };
        static readonly DEl DSeam = WearEl(2, 2, 226, 0, 286, 512), DDamp = WearEl(2, 3, 47, 126, 452, 395), DGrateT1 = WearEl(2, 1, 45, 125, 467, 387);
        static readonly DEl DColdMix = WearEl(3, 0, 82, 88, 405, 377), DAlligator = WearEl(3, 1, 49, 49, 493, 494), DSunkRing = WearEl(3, 2, 0, 0, 512, 512), DGravel = WearEl(3, 3, 15, 15, 497, 497);
        // GPT atlases (Working/Reviews/Textures_2026-10-17/gpt_missing_v02_2026-10-18/ATLAS_UV.json, uv_unity_bottom_left), T1 cleaned copies
        static readonly DEl DManhole = new("util", Rect.MinMaxRect(.0635f, .7295f, .2705f, .9365f), .75f, .75f);
        static readonly DEl DGrate = new("util", Rect.MinMaxRect(.396f, .7593f, .6045f, .9072f), .8f, .57f);
        static readonly DEl DOilCar = new("gptwear", Rect.MinMaxRect(.6821f, .3379f, .8252f, .416f), 2.2f, 1f);
        static readonly DEl DPuddle = new("gptwear", Rect.MinMaxRect(.187f, .0884f, .3262f, .1631f), 2.5f, 1.3f);
        static readonly DEl DEdge = new("gptwear", Rect.MinMaxRect(.6792f, .0986f, .8223f, .1655f), 3f, 1.2f);
        static readonly DEl[] DGPatches = { new("gptwear", Rect.MinMaxRect(.6787f, .5811f, .8198f, .6724f), 2.5f, 1.5f), new("gptwear", Rect.MinMaxRect(.1787f, .3311f, .3198f, .4224f), 2.5f, 1.5f) };
        static readonly DEl[] DTar =
        {
            new("oil", Rect.MinMaxRect(.0625f, .6709f, .2695f, .8467f), 1.18f, 1f), new("oil", Rect.MinMaxRect(.4229f, .6523f, .5879f, .8564f), .81f, 1f),
            new("oil", Rect.MinMaxRect(.7725f, .6777f, .9043f, .8193f), .93f, 1f), new("oil", Rect.MinMaxRect(.0586f, .1768f, .2773f, .3125f), 1.61f, 1f),
            new("oil", Rect.MinMaxRect(.4043f, .1592f, .5898f, .3311f), 1.08f, 1f),
        };
        // T1 b markings atlas (cells: 0,0 solid; 0,1 dash; 0,2 stop line; 0,3 zebra block of 5 stripes; 1,0..2 arrows; 2,3 BUS)
        static readonly Rect DSolidUv = DCell(0, 0, 235, 120, 277, 380), DDashUv = DCell(0, 1, 233, 29, 279, 243), DStopUv = DCell(0, 2, 39, 225, 473, 287);
        static readonly Rect DArrowS = DCell(1, 0, 182, 40, 330, 471), DArrowL = DCell(1, 1, 120, 80, 331, 471), DArrowR = DCell(1, 2, 181, 80, 392, 471), DBusUv = DCell(2, 3, 135, 193, 383, 335);
        static Rect DZebraUv(int k) { int c = ((k % 5) + 5) % 5; return DCell(0, 3, 39 + 90 * c, 39, 91 + 90 * c, 473); }

        // ------------------------------------------------------------------ materials: copies of the T1 picks, fixed transparent queues
        static Material DMat(string key)
        {
            if (DMats.TryGetValue(key, out var m)) return m;
            string src = null; int off = 0; float alpha = 1f, smooth = -1f, tint = 1f;
            switch (key)
            {
                case "wear": src = "T1_dec_wear_b"; off = -50; break;
                case "gptwear": src = "T1_dec_gpt_wear"; off = -50; break;
                case "wear_rough": src = "T1_dec_wear_b"; off = -50; tint = 2.8f; alpha = .85f; break;      // pale old asphalt: grey, not black
                case "gptwear_rough": src = "T1_dec_gpt_wear"; off = -50; tint = 2.4f; alpha = .85f; break;
                case "oil": src = "T1_dec_gpt_oil"; off = -49; break;
                case "marks": src = "T1_dec_marks_b"; off = -48; break;
                case "marks_worn": src = "T1_dec_marks_c"; off = -48; alpha = 1.3f; break;
                case "util": src = "T1_dec_gpt_util"; off = -47; break;
                case "foam": src = "T1_dec_foam_b"; off = 1; alpha = 1.3f; break;
                case "oilfilm": src = "T1_dec_wear_b"; off = 2; alpha = .55f; smooth = .9f; break;
            }
            var s = src == null ? null : T1M(src);
            if (!s) { Note("decals: material " + key + " missing (" + src + ")"); return DMats[key] = null; }
            m = new Material(s) { name = "W86D_" + key, enableInstancing = false };
            if (m.HasProperty("_QueueOffset")) m.SetFloat("_QueueOffset", off);
            m.renderQueue = 3000 + off;
            if ((alpha != 1f || tint != 1f) && m.HasProperty("_BaseColor")) { var c = m.GetColor("_BaseColor"); c = new Color(c.r * tint, c.g * tint, c.b * tint, c.a * alpha); m.SetColor("_BaseColor", c); }
            // plain alpha blend: the T1 picks preserve specular (premultiplied), which lit the whole quad incl. its transparent part
            m.SetFloat("_BlendModePreserveSpecular", 0f); m.DisableKeyword("_ALPHAPREMULTIPLY_ON");
            m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
            m.SetFloat("_SrcBlendAlpha", (float)BlendMode.One); m.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
            if (smooth >= 0f && m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", smooth);
            Folder(Gen + "/Materials/Decals");
            AssetDatabase.CreateAsset(m, Gen + "/Materials/Decals/W86D_" + key + ".mat"); created++;
            return DMats[key] = m;
        }

        // ------------------------------------------------------------------ batching
        static void DGroupMake(Transform hooks, string name, float chunk, float cull, string note)
        {
            var t = hooks.Find(name);
            if (!t) { t = new GameObject(name).transform; t.SetParent(hooks, false); }
            var h = t.GetComponent<W86DecalHook>();
            if (!h) h = t.gameObject.AddComponent<W86DecalHook>();
            h.Note = note;
            DGrp[name] = (t, chunk, cull);
        }

        static MB DBatch(string g, string m, Vector2 at)
        {
            float ch = DGrp[g].chunk;
            var k = (g, m, Mathf.FloorToInt(at.x / ch), Mathf.FloorToInt(at.y / ch));
            if (!DBat.TryGetValue(k, out var mb)) DBat[k] = mb = new MB();
            return mb;
        }

        static Vector3 D3(Vector2 p, float y) => new(p.x, y, p.y);

        // quad that always faces up (winding fixed from its geometric normal)
        static void DQuadUp(MB mb, Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ud)
        {
            if (Vector3.Cross(b - a, c - a).y >= 0f) mb.Quad(a, b, c, d, ua, ub, uc, ud);
            else mb.Quad(a, d, c, b, ua, ud, uc, ub);
        }

        // flat decal on a host surface: centre c, v along fwd (sz m), u along right = (fwd.y, -fwd.x) (sx m); grid <= step m so it
        // follows the surface; dropped if the host misses any vertex (off the road / zone)
        static bool DPatch(string g, DEl e, Func<Vector2, float> host, Vector2 c, Vector2 fwd, float sx, float sz, float lift, bool flipU = false, bool flipV = false, float step = .9f)
        {
            if (DMat(e.M) == null || sx < .02f || sz < .02f) return false;
            fwd = fwd.sqrMagnitude > 1e-6f ? fwd.normalized : Vector2.up;
            Vector2 right = new(fwd.y, -fwd.x);
            int nx = Mathf.Max(1, Mathf.CeilToInt(sx / step)), nz = Mathf.Max(1, Mathf.CeilToInt(sz / step));
            var vs = new Vector3[(nx + 1) * (nz + 1)]; var us = new Vector2[vs.Length];
            for (int j = 0; j <= nz; j++)
                for (int i = 0; i <= nx; i++)
                {
                    float a = i / (float)nx, b = j / (float)nz;
                    Vector2 p = c + right * ((a - .5f) * sx) + fwd * ((b - .5f) * sz);
                    float y = host(p);
                    if (float.IsNaN(y)) return false;
                    int k = j * (nx + 1) + i;
                    vs[k] = D3(p, y + lift);
                    us[k] = new Vector2(Mathf.Lerp(e.Uv.xMin, e.Uv.xMax, flipU ? 1f - a : a), Mathf.Lerp(e.Uv.yMin, e.Uv.yMax, flipV ? 1f - b : b));
                }
            var mb = DBatch(g, e.M, c);
            int o = mb.V.Count;
            mb.V.AddRange(vs); mb.UV.AddRange(us);
            for (int j = 0; j < nz; j++)
                for (int i = 0; i < nx; i++)
                {
                    int a0 = o + j * (nx + 1) + i, a1 = a0 + nx + 1;
                    mb.T.Add(a0); mb.T.Add(a1); mb.T.Add(a1 + 1);
                    mb.T.Add(a0); mb.T.Add(a1 + 1); mb.T.Add(a0 + 1);
                }
            return true;
        }

        // strip along pts (absolute heights ys), width w; u across, v along: repeat = every piece maps vMin..vMax (solid paint),
        // else stretched once over the whole strip (one dash)
        static void DStrip(string g, string m, IList<Vector2> pts, IList<float> ys, float w, Rect uv, bool repeat)
        {
            int n = pts.Count; if (n < 2 || DMat(m) == null) return;
            var cum = DCum(pts); float total = Mathf.Max(cum[n - 1], 1e-4f);
            for (int i = 0; i + 1 < n; i++)
            {
                Vector2 na = DNormal(pts, i) * (w * .5f), nb = DNormal(pts, i + 1) * (w * .5f);
                float v0 = repeat ? uv.yMin : Mathf.Lerp(uv.yMin, uv.yMax, cum[i] / total), v1 = repeat ? uv.yMax : Mathf.Lerp(uv.yMin, uv.yMax, cum[i + 1] / total);
                var mb = DBatch(g, m, (pts[i] + pts[i + 1]) * .5f);
                DQuadUp(mb, D3(pts[i] + na, ys[i]), D3(pts[i + 1] + nb, ys[i + 1]), D3(pts[i + 1] - nb, ys[i + 1]), D3(pts[i] - na, ys[i]),
                    new Vector2(uv.xMin, v0), new Vector2(uv.xMin, v1), new Vector2(uv.xMax, v1), new Vector2(uv.xMax, v0));
            }
        }

        // painted line over 1 m samples; state 0 = none, 1 = dashed, 2 = solid; dashes `dash` m long every dash + gap m from `phase`
        static int DPaint(string g, string m, Func<Vector2, float> host, List<Vector2> line, float w, Func<Vector2, int> state, float dash = 0f, float gap = 0f, float phase = 0f)
        {
            int n = line.Count, made = 0; if (n < 2) return 0;
            var st = new int[n]; var ys = new float[n]; var cum = DCum(line);
            for (int i = 0; i < n; i++)
            {
                st[i] = state(line[i]);
                ys[i] = st[i] == 0 ? float.NaN : host(line[i]) + DLift;
                if (float.IsNaN(ys[i])) st[i] = 0;
            }
            for (int i = 0, a = -1; i <= n; i++)
            {
                bool on = i < n && st[i] == 2;
                if (on && a < 0) a = i;
                if (!on && a >= 0)
                {
                    if (i - a >= 2) { DStrip(g, m, line.GetRange(a, i - a), new ArraySegment<float>(ys, a, i - a), w, DSolidUv, true); made++; }
                    a = -1;
                }
            }
            if (dash <= 0f) return made;
            for (float s = phase; s + dash <= cum[n - 1]; s += dash + gap)
            {
                float s1 = s + dash;
                int i0 = DSeg(cum, s), i1 = DSeg(cum, s1);
                bool ok = true;
                for (int i = i0; i <= Mathf.Min(i1 + 1, n - 1) && ok; i++) if (st[i] != 1) ok = false;
                if (!ok) continue;
                var pts = new List<Vector2>(); var yy = new List<float>();
                void At(float sv) { int k = DSeg(cum, sv); float t = Mathf.Clamp01((sv - cum[k]) / Mathf.Max(1e-4f, cum[k + 1] - cum[k])); pts.Add(Vector2.Lerp(line[k], line[k + 1], t)); yy.Add(Mathf.Lerp(ys[k], ys[k + 1], t)); }
                At(s);
                for (int i = i0 + 1; i <= i1; i++) if (cum[i] > s + .05f && cum[i] < s1 - .05f) { pts.Add(line[i]); yy.Add(ys[i]); }
                At(s1);
                DStrip(g, m, pts, yy, w, DDashUv, false); made++;
            }
            return made;
        }

        // ------------------------------------------------------------------ geometry helpers
        static float[] DCum(IList<Vector2> p) { var c = new float[p.Count]; for (int i = 1; i < p.Count; i++) c[i] = c[i - 1] + (p[i] - p[i - 1]).magnitude; return c; }
        static int DSeg(float[] cum, float s) { int i = 0; while (i < cum.Length - 2 && cum[i + 1] < s) i++; return i; }
        static Vector2 DNormal(IList<Vector2> p, int i)
        {
            Vector2 d = (p[Mathf.Min(i + 1, p.Count - 1)] - p[Mathf.Max(i - 1, 0)]).normalized;
            return new Vector2(-d.y, d.x);
        }
        static Vector2 DAt(IList<Vector2> p, float[] cum, float s, out Vector2 dir)
        {
            int i = DSeg(cum, s);
            float L = Mathf.Max(1e-4f, cum[i + 1] - cum[i]);
            dir = (p[i + 1] - p[i]) / L;
            return Vector2.Lerp(p[i], p[i + 1], Mathf.Clamp01((s - cum[i]) / L));
        }
        static List<Vector2> DOffset(IList<Vector2> pts, float off)
        {
            var o = new List<Vector2>(pts.Count);
            for (int i = 0; i < pts.Count; i++) o.Add(pts[i] + DNormal(pts, i) * off);
            return o;
        }
        static Vector2 DRot(Vector2 v, float deg) { float r = deg * Mathf.Deg2Rad, c = Mathf.Cos(r), s = Mathf.Sin(r); return new Vector2(v.x * c - v.y * s, v.x * s + v.y * c); }
        static float DLat(SRandom R, float hw, float r) { float m = hw - r - .15f; return m <= 0f ? 0f : (float)(R.NextDouble() * 2 - 1) * m; }
        static float DClampLat(float lat, float hw, float r) { float m = Mathf.Max(0f, hw - r - .15f); return Mathf.Clamp(lat, -m, m); }
        static float DRnd(SRandom R, float a, float b) => a + (b - a) * (float)R.NextDouble();
        static Rect DBox(Vector2[] pl) { float x0 = pl.Min(q => q.x), x1 = pl.Max(q => q.x), z0 = pl.Min(q => q.y), z1 = pl.Max(q => q.y); return Rect.MinMaxRect(x0, z0, x1, z1); }
        static bool DNearPoly(List<Vector2[]> polys, Vector2 p, float r)
        {
            foreach (var poly in polys)
            {
                if (poly.Length < 3) continue;
                if (W76Atmosphere.Inside(poly, p)) return true;
                if (r > 0f && W76Atmosphere.Distance(poly.Append(poly[0]).ToArray(), p) < r) return true;
            }
            return false;
        }
        static float DArea(Vector2[] poly) { float a = 0f; for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++) a += (poly[j].x + poly[i].x) * (poly[j].y - poly[i].y); return Mathf.Abs(a) * .5f; }
        static bool DInPoly(SRandom R, Vector2[] poly, out Vector2 p, Func<Vector2, bool> ok = null)
        {
            var b = DBox(poly);
            for (int k = 0; k < 60; k++)
            {
                p = new Vector2(DRnd(R, b.xMin, b.xMax), DRnd(R, b.yMin, b.yMax));
                if (W76Atmosphere.Inside(poly, p) && (ok == null || ok(p))) return true;
            }
            p = default; return false;
        }
        // oriented box of a small polygon (longest edge direction): centre, unit axis, size along / across
        static void DFit(Vector2[] poly, out Vector2 c, out Vector2 ax, out float along, out float across)
        {
            Vector2 bx = Vector2.right; float best = 0f;
            for (int i = 0; i < poly.Length; i++) { var e = poly[(i + 1) % poly.Length] - poly[i]; if (e.sqrMagnitude > best) { best = e.sqrMagnitude; bx = e.normalized; } }
            Vector2 ay = new(-bx.y, bx.x);
            float a0 = poly.Min(q => Vector2.Dot(q, bx)), a1 = poly.Max(q => Vector2.Dot(q, bx)), b0 = poly.Min(q => Vector2.Dot(q, ay)), b1 = poly.Max(q => Vector2.Dot(q, ay));
            ax = bx; c = bx * ((a0 + a1) * .5f) + ay * ((b0 + b1) * .5f); along = a1 - a0; across = b1 - b0;
        }
        static List<Vector2> DSmooth(List<Vector2> p, int k)
        {
            var o = new List<Vector2>(p.Count);
            for (int i = 0; i < p.Count; i++)
            {
                int a = Mathf.Max(0, i - k), b = Mathf.Min(p.Count - 1, i + k); Vector2 s = Vector2.zero;
                for (int j = a; j <= b; j++) s += p[j];
                o.Add(s / (b - a + 1));
            }
            return o;
        }
        static List<Vector2> DChaikin(List<Vector2> p, int it)
        {
            for (int k = 0; k < it; k++)
            {
                if (p.Count < 3) return p;
                var o = new List<Vector2> { p[0] };
                for (int i = 0; i + 1 < p.Count; i++) { o.Add(Vector2.Lerp(p[i], p[i + 1], .25f)); o.Add(Vector2.Lerp(p[i], p[i + 1], .75f)); }
                o.Add(p[p.Count - 1]); p = o;
            }
            return p;
        }

        // ------------------------------------------------------------------ hosts (surface height under a point, NaN = none)
        static Func<Vector2, float> DColHost(Collider c) => p =>
            c && c.Raycast(new Ray(new Vector3(p.x, 800f, p.y), Vector3.down), out var hit, 1600f) ? hit.point.y : float.NaN;
        static float DSurfY(Vector2 p)
        {
            float best = float.NaN;
            foreach (var h in Physics.RaycastAll(new Vector3(p.x, 600f, p.y), Vector3.down, 1200f, ~0, QueryTriggerInteraction.Ignore))
                if (DSurf.Contains(h.collider) && (float.IsNaN(best) || h.point.y > best)) best = h.point.y;
            return best;
        }
        static float DSurfOrGround(Vector2 p) { float y = DSurfY(p); return float.IsNaN(y) ? Height(p.x, p.y) + .035f : y; }
        static float DGround(Vector2 p) => Height(p.x, p.y) + .035f;

        // ------------------------------------------------------------------ junction boxes
        static bool DInBox(DCw self, Vector2 p, float margin)
        {
            foreach (var o in DCws)
            {
                if (ReferenceEquals(o, self)) continue;
                float r = o.W * .5f + margin;
                if (p.x < o.Box.xMin - r || p.x > o.Box.xMax + r || p.y < o.Box.yMin - r || p.y > o.Box.yMax + r) continue;
                if (W76Atmosphere.Distance(o.Pl, p) >= r) continue;
                if (self != null && DConts.Any(c => (c.a == self.Id && c.b == o.Id || c.b == self.Id && c.a == o.Id) && (c.node - p).sqrMagnitude < 625f)) continue;
                return true;
            }
            return false;
        }

        static void DAddCw(string id, Vector2[] pl, float w)
        {
            if (pl == null || pl.Length < 2) return;
            DCws.Add(new DCw { Id = id, Pl = pl, W = w, Box = DBox(pl) });
        }

        static void DContinuations()
        {
            for (int i = 0; i < DCws.Count; i++)
                for (int j = i + 1; j < DCws.Count; j++)
                {
                    var A = DCws[i]; var B = DCws[j];
                    int na = A.Pl.Length, nb = B.Pl.Length;
                    foreach (bool aEnd in new[] { false, true })
                        foreach (bool bEnd in new[] { false, true })
                        {
                            Vector2 ea = aEnd ? A.Pl[na - 1] : A.Pl[0], eb = bEnd ? B.Pl[nb - 1] : B.Pl[0];
                            if ((ea - eb).sqrMagnitude > 9f) continue;
                            Vector2 outA = aEnd ? A.Pl[na - 1] - A.Pl[na - 2] : A.Pl[0] - A.Pl[1];
                            Vector2 inB = bEnd ? B.Pl[nb - 2] - B.Pl[nb - 1] : B.Pl[1] - B.Pl[0];
                            if (Vector2.Dot(outA.normalized, inB.normalized) > .77f) DConts.Add((A.Id, B.Id, (ea + eb) * .5f));
                        }
                }
        }

        static bool DNoMarkAt(Vector2 p) => DNoMark.Any(l => W76Atmosphere.Distance(l, p) < 4.6f);

        // ================================================================== entry point
        static void W86Decals(Transform root)
        {
            var t0 = DateTime.Now;
            DMats.Clear(); DBat.Clear(); DGrp.Clear(); DCnt.Clear(); DSurf.Clear(); DCws.Clear(); DConts.Clear(); DNoMark.Clear(); DDrives.Clear(); DFoot.Clear();
            Physics.SyncTransforms();
            var hooks = root.Find("DecalHooks_W86");
            if (!hooks) { hooks = new GameObject("DecalHooks_W86").transform; hooks.SetParent(root, false); }
            DGroupMake(hooks, GM, 128f, 0f, "T123 b markings (T1_dec_marks_b, worn T1_dec_marks_c on the Rough roads): centre / edge / parking-lane lines, stop lines, zebras (Downtown legend crosswalks), arrows, BUS, stall lines; mesh strips +2.5 cm on the road's own collider");
            DGroupMake(hooks, GW, 64f, 150f, "T124 b wear (T1_dec_wear_b + GPT RoadWear): cracks, patches, tar seams, Rough cold-mix / alligator / gravel / puddles / broken edges; LOD cull ~150 m");
            DGroupMake(hooks, GU, 64f, 120f, "T124 street utility (GPT StreetUtility): manholes off the wheel tracks, storm drains at the kerbs; LOD cull ~120 m");
            DGroupMake(hooks, GO, 64f, 150f, "T124 oil (GPT OilTar / RoadWear oil): fuel pumps, garage gates, vehicles, port yard / apron / drums, parking lots, beach oil spill; LOD cull ~150 m");
            DGroupMake(hooks, GG, 64f, 150f, "T124 ground (GPT puddle, T1 damp): Construction puddles, ruts of the dirt roads / tracks, Hamlet mud patches; LOD cull ~150 m");
            DGroupMake(hooks, GFilm, 128f, 0f, "T124 oil film on the sea in front of the beach oil spill (data 09-oil-film)");
            DGroupMake(hooks, GF, 128f, 0f, "T134 b shore foam (T1_dec_foam_b): strip along the sea shoreline (smoothed 0 m contour), 1.2 m over the sand .. 3.5 m into the water + an outer wave line 5-7 m out, sea level + 5 cm; port quay excluded");
            DGroupMake(hooks, GR, 128f, 300f, "T134 b river foam (T1_dec_foam_b): across / along the river at the cascades, the pool outlet and in the rapids");

            foreach (var c in root.GetComponentsInChildren<Collider>(true))
            {
                string cn = c.gameObject.name;
                if (cn.StartsWith("Road_") || cn.StartsWith("Street_") || cn.StartsWith("Zone_") || cn.StartsWith("Alley_") || cn == "Tunnel_road"
                    || (cn.StartsWith("Bridge_") && cn.EndsWith("_deck")) || cn.StartsWith("Pier_")) DSurf.Add(c);
            }
            var tj = Obj(Json.Parse(File.ReadAllText(Data + "/terrain_v85.json")));
            DPortPad = V2s(Get(Obj(Get(Obj(Get(tj, "pads")), "port")), "poly"));
            var rj = Obj(Json.Parse(File.ReadAllText(Data + "/roads_v85.json")));
            var ds = Directory.GetFiles(Data + "/districts", "*_v85.json").OrderBy(s => s).Select(f => Obj(Json.Parse(File.ReadAllText(f)))).Where(d => d != null).ToList();
            var details = Arr(Get(Obj(Json.Parse(File.ReadAllText(Data + "/details_v85.json"))), "props")).Select(Obj).Where(o => o != null).ToList();
            var wj = Obj(Json.Parse(File.ReadAllText(Data + "/water_v85.json")));

            DCollect(rj, ds, Obj(Get(tj, "tunnel")));
            DContinuations();
            void Part(string what, Action a) { try { a(); } catch (Exception e) { Note("decals: FAILED " + what + ": " + e.Message); Debug.LogException(e); } }
            Part("world roads", () => DWorldRoads(root, rj, Obj(Get(tj, "tunnel"))));
            Part("district roads", () => DDistrictRoads(root, ds));
            Part("downtown", () => DDowntown(root, ds.FirstOrDefault(d => S(Get(d, "district"), "") == "downtown"), details));
            Part("parking", () => DParking(ds));
            Part("oil", () => DOil(ds));
            Part("ground", () => DGroundDecals(ds, rj));
            Part("shore foam", DShoreFoam);
            Part("river foam", () => DRiverFoam(wj));
            int n = DFlush();
            var groups = DGrp.Keys.Select(g => $"{g} {DGrp[g].t.childCount}");
            Note($"decals: {n} renderers ({string.Join(", ", groups)}), chunks 64 / 128 m, LOD cull at {QualitySettings.lodBias:0.##} lod bias / FOV {DFov:0}; " +
                 string.Join(", ", DCnt.OrderBy(k => k.Key).Select(k => $"{k.Key} {k.Value}")) + $"; {(DateTime.Now - t0).TotalSeconds:0.0} s");
        }

        // carriageways for the junction boxes: world roads (not tunnel / dirt / sand), the tunnel, district roads, Downtown streets (+6 m caps)
        static void DCollect(Dictionary<string, object> rj, List<Dictionary<string, object>> ds, Dictionary<string, object> tunnel)
        {
            foreach (var r in Arr(Get(rj, "roads")).Select(Obj).Where(o => o != null))
            {
                string kind = S(Get(r, "kind"), "");
                if (kind == "tunnel" || kind == "dirt" || kind == "sand_track") continue;
                DAddCw("w:" + S(Get(r, "id"), ""), V2s(Get(r, "points")), kind == "bridge" ? F(Get(r, "carriageway_m"), 6.4f) : F(Get(r, "width_m"), 6.4f));
            }
            if (TunnelAxis.Length >= 2) DAddCw("tunnel", TunnelAxis, F(Get(tunnel, "width_m"), 9f));
            foreach (var dj in ds)
            {
                string dn = S(Get(dj, "district"), "");
                foreach (var z in Arr(Get(dj, "zones")).Select(Obj).Where(o => o != null))
                {
                    string kind = S(Get(z, "kind"), ""), id = S(Get(z, "id"), "");
                    var line = V2s(Get(z, "line") ?? Get(z, "poly_line"));
                    bool world = Get(z, "world_road") is bool wr && wr;
                    if ((kind == "road" || kind == "ring_road") && line.Length >= 2)
                    {
                        if (Get(z, "markings") is bool mk && !mk && world) DNoMark.Add(line);
                        if (!world && !OnWorldRoad(line)) DAddCw("d:" + id, line, F(Get(z, "width_m"), 6.4f));
                    }
                    if (dn == "downtown" && kind == "street") DAddCw("s:" + id, Extend(V2s(Get(z, "poly_line")), CarriagewayOf(z) * .5f), CarriagewayOf(z));
                    if (kind == "driveway" || kind == "curb_drop") { var p = V2s(Get(z, "poly")); if (p.Length >= 3) DDrives.Add(p); }
                    if (kind == "entry") { var p = V2s(Get(z, "curb_drop")); if (p.Length >= 3) DDrives.Add(p); }
                }
                foreach (var b in Arr(Get(dj, "buildings")).Select(Obj).Where(o => o != null))
                {
                    var fp = V2s(Get(b, "footprint"));
                    if (fp.Length >= 3) DFoot.Add(fp);
                }
            }
        }

        // ================================================================== world roads (rural asphalt, serpentines, Rough ring, bridge, tunnel)
        static readonly Dictionary<string, Dictionary<string, float>> DWearSpec = new()
        {
            ["rural"] = new() { ["crack"] = 26, ["patch"] = 75, ["gpatch"] = 140, ["seam"] = 55, ["edge"] = 95 },
            ["valley"] = new() { ["crack"] = 45, ["seam"] = 90, ["edge"] = 170 },
            ["drive"] = new() { ["crack"] = 30, ["patch"] = 80, ["oil"] = 55 },
            ["bridge"] = new() { ["crack"] = 40, ["seam"] = 21 },
            ["rough"] = new() { ["crack"] = 9, ["patch"] = 22, ["coldmix"] = 24, ["alligator"] = 28, ["seam"] = 22, ["sunk"] = 45, ["gravel"] = 19, ["puddle"] = 27, ["edge"] = 24, ["oil"] = 42, ["damp"] = 60, ["drain"] = 55 },
            ["port"] = new() { ["crack"] = 18, ["patch"] = 38, ["seam"] = 40, ["manhole"] = 60, ["oil"] = 24 },
            ["tunnel"] = new() { ["crack"] = 32, ["oil"] = 30, ["damp"] = 26 },
            ["elite"] = new() { ["manhole"] = 70 },
        };

        static void DWorldRoads(Transform root, Dictionary<string, object> rj, Dictionary<string, object> tunnel)
        {
            foreach (var r in Arr(Get(rj, "roads")).Select(Obj).Where(o => o != null))
            {
                string kind = S(Get(r, "kind"), ""), id = S(Get(r, "id"), ""), surf = S(Get(r, "surface"), "asphalt_A5d12");
                var pl = V2s(Get(r, "points"));
                if (pl.Length < 2 || !surf.StartsWith("asphalt")) continue;
                if (kind == "tunnel" || kind == "dirt" || kind == "sand_track" || kind == "stone_serpentine") continue;
                bool bridge = kind == "bridge";
                var go = root.Find(bridge ? "Roads/Bridge_" + id + "_deck" : "Roads/Road_" + id);
                var col = go ? go.GetComponent<Collider>() : null;
                if (!col) { DC("roads skipped (no collider)"); continue; }
                var host = DColHost(col);
                float carriage = bridge ? F(Get(r, "carriageway_m"), 6.4f) : F(Get(r, "width_m"), 6.4f);
                var cw = DCws.FirstOrDefault(c => c.Id == "w:" + id);
                bool rough = id.Contains("rough_ring") || id.Contains("border_checkpoint");
                string cls = rough ? "rough" : bridge ? "bridge" : kind == "drive" ? "drive" : id == "port_road" ? "port" : id.Contains("valley") ? "valley" : "rural";
                string mm = surf.Contains("old") || rough ? "marks_worn" : "marks";
                var pts = ResamplePy(pl, 2f);
                DRoadMarks(cw, host, pts, carriage, kind, mm);
                DRoadWear(id, cw, host, pts, carriage, cls);
                DC("roads with decals");
            }
            // tunnel: 9 m between the walls, 0.8 m kerbs -> 7.4 m carriageway
            var tun = root.Find("Tunnel/Tunnel_road");
            var tcol = tun ? tun.GetComponent<Collider>() : null;
            if (tcol && TunnelAxis.Length >= 2)
            {
                var host = DColHost(tcol);
                var pts = Resample(TunnelAxis, 2f);
                var cw = DCws.FirstOrDefault(c => c.Id == "tunnel");
                float carriage = F(Get(tunnel, "width_m"), 9f) - 1.6f;
                DRoadMarks(cw, host, pts, carriage, "tunnel", "marks");
                DRoadWear("tunnel", cw, host, pts, carriage, "tunnel");
                DC("roads with decals");
            }
        }

        static void DRoadMarks(DCw cw, Func<Vector2, float> host, List<Vector2> pts, float carriage, string kind, string mm, bool allowCentre = true)
        {
            bool centre = allowCentre && carriage >= 6f && kind != "drive";
            bool edges = carriage >= 4.9f && kind != "drive";
            if (!centre && !edges) return;
            bool Free(Vector2 p) => !DHamlet.Contains(p) && !DNoMarkAt(p) && !DInBox(cw, p, 1f);
            if (centre) DC("T123 centre dashes", DPaint(GM, mm, host, Resample(pts.ToArray(), 1f), .13f, p => Free(p) ? 1 : 0, 3f, 6f, 1.5f));
            if (edges)
                foreach (int sg in new[] { 1, -1 })
                    DC("T123 edge line runs", DPaint(GM, mm, host, Resample(DOffset(pts, sg * (carriage * .5f - .3f)).ToArray(), 1f), .12f,
                        p => Free(p) && !DNearPoly(DDrives, p, 1.2f) ? 2 : 0));
        }

        static void DRoadWear(string id, DCw cw, Func<Vector2, float> host, List<Vector2> pts, float carriage, string cls)
        {
            if (!DWearSpec.TryGetValue(cls, out var spec)) return;
            var R = new SRandom(DSeed(id));
            float hw = carriage * .5f;
            var cum = DCum(pts); float L = cum[cum.Length - 1];
            bool rough = cls == "rough";
            bool Free(Vector2 p) => !DInBox(cw, p, .4f);
            bool DP(string g, DEl e, Vector2 c, Vector2 fwd, float sx, float sz, float lift, bool fu = false, bool fv = false) =>
                DPatch(g, rough && e.M == "wear" ? e.As("wear_rough") : rough && e.M == "gptwear" ? e.As("gptwear_rough") : e, host, c, fwd, sx, sz, lift, fu, fv);
            foreach (var kv in spec.OrderBy(k => k.Key))
            {
                string what = kv.Key; float sp = kv.Value;
                for (float s = sp * DRnd(R, .25f, 1f); s < L - 1.5f; s += sp * DRnd(R, .6f, 1.4f))
                {
                    Vector2 p = DAt(pts, cum, s, out Vector2 d), nl = new(-d.y, d.x);
                    int side = R.NextDouble() < .5 ? 1 : -1;
                    switch (what)
                    {
                        case "crack":
                        {
                            var e = DCracks[R.Next(DCracks.Length)]; float sc = (rough ? .95f : .75f) + .45f * (float)R.NextDouble();
                            float sx = e.W * sc, sz = e.H * sc, lat = DLat(R, hw, Mathf.Max(sx, sz) * .5f);
                            Vector2 c = p + nl * lat; if (!Free(c)) break;
                            if (DP(GW, e, c, DRot(d, R.Next(4) * 90f + DRnd(R, -15f, 15f)), sx, sz, DLift, R.NextDouble() < .5)) DC("T124 cracks");
                            break;
                        }
                        case "patch":
                        {
                            var e = DPatches[R.Next(DPatches.Length)]; float sc = DRnd(R, 1f, rough ? 1.9f : 1.5f);
                            float sx = e.W * sc, sz = e.H * sc, lat = DLat(R, hw, Mathf.Max(sx, sz) * .5f);
                            Vector2 c = p + nl * lat; if (!Free(c)) break;
                            if (DP(GW, e, c, d, sx, sz, DLift, R.NextDouble() < .5, R.NextDouble() < .5)) DC("T124 patches");
                            break;
                        }
                        case "gpatch":
                        {
                            var e = DGPatches[R.Next(DGPatches.Length)]; float sc = DRnd(R, .8f, 1.2f);
                            float sx = e.W * sc, sz = e.H * sc, lat = DLat(R, hw, sz * .5f);
                            Vector2 c = p + nl * lat; if (!Free(c)) break;
                            if (DP(GW, e, c, nl, sx, sz, DLift, R.NextDouble() < .5)) DC("T124 patches (GPT)");
                            break;
                        }
                        case "seam":
                        {
                            Vector2 c; bool ok;
                            if (cls == "bridge" || R.NextDouble() < .7)
                            {   // sealed crack / expansion joint across the road
                                c = p + nl * DRnd(R, -.2f, .2f); if (!Free(c)) break;
                                ok = DP(GW, DSeam, c, DRot(nl, DRnd(R, -8f, 8f)), .28f, 2f * hw - .5f, DLift);
                            }
                            else
                            {
                                float len = DRnd(R, 3f, 7f); c = p + nl * side * DRnd(R, 1f, Mathf.Max(1.05f, hw - .5f)); if (!Free(c)) break;
                                ok = DP(GW, DSeam, c, d, .26f, len, DLift);
                            }
                            if (ok) DC("T124 tar seams");
                            break;
                        }
                        case "edge":
                        {
                            float sx = 3f * DRnd(R, .8f, 1.2f);
                            Vector2 c = p + nl * side * (hw - .68f); if (!Free(c)) break;
                            if (DP(GW, DEdge, c, -nl * side, sx, 1.2f, DLift, R.NextDouble() < .5)) DC("T124 broken edges (GPT)");
                            break;
                        }
                        case "coldmix":
                        {
                            float sc = DRnd(R, .9f, 1.5f), sx = DColdMix.W * sc, sz = DColdMix.H * sc;
                            Vector2 c = p + nl * DLat(R, hw, Mathf.Max(sx, sz) * .5f); if (!Free(c)) break;
                            if (DP(GW, DColdMix, c, DRot(d, DRnd(R, 0f, 360f)), sx, sz, DLift)) DC("T124 Rough cold-mix");
                            break;
                        }
                        case "alligator":
                        {
                            float sc = DRnd(R, .7f, 1.1f), sx = DAlligator.W * sc;
                            Vector2 c = p + nl * DClampLat(side * DRnd(R, 1.1f, 2.1f), hw, sx * .5f); if (!Free(c)) break;
                            if (DP(GW, DAlligator, c, DRot(d, R.Next(4) * 90f), sx, sx, DLift)) DC("T124 Rough alligator");
                            break;
                        }
                        case "sunk":
                        {
                            Vector2 c = p + nl * DClampLat(side * 1.6f, hw, .7f); if (!Free(c)) break;
                            if (DP(GW, DSunkRing, c, DRot(d, DRnd(R, 0f, 360f)), 1.3f, 1.3f, DLift) &&
                                DP(GU, DManhole, c, DRot(d, DRnd(R, 0f, 360f)), .78f, .78f, DLift + .004f)) DC("T124 manholes (Rough, sunk ring)");
                            break;
                        }
                        case "manhole":
                        {
                            Vector2 c = p + nl * DClampLat(side * 1.6f, hw, .45f); if (!Free(c)) break;
                            if (DP(GU, DManhole, c, DRot(d, DRnd(R, 0f, 360f)), .75f, .75f, DLift)) DC("T124 manholes");
                            break;
                        }
                        case "gravel":
                        {
                            float sz = DGravel.W * DRnd(R, .55f, .85f);
                            Vector2 c = p + nl * DClampLat(side * (hw - sz * .5f - .1f), hw, sz * .5f); if (!Free(c)) break;
                            if (DP(GW, DGravel, c, DRot(d, DRnd(R, 0f, 360f)), sz, sz, DLift)) DC("T124 Rough gravel");
                            break;
                        }
                        case "puddle":
                        {
                            float sx = DPuddle.W * DRnd(R, .7f, 1.05f), sz = DPuddle.H * DRnd(R, .7f, 1.05f);
                            Vector2 c = p + nl * DClampLat(side * (hw - 1.3f), hw, sz * .5f + .2f); if (!Free(c)) break;
                            if (DP(GW, DPuddle, c, nl, sx, sz, DLift, R.NextDouble() < .5)) DC("T124 puddles on asphalt (GPT)");
                            break;
                        }
                        case "oil":
                        {
                            var e = DOilSoft[R.Next(DOilSoft.Length)]; float sc = DRnd(R, .55f, .9f);
                            Vector2 c = p + nl * DClampLat(side * 1.6f, hw, e.W * sc * .5f); if (!Free(c)) break;
                            if (DPatch(GW, e, host, c, DRot(d, DRnd(R, 0f, 360f)), e.W * sc, e.H * sc, DLift)) DC("T124 oil drips on roads");
                            break;
                        }
                        case "damp":
                        {
                            float sc = DRnd(R, .8f, 1.4f), sx = DDamp.W * sc, sz = DDamp.H * sc;
                            Vector2 c = p + nl * DLat(R, hw, sx * .5f); if (!Free(c)) break;
                            if (DP(GW, DDamp, c, nl, sx, sz, DLift)) DC("T124 damp patches");
                            break;
                        }
                        case "drain":
                        {
                            var e = R.NextDouble() < .5 ? DGrateT1 : DGrate; float sx = .8f, sz = .57f;
                            Vector2 c = p + nl * side * (hw - .42f); if (!Free(c)) break;
                            if (DP(e.M == "util" ? GU : GW, e, c, nl, sx, sz, DLift + .002f)) DC("T124 drains at the kerb");
                            break;
                        }
                    }
                }
            }
        }

        // ================================================================== district roads (not world roads): Rough east road, Elite ring,
        // valley drives; markings unless the data says "markings": false
        static void DDistrictRoads(Transform root, List<Dictionary<string, object>> ds)
        {
            foreach (var dj in ds)
            {
                string dn = S(Get(dj, "district"), "");
                foreach (var z in Arr(Get(dj, "zones")).Select(Obj).Where(o => o != null))
                {
                    string kind = S(Get(z, "kind"), ""), id = S(Get(z, "id"), ""), surf = S(Get(z, "surface"), "asphalt_A5d12");
                    if (kind != "road" && kind != "ring_road") continue;
                    if (Get(z, "world_road") is bool wr && wr) continue;
                    if (!surf.StartsWith("asphalt")) continue;
                    var go = root.Find("District_" + dn + "/Road_" + id);
                    var col = go ? go.GetComponent<Collider>() : null;
                    if (!col) continue;
                    var line = V2s(Get(z, "line"));
                    if (line.Length < 2) continue;
                    var host = DColHost(col);
                    var pts = ResamplePy(line, 2f);
                    float w = F(Get(z, "width_m"), 6.4f);
                    var cw = DCws.FirstOrDefault(c => c.Id == "d:" + id);
                    string rc = S(Get(z, "road_class"), "");
                    bool marks = !(Get(z, "markings") is bool mk && !mk);
                    string cls = dn.Contains("rough") ? "rough" : dn.Contains("elite") ? "elite" : rc == "drive" || w < 5.5f ? "drive" : "valley";
                    if (marks) DRoadMarks(cw, host, pts, w, rc == "drive" ? "drive" : kind, surf.Contains("old") || dn.Contains("rough") ? "marks_worn" : "marks");
                    DRoadWear(id, cw, host, pts, w, cls);
                    DC("district roads with decals");
                }
            }
        }

        // ================================================================== Downtown (12 m streets, junctions of the legend)
        static void DDowntown(Transform root, Dictionary<string, object> dj, List<Dictionary<string, object>> details)
        {
            if (dj == null) return;
            var zones = Arr(Get(dj, "zones")).Select(Obj).Where(z => z != null).ToList();
            var streets = zones.Where(z => S(Get(z, "kind")) == "street").ToList();
            var raw = new Dictionary<string, Vector2[]>(); var rank = new Dictionary<string, int>();
            foreach (var z in streets)
            {
                string nm = S(Get(z, "id"), "").Replace("05-street-", "");
                raw[nm] = V2s(Get(z, "poly_line"));
                rank[nm] = Get(z, "boulevard") is bool bv && bv ? 0 : Get(z, "ring") is bool rg && rg ? 1 : 2;
            }
            float Len(Vector2[] pl) { float s = 0f; for (int i = 1; i < pl.Length; i++) s += (pl[i] - pl[i - 1]).magnitude; return s; }
            var drops = new List<Vector2[]>();
            foreach (var z in zones)
            {
                string k = S(Get(z, "kind"), "");
                if (k == "curb_drop") { var p = V2s(Get(z, "poly")); if (p.Length >= 3) drops.Add(p); }
                if (k == "entry") { var p = V2s(Get(z, "curb_drop")); if (p.Length >= 3) drops.Add(p); }
            }
            // junctions: legs, stop control, zebras, cut distances
            var jns = new List<DJn>();
            foreach (var z in zones.Where(z => S(Get(z, "kind")) == "junction"))
            {
                var J = new DJn { Pos = V2(Get(z, "pos")), Control = S(Get(z, "control"), "none"), Type = S(Get(z, "type"), "T") };
                var names = Arr(Get(z, "streets")).Select(o => S(o)).Where(s => s != null && raw.ContainsKey(s)).ToList();
                J.Walks = Arr(Get(z, "crosswalks")).Select(Obj).Where(o => o != null).ToList();
                foreach (float a in Arr(Get(z, "legs_deg")).Select(o => F(o)))
                {
                    var leg = new DLeg { Dir = new Vector2(Mathf.Cos(a * Mathf.Deg2Rad), Mathf.Sin(a * Mathf.Deg2Rad)) };
                    Vector2 probe = J.Pos + leg.Dir * 9f;
                    leg.Street = names.OrderBy(nm => W76Atmosphere.Distance(raw[nm], probe)).FirstOrDefault();
                    leg.Zebra = J.Walks.Any(w => Mathf.Abs(Mathf.DeltaAngle(F(Get(w, "leg_deg")), a)) < 5f);
                    J.Legs.Add(leg);
                }
                string minorStreet = names.OrderByDescending(nm => rank[nm]).ThenBy(nm => Len(raw[nm])).FirstOrDefault();
                foreach (var leg in J.Legs)
                {
                    bool minor = J.Control == "traffic_light" ||
                                 J.Control == "stop" && (J.Legs.Count == 3 ? !J.Legs.Any(o => o != leg && Vector2.Dot(o.Dir, leg.Dir) < -.9f) : leg.Street == minorStreet);
                    leg.Stop = minor && J.Type != "bend";
                    leg.TStop = leg.Zebra ? 11.4f : 7.6f;
                    leg.Cut = leg.Stop ? leg.TStop + .3f : leg.Zebra ? 10.9f : 6.9f;
                }
                jns.Add(J);
            }
            foreach (var J in jns)
                foreach (var leg in J.Legs)
                {
                    float best = 999f;
                    foreach (var K in jns)
                    {
                        if (K == J) continue;
                        Vector2 d = K.Pos - J.Pos; float t = Vector2.Dot(d, leg.Dir), l = Mathf.Abs(d.x * leg.Dir.y - d.y * leg.Dir.x);
                        if (t > 1f && l < 2f) best = Mathf.Min(best, t);
                    }
                    if (best > 998f && leg.Street != null) { var pl = raw[leg.Street]; best = Mathf.Max(Vector2.Dot(pl[0] - J.Pos, leg.Dir), Vector2.Dot(pl[pl.Length - 1] - J.Pos, leg.Dir)); }
                    leg.Len = best;
                }
            bool Cut(Vector2 p, float extra)
            {
                foreach (var J in jns)
                {
                    Vector2 d = p - J.Pos; if (d.sqrMagnitude > 1024f) continue;
                    foreach (var leg in J.Legs)
                    {
                        float t = Vector2.Dot(d, leg.Dir), l = Mathf.Abs(d.x * leg.Dir.y - d.y * leg.Dir.x);
                        if (t > -6.5f && t < leg.Cut + extra && l < 6.6f) return true;
                    }
                }
                return false;
            }
            bool Solid(Vector2 p)
            {
                foreach (var J in jns)
                {
                    Vector2 d = p - J.Pos; if (d.sqrMagnitude > 900f) continue;
                    foreach (var leg in J.Legs)
                    {
                        if (!leg.Stop) continue;
                        float t = Vector2.Dot(d, leg.Dir), l = Mathf.Abs(d.x * leg.Dir.y - d.y * leg.Dir.x);
                        if (t >= leg.Cut - .5f && t < leg.Cut + 12f && l < 1f) return true;
                    }
                }
                return false;
            }
            var cars = details.Where(o => (S(Get(o, "kind"), "") ?? "").StartsWith("car_")).Select(o => (street: S(Get(o, "street"), ""), pos: V2(Get(o, "pos")))).ToList();
            // ---- streets: lines + wear
            foreach (var z in streets)
            {
                string sid = S(Get(z, "id"), ""), nm = sid.Replace("05-street-", "");
                var go = root.Find("District_downtown/Streets/Street_" + sid);
                var col = go ? go.GetComponent<Collider>() : null;
                if (!col || raw[nm].Length < 2) { DC("downtown streets skipped (no collider)"); continue; }
                var host = DColHost(col);
                var cw = DCws.FirstOrDefault(c => c.Id == "s:" + sid);
                var pts = Resample(raw[nm], 1f);
                bool Boxed(Vector2 p) => DInBox(cw, p, .8f);
                DC("T123 Downtown centre dashes", DPaint(GM, "marks", host, pts, .14f, p => Boxed(p) || Cut(p, 0f) ? 0 : Solid(p) ? 2 : 1, 3f, 3f, 1.5f));
                foreach (int sg in new[] { 1, -1 })
                    DC("T123 Downtown parking-lane line runs", DPaint(GM, "marks", host, DOffset(pts, sg * (DowntownCarriageway * .5f - 2.3f)), .12f,
                        p => Boxed(p) || Cut(p, 4f) || DNearPoly(drops, p, 1.5f) ? 0 : 2));
                // wear: clean city - few cracks / patches, manholes 40-60 m off the wheel tracks, drains at the kerbs, oil in the parking gaps
                var R = new SRandom(DSeed(sid));
                var cum = DCum(pts); float L = cum[cum.Length - 1], hw = DowntownCarriageway * .5f;
                bool Free(Vector2 p) => !Boxed(p) && !Cut(p, 0f);
                for (float s = DRnd(R, 8f, 30f); s < L - 2f; s += DRnd(R, 25f, 50f))
                {
                    Vector2 p = DAt(pts, cum, s, out Vector2 d), nl = new(-d.y, d.x);
                    var e = DCracks[R.Next(DCracks.Length)]; float sc = DRnd(R, .65f, .95f), sx = e.W * sc, sz = e.H * sc;
                    Vector2 c = p + nl * DLat(R, hw, Mathf.Max(sx, sz) * .5f);
                    if (Free(c) && DPatch(GW, e, host, c, DRot(d, R.Next(4) * 90f + DRnd(R, -10f, 10f)), sx, sz, DLift, R.NextDouble() < .5)) DC("T124 cracks (Downtown)");
                }
                for (float s = DRnd(R, 30f, 90f); s < L - 2f; s += DRnd(R, 90f, 140f))
                {
                    Vector2 p = DAt(pts, cum, s, out Vector2 d), nl = new(-d.y, d.x);
                    var e = DGPatches[R.Next(DGPatches.Length)]; float sx = e.W * DRnd(R, .8f, 1.1f), sz = e.H * DRnd(R, .8f, 1.1f);
                    Vector2 c = p + nl * DLat(R, hw - 2.3f, sz * .5f);
                    if (Free(c) && DPatch(GW, e, host, c, nl, sx, sz, DLift, R.NextDouble() < .5)) DC("T124 patches (Downtown)");
                }
                float[] manholeLat = { 1.9f, -1.9f, 4.8f, -4.8f };
                for (float s = DRnd(R, 10f, 30f); s < L - 2f; s += DRnd(R, 40f, 60f))
                {
                    Vector2 p = DAt(pts, cum, s, out Vector2 d), nl = new(-d.y, d.x);
                    Vector2 c = p + nl * manholeLat[R.Next(manholeLat.Length)];
                    if (Free(c) && DPatch(GU, DManhole, host, c, DRot(d, DRnd(R, 0f, 360f)), .75f, .75f, DLift + .004f)) DC("T124 manholes (Downtown)");
                }
                foreach (int sg in new[] { 1, -1 })
                {
                    for (float s = DRnd(R, 5f, 35f); s < L - 2f; s += DRnd(R, 38f, 55f))
                    {
                        Vector2 p = DAt(pts, cum, s, out Vector2 d), nl = new(-d.y, d.x);
                        Vector2 c = p + nl * sg * (hw - .42f);
                        if (Free(c) && !DNearPoly(drops, c, 1f) && DPatch(GU, DGrate, host, c, nl, .8f, .57f, DLift + .004f)) DC("T124 drains at the kerb (Downtown)");
                    }
                    for (float s = 3f; s < L - 3f; s += 6.5f)
                    {
                        Vector2 p = DAt(pts, cum, s, out Vector2 d), nl = new(-d.y, d.x);
                        Vector2 c = p + nl * sg * (hw - 1.2f);
                        if (R.NextDouble() > .1) continue;
                        if (cars.Any(k => (k.pos - c).sqrMagnitude < 11.5f) || !Free(c) || DNearPoly(drops, c, 1.5f)) continue;
                        if (DPatch(GO, DOilCar, host, c, nl, DOilCar.W * DRnd(R, .85f, 1.1f), DOilCar.H * DRnd(R, .85f, 1.1f), DLift, R.NextDouble() < .5, R.NextDouble() < .5)) DC("T124 oil in the parking strip (Downtown)");
                    }
                }
            }
            // ---- junctions: zebras, stop lines, arrows, corner drains
            Func<Vector2, float> top = DSurfY;
            foreach (var J in jns)
            {
                foreach (var w in J.Walks)
                {
                    Vector2 c = V2(Get(w, "centre")); float wa = F(Get(w, "walk_deg")) * Mathf.Deg2Rad;
                    Vector2 wdir = new(Mathf.Cos(wa), Mathf.Sin(wa)), sdir = new(-wdir.y, wdir.x);
                    float span = F(Get(w, "span_m"), 12f), len = F(Get(w, "w_m"), 4f);
                    int k = 0, made = 0;
                    for (float o = -span * .5f + .75f; o <= span * .5f - .74f; o += 1f, k++)
                        if (DPatch(GM, new DEl("marks", DZebraUv(k), .5f, len), top, c + wdir * o, sdir, .5f, len, DLift)) made++;
                    DC("T123 zebra stripes", made); if (made > 0) DC("T123 zebras");
                }
                foreach (var leg in J.Legs)
                {
                    Vector2 h = -leg.Dir, rt = new(h.y, -h.x);
                    if (leg.Stop && DPatch(GM, new DEl("marks", DStopUv, 5.6f, .45f), top, J.Pos + leg.Dir * leg.TStop + rt * 2.95f, h, 5.6f, .45f, DLift)) DC("T123 stop lines");
                    if (J.Control == "traffic_light" && leg.Stop && leg.Len >= 36f)
                    {
                        bool straight = J.Legs.Any(o => Vector2.Dot(o.Dir, h) > .9f), left = J.Legs.Any(o => Vector2.Dot(o.Dir, new Vector2(-h.y, h.x)) > .9f), right = J.Legs.Any(o => Vector2.Dot(o.Dir, rt) > .9f);
                        Rect? uv = straight ? DArrowS : left && !right ? DArrowL : right && !left ? DArrowR : (Rect?)null;
                        if (uv != null)
                        {
                            float aw = straight ? 1.55f : 2.16f, al = straight ? 4.5f : 4f;
                            if (DPatch(GM, new DEl("marks", uv.Value, aw, al), top, J.Pos + leg.Dir * (leg.TStop + 7.5f) + rt * 1.9f, h, aw, al, DLift)) DC("T123 lane arrows");
                        }
                    }
                    if (leg.Street != null)
                    {
                        Vector2 q = J.Pos + leg.Dir * (leg.Cut + 1.4f) + rt * (DowntownCarriageway * .5f - .42f);
                        if (!DNearPoly(drops, q, 1f) && DPatch(GU, DGrate, top, q, rt, .8f, .57f, DLift + .004f)) DC("T124 drains at the junction corners (Downtown)");
                    }
                }
            }
            // ---- BUS in the kerb strip at the bus stop, readable for the drivers that stop there
            foreach (var p in Arr(Get(dj, "props")).Select(Obj).Where(o => o != null && S(Get(o, "kind"), "") == "bus_stop_shelter"))
            {
                Vector2 sp = V2(Get(p, "pos"));
                var near = streets.Select(z => V2s(Get(z, "poly_line"))).OrderBy(pl => W76Atmosphere.Distance(pl, sp)).FirstOrDefault();
                if (near == null) continue;
                W76Atmosphere.Distance(near, sp, out float along, out _);
                var npts = Resample(near, 1f); var ncum = DCum(npts);
                Vector2 q = DAt(npts, ncum, along, out Vector2 d), nl = new(-d.y, d.x);
                int side = Vector2.Dot(sp - q, nl) > 0f ? 1 : -1;
                Vector2 hdir = side > 0 ? -d : d;
                if (DPatch(GM, new DEl("marks", DBusUv, 2.6f, 1.5f), top, q + nl * side * (DowntownCarriageway * .5f - 1.2f), hdir, 2.6f, 1.5f, DLift)) DC("T123 BUS");
            }
            // ---- alleys (old asphalt): a crack, a damp patch, an oil drip
            var R2 = new SRandom(8605);
            foreach (var z in zones.Where(z => (S(Get(z, "kind"), "") ?? "").StartsWith("dead_end_alley")))
            {
                var poly = V2s(Get(z, "poly")); if (poly.Length < 3) continue;
                int n = Mathf.Clamp(Mathf.RoundToInt(DArea(poly) / 70f), 1, 6);
                for (int i = 0; i < n; i++)
                {
                    if (!DInPoly(R2, poly, out Vector2 c)) continue;
                    double r = R2.NextDouble();
                    var e = r < .4 ? DCracks[R2.Next(DCracks.Length)] : r < .7 ? DDamp : DOilSoft[R2.Next(DOilSoft.Length)];
                    float sc = DRnd(R2, .5f, .8f);
                    if (DPatch(GW, e, top, c, DRot(Vector2.up, DRnd(R2, 0f, 360f)), e.W * sc, e.H * sc, DLift)) DC("T124 alley wear (Downtown)");
                }
            }
        }

        // ================================================================== parking stall lines (data: beach rows, casino bays, fuel stalls)
        static void DParking(List<Dictionary<string, object>> ds)
        {
            var R = new SRandom(8603);
            void Line(Vector2 a, Vector2 b, string what)
            {
                if (DPaint(GM, "marks", DSurfY, Resample(new[] { a, b }, 1f), .12f, p => 2) > 0) DC(what);
            }
            void OilIn(Vector2 c, Vector2 along, float p)
            {
                if (R.NextDouble() < p && DPatch(GO, DOilCar, DSurfY, c, new Vector2(-along.y, along.x), DOilCar.W * DRnd(R, .8f, 1f), DOilCar.H * DRnd(R, .85f, 1.1f), DLift, R.NextDouble() < .5, R.NextDouble() < .5))
                    DC("T124 oil in parking stalls");
            }
            foreach (var dj in ds)
                foreach (var z in Arr(Get(dj, "zones")).Select(Obj).Where(o => o != null && S(Get(o, "kind"), "") == "parking"))
                {
                    var poly = V2s(Get(z, "poly")); if (poly.Length < 3) continue;
                    var b = DBox(poly);
                    var rows = Arr(Get(z, "stall_rows_y")).Select(o => F(o)).ToList();
                    var stallPolys = Arr(Get(z, "stall_polys")).Select(V2s).Where(p => p.Length >= 4).ToList();
                    bool marked = Get(z, "markings") is bool mk ? mk : Get(z, "markings") is string || rows.Count > 0 || stallPolys.Count > 0;
                    if (!marked) continue;
                    if (rows.Count > 0)
                    {   // beach: stalls N-S across the rows, stall_w along x
                        float sw = F(Get(z, "stall_w_m"), 3f); int ns = Mathf.FloorToInt(b.width / sw); float x0 = b.xMin + (b.width - ns * sw) * .5f;
                        foreach (float y in rows)
                        {
                            for (int k = 0; k <= ns; k++) Line(new Vector2(x0 + k * sw, y - 2.5f), new Vector2(x0 + k * sw, y + 2.5f), "T123 stall lines");
                            for (int k = 0; k < ns; k++) OilIn(new Vector2(x0 + (k + .5f) * sw, y), Vector2.up, .25f);
                        }
                    }
                    else if (stallPolys.Count > 0)
                    {   // fuel station stalls: sides + the back line on the nose side
                        var done = new HashSet<string>();
                        bool noseSouth = (S(Get(z, "stall_dir"), "") ?? "").Contains("south");
                        foreach (var sp in stallPolys)
                        {
                            for (int i = 0; i < sp.Length; i++)
                            {
                                Vector2 a = sp[i], c = sp[(i + 1) % sp.Length];
                                string key = $"{Mathf.Round(Mathf.Min(a.x, c.x) * 10)}_{Mathf.Round(Mathf.Min(a.y, c.y) * 10)}_{Mathf.Round(Mathf.Max(a.x, c.x) * 10)}_{Mathf.Round(Mathf.Max(a.y, c.y) * 10)}";
                                if (!done.Add(key)) continue;
                                bool side = Mathf.Abs(a.x - c.x) < .05f;
                                bool back = !side && Mathf.Abs(a.y - (noseSouth ? sp.Min(q => q.y) : sp.Max(q => q.y))) < .05f;
                                if (side || back) Line(a, c, "T123 stall lines");
                            }
                            var cc = sp.Aggregate(Vector2.zero, (s, q) => s + q) / sp.Length;
                            OilIn(cc, Vector2.up, .5f);
                        }
                    }
                    else
                    {   // bays along the long side, 5 m deep from the side next to the nearest building
                        int bays = Mathf.Max(1, (int)F(Get(z, "bays"), 4f));
                        bool alongZ = b.height >= b.width;
                        Vector2 cen = b.center;
                        var fp = DFoot.OrderBy(f => (f.Aggregate(Vector2.zero, (s, q) => s + q) / f.Length - cen).sqrMagnitude).FirstOrDefault();
                        Vector2 bc = fp != null ? fp.Aggregate(Vector2.zero, (s, q) => s + q) / fp.Length : cen;
                        for (int k = 0; k <= bays; k++)
                        {
                            if (alongZ)
                            {
                                float zz = b.yMin + k * b.height / bays, xe = bc.x > cen.x ? b.xMax - .3f : b.xMin + .3f, xs = bc.x > cen.x ? xe - 5f : xe + 5f;
                                Line(new Vector2(xs, zz), new Vector2(xe, zz), "T123 stall lines");
                                if (k < bays) OilIn(new Vector2((xs + xe) * .5f, zz + b.height / bays * .5f), Vector2.right, .35f);
                            }
                            else
                            {
                                float xx = b.xMin + k * b.width / bays, ze = bc.y > cen.y ? b.yMax - .3f : b.yMin + .3f, zs = bc.y > cen.y ? ze - 5f : ze + 5f;
                                Line(new Vector2(xx, zs), new Vector2(xx, ze), "T123 stall lines");
                                if (k < bays) OilIn(new Vector2(xx + b.width / bays * .5f, (zs + ze) * .5f), Vector2.up, .35f);
                            }
                        }
                    }
                }
            // KPP stop line (Rough data road_marking)
            foreach (var dj in ds)
                foreach (var z in Arr(Get(dj, "zones")).Select(Obj).Where(o => o != null && S(Get(o, "kind"), "") == "road_marking"))
                {
                    var line = V2s(Get(z, "line")); if (line.Length < 2) continue;
                    Vector2 a = line[0], c = line[line.Length - 1], d = (c - a).normalized;
                    if (DPatch(GM, new DEl("marks_worn", DStopUv, (c - a).magnitude, .45f), DSurfY, (a + c) * .5f, new Vector2(d.y, -d.x) * -1f, (c - a).magnitude, .45f, DLift)) DC("T123 KPP stop line");
                }
        }

        // ================================================================== oil: pumps, garage gates, vehicles, port, aprons, beach spill
        static bool DBlob(string g, SRandom R, Vector2 c, float size, Func<Vector2, float> host)
        {
            var e = DTar[R.Next(DTar.Length)];
            float k = Mathf.Sqrt(e.W / e.H);
            return DPatch(g, e, host, c, DRot(Vector2.up, DRnd(R, 0f, 360f)), size * k, size / k, DLift, R.NextDouble() < .5, R.NextDouble() < .5, .7f);
        }

        static void DOil(List<Dictionary<string, object>> ds)
        {
            var R = new SRandom(8601);
            Func<Vector2, float> host = DSurfOrGround;
            foreach (var dj in ds)
            {
                string dn = S(Get(dj, "district"), "");
                bool clean = dn.Contains("elite") || dn.Contains("beach") || dn.Contains("hamlet") || dn.Contains("forest");
                var props = Arr(Get(dj, "props")).Select(Obj).Where(o => o != null).ToList();
                // fuel pumps: stains on both sides of each island (cars stand there)
                foreach (var p in props.Where(o => S(Get(o, "kind"), "") == "fuel_pump_island"))
                {
                    Vector2 c = V2(Get(p, "pos")); var size = Arr(Get(p, "size")).Select(o => F(o)).ToArray();
                    float yaw = F(Get(p, "rot_deg")) * Mathf.Deg2Rad;
                    Vector2 lx = new(Mathf.Cos(yaw), -Mathf.Sin(yaw)), lz = new(Mathf.Sin(yaw), Mathf.Cos(yaw));
                    bool longX = size.Length >= 3 ? size[0] >= size[2] : true;
                    Vector2 along = longX ? lx : lz, across = longX ? lz : lx;
                    float half = (longX ? (size.Length > 0 ? size[0] : 2f) : size[2]) * .5f;
                    foreach (int sg in new[] { 1, -1 })
                        for (int i = 0; i < 2 + R.Next(2); i++)
                            if (DBlob(GO, R, c + across * sg * DRnd(R, 1.6f, 2.6f) + along * DRnd(R, -half, half), DRnd(R, .5f, 1.2f), host)) DC("T124 oil at fuel pumps");
                    var e = DOilSoft[R.Next(DOilSoft.Length)];
                    if (DPatch(GW, e, host, c + across * (R.NextDouble() < .5 ? 2.2f : -2.2f), across, e.W * 1.1f, e.H * 1.1f, DLift)) DC("T124 oil at fuel pumps");
                }
                if (clean) continue;
                float pg = dn.Contains("rough") ? .55f : dn.Contains("downtown") ? .8f : dn.Contains("construction") || dn.Contains("port") ? .9f : .5f;
                // garage gates
                foreach (var b in Arr(Get(dj, "buildings")).Select(Obj).Where(o => o != null))
                {
                    string bk = S(Get(b, "kind"), "") ?? "";
                    bool garageLike = bk.Contains("garage") || bk.Contains("van_shop") || bk.Contains("workshop") || bk.Contains("taxi") || bk.Contains("warehouse");
                    foreach (var en in Arr(Get(b, "entrances")).Select(Obj).Where(o => o != null))
                    {
                        string ek = S(Get(en, "kind"), "") ?? "";
                        if (!(ek.Contains("garage") || ek.Contains("gate") || garageLike && !ek.Contains("door"))) continue;
                        if (R.NextDouble() > pg) continue;
                        float a = F(Get(en, "facing_deg")) * Mathf.Deg2Rad; Vector2 f = new(Mathf.Cos(a), Mathf.Sin(a)), sd = new(-f.y, f.x);
                        Vector2 at = V2(Get(en, "pos"));
                        int nb = 1 + (R.NextDouble() < .45 ? 1 : 0);
                        for (int i = 0; i < nb; i++)
                            if (DBlob(GO, R, at + f * DRnd(R, 1.2f, 3.2f) + sd * DRnd(R, -.8f, .8f), DRnd(R, .5f, 1.25f), host)) DC("T124 oil at garage gates");
                        if (R.NextDouble() < .3) { var e = DOilSoft[R.Next(DOilSoft.Length)]; if (DPatch(GW, e, host, at + f * 2.4f, f, e.W * 1.2f, e.H * 1.2f, DLift)) DC("T124 oil at garage gates"); }
                    }
                }
                // vehicles (data props): a drip under the engine
                float pv = dn.Contains("rough") ? .75f : dn.Contains("construction") || dn.Contains("port") ? .9f : dn.Contains("downtown") ? .35f : .5f;
                foreach (var p in props)
                {
                    string k = S(Get(p, "kind"), "") ?? "";
                    if (k == "food_truck" || k.Contains("stop") || k.Contains("shelter")) continue;
                    var tok = k.Split('_');
                    if (!tok.Any(t => t == "car" || t == "truck" || t == "forklift" || t == "stacker" || t == "loader" || t == "bus" || t == "van" || t == "jeep" || t == "tractor" || t == "bulldozer" || t == "excavator")) continue;
                    if (R.NextDouble() > pv) continue;
                    Vector2 c = V2(Get(p, "pos"));
                    float yaw = F(Get(p, "rot_deg")) * Mathf.Deg2Rad; Vector2 fw = new(Mathf.Sin(yaw), Mathf.Cos(yaw));
                    float big = k.Contains("jacks") || k.Contains("mixer") || k.Contains("dump") || k.Contains("loader") ? 1.6f : 1f;
                    if (DBlob(GO, R, c + fw * DRnd(R, -1.6f, 1.6f) + new Vector2(fw.y, -fw.x) * DRnd(R, -.5f, .5f), DRnd(R, .6f, 1.2f) * big, host)) DC("T124 oil under vehicles");
                    if (big > 1f && DBlob(GO, R, c + fw * DRnd(R, -2.5f, 2.5f), DRnd(R, .5f, 1f), host)) DC("T124 oil under vehicles");
                }
                // drums: a leak round the stack
                var drums = props.Where(o => S(Get(o, "kind"), "") == "oil_drum").Select(o => V2(Get(o, "pos"))).ToList();
                if (drums.Count > 0)
                {
                    Vector2 dc = drums.Aggregate(Vector2.zero, (s, q) => s + q) / drums.Count;
                    for (int i = 0; i < 4; i++) if (DBlob(GO, R, dc + DRot(Vector2.right, DRnd(R, 0f, 360f)) * DRnd(R, 1.5f, 3f), DRnd(R, .6f, 1.4f), host)) DC("T124 oil at the drums");
                    var e = DOilSoft[0]; if (DPatch(GW, e, host, dc + new Vector2(2.2f, -1.6f), Vector2.up, e.W * 1.4f, e.H * 1.4f, DLift)) DC("T124 oil at the drums");
                }
                // yards / pads / aprons with traffic: port yard (oil + cracks), loading pads, aprons, fuel pad, taxi stand
                foreach (var z in Arr(Get(dj, "zones")).Select(Obj).Where(o => o != null))
                {
                    string zk = S(Get(z, "kind"), "") ?? "", surf = S(Get(z, "surface"), "") ?? "";
                    var poly = V2s(Get(z, "poly")); if (poly.Length < 3) continue;
                    bool hard = surf.StartsWith("concrete") || surf.StartsWith("asphalt");
                    if (!hard) continue;
                    float area = DArea(poly);
                    int blobs = 0, wear = 0;
                    if (zk == "yard" && dn.Contains("port")) { blobs = Mathf.RoundToInt(area / 260f); wear = Mathf.RoundToInt(area / 240f); }
                    else if (zk == "loading_pad" || zk == "apron" || zk == "fuel_pad" || zk == "taxi_stand" || zk == "gas_station") { blobs = Mathf.Clamp(Mathf.RoundToInt(area / 70f), 2, 7); wear = Mathf.Clamp(Mathf.RoundToInt(area / 200f), 0, 3); }
                    else continue;
                    bool Ok(Vector2 q) => !DNearPoly(DFoot, q, 1.2f) && Height(q.x, q.y) > .3f;
                    for (int i = 0; i < blobs; i++)
                        if (DInPoly(R, poly, out Vector2 c, Ok) && DBlob(GO, R, c, DRnd(R, .5f, 1.5f), host)) DC("T124 oil on yards / pads");
                    for (int i = 0; i < wear; i++)
                    {
                        if (!DInPoly(R, poly, out Vector2 c, Ok)) continue;
                        double r = R.NextDouble();
                        var e = r < .5 ? DCracks[R.Next(DCracks.Length)] : r < .75 ? DPatches[R.Next(DPatches.Length)] : DOilSoft[R.Next(DOilSoft.Length)];
                        float sc = DRnd(R, .8f, 1.3f);
                        if (DPatch(GW, e, host, c, DRot(Vector2.up, R.Next(4) * 90f), e.W * sc, e.H * sc, DLift, R.NextDouble() < .5)) DC("T124 wear on yards / pads");
                    }
                }
            }
            // beach oil spill (data 09-oil-spill: drops with fans of small spray "from a brush", dense at the water, sparse inland) + film
            foreach (var dj in ds)
                foreach (var z in Arr(Get(dj, "zones")).Select(Obj).Where(o => o != null))
                {
                    string zk = S(Get(z, "kind"), "") ?? "";
                    var poly = V2s(Get(z, "poly")); if (poly.Length < 3) continue;
                    if (zk == "oil_spill")
                    {
                        var b = DBox(poly); int main = 0;
                        Func<Vector2, float> sand = p => Height(p.x, p.y) + .04f;
                        for (int tries = 0; tries < 600 && main < 24; tries++)
                        {
                            if (!DInPoly(R, poly, out Vector2 c)) continue;
                            float wgt = 1f - .8f * (c.y - b.yMin) / Mathf.Max(1f, b.height);
                            if (R.NextDouble() > wgt || Height(c.x, c.y) < .08f) continue;
                            float size = DRnd(R, .45f, 1.35f);
                            if (!DBlob(GO, R, c, size, sand)) continue;
                            main++; DC("T124 beach oil spill drops");
                            float fan = DRnd(R, 0f, 360f); int nSpray = 4 + R.Next(6);
                            for (int i = 0; i < nSpray; i++)
                            {
                                Vector2 q = c + DRot(Vector2.right, fan + DRnd(R, -28f, 28f)) * (size * .6f + DRnd(R, .2f, 1.8f));
                                if (Height(q.x, q.y) > .05f && DBlob(GO, R, q, DRnd(R, .07f, .28f), sand)) DC("T124 beach oil spray");
                            }
                        }
                    }
                    else if (zk == "oil_film_water")
                    {
                        for (int i = 0; i < 9; i++)
                        {
                            if (!DInPoly(R, poly, out Vector2 c)) continue;
                            var e = DOilSoft[R.Next(DOilSoft.Length)].As("oilfilm"); float sz = DRnd(R, 4f, 9f);
                            if (DPatch(GFilm, e, p => .03f, c, DRot(Vector2.up, DRnd(R, 0f, 360f)), sz * e.W / e.H, sz, 0f, false, false, 4f)) DC("T124 oil film on the sea");
                        }
                    }
                }
        }

        // ================================================================== ground: puddles on dirt, Hamlet mud, Construction puddles
        static void DGroundDecals(List<Dictionary<string, object>> ds, Dictionary<string, object> rj)
        {
            var R = new SRandom(8602);
            Func<Vector2, float> ground = DGround;
            bool Flat(Vector2 c, Vector2 d) => Mathf.Abs(Height(c.x + d.x * 1.3f, c.y + d.y * 1.3f) - Height(c.x - d.x * 1.3f, c.y - d.y * 1.3f)) < .3f && Height(c.x, c.y) > .3f;
            void Ruts(Vector2[] line, float width, float spacing, string what)
            {
                if (line.Length < 2) return;
                var pts = Resample(line, 1f); var cum = DCum(pts); float L = cum[cum.Length - 1];
                for (float s = spacing * DRnd(R, .2f, 1f); s < L - 1f; s += spacing * DRnd(R, .6f, 1.4f))
                {
                    Vector2 p = DAt(pts, cum, s, out Vector2 d), nl = new(-d.y, d.x);
                    Vector2 c = p + nl * (R.NextDouble() < .5 ? 1 : -1) * Mathf.Min(.9f, width * .25f);
                    if (!Flat(c, d) || DNearPoly(DFoot, c, .5f)) continue;
                    float sx = DPuddle.W * DRnd(R, .55f, .95f), sz = DPuddle.H * DRnd(R, .55f, .9f);
                    if (DPatch(GG, DPuddle, ground, c, nl, sx, sz, 0f, R.NextDouble() < .5, false, .7f)) DC(what);
                }
            }
            foreach (var dj in ds)
            {
                string dn = S(Get(dj, "district"), "");
                foreach (var z in Arr(Get(dj, "zones")).Select(Obj).Where(o => o != null))
                {
                    string zk = S(Get(z, "kind"), "") ?? "", surf = S(Get(z, "surface"), "") ?? "";
                    if (zk == "decal_patch")
                    {
                        var poly = V2s(Get(z, "poly")); if (poly.Length < 3) continue;
                        if (S(Get(z, "decal"), "") != "mud") { DC("Hamlet dung patches skipped (no dung texture)"); continue; }
                        DFit(poly, out Vector2 c, out Vector2 ax, out float along, out float across);
                        if (DPatch(GG, DDamp, ground, c, new Vector2(-ax.y, ax.x), Mathf.Max(1f, along * 1.3f), Mathf.Max(.8f, across * 1.3f), 0f, R.NextDouble() < .5, false, .7f)) DC("T124 Hamlet mud patches");
                    }
                    else if (zk == "puddle")
                    {
                        var poly = V2s(Get(z, "poly")); if (poly.Length < 3) continue;
                        DFit(poly, out Vector2 c, out Vector2 ax, out float along, out float across);
                        if (DPatch(GG, DPuddle, ground, c, new Vector2(-ax.y, ax.x), Mathf.Max(1f, along * 1.2f), Mathf.Max(.7f, across * 1.25f), 0f, false, false, .7f)) DC("T124 Construction puddles");
                    }
                    else if ((zk == "street" || zk == "track" || zk == "road") && surf.StartsWith("dirt"))
                    {
                        var line = V2s(Get(z, "line") ?? Get(z, "poly_line")); float w = F(Get(z, "width_m"), 4f);
                        if (dn.Contains("hamlet") && Get(z, "puddles") is bool pu && pu) Ruts(line, w, 42f, "T124 puddles in the Hamlet ruts");
                        else if (dn.Contains("rough")) Ruts(line, w, 30f, "T124 puddles in the Rough tracks");
                        else if (dn.Contains("construction")) Ruts(line, w, 36f, "T124 puddles in the Construction ruts");
                    }
                }
            }
            foreach (var r in Arr(Get(rj, "roads")).Select(Obj).Where(o => o != null && S(Get(o, "kind"), "") == "dirt"))
                Ruts(V2s(Get(r, "points")), F(Get(r, "width_m"), 5.4f), 55f, "T124 puddles on the forest roads");
        }

        // ================================================================== sea shore foam
        static void DShoreFoam()
        {
            var lines = DShoreLines();
            int runs = 0; float total = 0f;
            foreach (var raw in lines)
            {
                var pts = Resample(DChaikin(DSmooth(Resample(raw.ToArray(), 2f), 4), 1).ToArray(), 2f);
                if (pts.Count < 6) continue;
                float sgn = 0f;
                for (int i = 0; i < pts.Count; i += 3)
                {
                    Vector2 nl = DNormal(pts, i);
                    sgn += Height(pts[i].x + nl.x * 3f, pts[i].y + nl.y * 3f) - Height(pts[i].x - nl.x * 3f, pts[i].y - nl.y * 3f);
                }
                float toSea = sgn > 0f ? -1f : 1f;
                var keep = pts.Select(p => p.x > 3f && p.x < W - 3f && p.y > 3f && p.y < Hh - 3f && !(DPortPad.Length >= 3 && DNearPoly(new List<Vector2[]> { DPortPad }, p, 10f))).ToArray();
                for (int i = 0, a = -1; i <= pts.Count; i++)
                {
                    bool on = i < pts.Count && keep[i];
                    if (on && a < 0) a = i;
                    if (!on && a >= 0)
                    {
                        if (i - a >= 3)
                        {
                            var run = pts.GetRange(a, i - a);
                            DFoamStrip(GF, run, toSea, 1.2f, 3.5f, p => .05f);
                            DFoamStrip(GF, run, toSea, -5f, 7f, p => .045f, 13f);          // fainter outer wave line 5-7 m out
                            runs++; total += DCum(run).Last();
                        }
                        a = -1;
                    }
                }
            }
            DC("T134 shore foam runs", runs); DC("T134 shore foam metres", Mathf.RoundToInt(total));
        }

        // strip along pts, inner .. outer offsets on the `toSea` side of the left normal (v 0 inner -> 1 outer), u = metres / uLen
        static void DFoamStrip(string g, List<Vector2> pts, float toSea, float inner, float outer, Func<Vector2, float> y, float uLen = 8f)
        {
            if (pts.Count < 2 || DMat("foam") == null) return;
            float s = 0f;
            for (int i = 0; i + 1 < pts.Count; i++)
            {
                Vector2 a = pts[i], b = pts[i + 1], na = DNormal(pts, i) * toSea, nb = DNormal(pts, i + 1) * toSea;
                float L = (b - a).magnitude;
                Vector2 ai = a - na * inner, ao = a + na * outer, bi = b - nb * inner, bo = b + nb * outer;
                var mb = DBatch(g, "foam", (a + b) * .5f);
                DQuadUp(mb, D3(ai, y(ai)), D3(bi, y(bi)), D3(bo, y(bo)), D3(ao, y(ao)),
                    new Vector2(s / uLen, 0f), new Vector2((s + L) / uLen, 0f), new Vector2((s + L) / uLen, 1f), new Vector2(s / uLen, 1f));
                s += L;
            }
        }

        // 0 m contour of the sea connected to the map edge (1 m grid, marching squares), chained into polylines
        static List<List<Vector2>> DShoreLines()
        {
            int nx = Mathf.FloorToInt(W) + 1, nz = Mathf.FloorToInt(Hh) + 1;
            var h = new float[nx * nz];
            for (int j = 0; j < nz; j++) for (int i = 0; i < nx; i++) h[j * nx + i] = Height(Mathf.Min(i, W - .05f), Mathf.Min(j, Hh - .05f));
            var sea = new bool[nx * nz]; var q = new Queue<int>();
            void Seed(int i, int j) { int k = j * nx + i; if (!sea[k] && h[k] < 0f) { sea[k] = true; q.Enqueue(k); } }
            for (int i = 0; i < nx; i++) { Seed(i, 0); Seed(i, nz - 1); }
            for (int j = 0; j < nz; j++) { Seed(0, j); Seed(nx - 1, j); }
            while (q.Count > 0)
            {
                int k = q.Dequeue(), i = k % nx, j = k / nx;
                if (i > 0) Seed(i - 1, j); if (i < nx - 1) Seed(i + 1, j); if (j > 0) Seed(i, j - 1); if (j < nz - 1) Seed(i, j + 1);
            }
            Vector2 EdgePos(int id)
            {
                int k = id >> 1, i = k % nx, j = k / nx, i1 = (id & 1) == 0 ? i + 1 : i, j1 = (id & 1) == 0 ? j : j + 1;
                float a = h[k], b = h[j1 * nx + i1];
                float t = (a < 0f) != (b < 0f) ? Mathf.Clamp01(a / (a - b)) : .5f;
                return Vector2.Lerp(new Vector2(i, j), new Vector2(i1, j1), t);
            }
            var adj = new Dictionary<int, List<int>>();
            void Link(int a, int b)
            {
                if (!adj.TryGetValue(a, out var la)) adj[a] = la = new List<int>(2); la.Add(b);
                if (!adj.TryGetValue(b, out var lb)) adj[b] = lb = new List<int>(2); lb.Add(a);
            }
            for (int j = 0; j + 1 < nz; j++)
                for (int i = 0; i + 1 < nx; i++)
                {
                    int k = j * nx + i;
                    int c = (sea[k] ? 1 : 0) | (sea[k + 1] ? 2 : 0) | (sea[k + nx + 1] ? 4 : 0) | (sea[k + nx] ? 8 : 0);
                    if (c == 0 || c == 15) continue;
                    int B = 2 * k, T = 2 * (k + nx), Lf = 2 * k + 1, Rt = 2 * (k + 1) + 1;
                    switch (c)
                    {
                        case 1: case 14: Link(Lf, B); break;
                        case 2: case 13: Link(B, Rt); break;
                        case 3: case 12: Link(Lf, Rt); break;
                        case 4: case 11: Link(Rt, T); break;
                        case 6: case 9: Link(B, T); break;
                        case 7: case 8: Link(Lf, T); break;
                        case 5: Link(Lf, B); Link(Rt, T); break;
                        case 10: Link(B, Rt); Link(Lf, T); break;
                    }
                }
            var used = new HashSet<int>(); var lines = new List<List<Vector2>>();
            List<Vector2> Walk(int start)
            {
                var o = new List<Vector2>(); int prev = -1, cur = start;
                while (cur >= 0 && used.Add(cur))
                {
                    o.Add(EdgePos(cur));
                    int nxt = -1;
                    foreach (int m in adj[cur]) if (m != prev && !used.Contains(m)) { nxt = m; break; }
                    prev = cur; cur = nxt;
                }
                return o;
            }
            foreach (int k in adj.Keys.ToList()) if (adj[k].Count == 1 && !used.Contains(k)) lines.Add(Walk(k));
            foreach (int k in adj.Keys.ToList()) if (!used.Contains(k)) { var l = Walk(k); if (l.Count > 2) l.Add(l[0]); lines.Add(l); }
            return lines.Where(l => l.Count >= 12).ToList();
        }

        // ================================================================== river foam (cascades, pool outlet, rapids)
        static void DRiverFoam(Dictionary<string, object> wj)
        {
            var b = Arr(Get(wj, "bodies")).Select(Obj).FirstOrDefault(o => o != null && S(Get(o, "kind"), "") == "river");
            if (b == null) return;
            var axis = V2s(Get(b, "axis")); int N = axis.Length; if (N < 3) return;
            var wid = Arr(Get(b, "width_m")).Select(x => F(x)).ToArray(); var surf = Arr(Get(b, "surface_m")).Select(x => F(x)).ToArray();
            var reach = Arr(Get(b, "reach")).Select(x => S(x, "") ?? "").ToArray();
            var spans = Arr(Get(b, "underground_spans")).Select(o => { var s = Arr(o); return (a: (int)F(s[0]), b: (int)F(s[1])); }).ToList();
            float Wd(int i) => i < wid.Length ? wid[i] : 6f;
            float Lv(int i) => i < surf.Length ? surf[i] : 0f;
            string Rc(int i) => i >= 0 && i < reach.Length ? reach[i] : "river";
            bool Wet(int i) => i >= 0 && i < N && !spans.Any(s => i >= s.a - 1 && i <= s.b + 1) && Rc(i) != "pool" && Rc(i) != "waterfall";
            float Ry(Vector2 p)
            {
                float best = float.MaxValue, y = 0f;
                for (int i = 0; i + 1 < N; i++)
                {
                    Vector2 a = axis[i], v = axis[i + 1] - a;
                    float t = Mathf.Clamp01(Vector2.Dot(p - a, v) / Mathf.Max(1e-4f, v.sqrMagnitude)), d = (p - (a + v * t)).sqrMagnitude;
                    if (d < best) { best = d; y = Mathf.Lerp(Lv(i), Lv(i + 1), t); }
                }
                return y + .04f;
            }
            var axisL = axis.ToList(); var cum = DCum(axisL);
            var R = new SRandom(8604);
            void Band(int ci, float frac, float side, float thick, string what)
            {   // foam band across the flow just below index ci (frac = part of the width, side = which bank it starts from)
                Vector2 d = (axis[Mathf.Min(ci + 1, N - 1)] - axis[Mathf.Max(ci - 1, 0)]).normalized, nl = new(-d.y, d.x);
                float hw = Wd(ci) * .5f + .4f, from = side >= 0f ? hw : -hw, to = from - Mathf.Sign(side >= 0f ? 1f : -1f) * 2f * hw * frac;
                var across = new List<Vector2>();
                int steps = Mathf.Max(2, Mathf.CeilToInt(Mathf.Abs(to - from)));
                for (int k = 0; k <= steps; k++) across.Add(axis[ci] + d * (thick * .5f + .3f) + nl * Mathf.Lerp(from, to, k / (float)steps));
                // the left normal of `across` points up- or downstream; the band spans thick / 2 to both sides
                DFoamStrip(GR, across, 1f, thick * .5f, thick * .5f, Ry, 6f);
                DC(what);
            }
            void Trails(int ci, float len, int sides, string what)
            {   // foam along the banks downstream of ci
                float s0 = cum[ci];
                foreach (int sg in sides == 2 ? new[] { 1, -1 } : new[] { R.NextDouble() < .5 ? 1 : -1 })
                {
                    var pts = new List<Vector2>();
                    for (float s = s0; s <= s0 + len && s < cum[N - 1]; s += 1f)
                    {
                        Vector2 p = DAt(axisL, cum, s, out Vector2 d); int k = DSeg(cum, s);
                        if (!Wet(k)) break;
                        pts.Add(p + new Vector2(-d.y, d.x) * sg * (Wd(k) * .5f - .1f));
                    }
                    if (pts.Count < 3) continue;
                    DFoamStrip(GR, pts, -sg, .4f, .6f, Ry, 6f);
                    DC(what);
                }
            }
            var cascades = Arr(Get(b, "cascades_axis_index")).Select(x => (int)F(x)).Where(Wet).ToList();
            for (int i = 1; i < N; i++) if (Rc(i - 1) == "pool" && Rc(i) != "pool" && Wet(i)) cascades.Add(i);      // plunge pool outlet
            foreach (int ci in cascades.Distinct()) { Band(ci, 1f, 1f, 2.6f, "T134 river cascade bands"); Trails(ci, 14f, 2, "T134 river bank trails"); }
            // rapids: the mountain stream and the gorge through the grey rocks
            for (float s = 6f; s < cum[N - 1] - 4f; s += DRnd(R, 9f, 16f))
            {
                int k = DSeg(cum, s);
                string rc = Rc(k);
                if ((rc != "stream" && rc != "gorge_rocks") || !Wet(k) || cascades.Any(c => Mathf.Abs(c - k) <= 2)) continue;
                Band(k, DRnd(R, .35f, .7f), R.NextDouble() < .5 ? 1f : -1f, DRnd(R, 1.2f, 1.9f), "T134 river rapids bands");
                if (R.NextDouble() < .6) Trails(k, DRnd(R, 4f, 8f), 1, "T134 river bank trails");
            }
        }

        // ================================================================== renderers: one per group / material / chunk
        static int DFlush()
        {
            int n = 0;
            float bias = Mathf.Max(.25f, QualitySettings.lodBias), tanH = Mathf.Tan(DFov * .5f * Mathf.Deg2Rad);
            foreach (var kv in DBat.OrderBy(k => k.Key.g).ThenBy(k => k.Key.m).ThenBy(k => k.Key.cx).ThenBy(k => k.Key.cz))
            {
                var (g, m, cx, cz) = kv.Key; var mb = kv.Value;
                if (mb.V.Count < 3 || mb.T.Count < 3) continue;
                var mat = DMat(m); if (!mat) continue;
                var grp = DGrp[g];
                string nm = $"Decal_{g}_{m}_{cx}_{cz}";
                var mesh = mb.Build(nm);
                mesh.RecalculateTangents(); EditorUtility.SetDirty(mesh);
                var go = new GameObject(nm); go.transform.SetParent(grp.t, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = mat;
                mr.shadowCastingMode = ShadowCastingMode.Off; mr.receiveShadows = true;
                mr.lightProbeUsage = LightProbeUsage.Off; mr.motionVectorGenerationMode = MotionVectorGenerationMode.Camera;
                if (grp.cull > 0f)
                {
                    var lod = go.AddComponent<LODGroup>();
                    lod.SetLODs(new[] { new LOD(.01f, new Renderer[] { mr }) });
                    lod.RecalculateBounds();                                        // size / reference point = the decals of this chunk
                    lod.SetLODs(new[] { new LOD(Mathf.Clamp(lod.size * .5f * bias / (grp.cull * tanH), .0002f, .95f), new Renderer[] { mr }) });
                }
                n++;
            }
            return n;
        }
    }
}
