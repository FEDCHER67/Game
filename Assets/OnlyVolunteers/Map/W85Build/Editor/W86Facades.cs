using System.Collections.Generic;
using System.Linq;
using OnlyVolunteers.Map.W76;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.W85
{
    // W86 Downtown v37 (Fedya 22.10: buildings vary in height and must not read as one continuous wall; offices get their own facade):
    //  - D4 houses read buildings[].separation (s04_downtown): facade_variant A-F (window rhythm / size / lintels / pairs / floor belts),
    //    end_pilasters (w, proud, tone) at both ends of every street / alley facade, corner_trim quoins on free corners, own cornice profile
    //    (flat_band / stepped / metal_cap / brick_corbel / dentil) with a break at the party walls, plinth height + material, party wall
    //    joint (dark recess strip, optional downpipe), setback_m (the street facade stands back, the strip in front is paved);
    //  - O class (facade_class "office", plan 05 / 06): aligned grid of large punched windows (~50 % glass) with stone spandrels and
    //    piers, thin dark metal frames, glazed lobby on the street, metal cap cornice, roof light over the lobby; NOT a curtain wall.
    //  - material hook: a slot of materials_v85.json may carry "texture_test" (one material) or "rollout_variants" [{"material": path,
    //    "share": 0.8, "tile_m": 3}] -> the rollout uses it for that slot's walls (per building by hash), else the approved TT surface.
    public static partial class W85Builder
    {
        sealed class SepP
        {
            public bool On, Lintel, Paired, Belts, Break, Quoins, Downpipe;
            public float Bay = 3.5f, Hw = .8f, Sill = .7f, Head = 2.7f, Setback, PlinthH = .5f, CorniceH, CorniceP, PilW, PilP = .12f, JointW;
            public string Variant = "A", Cornice, PilTone, PlinthMat = "stone";
            // W86 integration (v07 DS1 / DS2 / DS3, Fedya 22.10): own colours, rusticated base, string course, hooded windows
            public string Ds, CorCol, PilCol, StringCol, FrameCol; public bool Rustic, Hood; public int StringFl;
        }

        static SepP SepOf(Dictionary<string, object> sep)
        {
            var p = new SepP();
            if (sep == null) return p;
            p.On = true;
            p.Variant = S(Get(sep, "facade_variant"), "A");
            switch (p.Variant)
            {   // window rhythm per variant (A = the approved D4 face)
                case "B": p.Bay = 3.0f; p.Hw = .62f; p.Sill = .75f; p.Head = 2.75f; p.Lintel = true; break;
                case "C": p.Bay = 3.9f; p.Hw = .42f; p.Sill = .8f; p.Head = 2.6f; p.Paired = true; break;
                case "D": p.Bay = 3.5f; p.Hw = .75f; p.Sill = .8f; p.Head = 2.6f; p.Belts = true; break;
                case "E": p.Bay = 3.2f; p.Hw = .6f; p.Sill = .55f; p.Head = 2.95f; p.Lintel = true; break;
                case "F": p.Bay = 4.0f; p.Hw = .95f; p.Sill = .9f; p.Head = 2.5f; break;
            }
            var pil = Obj(Get(sep, "end_pilasters"));
            if (pil != null) { p.PilW = F(Get(pil, "w_m"), .45f); p.PilP = F(Get(pil, "proud_m"), .12f); p.PilTone = S(Get(pil, "tone"), "stone"); }
            p.Quoins = S(Get(sep, "corner_trim")) == "quoins";
            var co = Obj(Get(sep, "cornice"));
            if (co != null) { p.Cornice = S(Get(co, "profile"), "flat_band"); p.CorniceH = F(Get(co, "h_m"), .6f); p.CorniceP = F(Get(co, "proud_m"), .3f); }
            p.Break = !(Get(sep, "cornice_break") is bool cb) || cb;
            var pl = Obj(Get(sep, "plinth"));
            if (pl != null) { p.PlinthH = F(Get(pl, "h_m"), .5f); p.PlinthMat = S(Get(pl, "material"), "stone"); }
            var pj = Obj(Get(sep, "party_wall_joint"));
            if (pj != null) { p.JointW = F(Get(pj, "w_m"), .25f); p.Downpipe = Get(pj, "downpipe") is bool dp && dp; }
            p.Setback = Mathf.Clamp(F(Get(sep, "setback_m")), 0f, 1.5f);
            return p;
        }

        // street faces (kind 1) moved back by the setback (rect, CCW); the corners of two street faces move along both normals
        static List<Vector2> SetbackFp(List<Vector2> fp, int[] kinds, float by)
        {
            var o = fp.ToList();
            for (int i = 0; i < 4; i++)
            {
                if (kinds[i] != 1) continue;
                Vector2 d = (fp[(i + 1) % 4] - fp[i]).normalized, n = new(d.y, -d.x);
                o[i] -= n * by; o[(i + 1) % 4] -= n * by;
            }
            return o;
        }

        static Color Tone(string tone, Color wall, Color stone) =>
            tone == "lighter" ? new Color(Mathf.Min(1f, wall.r * 1.16f + .03f), Mathf.Min(1f, wall.g * 1.16f + .03f), Mathf.Min(1f, wall.b * 1.16f + .03f), 1f) :
            tone == "darker" ? new Color(wall.r * .8f, wall.g * .8f, wall.b * .8f, 1f) : stone;

        // the free width a facade end needs for its joint + pilaster / quoins (windows keep clear of it)
        static float SepEndClear(SepP sp, bool party) => !sp.On ? 0f : (party ? sp.JointW : 0f) + Mathf.Max(sp.PilW, sp.Quoins && !party ? .6f : 0f) + .12f;

        // ends of one street / alley face: party wall end -> dark joint strip (+ downpipe) and the end pilaster; free corner -> quoins
        // (corner_trim) else the pilaster
        static void SepEnds(RBatch det, Transform details, RFr w, float L, float yb, float tl, SepP sp, bool partyStart, bool partyEnd, Color wall, Color stone)
        {
            if (!sp.On) return;
            Color pc = sp.PilCol != null ? RX(sp.PilCol) : Tone(sp.PilTone, wall, stone), joint = new Color(wall.r * .55f, wall.g * .55f, wall.b * .55f, 1f);
            if (sp.PilCol != null) stone = RX(sp.PilCol);
            foreach (int e in new[] { 0, 1 })
            {
                bool party = e == 0 ? partyStart : partyEnd;
                float dir = e == 0 ? 1f : -1f, s0 = e == 0 ? 0f : L;
                float at = s0;
                if (party && sp.JointW > .05f)
                {
                    float a = at, b = at + dir * sp.JointW;
                    RWallBox(det, "flat", w, Mathf.Min(a, b), Mathf.Max(a, b), yb, tl, .012f, joint);
                    if (sp.Downpipe)
                        for (float y = .3f; y < tl - .6f; y += 2.8f) RPiece("FK_R_Drainpipe_2m8", details, w.P((a + b) * .5f, y, 0), w.Out);
                    at = b;
                }
                if (!party && sp.Quoins)
                {
                    int k = 0;
                    for (float y = sp.PlinthH + .05f; y + .5f < tl - .2f; y += .55f, k++)
                    {
                        float qw = k % 2 == 0 ? .6f : .34f, a = at, b = at + dir * qw;
                        RWallBox(det, "flat", w, Mathf.Min(a, b), Mathf.Max(a, b), y, y + .5f, .05f, stone);
                    }
                }
                else if (sp.PilW > .05f)
                {
                    float a = at, b = at + dir * sp.PilW;
                    RWallBox(det, "flat", w, Mathf.Min(a, b), Mathf.Max(a, b), yb, tl, sp.PilP, pc);
                }
            }
        }

        // cornice band along a street face at the roof line, inset at the ends (cornice break at the party walls)
        static void SepCornice(RBatch det, RFr w, float L, float tl, SepP sp, float i0, float i1, Color wall, Color stone)
        {
            float s0 = i0, s1 = L - i1, h = Mathf.Max(.25f, sp.CorniceH), p = Mathf.Max(.08f, sp.CorniceP);
            if (s1 - s0 < .5f || sp.Cornice == "none") return;
            if (sp.CorCol != null) stone = RX(sp.CorCol);
            Color brick = RNearest(DtBrick, wall), metal = RX("3B4045"), band = Tone("lighter", wall, stone);
            void Bx(float y0, float y1, float pr, Color c) => RWallBox(det, "flat", w, s0, s1, y0, y1, pr, c);
            switch (sp.Cornice)
            {
                case "stepped": Bx(tl - h, tl - h * .55f, p * .5f, stone); Bx(tl - h * .55f, tl, p, stone); break;
                case "metal_cap": Bx(tl - h, tl - h * .25f, p * .55f, band); Bx(tl - h * .25f, tl, p, metal); break;
                case "brick_corbel": Bx(tl - h, tl - h * .66f, p * .33f, brick); Bx(tl - h * .66f, tl - h * .33f, p * .66f, brick); Bx(tl - h * .33f, tl, p, brick); break;
                case "dentil":
                    Bx(tl - h * .5f, tl, p, stone);
                    for (float s = s0 + .12f; s + .14f < s1; s += .32f) RWallBox(det, "flat", w, s, s + .14f, tl - h * .85f, tl - h * .5f, p * .6f, stone);
                    break;
                default: Bx(tl - h, tl, p, stone); break;            // flat_band
            }
        }

        // ------------------------------------------------------------------ material hook per slot (next texture rollout)
        static string RolloutWallSurf(string slot, string id, string fallbackKey)
        {
            var rec = Obj(Get(Slots, slot ?? ""));
            if (rec == null) return fallbackKey;
            string path = null; float tile = F(Get(rec, "rollout_tile_m"), 3f);
            var variants = Arr(Get(rec, "rollout_variants")).Select(Obj).Where(v => v != null && S(Get(v, "material")) != null).ToList();
            if (variants.Count > 0)
            {
                float h = RHash(id, 61), total = variants.Sum(v => F(Get(v, "share"), 1f)), acc = 0f;
                foreach (var v in variants)
                {
                    acc += F(Get(v, "share"), 1f) / Mathf.Max(1e-4f, total);
                    if (h <= acc || v == variants[variants.Count - 1]) { path = S(Get(v, "material")); tile = F(Get(v, "tile_m"), tile); break; }
                }
            }
            else path = S(Get(rec, "texture_test"));
            if (string.IsNullOrEmpty(path)) return fallbackKey;
            string key = "slot:" + path + ":" + tile;
            if (RS.ContainsKey(key)) return key;
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { RolloutIssue($"slot {slot}: material {path} missing, approved surface kept"); return fallbackKey; }
            RS[key] = RSurfOf(m, tile, tile);
            return key;
        }

        // ================================================================== Downtown offices (O class, plan 05 / 06)
        static bool RolloutOffice(Transform go, Dictionary<string, object> b, List<Vector2> fp, string id, string district)
        {
            var roof = Obj(Get(b, "roof")) ?? new Dictionary<string, object> { ["type"] = "flat" };
            int floors = Mathf.Clamp((int)F(Get(b, "floors"), 6f), 1, 12);
            float Fh = F(Get(b, "floor_h_m"), 3.6f), Gf = 4.4f;
            float H = floors == 1 ? Mathf.Max(Gf, F(Get(b, "height_m"), Gf)) : Gf + (floors - 1) * Fh;
            var sk = Obj(Get(b, "sockets")) ?? new Dictionary<string, object>();
            var ents = Arr(Get(b, "entrances")).Select(Obj).Where(e => e != null && Get(e, "pos") != null).ToList();
            var kinds = D4Faces(fp, id, ents, out float floor0);
            float baseY = Mathf.Min(fp.Min(q => Height(q.x, q.y)) - .25f, floor0 - .4f);
            float top = floor0 + H, yb = baseY - floor0, tl = H;
            string slot = S(Get(b, "material_slot"), "downtown_office");
            string wallKey = RolloutWallSurf(slot, id, "acg_plaster");
            Color tint = RX(S(Get(b, "tint")) ?? "B3B0A7");
            Color wall = Color.Lerp(RNearest(DtPlaster, tint), RX("CFC7B4"), .55f);      // light stone-like render (placeholder look)
            Color stone = RX(RPick(DtStone, id, 46)), metal = RX("2E3236"), glassTint = RX("3A4752");
            var details = new GameObject("details").transform; details.SetParent(go, false);
            var kit = new GameObject("kit").transform; kit.SetParent(go, false);
            var body = new RBatch(); var det = new RBatch();
            var f = RFr.Yaw(new Vector3(0, floor0, 0), 0);
            var mainDoor = ents.FirstOrDefault(e => (S(Get(e, "role"), "") ?? "").Contains("main")) ?? ents.FirstOrDefault();
            for (int i = 0; i < 4; i++)
            {
                Vector2 p0 = fp[i], p1 = fp[(i + 1) % 4];
                var w = f.Wall(p0, p1); float L = (p1 - p0).magnitude;
                int np2 = Mathf.Max(1, Mathf.RoundToInt(L / 2f)); float pst = L / np2;
                for (int k = 0; k < np2; k++) { var pp = RPiece("FK_D_Parapet_2m", details, w.P(pst * (k + .5f), tl, 0), w.Out, ("FK_Stone", RAcc("FK_Stone", "CEC4B1")), ("FK_Brick", RAcc("FK_Stone", "CEC4B1"))); if (pp) pp.transform.localScale = new Vector3(pst / 2f, 1f, 1f); }
                if (kinds[i] == 2 || L < 3f) { RWall(body, wallKey, w, 0, L, yb, tl, wall); continue; }
                bool street = kinds[i] == 1;
                int bays = Mathf.Max(1, Mathf.RoundToInt(L / 3.6f)); float bw = L / bays;
                float Bay(int k) => bw * (k + .5f);
                float hw = bw * .5f - .45f;
                var holes = new List<Rect>(); var kindsH = new List<int>();          // 0 office window, 1 lobby glass, 2 lobby door
                for (int fl = 1; fl < floors; fl++)
                {
                    float yf = Gf + (fl - 1) * Fh;
                    for (int k = 0; k < bays; k++) { holes.Add(Rect.MinMaxRect(Bay(k) - hw, yf + .85f, Bay(k) + hw, yf + Fh - .45f)); kindsH.Add(0); }
                }
                float sDoor = -1f;
                if (mainDoor != null)
                {
                    Vector2 dp = V2(Get(mainDoor, "pos")); float s = Vector2.Dot(dp - p0, (p1 - p0) / L);
                    if (s > -.2f && s < L + .2f && Mathf.Abs(Cross(p0, p1, dp)) / L < .8f) sDoor = Mathf.Clamp(s, 1.6f, L - 1.6f);
                }
                for (int k = 0; k < bays; k++)
                {
                    if (street) { bool door = sDoor >= 0f && Mathf.Abs(Bay(k) - sDoor) < bw * .5f; holes.Add(Rect.MinMaxRect(Bay(k) - (bw * .5f - .3f), door ? 0f : .35f, Bay(k) + (bw * .5f - .3f), Gf - .55f)); kindsH.Add(door ? 2 : 1); }
                    else if (k % 2 == 0) { holes.Add(Rect.MinMaxRect(Bay(k) - Mathf.Min(hw, 1f), 1.1f, Bay(k) + Mathf.Min(hw, 1f), Gf - .9f)); kindsH.Add(0); }
                }
                ROpenings(body, wallKey, w, L, yb, tl, wall, holes, .2f);
                for (int j = 0; j < holes.Count; j++)
                {
                    var o = holes[j];
                    RBox(body, "glass_dt", w, new Vector3(o.center.x, o.center.y, .205f), new Vector3(o.width, o.height, .01f), glassTint, RZN);
                    float zc = .17f, t = kindsH[j] == 0 ? .06f : .09f;
                    RBox(det, "flat", w, new Vector3(o.center.x, o.yMin + t / 2, zc), new Vector3(o.width, t, .06f), metal, RFM);
                    RBox(det, "flat", w, new Vector3(o.center.x, o.yMax - t / 2, zc), new Vector3(o.width, t, .06f), metal, RFM);
                    RBox(det, "flat", w, new Vector3(o.xMin + t / 2, o.center.y, zc), new Vector3(t, o.height, .06f), metal, RFM);
                    RBox(det, "flat", w, new Vector3(o.xMax - t / 2, o.center.y, zc), new Vector3(t, o.height, .06f), metal, RFM);
                    int mull = Mathf.Max(1, Mathf.RoundToInt(o.width / 1.3f));
                    for (int m = 1; m < mull; m++) RBox(det, "flat", w, new Vector3(o.xMin + o.width * m / mull, o.center.y, zc), new Vector3(.045f, o.height, .05f), metal, RFM);
                    RBox(det, "flat", w, new Vector3(o.center.x, o.yMin + (kindsH[j] == 0 ? o.height * .72f : 2.5f), zc), new Vector3(o.width, .045f, .05f), metal, RFM);   // transom
                    if (kindsH[j] == 0) RBox(det, "flat", w, new Vector3(o.center.x, o.yMin - .03f, .06f), new Vector3(o.width + .1f, .06f, .3f), stone, ROUT);              // sill
                }
                // stone spandrels (floor bands) + piers on the bay grid: the aligned office grid
                for (int fl = 1; fl < floors; fl++)
                {
                    float yf = Gf + (fl - 1) * Fh;
                    RWallBox(det, "flat", w, 0, L, yf - .45f, yf + .85f, .05f, stone);
                }
                for (int k = 0; k <= bays; k++)
                {
                    float s = bw * k, a = Mathf.Max(0f, s - .22f), c = Mathf.Min(L, s + .22f);
                    RWallBox(det, "flat", w, a, c, street ? Gf - .55f : Gf, tl - .55f, .09f, stone);
                }
                if (street)
                {
                    RWallBox(det, "flat", w, 0, L, Gf - .55f, Gf, .12f, stone);                     // lobby head band
                    RWallBox(det, "flat", w, 0, L, yb, .35f, .06f, RX("4A4F52"));                    // dark granite plinth
                    if (sDoor >= 0f)
                    {   // entrance canopy (flat, stone edge) over the main door
                        RBox(det, "flat", w, new Vector3(sDoor, Gf - .2f, -.7f), new Vector3(Mathf.Min(5f, bw + 1f), .22f, 1.4f), stone, RALL6);
                        RBox(det, "flat", w, new Vector3(sDoor, .06f, -.6f), new Vector3(Mathf.Min(5f, bw + 1f), .12f, 1.2f), RX("8E8A82"), RALL6);   // step
                    }
                }
                RWallBox(det, "flat", w, -.02f, L + .02f, tl - .55f, tl - .12f, .22f, metal);   // metal cap cornice
            }
            Frame(fp, new Dictionary<string, object>(), out Vector2 rc, out Vector2 rax, out Vector2 ray, out float rhx, out float rhy);
            var rf = RFr.Yaw(new Vector3(rc.x, floor0, rc.y), Mathf.Atan2(ray.x, ray.y) * Mathf.Rad2Deg);
            RPlane(body, "roof_flat", rf, -rhx, -rhy, rhx, rhy, tl, RS["roof_flat"].Own);
            // roof light over the lobby (plan: blue gridded roof): glazed box near the street side
            int streetFace = System.Array.IndexOf(kinds, 1);
            Vector2 lc = rc;
            if (streetFace >= 0) { Vector2 m = (fp[streetFace] + fp[(streetFace + 1) % 4]) * .5f; lc = Vector2.Lerp(rc, m, .45f); }
            var lf = RFr.Yaw(new Vector3(lc.x, floor0, lc.y), Mathf.Atan2(ray.x, ray.y) * Mathf.Rad2Deg);
            float lx = Mathf.Min(4f, rhx * .5f), lz = Mathf.Min(2.4f, rhy * .5f);
            RBox(body, "glass_dt", lf, new Vector3(0, tl + .45f, 0), new Vector3(2 * lx, .9f, 2 * lz), glassTint, RALL5);
            for (float x = -lx; x <= lx + .01f; x += lx / 2f) RBox(det, "flat", lf, new Vector3(x, tl + .92f, 0), new Vector3(.06f, .06f, 2 * lz), metal, RALL5);
            int ac = Mathf.Clamp((int)F(Get(sk, "ac_units"), 1f), 0, 4);
            for (int k = 0; k < ac; k++) RPiece("FK_D_AC_Unit", kit, lf.P(-rhx * .7f + k * 1.6f, tl, -rhy * .6f) + new Vector3(0, 0, 0), Vector3.forward);
            if (Get(sk, "antenna") is bool an && an) RBox(det, "flat", rf, new Vector3(rhx * .6f, tl + 2f, rhy * .4f), new Vector3(.12f, 4f, .12f), metal, RALL5);
            var bodyT = new GameObject("body").transform; bodyT.SetParent(go, false);
            RFlush(body, bodyT, "B_" + id + "_O");
            RFlush(det, details, "B_" + id + "_O_det");
            Colliders(go, id, fp, baseY, top, "flat", roof, new List<Arch>());
            Built.Add(new BInfo { Go = go.gameObject, Id = district + "/" + id, Fp = fp, Base = baseY, Top = top, Type = "flat", Roof = roof });
            RolloutLod(go.gameObject, details);
            rolledO++;
            return true;
        }

        static int rolledO;
    }
}
