using System.Collections.Generic;
using System.Linq;
using OnlyVolunteers.Map.W76;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map.W85
{
    // W86 district readers (data v02): pieces the generic W85 builder had no rule for.
    //  - Construction fuel station 02 (Fedya 22.10 item 16): canopy 12 x 6.8 m on 4 columns, clear 4.6 m (white fascia, colour stripe,
    //    LED panels, no text), pump island with 2 dispensers + bollards, driveways flush with the road, kerbed planter, parked cars;
    //  - Downtown NEB courtyard (item 9): black wrought-iron double gate with an arched top between brick piers (stone cap, lantern),
    //    trimmed box hedges (planter kerb), bench; side gaps between row houses (8, iron gate / railing 2.2 m on the facade line, a second
    //    one at the back where no house closes it);
    //  - markers, not boxes: NPC spots (fuel station cashier / customers, Elite beach guards, the Hamlet grandpa-policeman post) and the
    //    Elite beach guard patrol loop (waypoints; patrol behaviour = gameplay code).
    public static partial class W85Builder
    {
        static int w86Gates, w86Gaps, w86Markers, w86Patrols, w86Hedges, w86Planters;
        static readonly Dictionary<string, Material> W86Mats = new();

        static Material W86Mat(string name, Color c, float smooth = .15f, float metal = 0f, Color? emission = null)
        {
            if (W86Mats.TryGetValue(name, out var m) && m) return m;
            m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = name, enableInstancing = true };
            m.SetColor("_BaseColor", c); m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", metal);
            if (emission.HasValue) { m.EnableKeyword("_EMISSION"); m.SetColor("_EmissionColor", emission.Value); m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None; }
            Folder(Gen + "/Materials/W86");
            AssetDatabase.CreateAsset(m, Gen + "/Materials/W86/" + name + ".mat"); created++;
            return W86Mats[name] = m;
        }

        static Material Iron => W86Mat("W86_iron_black", new Color(.09f, .09f, .1f), .35f, .5f);

        // box (centre, size in the yaw frame) into a mesh builder: 6 outward faces, UV in metres
        static void MBBox(MB mb, Vector3 c, Vector3 size, float yawDeg)
        {
            var q = Quaternion.Euler(0, yawDeg, 0);
            Vector3 hx = q * Vector3.right * size.x * .5f, hy = Vector3.up * size.y * .5f, hz = q * Vector3.forward * size.z * .5f;
            void F4(Vector3 o, Vector3 u, Vector3 v, float lu, float lv)
            {   // face centre o, half axes u (along), v (up): front = u x v ... MB.Quad front = (b - a) x (c - a)
                mb.Quad(o - u - v, o - u + v, o + u + v, o + u - v, Vector2.zero, new Vector2(0, lv), new Vector2(lu, lv), new Vector2(lu, 0));
            }
            F4(c - hz, hx, hy, size.x, size.y); F4(c + hz, -hx, hy, size.x, size.y);
            F4(c + hx, hz, hy, size.z, size.y); F4(c - hx, -hz, hy, size.z, size.y);
            F4(c + hy, hx, hz, size.x, size.z); F4(c - hy, hx, -hz, size.x, size.z);
        }

        // ------------------------------------------------------------------ building hook
        static bool W86Building(Transform parent, Dictionary<string, object> b, string district, string kind, List<Vector2> fp, string id)
        {
            if (kind == "fuel_canopy" || (kind.EndsWith("canopy") && S(Get(b, "walls")) == null))
            {   // W86 integration: XC1 a (T2) look on the W86 canopy (its columns / colliders kept)
                if (!FuelCanopy(parent, b, district, fp, id)) return false;
                var cg = parent.Find("B_" + id); if (cg) T2Building(cg, b, fp, id, "XC1canopy", 'a', 270f);
                return true;
            }
            if (kind == "kiosk" && id.Contains("fuel") && fp.Count == 4)
            {
                if (!FuelKiosk(parent, b, district, fp, id)) return false;
                var kg = parent.Find("B_" + id); if (kg) T2Building(kg, b, fp, id, "XC1kiosk", 'a');
                return true;
            }
            return false;
        }

        static bool FuelCanopy(Transform parent, Dictionary<string, object> b, string district, List<Vector2> fp, string id)
        {
            Frame(fp, new Dictionary<string, object>(), out Vector2 c, out Vector2 ax, out Vector2 ay, out float hx, out float hy);
            float clear = F(Get(b, "height_m"), 4.6f), fascia = .85f, ground = fp.Max(q => Height(q.x, q.y));
            float yaw = -Mathf.Atan2(ax.y, ax.x) * Mathf.Rad2Deg, y0 = ground + clear;
            var go = new GameObject("B_" + id); go.transform.SetParent(parent, false);
            var mb = new MB(); var stripe = new MB(); var led = new MB(); var cols = new MB();
            Vector3 C3(Vector2 p, float y) => new(p.x, y, p.y);
            MBBox(mb, C3(c, y0 + fascia * .5f), new Vector3(2 * hx, fascia, 2 * hy), yaw);
            MBBox(stripe, C3(c, y0 + fascia * .42f), new Vector3(2 * hx + .03f, .22f, 2 * hy + .03f), yaw);
            for (int k = -1; k <= 1; k++) MBBox(led, C3(c + ax * k * hx * .6f, y0 - .03f), new Vector3(hx * .45f, .05f, 2 * hy - 1.4f), yaw);
            var colPos = new List<Vector2>();
            foreach (int sx in new[] { -1, 1 }) foreach (int sy in new[] { -1, 1 }) colPos.Add(c + ax * sx * (hx - 1.1f) + ay * sy * (hy - .9f));
            foreach (var p in colPos) { float g = Height(p.x, p.y) - .2f; MBBox(cols, C3(p, (g + y0) * .5f), new Vector3(.4f, y0 - g, .4f), yaw); }
            var white = W86Mat("W86_canopy_white", RX(S(Get(b, "tint")) ?? "F2F2EE"), .3f);
            var shadowOn = MeshGo("canopy", go.transform, mb.Build("B_" + id + "_canopy"), white);
            MeshGo("stripe", go.transform, stripe.Build("B_" + id + "_stripe"), W86Mat("W86_canopy_stripe", RX("2F7F6F"), .3f)).GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
            MeshGo("led", go.transform, led.Build("B_" + id + "_led"), W86Mat("W86_led_panel", new Color(.92f, .94f, .95f), .5f, 0f, new Color(.9f, .92f, .95f))).GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
            MeshGo("columns", go.transform, cols.Build("B_" + id + "_columns"), W86Mat("W86_canopy_column", RX("D9DCDD"), .3f, .2f));
            var colT = new GameObject("colliders").transform; colT.SetParent(go.transform, false);
            AddBox(colT, c, y0, y0 + fascia, 2 * hx, 2 * hy, yaw);
            foreach (var p in colPos) AddBox(colT, p, Height(p.x, p.y) - .2f, y0, .4f, .4f, yaw);
            Built.Add(new BInfo { Go = go, Id = district + "/" + id, Fp = fp, Base = ground, Top = y0 + fascia, Type = "flat", Roof = new Dictionary<string, object>() });
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            return true;
        }

        // fuel station cash kiosk (plan v11): light panel walls, glazed front with the door to the pumps, service window to the road,
        // dark fascia with the station stripe, flat roof; W85 body collider + roof test
        static bool FuelKiosk(Transform parent, Dictionary<string, object> b, string district, List<Vector2> fp, string id)
        {
            if (!rollout) return false;
            var go = new GameObject("B_" + id); go.transform.SetParent(parent, false);
            float H = F(Get(b, "height_m"), 2.8f), floor0 = fp.Max(q => Height(q.x, q.y)) + .12f, baseY = fp.Min(q => Height(q.x, q.y)) - .25f, yb = baseY - floor0;
            Color wall = RX(S(Get(b, "tint")) ?? "DCE3E6"), frame = RX("33393D"), glass = RX("3E4B55"), stripe = RX("2F7F6F");
            var ents = Arr(Get(b, "entrances")).Select(Obj).Where(e => e != null && Get(e, "pos") != null).ToList();
            var body = new RBatch(); var det = new RBatch();
            var f = RFr.Yaw(new Vector3(0, floor0, 0), 0);
            for (int i = 0; i < 4; i++)
            {
                Vector2 p0 = fp[i], p1 = fp[(i + 1) % 4]; var w = f.Wall(p0, p1); float L = (p1 - p0).magnitude;
                var mine = ents.Where(e => Mathf.Abs(Cross(p0, p1, V2(Get(e, "pos")))) / L < .6f).ToList();
                var holes = new List<Rect>(); var door = new List<bool>();
                foreach (var e in mine)
                {
                    float s = Mathf.Clamp(Vector2.Dot(V2(Get(e, "pos")) - p0, (p1 - p0) / L), .8f, L - .8f), ew = F(Get(e, "w_m"), 1f);
                    bool isDoor = S(Get(e, "kind"), "door") == "door";
                    if (isDoor)
                    {   // glazed front: the door + glass panes over the rest of this face
                        holes.Add(Rect.MinMaxRect(s - ew * .5f, 0f, s + ew * .5f, 2.2f)); door.Add(true);
                        if (s - ew * .5f - .3f > .9f) { holes.Add(Rect.MinMaxRect(.3f, .5f, s - ew * .5f - .3f, 2.3f)); door.Add(false); }
                        if (L - .3f - (s + ew * .5f + .3f) > .6f) { holes.Add(Rect.MinMaxRect(s + ew * .5f + .3f, .5f, L - .3f, 2.3f)); door.Add(false); }
                    }
                    else { holes.Add(Rect.MinMaxRect(s - ew * .5f, .95f, s + ew * .5f, 2.0f)); door.Add(false); }
                }
                ROpenings(body, "flat", w, L, yb, H, wall, holes, .12f);
                for (int j = 0; j < holes.Count; j++)
                {
                    var o = holes[j];
                    RBox(body, "glass_dt", w, new Vector3(o.center.x, o.center.y, .125f), new Vector3(o.width, o.height, .01f), glass, RZN);
                    foreach (float x in new[] { o.xMin + .04f, o.xMax - .04f }) RBox(det, "flat", w, new Vector3(x, o.center.y, .09f), new Vector3(.08f, o.height, .06f), frame, RFM);
                    RBox(det, "flat", w, new Vector3(o.center.x, o.yMax - .04f, .09f), new Vector3(o.width, .08f, .06f), frame, RFM);
                    if (!door[j]) RBox(det, "flat", w, new Vector3(o.center.x, o.yMin + .04f, .09f), new Vector3(o.width, .08f, .06f), frame, RFM);
                    if (!door[j] && o.yMin > .9f) RBox(det, "flat", w, new Vector3(o.center.x, o.yMin - .03f, -.15f), new Vector3(o.width + .2f, .06f, .4f), frame, ROUT);   // counter shelf
                }
                RWallBox(det, "flat", w, -.05f, L + .05f, H - .45f, H + .05f, .08f, frame);
                RWallBox(det, "flat", w, -.06f, L + .06f, H - .32f, H - .2f, .09f, stripe);
            }
            Frame(fp, new Dictionary<string, object>(), out Vector2 rc, out _, out Vector2 ray, out float rhx, out float rhy);
            RPlane(body, "roof_flat", RFr.Yaw(new Vector3(rc.x, floor0, rc.y), Mathf.Atan2(ray.x, ray.y) * Mathf.Rad2Deg), -rhx, -rhy, rhx, rhy, H, RS["roof_flat"].Own);
            var details = new GameObject("details").transform; details.SetParent(go.transform, false);
            var bodyT = new GameObject("body").transform; bodyT.SetParent(go.transform, false);
            RFlush(body, bodyT, "B_" + id + "_kiosk"); RFlush(det, details, "B_" + id + "_kiosk_det");
            Colliders(go.transform, id, fp, baseY, floor0 + H, "flat", new Dictionary<string, object>(), new List<Arch>());
            Built.Add(new BInfo { Go = go, Id = district + "/" + id, Fp = fp, Base = baseY, Top = floor0 + H, Type = "flat", Roof = new Dictionary<string, object>() });
            RolloutLod(go, details);
            return true;
        }

        // ------------------------------------------------------------------ prop hook
        static bool W86Prop(Transform parent, Dictionary<string, object> p, string kind, string id, Vector2 q)
        {
            float rot = F(Get(p, "rot_deg", "facing_deg")), yaw = -rot;
            var sz = Arr(Get(p, "size"));
            Vector3 size = sz.Count >= 3 ? new Vector3(F(sz[0]), F(sz[2]), F(sz[1])) : new Vector3(1, 1, 1);
            if (kind.Contains("waterfall")) return true;                               // built by the water step from water_v85.json (W86)
            if (kind == "npc_spot" || kind.EndsWith("_npc") || kind.StartsWith("npc_"))
            {   // a named marker for gameplay (role in the name), facing the data direction
                string role = S(Get(p, "role")) ?? S(Get(p, "npc")) ?? kind;
                var mk = new GameObject("NpcSpot_" + id + "_" + Safe(role.Split('(')[0].Trim()));
                mk.transform.SetParent(parent, false);
                mk.transform.SetPositionAndRotation(P(q), Quaternion.Euler(0, 90f - rot, 0));
                w86Markers++;
                return true;
            }
            switch (kind)
            {
                case "courtyard_gate":
                {
                    Vector2 d = new(Mathf.Cos(rot * Mathf.Deg2Rad), Mathf.Sin(rot * Mathf.Deg2Rad));
                    IronGate(parent, id, q - d * size.x * .5f, q + d * size.x * .5f, Mathf.Max(1.8f, size.y), true, Get(p, "grip_anchor") is bool g && g);
                    return true;
                }
                case "gate_pier":
                {
                    float h = Mathf.Max(1f, size.y);
                    var pier = Box(parent, id, P(q, h * .5f - .1f), new Vector3(size.x, h + .2f, size.z), yaw, S(Get(p, "material"), "brick_SK3a"), true);
                    Box(pier.transform.parent, id + "_cap", P(q, h + .07f), new Vector3(size.x + .16f, .14f, size.z + .16f), yaw, "plaza_M3", false);
                    var lantern = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    lantern.name = id + "_lantern"; lantern.transform.SetParent(parent, false);
                    Object.DestroyImmediate(lantern.GetComponent<Collider>());
                    lantern.transform.SetPositionAndRotation(P(q, h + .32f), Quaternion.Euler(0, yaw, 0)); lantern.transform.localScale = new Vector3(.24f, .34f, .24f);
                    lantern.GetComponent<MeshRenderer>().sharedMaterial = W86Mat("W86_lantern", new Color(.95f, .86f, .62f), .4f, 0f, new Color(.6f, .5f, .3f));
                    if (Get(p, "grip_anchor") is bool g && g) pier.AddComponent<W76GripAnchor>();
                    return true;
                }
                case "hedge_trimmed":
                {
                    float h = Mathf.Max(.4f, size.y);
                    Box(parent, "Hedge_" + id, P(q, h * .5f - .05f), new Vector3(size.x, h + .1f, size.z), yaw, "lawn_hedge", true);
                    if ((S(Get(p, "style"), "") ?? "").Contains("kerb"))
                        Box(parent, "Hedge_" + id + "_kerb", P(q, .1f), new Vector3(size.x + .16f, .3f, size.z + .16f), yaw, "concrete_SK3c", false);
                    w86Hedges++;
                    return true;
                }
                case "fuel_pump_island":
                {
                    Vector2 d = new(Mathf.Cos(rot * Mathf.Deg2Rad), Mathf.Sin(rot * Mathf.Deg2Rad));
                    float L = Mathf.Max(3f, size.x), Wd = Mathf.Max(.8f, size.z);
                    Box(parent, id + "_kerb", P(q, .07f), new Vector3(L, .3f, Wd), yaw, "concrete_SK3c", true);
                    foreach (int s in new[] { -1, 1 })
                    {
                        var disp = Box(parent, id + "_dispenser" + (s < 0 ? "A" : "B"), P(q + d * s * L * .22f, 1.05f), new Vector3(.9f, 1.8f, .5f), yaw, "metal_painted_SK6a", true);
                        disp.GetComponent<MeshRenderer>().sharedMaterial = W86Mat("W86_dispenser", RX("E9ECEB"), .35f);
                        var band = Box(parent, id + "_band" + (s < 0 ? "A" : "B"), P(q + d * s * L * .22f, 1.6f), new Vector3(.92f, .2f, .52f), yaw, "metal_painted_SK6a", false);
                        band.GetComponent<MeshRenderer>().sharedMaterial = W86Mat("W86_canopy_stripe", RX("2F7F6F"), .3f);
                        if (Get(p, "grip_anchor") is bool g && g) disp.AddComponent<W76GripAnchor>();
                        var bol = Box(parent, id + "_bollard" + (s < 0 ? "A" : "B"), P(q + d * s * (L * .5f - .15f), .55f), new Vector3(.16f, .9f, .16f), yaw, "metal_painted_SK6a", true);
                        bol.GetComponent<MeshRenderer>().sharedMaterial = W86Mat("W86_bollard_yellow", RX("D9B23A"), .3f);
                    }
                    return true;
                }
                case "parked_car":
                {
                    Color t = RX(S(Get(p, "tint")) ?? "8FA9C2");
                    var opts = new (string k, Color c)[] { ("car_sedan_beige", RX("C9B79A")), ("car_sedan_blue", RX("5A7FA6")), ("car_sedan_green", RX("6F8F6A")), ("car_sedan_red", RX("A8504A")), ("car_hatchback", RX("9A9A94")) };
                    string pick = opts.OrderBy(o => (o.c.r - t.r) * (o.c.r - t.r) + (o.c.g - t.g) * (o.c.g - t.g) + (o.c.b - t.b) * (o.c.b - t.b)).First().k;
                    var pf = Prefab(pick);
                    if (!pf) return false;
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(pf, parent);
                    go.name = id; go.transform.SetPositionAndRotation(P(q), Quaternion.Euler(0, 90f - rot, 0));
                    foreach (Transform tr in go.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(tr.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
                    return true;
                }
            }
            return false;
        }

        static object Get(Dictionary<string, object> d, string k, string alt) => Get(d, k) ?? Get(d, alt);

        // Wrought-iron gate / railing a -> b: frame, bars every 0.13 m (arched top optional), one thin box collider.
        static void IronGate(Transform parent, string id, Vector2 a, Vector2 b, float h, bool arch, bool grip)
        {
            Vector2 d = b - a; float L = d.magnitude;
            if (L < .3f) return;
            d /= L;
            float yaw = -Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg;
            float g0 = Mathf.Min(Height(a.x, a.y), Height(b.x, b.y));
            var mb = new MB();
            Vector3 At(float s, float y) { var p = a + d * s; return new Vector3(p.x, g0 + y, p.y); }
            float top(float s) => arch ? h - .35f + .35f * Mathf.Sin(Mathf.PI * Mathf.Clamp01(s / L)) : h;
            MBBox(mb, At(L * .5f, .12f), new Vector3(L, .06f, .05f), yaw);                    // bottom rail
            MBBox(mb, At(L * .5f, h - .45f), new Vector3(L, .06f, .05f), yaw);                // upper rail
            foreach (float s in new[] { .04f, L * .5f, L - .04f }) MBBox(mb, At(s, top(s) * .5f), new Vector3(.08f, top(s), .07f), yaw);   // stiles
            for (float s = .17f; s < L - .1f; s += .13f) { float t = top(s); MBBox(mb, At(s, t * .5f + .03f), new Vector3(.025f, t - .06f, .025f), yaw); }
            if (arch) for (int k = 0; k < 12; k++)
                {   // arched top rail as short segments
                    float s0 = L * k / 12f, s1 = L * (k + 1) / 12f, y0 = top(s0), y1 = top(s1);
                    Vector3 p0 = At(s0, y0), p1 = At(s1, y1);
                    MBBox(mb, (p0 + p1) * .5f, new Vector3((p1 - p0).magnitude + .02f, .06f, .05f), yaw);
                }
            var go = MeshGo("Gate_" + id, parent, mb.Build("Gate_" + id), Iron);
            var col = new GameObject("collider").AddComponent<BoxCollider>();
            col.transform.SetParent(go.transform, false);
            col.transform.SetPositionAndRotation(At(L * .5f, h * .5f), Quaternion.Euler(0, yaw, 0));
            col.size = new Vector3(L, h, .12f);
            if (grip) go.AddComponent<W76GripAnchor>();
            w86Gates++;
        }

        // ------------------------------------------------------------------ zone hook (inside Extras)
        static bool W86Zone(Transform parent, Dictionary<string, object> z, string kind, string id, Vector2[] line, string district, List<Dictionary<string, object>> zones)
        {
            switch (kind)
            {
                case "railway": RailwayX01(parent, z, id); return true;                  // W86 integration: X01 b dead-end track
                case "curb_drop":
                {   // the sidewalk stops at a drop (Streets): pave the drop flush with the carriageway (base-4 arch entry, alley entries)
                    var poly = V2s(Get(z, "poly"));
                    string surf = S(Get(z, "surface"));
                    if (poly.Length >= 3) FlatPatch(parent, "Zone_curbdrop_" + id, poly, surf != null && Get(MatMap, surf) != null ? surf : "asphalt_A5d12", .07f);
                    return true;
                }
                case "side_gap":
                {
                    var poly = V2s(Get(z, "poly"));
                    if (poly.Length < 4) return true;
                    FlatPatch(parent, "Zone_" + id, poly, S(Get(z, "surface"), "concrete_SK3c"), .04f);
                    // ends = the two short edges; the one nearer to the street gets the gate on the facade line
                    var edges = Enumerable.Range(0, poly.Length).Select(i => (a: poly[i], b: poly[(i + 1) % poly.Length])).OrderBy(e => (e.b - e.a).magnitude).Take(2).ToList();
                    var street = zones.FirstOrDefault(o => S(Get(o, "kind")) == "street" && (S(Get(o, "id"), "") ?? "").EndsWith("-street-" + S(Get(z, "street"), "?")));
                    var sl = street != null ? V2s(Get(street, "poly_line")) : new Vector2[0];
                    var front = sl.Length >= 2 ? edges.OrderBy(e => W76Atmosphere.Distance(sl, (e.a + e.b) * .5f)).First() : edges[0];
                    IronGate(parent, id + "_street", front.a, front.b, 2.2f, false, false);
                    var back = edges[0].Equals(front) ? edges[1] : edges[0];
                    Vector2 bm = (back.a + back.b) * .5f, outDir = (bm - (front.a + front.b) * .5f).normalized;
                    bool closed = DistrictFps.Any(o => W76Atmosphere.Inside(o.fp, bm + outDir * .6f));
                    if (!closed) IronGate(parent, id + "_back", back.a, back.b, 2.2f, false, false);
                    w86Gaps++;
                    return true;
                }
                case "patrol_route":
                {
                    var loop = V2s(Get(z, "loop") ?? Get(z, "line"));
                    if (loop.Length < 2) return true;
                    var pr = new GameObject($"Patrol_{id}_{(int)F(Get(z, "guards"), 1f)}guards_{F(Get(z, "speed_mps"), 1.3f):0.0}mps").transform;
                    pr.SetParent(parent, false);
                    pr.position = P(loop[0]);
                    for (int i = 0; i < loop.Length; i++)
                    {
                        var wp = new GameObject($"WP_{i:00}").transform; wp.SetParent(pr, false);
                        Vector2 nx = loop[(i + 1) % loop.Length] - loop[i];
                        wp.SetPositionAndRotation(P(loop[i]), Quaternion.Euler(0, Mathf.Atan2(nx.x, nx.y) * Mathf.Rad2Deg, 0));
                    }
                    w86Patrols++;
                    return true;
                }
                case "planter_strip":
                {
                    if (line.Length < 2) return true;
                    float w = F(Get(z, "w_m"), .8f), h = F(Get(z, "h_m"), .35f);
                    for (int i = 1; i < line.Length; i++)
                    {
                        Vector2 a = line[i - 1], b = line[i], m = (a + b) * .5f;
                        float yawP = -Mathf.Atan2(b.y - a.y, b.x - a.x) * Mathf.Rad2Deg, L = (b - a).magnitude;
                        Box(parent, "Planter_" + id + "_kerb", P(m, h * .5f - .1f), new Vector3(L, h + .2f, w), yawP, "concrete_SK3c", true);
                        Box(parent, "Planter_" + id + "_green", P(m, h + .02f), new Vector3(L - .16f, .1f, w - .16f), yawP, "lawn_hedge", false);
                    }
                    w86Planters++;
                    return true;
                }
            }
            return false;
        }

        static string W86ExtrasNote()
        {
            string s = (w86Gaps > 0 ? $", {w86Gaps} side gaps" : "") + (w86Gates > 0 ? $", {w86Gates} iron gates" : "") + (w86Hedges > 0 ? $", {w86Hedges} trimmed hedges" : "") +
                       (w86Planters > 0 ? $", {w86Planters} planter strips" : "") + (w86Markers > 0 ? $", {w86Markers} NPC spot markers" : "") + (w86Patrols > 0 ? $", {w86Patrols} patrol loops" : "");
            w86Gates = w86Gaps = w86Markers = w86Patrols = w86Hedges = w86Planters = 0;
            return s;
        }
    }
}
