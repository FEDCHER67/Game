using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.EditorTools
{
    /// <summary>
    /// v03: left/right mirror of the patient's escape clips (Generic rig Buddy_Rig_Mixamo65, 65 bones).
    /// Op_EscapeFall_v01 leaves the gurney over the patient's LEFT side (table +X). Since v03 the instrument stand and
    /// the opened torso strap sit on that side, so the escape must leave over the RIGHT side (table -X, the table camera's
    /// side). Op_KnockedOut_v01 is mirrored with it, because its first pose continues the fall's last pose across the
    /// KnockedOut root offset (validation_op_v01.json cross_contracts).
    ///
    /// Method: sample the source at 60 Hz, take every bone in model space, reflect across the model's YZ plane (x -> -x)
    /// and swap Left/Right bones, with a per-bone rest correction so the result stays a proper rotation in each bone's
    /// own axes: R'(b) = mirror(R(b')) * mirror(Rrest(b'))^-1 * Rrest(b), P'(b) = reflect(P(b')). Then back to local.
    /// The source FBX files are not touched; new .anim assets are written next to them and never overwritten.
    /// </summary>
    public static class OperationClipMirrorV03
    {
        public const string AnimDir = "Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/Animations/";
        public const string PatientModel = "Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/SAUSAGE_BUDDY_PATIENT_v01.fbx";
        public static readonly string[,] Pairs =
        {
            { "Op_EscapeFall_v01", "Op_EscapeFall_Mirror_v01" },
            { "Op_KnockedOut_v01", "Op_KnockedOut_Mirror_v01" },
        };
        private const float SampleRate = 60f;

        [MenuItem("OnlyVolunteers/Operation/Mirror patient escape clips (v03)")]
        public static void MirrorMenu() => Debug.Log(MirrorAll());

        public static string MirrorAll()
        {
            var report = new List<string>();
            for (int i = 0; i < Pairs.GetLength(0); i++) report.Add(Mirror(Pairs[i, 0], Pairs[i, 1]));
            AssetDatabase.SaveAssets();
            return string.Join("\n", report);
        }

        public static AnimationClip SourceClip(string fbxName)
        {
            foreach (var o in AssetDatabase.LoadAllAssetsAtPath(AnimDir + fbxName + ".fbx"))
                if (o is AnimationClip c && !c.name.StartsWith("__preview")) return c;
            return null;
        }

        private static string Partner(string path) =>
            string.Join("/", path.Split('/').Select(s => s.Contains("Left") ? s.Replace("Left", "Right") : s.Contains("Right") ? s.Replace("Right", "Left") : s));
        private static Quaternion MirrorQ(Quaternion q) => new Quaternion(q.x, -q.y, -q.z, q.w);
        private static Vector3 MirrorP(Vector3 p) => new Vector3(-p.x, p.y, p.z);

        public static string Mirror(string sourceFbx, string outName)
        {
            string outPath = AnimDir + outName + ".anim";
            if (File.Exists(outPath)) return "exists (not overwritten): " + outPath;
            var src = SourceClip(sourceFbx);
            if (src == null) return "missing source " + sourceFbx;
            var modelAsset = AssetDatabase.LoadAssetAtPath<GameObject>(PatientModel);
            var go = Object.Instantiate(modelAsset);
            go.hideFlags = HideFlags.HideAndDontSave;
            try
            {
                var root = go.transform;
                root.SetPositionAndRotation(Vector3.zero, Quaternion.identity); root.localScale = Vector3.one;
                var paths = AnimationUtility.GetCurveBindings(src).Where(b => b.type == typeof(Transform)).Select(b => b.path).Distinct().ToList();
                var bones = new Dictionary<string, Transform>();
                foreach (var p in paths) { var t = root.Find(p); if (t == null) return "cannot bind " + p; bones[p] = t; }
                // hierarchy order (parents first)
                paths.Sort((a, b) => a.Count(ch => ch == '/').CompareTo(b.Count(ch => ch == '/')));
                foreach (var p in paths) if (!bones.ContainsKey(Partner(p))) return "no partner for " + p;

                // rest (bind) pose in model space, and its symmetry error
                var restR = new Dictionary<string, Quaternion>(); var restP = new Dictionary<string, Vector3>();
                foreach (var p in paths) { restR[p] = Quaternion.Inverse(root.rotation) * bones[p].rotation; restP[p] = root.InverseTransformPoint(bones[p].position); }
                float symErr = 0f;
                foreach (var p in paths) symErr = Mathf.Max(symErr, (MirrorP(restP[Partner(p)]) - restP[p]).magnitude);
                var correction = new Dictionary<string, Quaternion>();
                foreach (var p in paths) correction[p] = Quaternion.Inverse(MirrorQ(restR[Partner(p)])) * restR[p];

                int frames = Mathf.RoundToInt(src.length * SampleRate);
                var curves = new Dictionary<string, AnimationCurve[]>();
                foreach (var p in paths) { var c = new AnimationCurve[7]; for (int k = 0; k < 7; k++) c[k] = new AnimationCurve(); curves[p] = c; }
                var lastQ = new Dictionary<string, Quaternion>();
                var modelR = new Dictionary<string, Quaternion>(); var modelP = new Dictionary<string, Vector3>();
                var outR = new Dictionary<string, Quaternion>(); var outP = new Dictionary<string, Vector3>();
                for (int f = 0; f <= frames; f++)
                {
                    float t = Mathf.Min(src.length, f / SampleRate);
                    src.SampleAnimation(go, t);
                    foreach (var p in paths) { modelR[p] = Quaternion.Inverse(root.rotation) * bones[p].rotation; modelP[p] = root.InverseTransformPoint(bones[p].position); }
                    foreach (var p in paths)
                    {
                        string q = Partner(p);
                        outR[p] = MirrorQ(modelR[q]) * correction[p];
                        outP[p] = MirrorP(modelP[q]);
                    }
                    foreach (var p in paths)
                    {
                        int cut = p.LastIndexOf('/');
                        string parent = cut > 0 ? p.Substring(0, cut) : null;
                        Quaternion pr; Vector3 pp;
                        if (parent != null && outR.ContainsKey(parent)) { pr = outR[parent]; pp = outP[parent]; }
                        else
                        {
                            // top of the animated chain: its parent inside the model is not animated
                            var par = bones[p].parent;
                            pr = Quaternion.Inverse(root.rotation) * par.rotation; pp = root.InverseTransformPoint(par.position);
                        }
                        Vector3 ps = bones[p].parent.lossyScale; // uniform; constant (scale curves are constant 1)
                        Quaternion lr = Quaternion.Inverse(pr) * outR[p];
                        Vector3 lp = Quaternion.Inverse(pr) * (outP[p] - pp);
                        lp = new Vector3(lp.x / ps.x, lp.y / ps.y, lp.z / ps.z);
                        if (lastQ.TryGetValue(p, out var prev) && Quaternion.Dot(prev, lr) < 0f) lr = new Quaternion(-lr.x, -lr.y, -lr.z, -lr.w);
                        lastQ[p] = lr;
                        var c = curves[p];
                        c[0].AddKey(t, lp.x); c[1].AddKey(t, lp.y); c[2].AddKey(t, lp.z);
                        c[3].AddKey(t, lr.x); c[4].AddKey(t, lr.y); c[5].AddKey(t, lr.z); c[6].AddKey(t, lr.w);
                    }
                }
                var clip = new AnimationClip { name = outName, frameRate = SampleRate };
                string[] props = { "m_LocalPosition.x", "m_LocalPosition.y", "m_LocalPosition.z", "m_LocalRotation.x", "m_LocalRotation.y", "m_LocalRotation.z", "m_LocalRotation.w" };
                foreach (var p in paths)
                    for (int k = 0; k < 7; k++)
                    {
                        var curve = curves[p][k];
                        for (int i = 0; i < curve.length; i++) { AnimationUtility.SetKeyLeftTangentMode(curve, i, AnimationUtility.TangentMode.Linear); AnimationUtility.SetKeyRightTangentMode(curve, i, AnimationUtility.TangentMode.Linear); }
                        clip.SetCurve(p, typeof(Transform), props[k], curve);
                    }
                // Scale curves (constant in these clips) are copied from the partner bone.
                foreach (var b in AnimationUtility.GetCurveBindings(src))
                {
                    if (b.type != typeof(Transform) || !b.propertyName.StartsWith("m_LocalScale")) continue;
                    var partner = new EditorCurveBinding { path = Partner(b.path), type = b.type, propertyName = b.propertyName };
                    var curve = AnimationUtility.GetEditorCurve(src, partner) ?? AnimationUtility.GetEditorCurve(src, b);
                    clip.SetCurve(b.path, typeof(Transform), b.propertyName, curve);
                }
                clip.EnsureQuaternionContinuity();
                var settings = AnimationUtility.GetAnimationClipSettings(src);
                AnimationUtility.SetAnimationClipSettings(clip, settings);
                AssetDatabase.CreateAsset(clip, outPath);
                return $"{outPath}: {paths.Count} bones, {frames + 1} samples @ {SampleRate} Hz, loop={settings.loopTime}, rest symmetry error {symErr * 1000f:F3} mm";
            }
            finally { Object.DestroyImmediate(go); }
        }
    }
}
