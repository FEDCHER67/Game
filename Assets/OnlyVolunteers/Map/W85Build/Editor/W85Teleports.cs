using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using OnlyVolunteers.Map.Crowd;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.W85
{
    // W86 (lead brief 22.10): the F1-F8 teleports of the carried i10 van (GreyboxTripMeter + GreyboxTripFootSpots) pointed at v19 places
    // (F1 / B02 ~44 m west of the base-2 hut, at the NW ridge foot). Re-derived from the map data of the play scene, every run:
    //  F1 P02 grandpa's yard + F3 B02 hut = the base-2 van pad (the van's own pose there), F2 B01 wagon, F4 B03 Rough garage (van spot),
    //  F5 B04 Downtown garage (base-4 courtyard), F6 Downtown square (street beside square 20), F7 B05 lab (loading pad),
    //  F8 Construction fuel station (road beside it). Each van pose is checked free (van box), the on-foot spot beside it too.
    public static class W85Teleports
    {
        static readonly Vector3 VanHalf = new(1.2f, 1.0f, 3.35f);

        public static string Apply(GameObject van, string dataDir, Func<float, float, float> ground, HashSet<Transform> skip)
        {
            var meter = van ? van.GetComponentInChildren<GreyboxTripMeter>(true) : null;
            if (!meter) return "missing: GreyboxTripMeter on the van (F-key teleports not set)";
            if (dataDir == null || !Directory.Exists(dataDir + "/districts")) return "missing: map data dir (F-key teleports kept as carried)";
            Dictionary<string, object> D(string name)
            {
                string f = Directory.GetFiles(dataDir + "/districts", name + "_*.json").FirstOrDefault();
                return f != null ? MiniJson.Parse(File.ReadAllText(f)) as Dictionary<string, object> : null;
            }
            var hamlet = D("hamlet"); var forest = D("forest"); var rough = D("rough"); var downtown = D("downtown"); var valley = D("quiet_valley"); var construction = D("construction");
            // drivable centre lines: world roads + district streets / roads / tracks
            var drive = new List<Vector2[]>();
            string roadsFile = dataDir + "/roads_v85.json";
            if (File.Exists(roadsFile) && MiniJson.Parse(File.ReadAllText(roadsFile)) is Dictionary<string, object> rj)
                foreach (var r in List(rj, "roads").OfType<Dictionary<string, object>>())
                    if (Str(r, "kind") != "tunnel") { var pl = Pts(Get(r, "points")); if (pl.Length >= 2) drive.Add(pl); }
            foreach (var dj in new[] { hamlet, forest, rough, downtown, valley, construction })
                foreach (var z in List(dj, "zones").OfType<Dictionary<string, object>>())
                {
                    string k = Str(z, "kind");
                    if (k != "street" && k != "road" && k != "ring_road" && k != "track" && k != "drive") continue;
                    var pl = Pts(Get(z, "poly_line") ?? Get(z, "line"));
                    if (pl.Length >= 2) drive.Add(pl);
                }
            Vector3 vp = van.transform.position; float vy = van.transform.eulerAngles.y;
            var spots = new List<(string name, Vector3 pos, float yaw, string src)>();
            void FromVan(string name) => spots.Add((name, new Vector3(vp.x, ground(vp.x, vp.z), vp.z), vy, "van pad (the van's pose)"));
            void AtPad(string name, Vector2[] poly, string src)
            {   // on the pad, nose towards the nearest drivable line (drive out forwards)
                if (poly == null) { spots.Add((name, Vector3.zero, 0f, "missing: " + src)); return; }
                Vector2 c = Centre(poly).Value, q = Nearest(drive, c, out _, out _);
                Vector2 d = (q - c).sqrMagnitude > .25f ? (q - c).normalized : LongAxis(poly);
                spots.Add((name, new Vector3(c.x, ground(c.x, c.y), c.y), Yaw(d), src));
            }
            void OnRoad(string name, Vector2? target, string src)
            {   // on the nearest drivable line, along it
                if (!target.HasValue) { spots.Add((name, Vector3.zero, 0f, "missing: " + src)); return; }
                Vector2 q = Nearest(drive, target.Value, out Vector2 dir, out float dist);
                spots.Add((name, new Vector3(q.x, ground(q.x, q.y), q.y), Yaw(dir), $"{src} (road {dist:0} m from it)"));
            }
            FromVan("P02 Двор деда");
            OnRoad("B01 Вагон", Centre(Building(forest, "rail_wagon")), "base 1 wagon");
            FromVan("B02 Хижина");
            AtPad("B03 Гараж (спальник)", Zone(rough, "base3-van-spot", "poly"), "rough base-3 van spot");
            AtPad("B04 Гараж (даунтаун)", Zone(downtown, "-13-yard", "court_poly") ?? Zone(downtown, "-13-yard", "poly"), "downtown base-4 courtyard");
            OnRoad("Площадь (даунтаун)", Centre(Zone(downtown, "-20-square", "poly") ?? Zone(downtown, "-23-square", "poly")), "downtown square 20");
            AtPad("B05 Лаборатория", Zone(valley, "base5-loading", "poly"), "quiet valley lab loading pad");
            OnRoad("Заправка (стройка)", Centre(Zone(construction, "fuel-pad", "poly")), "construction fuel station");
            // free van box at each pose (nudged along / across the road when something stands there), on-foot spot beside it
            Physics.SyncTransforms();
            var log = new StringBuilder();
            var outSpots = new List<GreyboxTripMeter.Spot>(); var feet = new List<Vector3>();
            foreach (var s in spots)
            {
                if (s.pos == Vector3.zero) { log.Append($"\n  {s.name}: {s.src} - skipped"); continue; }
                Vector3 p = s.pos; int tries = 0;
                var fwd = Quaternion.Euler(0, s.yaw, 0) * Vector3.forward; var right = Quaternion.Euler(0, s.yaw, 0) * Vector3.right;
                if (Blocked(p, s.yaw, van, skip))
                {
                    bool ok = false;
                    foreach (float a in new[] { 2f, -2f, 4f, -4f, 6f, -6f, 9f, -9f })
                    {
                        foreach (Vector3 o in new[] { fwd * a, right * a * .6f })
                        {
                            tries++;
                            Vector3 q = p + o; q.y = ground(q.x, q.z);
                            if (!Blocked(q, s.yaw, van, skip)) { p = q; ok = true; break; }
                        }
                        if (ok) break;                                                      // first free nudge wins
                    }
                    if (!ok) log.Append($"\n  WARNING {s.name}: no free van spot within 9 m of ({s.pos.x:0.0}, {s.pos.z:0.0})");
                }
                Vector3 foot = Vector3.zero;
                foreach (Vector3 o in new[] { right * 4f, -right * 4f, -fwd * 5.5f, fwd * 5.5f, right * 6f, -right * 6f })
                {
                    Vector3 q = p + o; q.y = ground(q.x, q.z) + .1f;
                    if (!Physics.CheckCapsule(q + Vector3.up * .5f, q + Vector3.up * 1.4f, .42f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore) || OnlyGround(q, van, skip)) { foot = q; break; }
                }
                outSpots.Add(new GreyboxTripMeter.Spot { Name = s.name, Position = p, Yaw = s.yaw });
                feet.Add(foot);
                log.Append($"\n  F{outSpots.Count} {s.name}: ({p.x:0.0}, {p.y:0.00}, {p.z:0.0}) yaw {s.yaw:0} - {s.src}" + (p != s.pos ? $", nudged {(p - s.pos).magnitude:0.0} m" : "") + (foot == Vector3.zero ? ", no free on-foot spot (the meter's default)" : ""));
            }
            Undo.RecordObject(meter, "W86 teleports");
            meter.Spots = outSpots.ToArray();
            EditorUtility.SetDirty(meter);
            var fs = meter.GetComponent<GreyboxTripFootSpots>() ?? meter.gameObject.AddComponent<GreyboxTripFootSpots>();
            fs.Positions = feet.ToArray();
            EditorUtility.SetDirty(fs);
            return $"teleports F1-F{outSpots.Count} re-derived from {dataDir}:" + log;
        }

        // something solid in the van's box (terrain, road / pad overlays, the carried objects and the van itself do not count)
        static bool Blocked(Vector3 p, float yaw, GameObject van, HashSet<Transform> skip)
        {
            var rot = Quaternion.Euler(0, yaw, 0);
            foreach (var c in Physics.OverlapBox(p + rot * new Vector3(0, VanHalf.y + .35f, .75f), VanHalf, rot, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore))
            {
                if (c is TerrainCollider || c.transform.IsChildOf(van.transform) || skip.Contains(c.transform.root)) continue;
                if (c.bounds.max.y < p.y + .4f) continue;
                return true;
            }
            return false;
        }

        static bool OnlyGround(Vector3 q, GameObject van, HashSet<Transform> skip)
        {
            foreach (var c in Physics.OverlapCapsule(q + Vector3.up * .5f, q + Vector3.up * 1.4f, .42f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore))
            {
                if (c is TerrainCollider || c.transform.IsChildOf(van.transform) || skip.Contains(c.transform.root)) continue;
                if (c.bounds.max.y < q.y + .35f) continue;
                return false;
            }
            return true;
        }

        static float Yaw(Vector2 d) => Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg;

        static Vector2 Nearest(List<Vector2[]> lines, Vector2 p, out Vector2 dir, out float dist)
        {
            Vector2 best = p; dir = Vector2.up; dist = float.MaxValue;
            foreach (var l in lines)
                for (int i = 0; i + 1 < l.Length; i++)
                {
                    Vector2 a = l[i], ab = l[i + 1] - a;
                    float t = ab.sqrMagnitude > 1e-6f ? Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude) : 0f;
                    Vector2 q = a + ab * t; float d = (p - q).magnitude;
                    if (d < dist) { dist = d; best = q; dir = ab.normalized; }
                }
            return best;
        }

        static Vector2 LongAxis(Vector2[] poly)
        {
            Vector2 best = Vector2.up; float bl = 0f;
            for (int i = 0; i < poly.Length; i++) { Vector2 e = poly[(i + 1) % poly.Length] - poly[i]; if (e.magnitude > bl) { bl = e.magnitude; best = e.normalized; } }
            return best;
        }

        static Vector2[] Zone(Dictionary<string, object> d, string idSuffix, string key)
        {
            var z = List(d, "zones").OfType<Dictionary<string, object>>().FirstOrDefault(o => Str(o, "id").EndsWith(idSuffix) && !Str(o, "id").Contains("no-tree"));
            var pts = z != null ? Pts(Get(z, key)) : null;
            return pts != null && pts.Length >= 3 ? pts : null;
        }

        static Vector2[] Building(Dictionary<string, object> d, string kindPrefix)
        {
            var b = List(d, "buildings").OfType<Dictionary<string, object>>().FirstOrDefault(o => Str(o, "kind").StartsWith(kindPrefix));
            var pts = b != null ? Pts(Get(b, "footprint")) : null;
            return pts != null && pts.Length >= 3 ? pts : null;
        }

        static Vector2? Centre(Vector2[] poly) => poly == null ? (Vector2?)null : new Vector2(poly.Average(p => p.x), poly.Average(p => p.y));
        static object Get(Dictionary<string, object> d, string k) => d != null && d.TryGetValue(k, out var v) ? v : null;
        static IEnumerable<object> List(Dictionary<string, object> d, string key) => d != null && d.TryGetValue(key, out var v) && v is List<object> l ? l : Enumerable.Empty<object>();
        static string Str(Dictionary<string, object> d, string key) => d != null && d.TryGetValue(key, out var v) && v is string s ? s : "";

        static Vector2[] Pts(object o)
        {
            var r = new List<Vector2>();
            if (o is List<object> l)
                foreach (var p in l)
                    if (p is List<object> xy && xy.Count >= 2 && !(xy[0] is List<object>)) r.Add(new Vector2(Convert.ToSingle(xy[0], CultureInfo.InvariantCulture), Convert.ToSingle(xy[1], CultureInfo.InvariantCulture)));
            return r.ToArray();
        }
    }
}
