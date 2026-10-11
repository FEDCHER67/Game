using System.Collections.Generic;
using System.IO;
using System.Text;
using OnlyVolunteers.Vehicles;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // Quick Play smoke test of a look play scene (v17 phase A brief): spawn check (van and player clear of colliders),
    // a 20 s "walk" (the player teleported to six Downtown/Rough sidewalk and yard points, must settle on the ground and
    // not be inside geometry), a 30 s drive along Downtown street 05_N (lane keeping at ~30 km/h; stuck = speed under
    // 5 km/h for 2 s after the start), then crowd NPCs inside building colliders are counted. Writes smoke_<label>.txt.
    // Application.runInBackground only for the run (restored); PlayerSettings untouched.
    [InitializeOnLoad]
    public static class V3SmokeRun
    {
        private const string Key = "OnlyVolunteers.V3SmokeRun.";
        private static readonly Vector2[] WalkPoints =
        {
            new(872f, 378f), new(868f, 355f), new(748.5f, 420f), new(700f, 600f), new(742f, 548f), new(650f, 640f),
        };

        static V3SmokeRun()
        {
            if (SessionState.GetBool(Key + "active", false)) EditorApplication.update += Tick;
        }

        public static string Start(string scenePath, string label)
        {
            if (EditorApplication.isPlaying) return "already playing";
            EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Single);
            SessionState.SetBool(Key + "active", true);
            SessionState.SetString(Key + "label", label);
            SessionState.SetInt(Key + "stage", 0);
            SessionState.SetString(Key + "out", "");
            SessionState.SetBool(Key + "rib_set", false);
            EditorApplication.update -= Tick;
            EditorApplication.update += Tick;
            EditorApplication.isPlaying = true;
            return "started " + label;
        }

        private static float stageStart, slowSince, minSpeed, maxSpeed;
        private static int walkIndex;
        private static VanController van;
        private static GreyboxPawn pawn;
        private static readonly StringBuilder log = new();

        private static void Out(string s) => log.AppendLine(s);

        private static void Tick()
        {
            if (!SessionState.GetBool(Key + "active", false))
            {
                EditorApplication.update -= Tick;
                return;
            }
            if (!EditorApplication.isPlaying) return;
            float now = (float)EditorApplication.timeSinceStartup;
            int stage = SessionState.GetInt(Key + "stage", 0);
            var sampler = Object.FindAnyObjectByType<MapHeightSampler>();
            switch (stage)
            {
                case 0:
                    SessionState.SetBool(Key + "rib_old", Application.runInBackground);
                    Application.runInBackground = true;
                    log.Clear();
                    stageStart = now;
                    SessionState.SetInt(Key + "stage", 1);
                    return;
                case 1: // settle 3 s, then the spawn check
                {
                    if (now - stageStart < 3f) return;
                    van = Object.FindAnyObjectByType<VanController>();
                    pawn = Object.FindAnyObjectByType<GreyboxPawn>();
                    if (van != null)
                    {
                        var hits = Overlaps(van.transform, van.transform.position + Vector3.up * 1.3f, new Vector3(1.0f, 0.9f, 2.6f), van.transform.rotation);
                        Out($"spawn van at {V(van.transform.position)}: {(hits.Count == 0 ? "clear" : "OVERLAPS " + string.Join(", ", hits))}");
                    }
                    else Out("spawn: no VanController");
                    if (pawn != null)
                    {
                        var hits = Overlaps(pawn.Body, pawn.Position + Vector3.up * 1.0f, new Vector3(0.3f, 0.7f, 0.3f), Quaternion.identity);
                        Out($"spawn player at {V(pawn.Position)}: {(hits.Count == 0 ? "clear" : "OVERLAPS " + string.Join(", ", hits))}");
                    }
                    else Out("spawn: no player pawn");
                    walkIndex = 0;
                    stageStart = now - 10f;
                    SessionState.SetInt(Key + "stage", 2);
                    return;
                }
                case 2: // walk: six points, ~3.3 s each
                {
                    if (pawn == null) { SessionState.SetInt(Key + "stage", 3); return; }
                    if (now - stageStart < 3.3f) return;
                    if (walkIndex > 0)
                    {
                        Vector2 q = WalkPoints[walkIndex - 1];
                        float ground = sampler != null ? sampler.Height(q.x, q.y) : 0f;
                        Vector3 p = pawn.Position;
                        var hits = Overlaps(pawn.Body, p + Vector3.up * 1.0f, new Vector3(0.25f, 0.6f, 0.25f), Quaternion.identity);
                        Out($"walk point {walkIndex} ({q.x:0}, {q.y:0}): settled at y {p.y:0.00} (ground {ground:0.00}), drift {Vector2.Distance(new Vector2(p.x, p.z), q):0.0} m, {(hits.Count == 0 ? "clear" : "INSIDE " + string.Join(", ", hits))}");
                    }
                    if (walkIndex >= WalkPoints.Length)
                    {
                        SessionState.SetInt(Key + "stage", 3);
                        return;
                    }
                    Vector2 w = WalkPoints[walkIndex++];
                    float h = sampler != null ? sampler.Height(w.x, w.y) : 0f;
                    pawn.Teleport(new Vector3(w.x, h + 0.2f, w.y), 0f);
                    stageStart = now;
                    return;
                }
                case 3: // drive 30 s east along 05_N, right lane
                {
                    if (van == null) { SessionState.SetInt(Key + "stage", 5); return; }
                    foreach (MonoBehaviour mb in van.GetComponents<MonoBehaviour>())
                        if (mb.GetType().Name == "GreyboxVanAutopilot" || mb.GetType().Name == "VanDriveInput") mb.enabled = false;
                    float y = sampler != null ? sampler.Height(690f, 468.8f) : 0f;
                    var rb = van.GetComponent<Rigidbody>();
                    van.transform.SetPositionAndRotation(new Vector3(690f, y + 0.6f, 468.8f), Quaternion.Euler(0f, 90f, 0f));
                    if (rb != null)
                    {
                        rb.position = van.transform.position;
                        rb.rotation = van.transform.rotation;
                        rb.linearVelocity = Vector3.zero;
                        rb.angularVelocity = Vector3.zero;
                    }
                    van.Handbrake = false;
                    stageStart = now;
                    slowSince = -1f;
                    minSpeed = float.MaxValue;
                    maxSpeed = 0f;
                    SessionState.SetInt(Key + "stage", 4);
                    return;
                }
                case 4:
                {
                    float t = now - stageStart;
                    Vector3 p = van.transform.position;
                    Vector3 f = van.transform.forward;
                    float lateral = p.z - 468.8f;                      // + = left of travel (north)
                    float heading = Mathf.Atan2(f.z, f.x);              // 0 = east
                    van.Throttle = Mathf.Clamp((30f - van.SpeedKmh) / 8f, -1f, 1f);
                    van.Steer = Mathf.Clamp(0.25f * lateral + 2.0f * heading, -1f, 1f);
                    van.Handbrake = false;
                    if (t > 6f)
                    {
                        minSpeed = Mathf.Min(minSpeed, van.SpeedKmh);
                        if (van.SpeedKmh < 5f) { if (slowSince < 0f) slowSince = now; }
                        else slowSince = -1f;
                    }
                    maxSpeed = Mathf.Max(maxSpeed, van.SpeedKmh);
                    bool stuck = slowSince > 0f && now - slowSince > 2f;
                    if (t < 30f && !stuck && p.x < 990f) return;
                    van.Throttle = 0f;
                    van.Handbrake = true;
                    Out($"drive 05_N: {t:0.0} s, from x 690 to {V(p)}, speed max {maxSpeed:0} km/h, min after 6 s {(minSpeed == float.MaxValue ? 0 : minSpeed):0} km/h, lateral {lateral:0.00} m, {(stuck ? "STUCK" : "no stuck spot")}");
                    stageStart = now;
                    SessionState.SetInt(Key + "stage", 5);
                    return;
                }
                case 5: // crowd NPCs inside buildings
                {
                    if (now - stageStart < 1f) return;
                    int npcs = 0, inside = 0;
                    var names = new List<string>();
                    foreach (var w in Object.FindObjectsByType<OnlyVolunteers.Map.Crowd.CrowdWalker>(FindObjectsInactive.Exclude))
                    {
                        npcs++;
                        foreach (Collider c in Physics.OverlapSphere(w.transform.position + Vector3.up * 1.0f, 0.15f, ~0, QueryTriggerInteraction.Ignore))
                            if (InBuildings(c.transform))
                            {
                                inside++;
                                if (names.Count < 5) names.Add(c.transform.parent != null ? c.transform.parent.name : c.name);
                                break;
                            }
                    }
                    Out($"crowd: {npcs} active walkers, {inside} inside building colliders {(names.Count > 0 ? "(" + string.Join(", ", names) + ")" : "")}");
                    string label = SessionState.GetString(Key + "label", "run");
                    string dir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", V3Sightlines.Dir));
                    File.WriteAllText(Path.Combine(dir, $"smoke_{label}.txt"), log.ToString());
                    Debug.Log("[V3SmokeRun]\n" + log);
                    Application.runInBackground = SessionState.GetBool(Key + "rib_old", false);
                    SessionState.SetBool(Key + "active", false);
                    EditorApplication.update -= Tick;
                    EditorApplication.isPlaying = false;
                    return;
                }
            }
        }

        private static bool InBuildings(Transform t)
        {
            for (Transform q = t; q != null; q = q.parent)
                if (q.name == "Buildings") return true;
            return false;
        }

        private static List<string> Overlaps(Transform self, Vector3 centre, Vector3 half, Quaternion rot)
        {
            var r = new List<string>();
            foreach (Collider c in Physics.OverlapBox(centre, half, rot, ~0, QueryTriggerInteraction.Ignore))
            {
                if (c.transform.IsChildOf(self) || self.IsChildOf(c.transform.root) && c.transform.root == self.root && c.transform.root != c.transform) continue;
                if (c is TerrainCollider) continue;
                string n = c.transform.parent != null ? c.transform.parent.name + "/" + c.name : c.name;
                if (!r.Contains(n)) r.Add(n);
            }
            return r;
        }

        private static string V(Vector3 p) => $"({p.x:0.0}, {p.y:0.0}, {p.z:0.0})";
    }
}
