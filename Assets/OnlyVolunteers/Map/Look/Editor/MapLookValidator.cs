using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    // Van parity and look rules check, from data only (no scene needed): a 2 m flood fill from the van spawn over the
    // look heights (slopes <= 22 deg between cells, water <= 0.8 m, buildings, fences, walls, rocks, furniture and
    // building extra colliders, blockers) compared with the same fill over the flat greybox (its buildings, walls, dead
    // ends and fences). Furniture, kit-building and building-extra colliders are the built scene's (or the registry
    // prefabs' when no scene is open), placeholder footprints only where a slot has no prefab. Also flags any fence run
    // or retaining wall that follows a district border (Fedya: none allowed except the elite ring) and any collider that
    // reaches into a carriageway. Writes a text report and a PNG map.
    public static class MapLookValidator
    {
        private const float Cell = 2f, MaxSlopeDeg = 22f, MaxFord = 0.8f;

        [Serializable] private sealed class GreyBox { public float x, y, w, d, a, h; public int f; public string label; }
        [Serializable] private sealed class GreyBarrier { public float x, y, w, d; }
        [Serializable] private sealed class GreyWall { public float[] pts; }
        [Serializable]
        private sealed class Greybox
        {
            public GreyBox[] buildings, hedges;
            public GreyBarrier[] barriers;
            public GreyWall[] walls;
        }

        [MenuItem("OnlyVolunteers/Map/Validate Map Look (latest plan)")]
        public static void ValidateLatest()
        {
            string rev = MapLookBuilder.LatestRevision();
            if (rev == null)
            {
                Debug.LogError("[MapLook] No look_vNN_flat.json found.");
                return;
            }
            LookData d = MapLookBuilder.Load(rev);
            var hm = new HeightModel(d);
            hm.Bake();
            // The built scene, when open, gives the exact colliders (nudged furniture, kit buildings); otherwise the
            // registry prefabs' colliders are placed from the plan (without the KeepOffRoads nudge).
            GameObject built = GameObject.Find($"MapLook_{rev}");
            Debug.Log(Validate(d, hm, rev, built != null ? built.transform : null));
        }

        // `built`: the MapLook_vNN root of the built scene. With it, registry-art colliders (street furniture, kit
        // buildings, building extras) are measured from the scene, KeepOffRoads offsets included; placeholder
        // furniture always comes from the PlaceholderKit footprint (it is merged into collider chunks).
        public static string Validate(LookData d, HeightModel hm, string revision, Transform built = null)
        {
            LookTerrain t = d.terrain;
            int nx = Mathf.CeilToInt(t.sx / Cell), ny = Mathf.CeilToInt(t.sy / Cell);
            var domain = new bool[nx * ny];
            var heights = new float[nx * ny];
            var lookBlocked = new bool[nx * ny];
            var greyBlocked = new bool[nx * ny];
            var grid = new LookGrid(nx, ny, t.x0 + Cell / 2f, t.y0 + Cell / 2f, Cell, Cell);
            grid.ScanFill(d.boundary.pts, (i, j) => domain[j * nx + i] = true);
            grid.ScanFill(d.beach.pts, (i, j) => domain[j * nx + i] = true);
            grid.ScanFill(d.sea.pts, (i, j) => domain[j * nx + i] = false);
            foreach (LookRoad r in d.roads)
                if (r.van)
                    grid.Stamp(r.pts, false, r.w / 2f, (i, j, dist, s, tt) => domain[j * nx + i] = true);
            for (int j = 0; j < ny; j++)
                for (int i = 0; i < nx; i++)
                {
                    float x = grid.X(i), y = grid.Y(j);
                    int k = j * nx + i;
                    heights[k] = hm.Height(x, y);
                    if (domain[k] && hm.InWater(x, y, out float level) && level - heights[k] > MaxFord) lookBlocked[k] = true;
                }

            // Shared obstacles: building footprints (+0.3 m).
            foreach (LookBuilding b in d.buildings)
            {
                if (LookGeom.Count(b.fp) < 3) continue;
                Fill(grid, b.fp, 0.3f, lookBlocked);
            }
            // Look-only obstacles.
            var fenceRuns = new List<(string id, float[] line)>();
            Func<float, float, bool> border = FenceBuilder.BorderTest(d);
            foreach (LookYard y in d.yards)
                foreach (float[] run in FenceBuilder.YardLines(y, border))
                {
                    fenceRuns.Add((y.id, run));
                    StampLine(grid, run, 0.6f, lookBlocked);
                }
            foreach (LookEliteFence f in d.elite_fence)
            {
                float[] cum = LookGeom.Cumulative(f.pts);
                foreach (float[] run in Runs(f.pts, cum, false, f.gaps)) StampLine(grid, run, 1.2f, lookBlocked);
            }
            foreach (HeightModel.RetainingWall w in hm.Walls)
            {
                StampLine(grid, Close(w.Ring), 0.5f, lookBlocked);
                fenceRuns.Add(("wall " + w.BuildingId, Close(w.Ring)));
            }
            foreach (LookRock r in d.rocks) StampLine(grid, new[] { r.x, r.y }, Mathf.Max(r.sx, r.sz) * 0.45f, lookBlocked);
            // Collider boxes the build adds on the ground: street furniture (placeholder footprints) and building extras
            // (gas canopy columns and pumps, shelter panels, ad poles, bell towers).
            List<(string id, float[] box)> solids = SolidBoxes(d, hm, built, out string solidNote);
            foreach (var (_, box) in solids) Fill(grid, box, 0.01f, lookBlocked);
            foreach (LookBlocker b in d.blockers) Fill(grid, b.pts, 0.2f, lookBlocked);
            foreach (LookExit e in d.exits)
                foreach (LookPolyline p in e.barriers)
                    Fill(grid, p.pts, 0.2f, lookBlocked);

            // Greybox obstacles (flat, everything drivable but boxes and walls).
            Greybox grey = LoadGreybox(revision, out string greyNote);
            if (grey != null)
            {
                foreach (GreyBox b in grey.buildings ?? new GreyBox[0]) Box(grid, b.x, b.y, b.w, b.d, b.a, 0.3f, greyBlocked);
                foreach (GreyBox h in grey.hedges ?? new GreyBox[0]) Box(grid, h.x, h.y, Mathf.Max(h.w, 0.3f), Mathf.Max(h.d, 0.3f), h.a, 0.3f, greyBlocked);
                foreach (GreyBarrier b in grey.barriers ?? new GreyBarrier[0]) Box(grid, b.x, b.y, b.w, b.d, 0f, 0f, greyBlocked);
                foreach (GreyWall w in grey.walls ?? new GreyWall[0]) StampLine(grid, w.pts, 1.5f, greyBlocked);
            }
            else
                foreach (LookBuilding b in d.buildings)
                    Fill(grid, b.fp, 0.3f, greyBlocked);

            float maxStep = Mathf.Tan(MaxSlopeDeg * Mathf.Deg2Rad) * Cell;
            Vector2 spawn = Spawn(d);
            int start = Mathf.Clamp(Mathf.RoundToInt((spawn.y - grid.Y0) / Cell), 0, ny - 1) * nx + Mathf.Clamp(Mathf.RoundToInt((spawn.x - grid.X0) / Cell), 0, nx - 1);
            bool[] lookReach = Flood(nx, ny, start, k => domain[k] && !lookBlocked[k], (a, b) => Mathf.Abs(heights[a] - heights[b]) <= maxStep);
            bool[] greyReach = Flood(nx, ny, start, k => domain[k] && !greyBlocked[k], (a, b) => true);

            int greyCount = 0, lookCount = 0, lost = 0, gained = 0;
            var lostMask = new bool[nx * ny];
            for (int k = 0; k < nx * ny; k++)
            {
                if (greyReach[k]) greyCount++;
                if (lookReach[k]) lookCount++;
                if (greyReach[k] && !lookReach[k] && !InFootprintOrFence(k, lookBlocked, greyBlocked))
                {
                    lostMask[k] = true;
                    lost++;
                }
                if (lookReach[k] && !greyReach[k]) gained++;
            }
            var sb = new StringBuilder();
            sb.AppendLine($"[MapLook] Validation {revision}: van spawn ({spawn.x:0},{spawn.y:0}), {Cell} m cells, slope <= {MaxSlopeDeg} deg, ford <= {MaxFord} m");
            if (greyNote != null) sb.AppendLine("  " + greyNote);
            sb.AppendLine("  " + solidNote);
            sb.AppendLine($"  reachable: greybox {greyCount * Cell * Cell / 10000f:0.0} ha, look {lookCount * Cell * Cell / 10000f:0.0} ha; " +
                          $"lost {lost * Cell * Cell:0} m2 (outside footprints, fences and walls), newly open {gained * Cell * Cell:0} m2");
            Clusters(sb, d, grid, lostMask, nx, ny);
            Points(sb, d, grid, lookReach, greyReach, nx, ny);
            RoadCoverage(sb, d, grid, lookReach, nx, ny);
            LaneIntrusions(sb, d, solids);
            BorderFences(sb, d, fenceRuns);
            sb.AppendLine($"  roads: steepest grade {hm.MaxRoadGrade * 100f:0}% (target {hm.RoadGrade * 100f:0}%)");
            foreach (string w in hm.Warnings) sb.AppendLine("  height: " + w);
            string report = sb.ToString();
            string dir = Path.Combine(Application.dataPath, "..", MapLookBuilder.LookJsonDir);
            File.WriteAllText(Path.Combine(dir, $"look_{revision}_validation.txt"), report);
            WriteMap(Path.Combine(dir, $"look_{revision}_reach.png"), nx, ny, domain, lookReach, greyReach, lookBlocked);
            return report;
        }

        // Lost cells under a look obstacle that the greybox did not have (fence, wall, rock) are expected, not parity loss.
        private static bool InFootprintOrFence(int k, bool[] lookBlocked, bool[] greyBlocked) => lookBlocked[k] && !greyBlocked[k];

        private static Greybox LoadGreybox(string revision, out string note)
        {
            string path = Path.Combine(Application.dataPath, "..", "ArtSource", "References", "Map", "Greybox", $"greybox_{revision}_flat.json");
            if (!File.Exists(path))
            {
                note = $"greybox_{revision}_flat.json not found: greybox reachability approximated by footprints only";
                return null;
            }
            note = null;
            return JsonUtility.FromJson<Greybox>(File.ReadAllText(path));
        }

        // Same spawn rule as the greybox: nearest drivable road point to P02.
        public static Vector2 Spawn(LookData d)
        {
            Vector2 target = Vector2.zero;
            foreach (LookPoint p in d.points)
                if (p.id == "P02")
                    target = new Vector2(p.x, p.y);
            float best = float.MaxValue;
            Vector2 pos = target;
            foreach (LookRoad r in d.roads)
            {
                if (!r.van || r.cls == "passage" || LookGeom.Count(r.pts) < 2) continue;
                float dist = LookGeom.DistToPolyline(r.pts, target.x, target.y, false, out int seg, out float tt);
                if (dist >= best) continue;
                best = dist;
                pos = new Vector2(Mathf.Lerp(r.pts[2 * seg], r.pts[2 * seg + 2], tt), Mathf.Lerp(r.pts[2 * seg + 1], r.pts[2 * seg + 3], tt));
            }
            return pos;
        }

        private static bool[] Flood(int nx, int ny, int start, Func<int, bool> open, Func<int, int, bool> step)
        {
            var seen = new bool[nx * ny];
            if (!open(start))
            {
                // Spawn cell itself blocked (a kerb, a lamp): start from the nearest open neighbour.
                for (int r = 1; r < 4 && !open(start); r++)
                    foreach (int k in new[] { start + r, start - r, start + r * nx, start - r * nx })
                        if (k >= 0 && k < nx * ny && open(k))
                        {
                            start = k;
                            break;
                        }
                if (!open(start)) return seen;
            }
            var queue = new Queue<int>();
            queue.Enqueue(start);
            seen[start] = true;
            while (queue.Count > 0)
            {
                int k = queue.Dequeue();
                int i = k % nx, j = k / nx;
                if (i > 0) Try(k - 1);
                if (i < nx - 1) Try(k + 1);
                if (j > 0) Try(k - nx);
                if (j < ny - 1) Try(k + nx);
                void Try(int q)
                {
                    if (seen[q] || !open(q) || !step(k, q)) return;
                    seen[q] = true;
                    queue.Enqueue(q);
                }
            }
            return seen;
        }

        private static void Fill(LookGrid grid, float[] poly, float pad, bool[] mask)
        {
            if (LookGeom.Count(poly) < 3) return;
            grid.ScanFill(poly, (i, j) => mask[j * grid.Nx + i] = true);
            if (pad > 0f) grid.Stamp(poly, true, pad + grid.Dx * 0.5f, (i, j, dist, s, tt) => mask[j * grid.Nx + i] = true);
        }

        private static void StampLine(LookGrid grid, float[] line, float radius, bool[] mask)
        {
            if (line.Length < 2) return;
            grid.Stamp(line, false, Mathf.Max(radius, grid.Dx * 0.5f), (i, j, dist, s, tt) => mask[j * grid.Nx + i] = true);
        }

        // Greybox boxes are rotated by Euler(0, -a, 0): local X runs along (cos a, sin a) in plan space.
        private static void Box(LookGrid grid, float x, float y, float w, float dd, float a, float pad, bool[] mask)
        {
            float rad = a * Mathf.Deg2Rad, c = Mathf.Cos(rad), s = Mathf.Sin(rad);
            float hx = w / 2f + pad, hy = dd / 2f + pad;
            var poly = new[]
            {
                x - c * hx + s * hy, y - s * hx - c * hy, x + c * hx + s * hy, y + s * hx - c * hy,
                x + c * hx - s * hy, y + s * hx + c * hy, x - c * hx - s * hy, y - s * hx + c * hy,
            };
            Fill(grid, poly, grid.Dx * 0.5f, mask);
        }

        private static List<float[]> Runs(float[] pts, float[] cum, bool closed, float[] gaps)
        {
            float total = cum[cum.Length - 1];
            var g = new List<Vector2>();
            for (int i = 0; i + 1 < gaps.Length; i += 2) g.Add(new Vector2(gaps[i], gaps[i + 1]));
            g.Sort((a, b) => a.x.CompareTo(b.x));
            var runs = new List<float[]>();
            float s = 0f;
            void Add(float s0, float s1)
            {
                var list = new List<float>();
                for (float q = s0; q < s1; q += 0.5f)
                {
                    LookGeom.PointAt(pts, cum, q, closed, out float x, out float y, out _, out _);
                    list.Add(x);
                    list.Add(y);
                }
                LookGeom.PointAt(pts, cum, s1, closed, out float ex, out float ey, out _, out _);
                list.Add(ex);
                list.Add(ey);
                runs.Add(list.ToArray());
            }
            foreach (Vector2 gap in g)
            {
                if (gap.x - s > 0.3f) Add(s, gap.x);
                s = Mathf.Max(s, gap.y);
            }
            if (total - s > 0.3f) Add(s, total);
            return runs;
        }

        private static float[] Close(float[] ring)
        {
            var c = new float[ring.Length + 2];
            Array.Copy(ring, c, ring.Length);
            c[ring.Length] = ring[0];
            c[ring.Length + 1] = ring[1];
            return c;
        }

        // Connected lost areas, biggest first, with the nearest plan point for orientation.
        private static void Clusters(StringBuilder sb, LookData d, LookGrid grid, bool[] lost, int nx, int ny)
        {
            var seen = new bool[nx * ny];
            var list = new List<(int cells, float cx, float cy)>();
            for (int k = 0; k < nx * ny; k++)
            {
                if (!lost[k] || seen[k]) continue;
                var q = new Queue<int>();
                q.Enqueue(k);
                seen[k] = true;
                int cells = 0;
                float sx = 0f, sy = 0f;
                while (q.Count > 0)
                {
                    int c = q.Dequeue();
                    cells++;
                    sx += grid.X(c % nx);
                    sy += grid.Y(c / nx);
                    int i = c % nx, j = c / nx;
                    foreach (int n in new[] { i > 0 ? c - 1 : -1, i < nx - 1 ? c + 1 : -1, j > 0 ? c - nx : -1, j < ny - 1 ? c + nx : -1 })
                        if (n >= 0 && lost[n] && !seen[n])
                        {
                            seen[n] = true;
                            q.Enqueue(n);
                        }
                }
                list.Add((cells, sx / cells, sy / cells));
            }
            list.Sort((a, b) => b.cells.CompareTo(a.cells));
            for (int i = 0; i < Mathf.Min(12, list.Count); i++)
            {
                var c = list[i];
                if (c.cells < 3) break;
                sb.AppendLine($"  lost area {c.cells * Cell * Cell:0} m2 around ({c.cx:0},{c.cy:0}) near {NearestPoint(d, c.cx, c.cy)}");
            }
        }

        private static string NearestPoint(LookData d, float x, float y)
        {
            string best = "-";
            float bd = float.MaxValue;
            foreach (LookPoint p in d.points)
            {
                float dist = LookGeom.Dist(x, y, p.x, p.y);
                if (dist < bd)
                {
                    bd = dist;
                    best = $"{p.id} ({dist:0} m)";
                }
            }
            return best;
        }

        // Every plan point should be reachable by the van within 25 m in the look build when it was in the greybox.
        private static void Points(StringBuilder sb, LookData d, LookGrid grid, bool[] look, bool[] grey, int nx, int ny)
        {
            int ok = 0, total = 0;
            foreach (LookPoint p in d.points)
            {
                bool g = Near(grid, grey, nx, ny, p.x, p.y, 25f), l = Near(grid, look, nx, ny, p.x, p.y, 25f);
                if (!g) continue;
                total++;
                if (l) ok++;
                else sb.AppendLine($"  POINT LOST: {p.id} {p.label} ({p.x:0},{p.y:0}) was reachable in the greybox");
            }
            sb.AppendLine($"  points reachable (25 m): {ok}/{total}");
        }

        private static bool Near(LookGrid grid, bool[] mask, int nx, int ny, float x, float y, float r)
        {
            int ci = Mathf.RoundToInt((x - grid.X0) / Cell), cj = Mathf.RoundToInt((y - grid.Y0) / Cell), rr = Mathf.CeilToInt(r / Cell);
            for (int j = Mathf.Max(0, cj - rr); j <= Mathf.Min(ny - 1, cj + rr); j++)
                for (int i = Mathf.Max(0, ci - rr); i <= Mathf.Min(nx - 1, ci + rr); i++)
                    if (mask[j * nx + i]) return true;
            return false;
        }

        private static void RoadCoverage(StringBuilder sb, LookData d, LookGrid grid, bool[] look, int nx, int ny)
        {
            int ok = 0, total = 0;
            var cut = new HashSet<string>();
            foreach (LookRoad r in d.roads)
            {
                if (!r.van || LookGeom.Count(r.pts) < 2) continue;
                float[] line = LookGeom.Resample(r.pts, 4f, out _);
                for (int i = 0; i < LookGeom.Count(line); i++)
                {
                    total++;
                    if (Near(grid, look, nx, ny, line[2 * i], line[2 * i + 1], 2f)) ok++;
                    else cut.Add(r.road);
                }
            }
            sb.AppendLine($"  road samples reachable: {ok}/{total}" + (cut.Count > 0 ? "; unreachable stretches on " + string.Join(", ", cut) : ""));
        }

        // A fence run or retaining wall that follows a district border (within BorderBand m for BorderHug m or more) is
        // reported: district borders get no fences. Deliberately wider than the builder's own trim (1.2 m), so a fence
        // that runs alongside a border a little further out is caught too.
        private const float BorderBand = 3f, BorderHug = 6f;

        private static void BorderFences(StringBuilder sb, LookData d, List<(string id, float[] line)> runs)
        {
            int flagged = 0;
            foreach (var (id, raw) in runs)
            {
                float[] line = LookGeom.Count(raw) >= 2 ? LookGeom.Resample(raw, 1f, out _) : raw;
                float hug = 0f;
                for (int i = 0; i + 1 < LookGeom.Count(line); i++)
                {
                    float x = line[2 * i], y = line[2 * i + 1];
                    bool onBorder = false;
                    foreach (LookDistrict dist in d.districts)
                        if (LookGeom.DistToPolyline(dist.pts, x, y, true, out _, out _) < BorderBand)
                            onBorder = true;
                    hug = onBorder ? hug + LookGeom.Dist(x, y, line[2 * i + 2], line[2 * i + 3]) : 0f;
                    if (hug < BorderHug) continue;
                    sb.AppendLine($"  FENCE ON DISTRICT BORDER: {(id.StartsWith("wall ") ? id : "yard " + id)} near ({x:0},{y:0}) - drop or move it");
                    flagged++;
                    break;
                }
            }
            sb.AppendLine(flagged == 0 ? "  district borders: no fences (only plot fences and the elite ring)" : $"  district borders: {flagged} fence runs flagged");
        }

        // Plan-space boxes (4 corners) of every collider the build puts on the ground besides building shells and fences.
        private static List<(string id, float[] box)> SolidBoxes(LookData d, HeightModel hm, Transform built, out string note)
        {
            var list = new List<(string, float[])>();
            MapLookRegistry registry = LookAssetStore.Registry();
            registry.ResetCache();
            int placeholders = 0, art = 0, kit = 0, extras = 0;
            // Collider.bounds of a freshly built edit-mode scene still sit at the prefab origin until the transforms reach
            // PhysX (autoSyncTransforms is off): GroundBox's 2.2 m test and the mesh-collider AABB need them in place.
            if (built != null) Physics.SyncTransforms();
            Transform furnitureRoot = built != null ? built.Find("Props/Furniture") : null;
            for (int k = 0; k < d.furniture.Length; k++)
            {
                LookFurniture f = d.furniture[k];
                PrefabSlot slot = PropScatterer.FurnitureSlot(d, registry, k);
                if (slot?.prefab != null)
                {
                    if (furnitureRoot != null || !slot.collider) continue; // scene pass below / no collider at all
                    // No scene: the prefab's own colliders at the plan pose (yaw jitter included, no nudge).
                    PropScatterer.FurnitureCollider(d, f, k, out _, out _, out float yawArt);
                    var pose = Matrix4x4.TRS(new Vector3(f.x, hm.Height(f.x, f.y), f.y), Quaternion.Euler(0f, yawArt, 0f), slot.scale);
                    foreach (float[] box in PrefabBoxes(slot.prefab, pose))
                    {
                        list.Add(($"{f.type} ({slot.prefab.name}) at ({f.x:0},{f.y:0})", box));
                        art++;
                    }
                    continue;
                }
                if (!PropScatterer.FurnitureCollider(d, f, k, out Vector3 c, out Vector3 size, out float yaw)) continue;
                list.Add(($"{f.type} at ({f.x:0},{f.y:0})", Corners(new Vector3(f.x, 0f, f.y), Quaternion.Euler(0f, yaw, 0f), c, size, true)));
                placeholders++;
            }
            if (furnitureRoot != null)
                foreach (Collider col in furnitureRoot.GetComponentsInChildren<Collider>())
                {
                    if (!GroundBox(col, hm, out float[] box)) continue;
                    Transform top = TopBelow(col.transform, furnitureRoot);
                    list.Add(($"{top.name} at ({top.position.x:0},{top.position.z:0})", box));
                    art++;
                }

            // Parked vehicles and ground landmark pieces (kit prefabs, exact slots only). GroundBox drops colliders more
            // than 2.2 m above the terrain (roof crown, giant pin and ball) and falls back to AabbBox for mesh colliders.
            int kitProps = 0;
            if (built != null)
                foreach (string g in new[] { "Props/Vehicles", "Props/Landmarks" })
                {
                    Transform groupRoot = built.Find(g);
                    if (groupRoot == null) continue;
                    foreach (Collider col in groupRoot.GetComponentsInChildren<Collider>())
                    {
                        if (!GroundBox(col, hm, out float[] box)) continue;
                        Transform top = TopBelow(col.transform, groupRoot);
                        list.Add(($"{top.name} at ({top.position.x:0},{top.position.z:0})", box));
                        kitProps++;
                    }
                }
            else
            {
                // No scene: the prefabs' own colliders at the build's poses (no nudge); vehicles the build skips as
                // unparkable (PropScatterer.VehiclePose gap) are skipped here too.
                foreach (LookVehicle v in d.vehicles)
                {
                    PrefabSlot slot = registry.ExactPrefabSlot("prop/" + v.type);
                    MeshFilter vmf = slot != null ? slot.prefab.GetComponent<MeshFilter>() : null;
                    if (slot == null || !slot.collider || vmf == null || vmf.sharedMesh == null) continue;
                    PropScatterer.VehiclePose(v, vmf.sharedMesh.bounds, hm, out Vector3 vpos, out Quaternion vrot, out float gap);
                    if (gap > PropScatterer.MaxParkGap) continue;
                    var pose = Matrix4x4.TRS(vpos, vrot, slot.scale);
                    foreach (float[] box in PrefabBoxes(slot.prefab, pose))
                    {
                        list.Add(($"{v.type} ({v.spot}) at ({v.x:0},{v.y:0})", box));
                        kitProps++;
                    }
                }
                foreach (LookLandmark m in d.landmarks)
                {
                    if (m.mount != "ground") continue;
                    PrefabSlot slot = registry.ExactPrefabSlot("prop/" + m.type);
                    if (slot == null || !slot.collider) continue;
                    Vector3 scale = slot.scale * (m.s > 0f ? m.s : 1f);
                    var pose = Matrix4x4.TRS(new Vector3(m.x, hm.Height(m.x, m.y), m.y), Quaternion.Euler(0f, m.a, 0f), scale);
                    bool boxed = false;
                    foreach (float[] box in PrefabBoxes(slot.prefab, pose))
                    {
                        list.Add(($"{m.type} at ({m.x:0},{m.y:0})", box));
                        kitProps++;
                        boxed = true;
                    }
                    if (boxed) continue;
                    // LocalBox has no answer for a MeshCollider (the convex fountain): the scaled prefab mesh bounds instead.
                    MeshFilter mf = slot.prefab.GetComponent<MeshFilter>();
                    if (mf == null || mf.sharedMesh == null || slot.prefab.GetComponentInChildren<Collider>() == null) continue;
                    Bounds b = mf.sharedMesh.bounds;
                    list.Add(($"{m.type} at ({m.x:0},{m.y:0})",
                        Corners(new Vector3(m.x, 0f, m.y), Quaternion.Euler(0f, m.a, 0f), Vector3.Scale(b.center, scale), Vector3.Scale(b.size, scale), true)));
                    kitProps++;
                }
            }
            // Free-standing clock-tower shafts sit in the district colliders, not under Props: both passes add them.
            foreach (LookLandmark m in d.landmarks)
            {
                if (m.mount != "tower" || registry.ExactPrefabSlot("prop/" + m.type) == null) continue;
                float w = m.shaft_w > 0f ? m.shaft_w : 3.2f;
                list.Add(($"{m.type} shaft at ({m.x:0},{m.y:0})", Corners(new Vector3(m.x, 0f, m.y), Quaternion.Euler(0f, m.a, 0f), Vector3.zero, new Vector3(w + 0.4f, 10f, w + 0.4f), true)));
                kitProps++;
            }

            Transform buildingsRoot = built != null ? built.Find("Buildings") : null;
            if (buildingsRoot != null)
            {
                // Building extras ("Collider" children) and registry-prefab buildings (kiosks, ATM, bus shelter); the
                // building's own shell MeshCollider is its footprint, already filled above.
                foreach (Transform bt in buildingsRoot)
                    foreach (Collider col in bt.GetComponentsInChildren<Collider>())
                    {
                        if (col.transform == bt || !GroundBox(col, hm, out float[] box)) continue;
                        bool extra = col.gameObject.name == "Collider";
                        string id = bt.name.StartsWith("B_") ? bt.name.Substring(2) : bt.name;
                        list.Add(($"{id} {(extra ? "extra collider" : TopBelow(col.transform, bt).name)}", box));
                        if (extra) extras++;
                        else kit++;
                    }
            }
            else
                foreach (LookBuilding b in d.buildings)
                {
                    if (LookGeom.Count(b.fp) < 3) continue;
                    float pad = hm.Pads.TryGetValue(b.id, out float p) ? p : hm.Height(b.x, b.y);
                    var origin = new Vector3(b.x, 0f, b.y);
                    if (!string.IsNullOrEmpty(b.prop_key))
                    {
                        PrefabSlot slot = registry.ExactPrefabSlot(b.prop_key);
                        if (slot?.prefab == null) continue;
                        var pose = Matrix4x4.TRS(new Vector3(b.x, pad, b.y), Quaternion.Euler(0f, b.front_deg, 0f), slot.scale);
                        foreach (float[] box in PrefabBoxes(slot.prefab, pose))
                        {
                            list.Add(($"{b.id} {slot.prefab.name}", box));
                            kit++;
                        }
                        continue;
                    }
                    BuildingResult res = ProceduralBuilding.Build(b, BuildingStyles.For(b), pad, hm.LowestUnder(b.fp), PropScatterer.KitParts(d, registry, b.id));
                    if (res.Collision != null) UnityEngine.Object.DestroyImmediate(res.Collision);
                    foreach (ExtraCollider ec in res.Colliders)
                    {
                        Vector3 world = origin + ec.Centre;
                        if (ec.Optional && MapLookBuilder.OnRoad(d, world.x, world.z, Mathf.Max(ec.Size.x, ec.Size.z) / 2f + 0.5f)) continue;
                        list.Add(($"{b.id} extra collider", Corners(origin, ec.Rotation, ec.Centre, ec.Size, false)));
                        extras++;
                    }
                }
            note = (built != null ? "colliders from the built scene" : "colliders from registry prefabs at plan poses (no scene open; KeepOffRoads nudge not applied)") +
                   $": {art} street-art, {kitProps} vehicle/landmark, {kit} kit-building, {extras} building-extra, {placeholders} placeholder-furniture boxes";
            return list;
        }

        private static Transform TopBelow(Transform t, Transform root)
        {
            while (t.parent != null && t.parent != root) t = t.parent;
            return t;
        }

        // World footprint (4 plan corners) of a scene collider that stands on the ground (bottom within 2.2 m of the
        // terrain, so arms and canopies overhead are ignored, like the placeholder footprints).
        private static bool GroundBox(Collider col, HeightModel hm, out float[] box)
        {
            box = null;
            if (!col.enabled || col.isTrigger) return false;
            Bounds wb = col.bounds;
            if (wb.min.y > hm.Height(wb.center.x, wb.center.z) + 2.2f) return false;
            box = LocalBox(col, col.transform.localToWorldMatrix) ?? AabbBox(wb);
            return true;
        }

        // Every collider of a prefab asset, posed by `pose` (the instance's TRS).
        private static IEnumerable<float[]> PrefabBoxes(GameObject prefab, Matrix4x4 pose)
        {
            Matrix4x4 toRoot = prefab.transform.worldToLocalMatrix;
            foreach (Collider col in prefab.GetComponentsInChildren<Collider>())
            {
                if (col.isTrigger) continue;
                float[] box = LocalBox(col, pose * toRoot * col.transform.localToWorldMatrix);
                if (box != null) yield return box;
            }
        }

        // Box and capsule colliders as oriented plan boxes; null for other collider types.
        private static float[] LocalBox(Collider col, Matrix4x4 m)
        {
            Vector3 c, half;
            switch (col)
            {
                case BoxCollider b:
                    c = b.center;
                    half = b.size / 2f;
                    break;
                case CapsuleCollider cap:
                    c = cap.center;
                    half = new Vector3(cap.radius, cap.height / 2f, cap.radius);
                    if (cap.direction == 0) half.x = Mathf.Max(cap.radius, cap.height / 2f);
                    if (cap.direction == 2) half.z = Mathf.Max(cap.radius, cap.height / 2f);
                    break;
                default:
                    return null;
            }
            var pts = new float[8];
            int i = 0;
            foreach (var (sx, sz) in new[] { (-1f, -1f), (1f, -1f), (1f, 1f), (-1f, 1f) })
            {
                Vector3 w = m.MultiplyPoint3x4(c + new Vector3(sx * half.x, 0f, sz * half.z));
                pts[i++] = w.x;
                pts[i++] = w.z;
            }
            return pts;
        }

        private static float[] AabbBox(Bounds b) => new[] { b.min.x, b.min.z, b.max.x, b.min.z, b.max.x, b.max.z, b.min.x, b.max.z };

        // rotateCentre: the centre is in the rotated frame too (a prop's local collider), not just the box (an extra collider).
        private static float[] Corners(Vector3 origin, Quaternion rot, Vector3 centre, Vector3 size, bool rotateCentre)
        {
            var pts = new float[8];
            int i = 0;
            foreach (var (sx, sz) in new[] { (-1f, -1f), (1f, -1f), (1f, 1f), (-1f, 1f) })
            {
                var off = new Vector3(sx * size.x / 2f, 0f, sz * size.z / 2f);
                Vector3 w = rotateCentre ? origin + rot * (centre + off) : origin + centre + rot * off;
                pts[i++] = w.x;
                pts[i++] = w.z;
            }
            return pts;
        }

        // Any collider box reaching into a drivable carriageway (more than 0.1 m inside the road edge) is reported:
        // the flood fill cannot see a partial lane cut, the van can.
        private static void LaneIntrusions(StringBuilder sb, LookData d, List<(string id, float[] box)> solids)
        {
            int count = 0;
            var examples = new List<string>();
            foreach (var (id, box) in solids)
            {
                string hit = null;
                LookGeom.Centroid(box, out float cx, out float cy);
                foreach (LookRoad r in d.roads)
                {
                    if (!r.van || r.cls == "passage" || LookGeom.Count(r.pts) < 2) continue;
                    for (int q = 0; q <= 4 && hit == null; q++)
                    {
                        float x = q < 4 ? box[2 * q] : cx, y = q < 4 ? box[2 * q + 1] : cy;
                        if (LookGeom.DistToPolyline(r.pts, x, y, false, out _, out _) < r.w / 2f - 0.1f) hit = r.id;
                    }
                    if (hit != null) break;
                }
                if (hit == null) continue;
                count++;
                if (examples.Count < 8) examples.Add($"{id} in {hit}");
            }
            sb.AppendLine(count == 0 ? $"  lanes: none of {solids.Count} furniture, kit-building and building-extra colliders reaches into a carriageway"
                : $"  LANES BLOCKED: {count} colliders reach into a carriageway, e.g. " + string.Join("; ", examples));
        }

        private static void WriteMap(string path, int nx, int ny, bool[] domain, bool[] look, bool[] grey, bool[] blocked)
        {
            var tex = new Texture2D(nx, ny, TextureFormat.RGB24, false);
            var px = new Color32[nx * ny];
            for (int k = 0; k < px.Length; k++)
            {
                Color32 c = !domain[k] ? new Color32(40, 50, 70, 255)
                    : look[k] && grey[k] ? new Color32(120, 170, 110, 255)
                    : grey[k] && !blocked[k] ? new Color32(230, 60, 50, 255)
                    : grey[k] ? new Color32(150, 120, 90, 255)
                    : look[k] ? new Color32(80, 140, 220, 255)
                    : new Color32(90, 90, 90, 255);
                px[k] = c;
            }
            tex.SetPixels32(px);
            tex.Apply();
            File.WriteAllBytes(path, tex.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(tex);
        }
    }
}
