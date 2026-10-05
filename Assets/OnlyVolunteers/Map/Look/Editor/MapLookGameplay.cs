using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace OnlyVolunteers.Map.Look
{
    // Fedya's test map from 2026-10-05 on: the final-look environment (MapLookBuilder.BuildEnvironment + MapLookLighting)
    // with the grey-box gameplay (MapGreyboxBuilder.PlaceGameplay: van, cameras, KCC player, NPC crowd, pickups, sea
    // return) placed on its real ground, saved as Map_Look_vNN_Play next to Map_Look_vNN (never over it). The gameplay
    // points come from greybox_vNN_flat.json, which shares the look's coordinate frame (P02 = 209.41, 593.73 in both).
    public static class MapLookGameplay
    {
        private const string SceneDir = "Assets/OnlyVolunteers/Scenes/Map";
        // The play cameras see as far as the look's own fly camera: the sea apron runs 1.8 km out, the fog ends at 1.1 km.
        private const float FarClip = 3000f;

        [MenuItem("OnlyVolunteers/Map/Build Map Look + Gameplay (latest plan)")]
        public static void BuildLatest()
        {
            if (EditorApplication.isPlaying)
            {
                Debug.LogWarning("[MapLook+Play] Exit Play mode first, then build again.");
                return;
            }
            string rev = MapLookBuilder.LatestRevision();
            if (rev == null)
            {
                Debug.LogError($"[MapLook+Play] No look_vNN_flat.json in {MapLookBuilder.LookJsonDir}; run flatten_look.py first.");
                return;
            }
            string planPath = Path.GetFullPath(MapGreyboxBuilder.PlanPath(rev));
            if (!File.Exists(planPath))
            {
                Debug.LogError($"[MapLook+Play] {rev}: the gameplay points (van, crowd, pickups, sea) come from the grey-box plan, and " +
                               $"{planPath} is missing. Run ArtSource/References/Map/Greybox/flatten_plan.py for {rev} first.");
                return;
            }
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            var sw = Stopwatch.StartNew();
            MapGreyboxBuilder.Plan plan = MapGreyboxBuilder.LoadPlan(rev);
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            string sceneName = $"Map_Look_{rev}_Play";
            var root = new GameObject($"MapLook_{rev}").transform;
            MapHeightSampler sampler = MapLookBuilder.BuildEnvironment(rev, root, sceneName);
            if (sampler == null) return;
            MapLookLighting.Apply(root);
            LookData data = MapLookBuilder.Load(rev);
            string layers = CheckLayers(root);
            // Edit-time queries see the new environment's colliders only once their transforms are synced.
            Physics.SyncTransforms();
            var setup = new MapGreyboxBuilder.GameplaySetup
            {
                Plan = plan,
                Ground = new LookPlayGround(sampler, data, root),
                Pawn = MapGreyboxBuilder.PawnKind.Kcc,
                Sea = plan.sea,
                FarClip = FarClip,
                PostProcessing = true,
            };
            MapGreyboxBuilder.GameplayResult result = MapGreyboxBuilder.PlaceGameplay(setup);
            AddSurf(setup.SeaZone, data);
            LookAssetStore.EnsureFolder(SceneDir);
            string scenePath = $"{SceneDir}/{sceneName}.unity";
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), scenePath);
            Vector3 van = result.Van.transform.position;
            Debug.Log($"[MapLook+Play] {rev} (builder r{GreyboxVanSeat.CurrentBuildRevision}): van at ({van.x:0.0}, {van.y:0.00}, {van.z:0.0}), " +
                      $"{result.Npcs} of {result.CrowdSlots} crowd NPCs, {result.Pickups} pickups; {layers} -> {scenePath} in {sw.Elapsed.TotalSeconds:0.0} s");
        }

        // The beach runs under the sea's surface before the sea zone starts (the surf, BEACH_SURF): a point there below
        // the surface is no dry place to put someone back on. Only inside the beach polygon: lake and river beds and the
        // dry hollows inland below the sea level stay dry places (SeaReturnZone.Dry).
        private static void AddSurf(SeaReturnZone zone, LookData data)
        {
            if (zone == null || LookGeom.Count(data.sea.pts) < 3 || LookGeom.Count(data.beach.pts) < 3) return;
            float[] pts = data.beach.pts;
            var polygon = new Vector2[pts.Length / 2];
            for (int i = 0; i < polygon.Length; i++) polygon[i] = new Vector2(pts[2 * i], pts[2 * i + 1]);
            var surf = zone.gameObject.AddComponent<SeaReturnSurf>();
            surf.WaterLevel = data.sea.level;
            surf.Polygon = polygon;
        }

        // Every environment collider must be on a layer the KCC player, the van (its wheels and body on Vehicle), NPC
        // bodies (NpcBody, NpcSeated) collide with and the Q ray (OvLayers.ShootMask) and LMB see. The look builds on
        // Default; a registry prefab on another layer would be walked, driven or fallen through: put back on Default.
        private static string CheckLayers(Transform root)
        {
            int moved = 0, total = 0;
            foreach (Collider c in root.GetComponentsInChildren<Collider>(true))
            {
                total++;
                if (c.isTrigger) continue; // query volumes keep their layer (Ignore Raycast keeps them out of rays)
                int layer = c.gameObject.layer;
                if (Solid(layer)) continue;
                Debug.LogWarning($"[MapLook+Play] collider {c.name} on layer {LayerMask.LayerToName(layer)} ({layer}) is not solid for the " +
                                 "player, the van or NPC bodies; moved to Default.", c);
                c.gameObject.layer = 0;
                moved++;
            }
            return $"{total} environment colliders" + (moved > 0 ? $" ({moved} moved to Default)" : " all on solid layers");
        }

        private static bool Solid(int layer) =>
            layer != 2 && (OvLayers.ShootMask & (1 << layer)) != 0 &&
            !Physics.GetIgnoreLayerCollision(layer, OvLayers.Player) && !Physics.GetIgnoreLayerCollision(layer, OvLayers.Vehicle) &&
            !Physics.GetIgnoreLayerCollision(layer, OvLayers.NpcBody) && !Physics.GetIgnoreLayerCollision(layer, OvLayers.NpcSeated);
    }

    // The look map as ground for the gameplay. Height: terrain and bridge decks (MapHeightSampler), raised to the
    // environment's own flat collider surface right there (sidewalk, kerb, bridge deck; carriageways are drawn on the
    // terrain, which is what the wheels drive on), found by a ray at edit time. RoadHeight: the same, except that a road
    // crossing under a bridge deck stays on the terrain under it. Blocked: any collider in the body's capsule or the
    // van's box (props, furniture, fences, walls, blockers, the van and NPCs already placed); anything standing over the
    // spot (a body fully inside a big rock's or prop's mesh collider touches none of its faces); tree trunks, from the
    // terrain data, because TerrainCollider trees exist only in Play mode; building footprints (a building's mesh collider
    // reports only its walls, not its inside); water (lake, river, canal, sea and the surf below the sea level); the map edge.
    internal sealed class LookPlayGround : MapGreyboxBuilder.GameplayGround
    {
        private const int Mask = ~(1 << OvLayers.VehicleInterior);
        // Flat collider surfaces this far above the terrain or deck are still ground (decks, sidewalks at +0.12, kerbs,
        // plazas); a bench seat (0.45 m), a planter, a low wall or a rock top is an obstacle, not a place to stand.
        private const float SurfaceBand = 0.3f, SurfaceMinNormalY = 0.9f;
        // A road meeting a deck at more than about 45 degrees passes under it.
        private const float DeckAlongCos = 0.7f;
        // The spawn capsule starts this far above the feet, so kerbs and bumps of the ground do not block it.
        private const float Clearance = 0.25f;
        // Nothing may stand over a body up to this far above its head (awnings, rock tops, branches with colliders).
        private const float Headroom = 1.5f;
        private const float BuildingMargin = 1f, EdgeMargin = 3f, TrunkMargin = 0.3f, TrunkCell = 16f;

        private readonly MapHeightSampler sampler;
        private readonly LookData data;
        private readonly Transform environment;
        private readonly RaycastHit[] hits = new RaycastHit[32];
        private readonly Collider[] overlaps = new Collider[32];
        // Tree trunks per 16 m cell: (x, trunk radius, z).
        private readonly Dictionary<(int, int), List<Vector3>> trunks = new();

        public LookPlayGround(MapHeightSampler sampler, LookData data, Transform environment)
        {
            this.sampler = sampler;
            this.data = data;
            this.environment = environment;
            IndexTrunks(sampler.Terrain);
        }

        public override bool Checks => true;

        public override float Height(float x, float z) => Raise(sampler.Height(x, z), x, z);

        // Under a deck, across it: the terrain (that road's own surface), raised to colliders within the band only, so the
        // deck above is not taken for the road (the van's clearance box then tells whether it fits under).
        public override float RoadHeight(float x, float z, Vector2 dir)
        {
            if (dir.sqrMagnitude > 1e-6f && MapHeightSampler.DeckAt(sampler.Decks, x, z, out _, out Vector2 deckDir) &&
                Mathf.Abs(Vector2.Dot(dir.normalized, deckDir)) < DeckAlongCos)
                return Raise(TerrainHeight(x, z), x, z);
            return Height(x, z);
        }

        private float Raise(float h, float x, float z)
        {
            int n = Physics.RaycastNonAlloc(new Vector3(x, h + 3f, z), Vector3.down, hits, 6f, Mask, QueryTriggerInteraction.Ignore);
            float best = float.NegativeInfinity;
            for (int i = 0; i < n; i++)
            {
                float y = hits[i].point.y;
                if (y <= h + SurfaceBand && y > best && hits[i].normal.y > SurfaceMinNormalY && hits[i].collider.transform.IsChildOf(environment))
                    best = y;
            }
            return float.IsNegativeInfinity(best) ? h : best;
        }

        private float TerrainHeight(float x, float z)
        {
            Terrain t = sampler.Terrain;
            return t != null ? t.SampleHeight(new Vector3(x, 0f, z)) + t.transform.position.y : 0f;
        }

        public override bool Blocked(Vector3 feet, float radius, float height)
        {
            if (!OnMap(feet.x, feet.z, EdgeMargin) || sampler.InWater(feet.x, feet.z, out _) ||
                InBuilding(feet.x, feet.z, radius + BuildingMargin) || NearTrunk(feet.x, feet.z, radius + TrunkMargin))
                return true;
            Physics.SyncTransforms();
            Vector3 low = feet + Vector3.up * (radius + Clearance);
            Vector3 high = feet + Vector3.up * Mathf.Max(radius + Clearance, height - radius);
            if (Physics.CheckCapsule(low, high, radius, Mask, QueryTriggerInteraction.Ignore)) return true;
            float top = height + Headroom;
            return Physics.Raycast(feet + Vector3.up * top, Vector3.down, top - Clearance, Mask, QueryTriggerInteraction.Ignore);
        }

        public override bool Blocked(Vector3 centre, Vector3 halfExtents, Quaternion rotation)
        {
            if (!OnMap(centre.x, centre.z, EdgeMargin) || sampler.InWater(centre.x, centre.z, out _) || TrunkInBox(centre, halfExtents, rotation))
                return true;
            Physics.SyncTransforms();
            // The terrain is left to the sampled test below: the box reaches far ahead of the axles its pitch comes from.
            int n = Physics.OverlapBoxNonAlloc(centre, halfExtents, overlaps, rotation, Mask, QueryTriggerInteraction.Ignore);
            if (n >= overlaps.Length) return true;
            for (int i = 0; i < n; i++)
                if (!(overlaps[i] is TerrainCollider)) return true;
            // Terrain clearance under the box's bottom corners and the middles of its long sides.
            for (int sx = -1; sx <= 1; sx += 2)
                for (int sz = -1; sz <= 1; sz++)
                {
                    Vector3 corner = centre + rotation * new Vector3(sx * halfExtents.x, -halfExtents.y, sz * halfExtents.z);
                    if (TerrainHeight(corner.x, corner.z) > corner.y) return true;
                }
            return false;
        }

        private bool OnMap(float x, float z, float margin)
        {
            float[] edge = data.boundary.pts;
            if (LookGeom.Count(edge) < 3) return true;
            return LookGeom.Inside(edge, x, z) && LookGeom.DistToPolyline(edge, x, z, true, out _, out _) >= margin;
        }

        private bool InBuilding(float x, float z, float margin)
        {
            foreach (LookBuilding b in data.buildings)
            {
                if (LookGeom.Count(b.fp) < 3) continue;
                if (LookGeom.Inside(b.fp, x, z) || LookGeom.DistToPolyline(b.fp, x, z, true, out _, out _) < margin) return true;
            }
            return false;
        }

        // Trunk radius = the tree prefab's capsule (every tree prototype has one) times the instance's width scale, as the
        // TerrainCollider builds it in Play mode.
        private void IndexTrunks(Terrain terrain)
        {
            if (terrain == null) return;
            TerrainData td = terrain.terrainData;
            TreePrototype[] prototypes = td.treePrototypes;
            var radius = new float[prototypes.Length];
            for (int i = 0; i < prototypes.Length; i++)
            {
                CapsuleCollider capsule = prototypes[i].prefab != null ? prototypes[i].prefab.GetComponentInChildren<CapsuleCollider>(true) : null;
                radius[i] = capsule != null ? capsule.radius * Mathf.Abs(capsule.transform.lossyScale.x) : 0.3f;
            }
            foreach (TreeInstance tree in td.treeInstances)
            {
                if (tree.prototypeIndex < 0 || tree.prototypeIndex >= radius.Length) continue;
                Vector3 w = Vector3.Scale(tree.position, td.size) + terrain.transform.position;
                var key = (Mathf.FloorToInt(w.x / TrunkCell), Mathf.FloorToInt(w.z / TrunkCell));
                if (!trunks.TryGetValue(key, out List<Vector3> list)) trunks[key] = list = new List<Vector3>();
                list.Add(new Vector3(w.x, radius[tree.prototypeIndex] * tree.widthScale, w.z));
            }
        }

        private bool NearTrunk(float x, float z, float reach) =>
            AnyTrunk(x, z, t => (t.x - x) * (t.x - x) + (t.z - z) * (t.z - z) < (reach + t.y) * (reach + t.y));

        private bool TrunkInBox(Vector3 centre, Vector3 half, Quaternion rotation)
        {
            Quaternion inverse = Quaternion.Inverse(rotation);
            return AnyTrunk(centre.x, centre.z, t =>
            {
                Vector3 local = inverse * (new Vector3(t.x, centre.y, t.z) - centre);
                return Mathf.Abs(local.x) < half.x + t.y && Mathf.Abs(local.z) < half.z + t.y;
            });
        }

        // Trunks in the 3 x 3 cells around (x, z): every reach used here is far below one cell (16 m).
        private bool AnyTrunk(float x, float z, Func<Vector3, bool> hit)
        {
            int cx = Mathf.FloorToInt(x / TrunkCell), cz = Mathf.FloorToInt(z / TrunkCell);
            for (int dx = -1; dx <= 1; dx++)
                for (int dz = -1; dz <= 1; dz++)
                    if (trunks.TryGetValue((cx + dx, cz + dz), out List<Vector3> list))
                        foreach (Vector3 t in list)
                            if (hit(t)) return true;
            return false;
        }
    }
}
