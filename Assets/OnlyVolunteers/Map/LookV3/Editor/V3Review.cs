using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // Review captures of the open Map_Look_v16 for Fedya: eye-level views (1.7 m) of the districts the brief names and a
    // top-down, rendered through the v3 pipeline asset (V3Capture).
    public static class V3Review
    {
        public const string Dir = "Working/Reviews/Map_v16_style_v3";

        public struct Pose
        {
            public string Name;
            public float X, Z, Eye, Tx, Tz, Th, Fov;
        }

        public static readonly Pose[] Poses =
        {
            new() { Name = "eye_01_downtown_square", X = 872f, Z = 378f, Eye = 1.7f, Tx = 828f, Tz = 452f, Th = 9f, Fov = 64f },
            new() { Name = "eye_02_rough_courtyard", X = 742f, Z = 548f, Eye = 1.7f, Tx = 724f, Tz = 590f, Th = 7f, Fov = 62f },
            new() { Name = "eye_03_hamlet_street", X = 288f, Z = 487f, Eye = 1.7f, Tx = 330f, Tz = 500f, Th = 2.5f, Fov = 60f },
            new() { Name = "eye_04_elite_hill", X = 1249f, Z = 338f, Eye = 1.7f, Tx = 1281f, Tz = 372f, Th = 3f, Fov = 64f },
            new() { Name = "eye_05_city_beach_water", X = 902f, Z = 116f, Eye = 2.2f, Tx = 862f, Tz = 52f, Th = 0f, Fov = 64f },
            new() { Name = "eye_06_canal", X = 868.2f, Z = 231f, Eye = 1.7f, Tx = 800f, Tz = 234f, Th = 0.3f, Fov = 60f },
            new() { Name = "eye_08_downtown_rooftops", X = 760f, Z = 300f, Eye = 38f, Tx = 860f, Tz = 420f, Th = 0f, Fov = 60f },
            new() { Name = "eye_09_village_pond", X = 166f, Z = 452f, Eye = 1.7f, Tx = 200f, Tz = 472f, Th = 0f, Fov = 62f },
            new() { Name = "eye_10_forest_lake", X = 262f, Z = 236f, Eye = 1.7f, Tx = 300f, Tz = 248f, Th = 0f, Fov = 62f },
            new() { Name = "eye_07_river_bridge", X = 414.8f, Z = 352f, Eye = 1.7f, Tx = 420f, Tz = 420f, Th = 0f, Fov = 60f },
        };

        public const string DirV17 = "Working/Reviews/Map_v17_A";

        // The van chase camera of the play scenes (VanCameraRig: 7.5 m back, 2.8 m up, looking at 1.2 m; FOV 70) behind a
        // Van.prefab placed on the road: two Downtown and two Rough District poses (van position, Unity yaw).
        public static readonly (string Name, float X, float Z, float Yaw)[] VanPoses =
        {
            ("van_01_downtown_boulevard", 757f, 346.3f, 90f),
            ("van_02_downtown_street", 790.8f, 439.5f, 180f),
            ("van_03_rough_drive_south", 684.5f, 552.6f, 90f),
            ("van_04_rough_drive_east", 826.4f, 600f, 0f),
        };
        private const string VanPrefab = "Assets/OnlyVolunteers/Vehicles/Van/Prefabs/Van.prefab";

        public static string ShootVan(string prefix, string folder, string revision, int width = 1920, int height = 1080)
        {
            var sampler = Object.FindAnyObjectByType<MapHeightSampler>();
            if (sampler == null) return "no MapHeightSampler in the open scene";
            string old = V3Capture.Revision;
            V3Capture.Revision = revision;
            var done = new List<string>();
            var prefab = UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(VanPrefab);
            try
            {
                foreach (var v in VanPoses)
                {
                    float y = sampler.Height(v.X, v.Z);
                    Quaternion rot = Quaternion.Euler(0f, v.Yaw, 0f);
                    var van = prefab != null ? (GameObject)UnityEditor.PrefabUtility.InstantiatePrefab(prefab) : null;
                    try
                    {
                        if (van != null) van.transform.SetPositionAndRotation(new Vector3(v.X, y + 0.05f, v.Z), rot);
                        Vector3 target = new Vector3(v.X, y, v.Z) + Vector3.up * 1.2f;
                        Vector3 eye = target + rot * new Vector3(0f, 2.8f - 1.2f, -7.5f);
                        done.Add(V3Capture.Shot(Path.Combine(folder, prefix + v.Name + ".png"), eye, target, 70f, width, height));
                    }
                    finally
                    {
                        if (van != null) Object.DestroyImmediate(van);
                    }
                }
            }
            finally
            {
                V3Capture.Revision = old;
            }
            return string.Join("\n", done);
        }

        public static string Shoot(string prefix, int width, int height, bool topDown, string folder, string revision)
        {
            string old = V3Capture.Revision;
            V3Capture.Revision = revision;
            try { return Shoot(prefix, width, height, topDown, folder); }
            finally { V3Capture.Revision = old; }
        }

        public static string Shoot(string prefix, int width, int height, bool topDown, string folder = null)
        {
            var sampler = Object.FindAnyObjectByType<MapHeightSampler>();
            if (sampler == null) return "no MapHeightSampler in the open scene";
            string dir = folder ?? Path.Combine(Path.GetFullPath(Path.Combine(Application.dataPath, "..")), Dir);
            var done = new List<string>();
            foreach (Pose p in Poses)
            {
                var eye = new Vector3(p.X, sampler.Height(p.X, p.Z) + p.Eye, p.Z);
                var target = new Vector3(p.Tx, sampler.Height(p.Tx, p.Tz) + p.Th, p.Tz);
                done.Add(V3Capture.Shot(Path.Combine(dir, prefix + p.Name + ".png"), eye, target, p.Fov, width, height));
            }
            if (topDown)
                done.Add(V3Capture.Shot(Path.Combine(dir, prefix + "top_down.png"), new Vector3(745f, 1200f, 400f), new Vector3(745f, 0f, 400.1f), 60f,
                    width, width * 1032 / 2000, true, 420f, false));
            return string.Join("\n", done);
        }
    }
}
