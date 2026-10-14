using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // The v16 look json fields the look_v1 schema (LookData, JsonUtility) does not carry, read with V3Json: water source
    // kinds, river/canal centrelines and widths (flow direction = point order), fire escapes and rooftop water towers
    // (world_v11_extensions.structures), typed fences with gates, forest zones (vegetation_hints).
    public static class V3LookData
    {
        public sealed class Fence
        {
            public string Id, Kind, District;
            public List<Vector2> Line = new();
            public List<(Vector2 p, float w)> Gates = new();
            public bool Closed;
        }

        public static Dictionary<string, string> WaterSource;
        public static Dictionary<string, List<Vector2>> Centrelines;
        public static Dictionary<string, float[]> WidthProfiles;
        public static List<(float x0, float y0, float x1, float y1)> FireEscapes;
        public static List<Vector2> RoofTanks;
        public static List<Fence> Fences;
        public static List<(string density, float[] poly)> ForestZones;
        public static List<(string kind, string id, float[] poly, Vector2 pos, float radius)> Structures;

        // v17 (look json "v17"): placed props (registry keys "prop/..." or procedural "proc/..."; Unity yaw degrees) and the
        // power line polyline. Empty for older revisions.
        public sealed class Prop
        {
            public string Key;
            public float X, Y, Yaw, Scale = 1f;
            public bool Solid, Cast = true;
        }

        public static List<Prop> Props;
        public static List<Vector2> PylonLine;

        public static void Load(string revision)
        {
            WaterSource = new Dictionary<string, string>();
            Centrelines = new Dictionary<string, List<Vector2>>();
            WidthProfiles = new Dictionary<string, float[]>();
            FireEscapes = new List<(float, float, float, float)>();
            RoofTanks = new List<Vector2>();
            Fences = new List<Fence>();
            ForestZones = new List<(string, float[])>();
            Structures = new List<(string, string, float[], Vector2, float)>();
            Props = new List<Prop>();
            PylonLine = new List<Vector2>();
            string path = Path.Combine(Application.dataPath, "..", MapLookBuilder.LookJsonDir, revision=="v19" ? "look_v19_build_v07_flat.json" : $"look_{revision}_flat.json");
            if (!File.Exists(path)) return;
            if (!(V3Json.Parse(File.ReadAllText(path)) is Dictionary<string, object> root)) return;
            if (root.TryGetValue("water", out object water) && water is List<object> waters)
                foreach (object o in waters)
                {
                    string id = V3Json.GetString(o, "id");
                    if (id == null) continue;
                    string src = V3Json.GetString(o, "source_kind");
                    if (src != null) WaterSource[id] = src;
                    var d = (Dictionary<string, object>)o;
                    if (d.TryGetValue("centerline_m", out object cl) && cl is List<object> pts && pts.Count >= 2) Centrelines[id] = Points(pts);
                    if (d.TryGetValue("width_profile_m", out object wp) && wp is List<object> ws && ws.Count > 0)
                    {
                        var arr = new float[ws.Count];
                        for (int i = 0; i < ws.Count; i++) arr[i] = ws[i] is double v ? (float)v : 0f;
                        WidthProfiles[id] = arr;
                    }
                }
            if (root.TryGetValue("v17", out object v17) && v17 is Dictionary<string, object> vd)
            {
                if (vd.TryGetValue("props", out object pr) && pr is List<object> plist)
                    foreach (object o in plist)
                    {
                        var d = (Dictionary<string, object>)o;
                        Props.Add(new Prop
                        {
                            Key = V3Json.GetString(o, "k") ?? "",
                            X = (float)V3Json.GetNumber(o, 0, "x"),
                            Y = (float)V3Json.GetNumber(o, 0, "y"),
                            Yaw = (float)V3Json.GetNumber(o, 0, "yaw"),
                            Scale = (float)V3Json.GetNumber(o, 1, "s"),
                            Solid = d.TryGetValue("solid", out object so) && so is bool sb && sb,
                            Cast = !d.TryGetValue("cast", out object co) || !(co is bool cb) || cb,
                        });
                    }
                if (vd.TryGetValue("pylon_line", out object pl) && pl is List<object> pls) PylonLine = Points(pls);
            }
            if (!root.TryGetValue("world_v11_extensions", out object ext) || !(ext is Dictionary<string, object> x)) return;
            if (x.TryGetValue("structures", out object st) && st is List<object> structs)
                foreach (object o in structs)
                {
                    string kind = V3Json.GetString(o, "kind") ?? "";
                    var d = (Dictionary<string, object>)o;
                    if (kind == "fire_escape" && d.TryGetValue("facade_segment_m", out object seg) && seg is List<object> s2 && s2.Count >= 2)
                    {
                        List<Vector2> p = Points(s2);
                        FireEscapes.Add((p[0].x, p[0].y, p[1].x, p[1].y));
                    }
                    Vector2 pos = d.TryGetValue("position_m", out object po) && po is List<object> pl && pl.Count >= 2 ? Points(new List<object> { pl })[0] : Vector2.zero;
                    if (kind == "rooftop_water_tower") RoofTanks.Add(pos);
                    float[] poly = d.TryGetValue("polygon_m", out object pg) && pg is List<object> pgl ? Flat(Points(pgl)) : null;
                    if (poly == null && d.TryGetValue("footprint_m", out object fp) && fp is List<object> fpl) poly = Flat(Points(fpl));
                    if (poly == null && d.TryGetValue("polyline_m", out object pll) && pll is List<object> plll) poly = Flat(Points(plll));
                    float radius = (float)V3Json.GetNumber(o, 0, "radius_m", "plaza_radius_m");
                    Structures.Add((kind, V3Json.GetString(o, "id") ?? "", poly, pos, radius));
                }
            if (x.TryGetValue("fences", out object fs) && fs is List<object> fences)
                foreach (object o in fences)
                {
                    var d = (Dictionary<string, object>)o;
                    var f = new Fence { Id = V3Json.GetString(o, "id") ?? "", Kind = V3Json.GetString(o, "kind") ?? "", District = V3Json.GetString(o, "district_id") ?? "" };
                    if (d.TryGetValue("polyline_m", out object pl) && pl is List<object> pts) f.Line = Points(pts);
                    else if (d.TryGetValue("polygon_m", out object pg) && pg is List<object> pgs)
                    {
                        f.Line = Points(pgs);
                        f.Closed = true;
                    }
                    if (d.TryGetValue("gates", out object gs) && gs is List<object> gates)
                        foreach (object g in gates)
                        {
                            var gd = (Dictionary<string, object>)g;
                            if (gd.TryGetValue("position_m", out object gp) && gp is List<object> gpl && gpl.Count >= 2)
                                f.Gates.Add((Points(new List<object> { gpl })[0], (float)V3Json.GetNumber(g, 6, "width_m")));
                        }
                    if (f.Line.Count >= 2) Fences.Add(f);
                }
            if (x.TryGetValue("vegetation_hints", out object vh) && vh is Dictionary<string, object> veg &&
                veg.TryGetValue("forest_zones", out object fz) && fz is List<object> zones)
                foreach (object o in zones)
                {
                    var d = (Dictionary<string, object>)o;
                    if (d.TryGetValue("polygon_m", out object pg) && pg is List<object> pts)
                        ForestZones.Add((V3Json.GetString(o, "density") ?? "", Flat(Points(pts))));
                }
        }

        private static List<Vector2> Points(List<object> list)
        {
            var r = new List<Vector2>();
            foreach (object o in list)
                if (o is List<object> p && p.Count >= 2 && p[0] is double a && p[1] is double b)
                    r.Add(new Vector2((float)a, (float)b));
            return r;
        }

        private static float[] Flat(List<Vector2> pts)
        {
            var f = new float[pts.Count * 2];
            for (int i = 0; i < pts.Count; i++)
            {
                f[2 * i] = pts[i].x;
                f[2 * i + 1] = pts[i].y;
            }
            return f;
        }
    }
}
