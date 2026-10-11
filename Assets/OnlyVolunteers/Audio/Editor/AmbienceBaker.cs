using System;
using System.Collections.Generic;
using System.IO;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Map.Look;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Audio.EditorTools
{
    // Reads the full plan for the revision selected by MapLookBuilder.BuildLatest, so the
    // baked ambience follows the map scene rather than a newer unbuilt 2D plan.
    public static class AmbienceBaker
    {
        // Per revision (Ambience_v16.asset next to the v12-era Ambience_latest.asset, which stays as it is): a newer plan
        // must not replace the ambience of the scenes already built. AmbiencePlayer loads its scene's revision first.
        private static string AssetPathFor(string revision) => "Assets/OnlyVolunteers/Audio/Resources/Ambience_" + revision + ".asset";
        private const string LibraryPath = "Assets/OnlyVolunteers/Audio/Resources/SfxLibrary.asset";
        private const string WorldClips = "Assets/OnlyVolunteers/Audio/Library_v1/world";
        private const string Tag = "[AmbienceBake]";

        private static readonly string[] SoundIds =
        {
            "amb_birds", "amb_city", "amb_office", "amb_sea", "amb_sea_gulls", "amb_fountain"
        };

        [MenuItem("OnlyVolunteers/Audio/Bake Ambience Zones (latest plan)")]
        public static void Bake()
        {
            if (EditorApplication.isPlaying)
            {
                Debug.LogWarning(Tag + " Exit Play mode before baking.");
                return;
            }

            string revision = MapLookBuilder.LatestRevision();
            if (string.IsNullOrEmpty(revision))
            {
                Debug.LogError(Tag + " No look_vNN_flat.json was found in " + MapLookBuilder.LookJsonDir + ".");
                return;
            }
            string path = Path.Combine(Application.dataPath, "..", "ArtSource", "References", "Map",
                                       "MAP_PLAN_R01_" + revision + ".json");
            if (!File.Exists(path))
            {
                Debug.LogError(Tag + " No full plan for " + revision + " at " + path + ".");
                return;
            }

            List<AmbienceData.District> districts = new List<AmbienceData.District>();
            List<AmbienceData.Coastline> coastlines = new List<AmbienceData.Coastline>();
            List<Vector3> fountains = new List<Vector3>();
            List<Vector3> offices = new List<Vector3>();
            try
            {
                LookData look = MapLookBuilder.Load(revision);
                Dictionary<string, object> plan = MiniJson.Parse(File.ReadAllText(path)) as Dictionary<string, object>;
                if (plan == null) throw new InvalidDataException("The plan is not a JSON object.");
                ReadDistricts(plan, districts);
                ReadCoastline(plan, coastlines);
                ReadFountains(plan, fountains);
                if (fountains.Count == 0) ReadLookFountains(look, fountains);
                ReadOffices(plan, offices);
            }
            catch (Exception exception)
            {
                Debug.LogError(Tag + " Could not read " + Path.GetFileName(path) + ": " + exception);
                return;
            }

            SfxLibrary library = AssetDatabase.LoadAssetAtPath<SfxLibrary>(LibraryPath);
            if (library == null)
            {
                Debug.LogError(Tag + " The SfxLibrary asset is missing at " + LibraryPath);
                return;
            }

            string assetPath = AssetPathFor(revision);
            AmbienceData data = AssetDatabase.LoadAssetAtPath<AmbienceData>(assetPath);
            bool created = data == null;
            if (created) data = ScriptableObject.CreateInstance<AmbienceData>();
            data.PlanRevision = revision;
            data.Districts = districts.ToArray();
            data.Coastlines = coastlines.ToArray();
            data.Fountains = fountains.ToArray();
            data.Offices = offices.ToArray();

            if (created) AssetDatabase.CreateAsset(data, assetPath);
            else EditorUtility.SetDirty(data);

            int foundClipCount = FillLibrary(library);
            AssetDatabase.SaveAssets();

            List<string> unmapped = new List<string>();
            for (int i = 0; i < data.Districts.Length; i++)
            {
                string id = data.Districts[i].Id;
                if (data.MappingFor(id) == null) unmapped.Add(id);
            }
            Debug.Log(Tag + " baked from " + revision + " (" + Path.GetFileName(path) + "): " +
                      districts.Count + " districts, " + coastlines.Count + " coastline segments, " +
                      fountains.Count + " fountains, " + offices.Count + " offices, " + foundClipCount +
                      " ambience clips. Unmapped plan districts: " +
                      (unmapped.Count == 0 ? "none" : string.Join(", ", unmapped)) + ". Saved " + assetPath, data);
        }

        private static void ReadDistricts(Dictionary<string, object> plan, List<AmbienceData.District> output)
        {
            List<object> districts = Items(plan, "districts");
            if (districts.Count == 0) throw new InvalidDataException("The full plan lacks districts[].polygon_m.");
            foreach (object item in districts)
            {
                Dictionary<string, object> district = item as Dictionary<string, object>;
                if (district == null) throw new InvalidDataException("A district is not a JSON object.");
                string id = String(district, "id");
                Vector2[] polygon = Polyline(district, "polygon_m");
                if (string.IsNullOrEmpty(id) || polygon.Length < 3)
                    throw new InvalidDataException("District " + (id ?? "<missing id>") + " lacks a usable polygon_m.");
                output.Add(new AmbienceData.District { Id = id, Polygon = polygon });
            }
        }

        private static void ReadCoastline(Dictionary<string, object> plan, List<AmbienceData.Coastline> output)
        {
            Dictionary<string, object> boundary = Object(plan, "boundary");
            foreach (object item in Items(boundary, "coast_segments_m"))
            {
                Vector2[] segment = Polyline(item as List<object>);
                if (segment.Length >= 2) output.Add(new AmbienceData.Coastline { Points = segment });
            }
        }

        private static void ReadFountains(Dictionary<string, object> plan, List<Vector3> output)
        {
            foreach (object item in Items(plan, "functional_sites"))
            {
                Dictionary<string, object> site = item as Dictionary<string, object>;
                if (site == null || !string.Equals(String(site, "type"), "fountain", StringComparison.OrdinalIgnoreCase)) continue;
                Vector2[] polygon = Polyline(site, "polygon_m");
                if (polygon.Length == 0) continue;
                Vector2 center = Vector2.zero;
                for (int i = 0; i < polygon.Length; i++) center += polygon[i];
                center /= polygon.Length;
                output.Add(new Vector3(center.x, 0f, center.y));
            }
        }

        private static void ReadLookFountains(LookData look, List<Vector3> output)
        {
            if (look == null || look.landmarks == null) return;
            for (int i = 0; i < look.landmarks.Length; i++)
            {
                LookLandmark landmark = look.landmarks[i];
                if (landmark != null && string.Equals(landmark.type, "fountain", StringComparison.OrdinalIgnoreCase))
                    output.Add(new Vector3(landmark.x, 0f, landmark.y));
            }
        }

        private static void ReadOffices(Dictionary<string, object> plan, List<Vector3> output)
        {
            foreach (object item in Items(plan, "functional_buildings"))
            {
                Dictionary<string, object> building = item as Dictionary<string, object>;
                if (building == null || !string.Equals(String(building, "type"), "office", StringComparison.OrdinalIgnoreCase)) continue;
                Vector2 center;
                if (!TryVector2(building, "center_m", out center)) continue;
                output.Add(new Vector3(center.x, 0f, center.y));
            }
        }

        private static int FillLibrary(SfxLibrary library)
        {
            List<string> paths = new List<string>();
            if (AssetDatabase.IsValidFolder(WorldClips))
            {
                string[] guids = AssetDatabase.FindAssets("t:AudioClip", new[] { WorldClips });
                for (int i = 0; i < guids.Length; i++) paths.Add(AssetDatabase.GUIDToAssetPath(guids[i]));
                paths.Sort(StringComparer.OrdinalIgnoreCase);
            }

            int total = 0;
            for (int i = 0; i < SoundIds.Length; i++)
            {
                string id = SoundIds[i];
                SfxLibrary.Entry entry = library.Find(id);
                if (entry == null)
                {
                    entry = new SfxLibrary.Entry { Id = id };
                    entry.Volume = Vector2.one;
                    entry.Pitch = Vector2.one;
                    entry.SpatialBlend = id == "amb_fountain" ? 1f : 0f;
                    entry.MinDistance = id == "amb_fountain" ? 3f : 1f;
                    entry.MaxDistance = id == "amb_fountain" ? 25f : 35f;
                    entry.Cooldown = 0f;
                    entry.Priority = 200;
                    library.Entries.Add(entry);
                    library.Rebuild();
                }
                if (!entry.Locked)
                {
                    List<AudioClip> clips = new List<AudioClip>();
                    for (int j = 0; j < paths.Count; j++)
                    {
                        if (!SfxLibraryImporter.MatchesPrefix(Path.GetFileNameWithoutExtension(paths[j]), id)) continue;
                        AudioClip clip = AssetDatabase.LoadAssetAtPath<AudioClip>(paths[j]);
                        if (clip != null) clips.Add(clip);
                    }
                    entry.Clips = clips.ToArray();
                }
                int count = 0;
                if (entry.Clips != null)
                    for (int j = 0; j < entry.Clips.Length; j++)
                        if (entry.Clips[j] != null) count++;
                total += count;
                if (count == 0) Debug.LogWarning(Tag + " No clips for " + id + " in " + WorldClips + "; this layer will be silent.");
            }
            library.Rebuild();
            EditorUtility.SetDirty(library);
            return total;
        }

        private static Dictionary<string, object> Object(Dictionary<string, object> parent, string key)
        {
            object value;
            return parent != null && parent.TryGetValue(key, out value) ? value as Dictionary<string, object> : null;
        }

        private static List<object> Items(Dictionary<string, object> parent, string key)
        {
            object value;
            return parent != null && parent.TryGetValue(key, out value) && value is List<object>
                ? (List<object>)value : new List<object>();
        }

        private static string String(Dictionary<string, object> parent, string key)
        {
            object value;
            return parent != null && parent.TryGetValue(key, out value) ? value as string : null;
        }

        private static Vector2[] Polyline(Dictionary<string, object> parent, string key)
        {
            object value;
            return parent != null && parent.TryGetValue(key, out value) ? Polyline(value as List<object>) : Array.Empty<Vector2>();
        }

        private static Vector2[] Polyline(List<object> pairs)
        {
            if (pairs == null) return Array.Empty<Vector2>();
            List<Vector2> points = new List<Vector2>(pairs.Count);
            for (int i = 0; i < pairs.Count; i++)
            {
                Vector2 point;
                if (TryVector2(pairs[i], out point)) points.Add(point);
            }
            return points.ToArray();
        }

        private static bool TryVector2(Dictionary<string, object> parent, string key, out Vector2 vector)
        {
            object value;
            if (parent != null && parent.TryGetValue(key, out value)) return TryVector2(value, out vector);
            vector = Vector2.zero;
            return false;
        }

        private static bool TryVector2(object value, out Vector2 vector)
        {
            List<object> pair = value as List<object>;
            if (pair != null && pair.Count >= 2 && pair[0] is double && pair[1] is double)
            {
                vector = new Vector2((float)(double)pair[0], (float)(double)pair[1]);
                return true;
            }
            vector = Vector2.zero;
            return false;
        }
    }
}
