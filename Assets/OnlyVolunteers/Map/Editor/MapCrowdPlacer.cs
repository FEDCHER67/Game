using System.IO;
using System.Text.RegularExpressions;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Player.Physics;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // The CrowdDirector half of "Build Map Look + Gameplay" (MapGreyboxBuilder.PlaceGameplay with CrowdKind.Director):
    // a "Crowd" object with the director (the latest crowd_vNN.json as a TextAsset in Map/Data, copied from
    // ArtSource/References/Map/Crowd if missing), the placeholder police hook, a pool of inactive grey-box Buddies (the
    // largest day/evening total + the police + spares) and two inactive templates to clone from if the pool runs dry.
    // The menu toggle switches back to the old static crowd (two standing Buddies per crowd point) as a fallback.
    internal static class MapCrowdPlacer
    {
        private const string PrefKey = "OnlyVolunteers.Map.CrowdDirector";
        private const string MenuPath = "OnlyVolunteers/Map/Crowd: use CrowdDirector in Build Map Look + Gameplay";
        private const string DataDir = "Assets/OnlyVolunteers/Map/Data";
        private const string SourceDir = "ArtSource/References/Map/Crowd";
        private const int PoolSpare = 10;

        public static bool UseDirector
        {
            get => EditorPrefs.GetBool(PrefKey, true);
            set => EditorPrefs.SetBool(PrefKey, value);
        }

        [MenuItem(MenuPath, false, 200)]
        private static void Toggle()
        {
            UseDirector = !UseDirector;
            Debug.Log($"[Crowd] Build Map Look + Gameplay will place {(UseDirector ? "the CrowdDirector (walking crowd)" : "the old static crowd")}.");
        }

        [MenuItem(MenuPath, true)]
        private static bool ToggleValidate()
        {
            Menu.SetChecked(MenuPath, UseDirector);
            return true;
        }

        internal static CrowdDirector Place(GameObject[] buddies, GrabPhysicsProfile grabProfile, bool sea, out int pool)
        {
            pool = 0;
            TextAsset data = EnsureData();
            if (data == null)
            {
                Debug.LogError($"[Crowd] no crowd_vNN.json in {DataDir} or {SourceDir}; no crowd placed.");
                return null;
            }
            CrowdData map = CrowdData.Parse(data.text);
            int size = PoolSpare + (map.Patrol != null ? map.Patrol.Officers : 0);
            foreach (CrowdDistrict d in map.Districts) size += Mathf.Max(d.Day, d.Evening);

            var root = new GameObject("Crowd");
            var director = root.AddComponent<CrowdDirector>();
            director.Data = data;
            director.Sampler = Object.FindAnyObjectByType<MapHeightSampler>();
            root.AddComponent<CrowdPoliceHook>();
            var poolRoot = new GameObject("Pool").transform;
            poolRoot.SetParent(root.transform, false);
            director.PoolRoot = poolRoot;
            for (int i = 0; i < size; i++)
            {
                GameObject npc = MapGreyboxBuilder.SpawnCrowdNpc(buddies[i % buddies.Length], $"CrowdPool_{i:000}", Vector3.zero, 0f, grabProfile, sea);
                npc.transform.SetParent(poolRoot, false);
                npc.SetActive(false);
            }
            var templates = new GameObject("Templates").transform;
            templates.SetParent(root.transform, false);
            director.Templates = new GameObject[buddies.Length];
            for (int i = 0; i < buddies.Length; i++)
            {
                GameObject npc = MapGreyboxBuilder.SpawnCrowdNpc(buddies[i], $"CrowdTemplate_{i}", Vector3.zero, 0f, grabProfile, sea);
                npc.transform.SetParent(templates, false);
                npc.SetActive(false);
                director.Templates[i] = npc;
            }
            pool = size;
            Debug.Log($"[Crowd] CrowdDirector placed: {map.Revision}, {map.Districts.Count} districts, pool {size} NPCs, data {AssetDatabase.GetAssetPath(data)}");
            return director;
        }

        // The highest crowd_vNN.json in Map/Data; the highest in ArtSource is copied in first if Map/Data lacks it. An
        // existing copy is never overwritten (a changed source under the same name only warns: delete the copy to refresh).
        private static TextAsset EnsureData()
        {
            string project = Path.GetDirectoryName(Application.dataPath);
            string source = Latest(Path.Combine(project, SourceDir));
            if (source != null)
            {
                string assetPath = $"{DataDir}/{Path.GetFileName(source)}";
                string full = Path.Combine(project, assetPath);
                if (!File.Exists(full))
                {
                    File.Copy(source, full);
                    AssetDatabase.ImportAsset(assetPath);
                    Debug.Log($"[Crowd] copied {Path.GetFileName(source)} into {DataDir}");
                }
                else if (new FileInfo(full).Length != new FileInfo(source).Length || File.ReadAllText(full) != File.ReadAllText(source))
                {
                    Debug.LogWarning($"[Crowd] {assetPath} differs from {SourceDir}/{Path.GetFileName(source)}; using the copy in Map/Data " +
                                     "(delete it to take the ArtSource version).");
                }
            }
            string latest = Latest(Path.Combine(project, DataDir));
            return latest != null ? AssetDatabase.LoadAssetAtPath<TextAsset>($"{DataDir}/{Path.GetFileName(latest)}") : null;
        }

        private static string Latest(string dir)
        {
            if (!Directory.Exists(dir)) return null;
            string best = null;
            int bestRev = -1;
            foreach (string f in Directory.GetFiles(dir, "crowd_v*.json"))
            {
                Match m = Regex.Match(Path.GetFileName(f), @"^crowd_v(\d+)\.json$");
                if (!m.Success) continue;
                int rev = int.Parse(m.Groups[1].Value);
                if (rev > bestRev)
                {
                    bestRev = rev;
                    best = f;
                }
            }
            return best;
        }
    }
}
