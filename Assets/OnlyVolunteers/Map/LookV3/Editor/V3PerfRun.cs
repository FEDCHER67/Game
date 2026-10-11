using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.Map.Look.V3
{
    // Same-spot render profile of a play scene (v16 vs v17, phase A brief): enters Play mode in the given scene, takes over
    // the view with a probe camera (eye 1.7 m, FOV 60, the scene's far clip, post on) at three fixed spots, warms up 2 s and
    // averages 4 s with V3PerfProbe at each, writes Working/Reviews/Map_v17_A/perf_<label>.txt and leaves Play mode.
    // Application.runInBackground is set only for the run and restored afterwards (PlayerSettings are never touched).
    // The state survives the domain reload of entering Play mode (SessionState + InitializeOnLoad).
    [InitializeOnLoad]
    public static class V3PerfRun
    {
        private const string Key = "OnlyVolunteers.V3PerfRun.";
        public static readonly (string Name, float X, float Z, float Yaw)[] Spots =
        {
            ("downtown_plaza", 872f, 378f, 330f),
            ("downtown_street", 790.8f, 452f, 180f),
            ("rough_yard", 742f, 548f, 345f),
        };

        static V3PerfRun()
        {
            if (SessionState.GetBool(Key + "active", false)) EditorApplication.update += Tick;
        }

        public static string Start(string scenePath, string label)
        {
            if (EditorApplication.isPlaying) return "already playing";
            EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Single);
            SessionState.SetBool(Key + "active", true);
            SessionState.SetString(Key + "label", label);
            SessionState.SetInt(Key + "spot", -1);
            SessionState.SetFloat(Key + "t", 0f);
            SessionState.SetString(Key + "out", "");
            SessionState.SetBool(Key + "rib_set", false);
            EditorApplication.update -= Tick;
            EditorApplication.update += Tick;
            EditorApplication.isPlaying = true;
            return "started " + label;
        }

        public static string Status() => SessionState.GetBool(Key + "active", false) ? "running spot " + SessionState.GetInt(Key + "spot", -1) : "idle; last: " + SessionState.GetString(Key + "out", "");

        private static Camera probeCam;

        private static void Tick()
        {
            if (!SessionState.GetBool(Key + "active", false))
            {
                EditorApplication.update -= Tick;
                return;
            }
            if (!EditorApplication.isPlaying) return;
            if (!SessionState.GetBool(Key + "rib_set", false))
            {
                SessionState.SetBool(Key + "rib_old", Application.runInBackground);
                Application.runInBackground = true;
                SessionState.SetBool(Key + "rib_set", true);
                SessionState.SetFloat(Key + "t", (float)EditorApplication.timeSinceStartup + 5f);
                return;
            }
            float now = (float)EditorApplication.timeSinceStartup;
            int spot = SessionState.GetInt(Key + "spot", -1);
            float t = SessionState.GetFloat(Key + "t", 0f);
            if (probeCam == null)
            {
                Camera main = Camera.main;
                var go = new GameObject("V3_PerfProbeCamera");
                probeCam = go.AddComponent<Camera>();
                probeCam.fieldOfView = 60f;
                probeCam.nearClipPlane = 0.1f;
                probeCam.farClipPlane = main != null ? main.farClipPlane : 460f;
                probeCam.depth = 100f;
                var data = go.AddComponent<UniversalAdditionalCameraData>();
                data.renderPostProcessing = true;
                data.requiresDepthOption = CameraOverrideOption.On;
                data.requiresColorOption = CameraOverrideOption.On;
                go.AddComponent<V3PerfProbe>();
            }
            foreach (Camera c in Camera.allCameras)
                if (c != probeCam) c.enabled = false;
            if (now < t) return;
            var probe = probeCam.GetComponent<V3PerfProbe>();
            string label = SessionState.GetString(Key + "label", "run");
            int phase = SessionState.GetInt(Key + "phase", 0);
            if (spot >= 0 && phase == 1)
            {
                string line = probe.Report($"{label} {Spots[spot].Name}");
                SessionState.SetString(Key + "out", SessionState.GetString(Key + "out", "") + line + "\n");
            }
            if (phase == 0 && spot >= 0)
            {
                probe.ResetStats();
                SessionState.SetInt(Key + "phase", 1);
                SessionState.SetFloat(Key + "t", now + 4f);
                return;
            }
            spot++;
            if (spot >= Spots.Length)
            {
                string text = SessionState.GetString(Key + "out", "");
                string dir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", V3Sightlines.Dir));
                Directory.CreateDirectory(dir);
                File.WriteAllText(Path.Combine(dir, $"perf_{label}.txt"), text);
                Debug.Log("[V3PerfRun]\n" + text);
                Application.runInBackground = SessionState.GetBool(Key + "rib_old", false);
                SessionState.SetBool(Key + "active", false);
                SessionState.SetInt(Key + "phase", 0);
                probeCam = null;
                EditorApplication.update -= Tick;
                EditorApplication.isPlaying = false;
                return;
            }
            var s = Spots[spot];
            var sampler = Object.FindAnyObjectByType<MapHeightSampler>();
            float y = sampler != null ? sampler.Height(s.X, s.Z) : 0f;
            probeCam.transform.SetPositionAndRotation(new Vector3(s.X, y + 1.7f, s.Z), Quaternion.Euler(4f, s.Yaw, 0f));
            SessionState.SetInt(Key + "spot", spot);
            SessionState.SetInt(Key + "phase", 0);
            SessionState.SetFloat(Key + "t", now + 2f);
        }
    }
}
