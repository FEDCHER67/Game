using System.Collections.Generic;
using OnlyVolunteers.Characters.Npc;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>The body bag as a RAGDOLL (Fedya 2026-10-18, replaces G35's "bag in hands" item): the corpse keeps its own
    /// NpcRagdoll (same bones, same colliders, same grab/carry physics) and the approved BODYBAG-ASTRA-001 v02 closed bag
    /// becomes a skinned wrapper on its trunk and leg bones. The character's own renderers are hidden. The bag mesh is
    /// densified once (its long faces cannot bend) and skinned by distance to the pelvis/chest/head/thigh/calf capsules
    /// while the body lies straight. In the bag the joints are stiff: the arms are locked to the trunk inside and the
    /// spine, hips, knees and neck bend only a little, so it reads as one heavy sack with no flailing limbs.</summary>
    public sealed class OperationBodyBagWrap : MonoBehaviour
    {
        /// <summary>Closed bag art (readable mesh) and its material; set from the scene (CaptureDirector).</summary>
        public static Mesh SourceMesh;
        public static Material SourceMaterial;
        public const float MaxEdge = 0.08f, WidthMetres = 0.62f, ThicknessMetres = 0.32f, LengthMargin = 0.14f;
        private static Mesh cachedSource;
        private static Vector3[] densePositions;
        private static Vector2[] denseUv;
        private static int[] denseTriangles;

        private NpcRagdoll ragdoll;
        private SkinnedMeshRenderer skin;
        private Mesh skinnedMesh;
        private readonly List<Renderer> hidden = new();
        public bool Applied => skin != null;
        public SkinnedMeshRenderer Skin => skin;

        public static bool ArtReady => SourceMesh != null && SourceMesh.isReadable;

        /// <summary>Wraps the ragdoll on 'root' (it must lie straight: NpcRagdoll.PlaceLying first). Idempotent.</summary>
        public static OperationBodyBagWrap Apply(NpcRagdoll ragdoll, bool stiffenJoints)
        {
            if (ragdoll == null || !ragdoll.Ready) return null;
            var wrap = ragdoll.GetComponent<OperationBodyBagWrap>();
            if (wrap == null) wrap = ragdoll.gameObject.AddComponent<OperationBodyBagWrap>();
            wrap.ragdoll = ragdoll;
            if (!wrap.Applied) wrap.Build();
            if (stiffenJoints) wrap.Stiffen();
            return wrap;
        }

        private void Build()
        {
            if (!ArtReady) { Debug.LogError("[BODYBAG] no readable closed-bag mesh: the bag cannot be shown"); return; }
            Densify();
            var profile = ragdoll.Profile;
            var bones = new List<int>();
            int pelvis = -1, head = -1;
            for (int i = 0; i < profile.Parts.Length; i++)
            {
                var kind = profile.Parts[i].Kind;
                if (kind == NpcRagdollProfile.Kind.UpperArm || kind == NpcRagdollProfile.Kind.ForeArm) continue;
                bones.Add(i);
                if (kind == NpcRagdollProfile.Kind.Pelvis) pelvis = i;
                if (kind == NpcRagdollProfile.Kind.Head) head = i;
            }
            if (pelvis < 0 || head < 0) return;
            // Bag frame: mesh Y along the body (head end +Y), mesh Z up from the bottom (z = 0), mesh X across.
            Vector3 hips = ragdoll.PartCenter(pelvis), headCentre = ragdoll.PartCenter(head);
            Vector3 along = headCentre - hips; along.y = 0f;
            along = along.sqrMagnitude > 1e-6f ? along.normalized : transform.forward;
            Vector3 up = Vector3.up, across = Vector3.Cross(along, up);
            ragdoll.LyingExtent(out float headward, out float footward);
            if (headward <= 0f) headward = 0.88f;
            if (footward <= 0f) footward = 0.87f;
            float lowest = float.MaxValue;
            foreach (var c in ragdoll.Colliders) if (c != null && c.enabled) lowest = Mathf.Min(lowest, c.bounds.min.y);
            if (lowest == float.MaxValue) lowest = hips.y - 0.14f;
            Bounds b = cachedSource.bounds;
            Vector3 scale = new Vector3(WidthMetres / Mathf.Max(0.01f, b.size.x * 0.75f),
                (headward + footward + LengthMargin) / Mathf.Max(0.01f, b.size.y), ThicknessMetres / Mathf.Max(0.01f, b.size.z));
            Vector3 centre = hips + along * ((headward - footward) * 0.5f); centre.y = lowest;
            var rotation = Quaternion.LookRotation(up, along); // local Z (mesh thickness) up, local Y (mesh length) along
            // LookRotation(forward=up, upwards=along) maps local Z -> up, local Y -> along, local X -> along x up (= across).
            Matrix4x4 meshToWorld = Matrix4x4.TRS(centre, rotation, scale) * Matrix4x4.Translate(new Vector3(-b.center.x, -b.center.y, -b.min.z));
            _ = across;

            var go = new GameObject("BodyBag (wrap)");
            go.transform.SetParent(transform, false);
            go.layer = gameObject.layer;
            Matrix4x4 worldToSkin = go.transform.worldToLocalMatrix;
            int n = densePositions.Length;
            var vertices = new Vector3[n];
            var weights = new BoneWeight[n];
            var segA = new Vector3[bones.Count]; var segB = new Vector3[bones.Count];
            for (int k = 0; k < bones.Count; k++) ragdoll.CapsuleSegment(bones[k], out segA[k], out segB[k], out _);
            var best = new float[4]; var bestIndex = new int[4];
            for (int v = 0; v < n; v++)
            {
                Vector3 world = meshToWorld.MultiplyPoint3x4(densePositions[v]);
                vertices[v] = worldToSkin.MultiplyPoint3x4(world);
                for (int s = 0; s < 4; s++) { best[s] = 0f; bestIndex[s] = 0; }
                for (int k = 0; k < bones.Count; k++)
                {
                    float d = OperationGeometry.DistanceToSegment(world, segA[k], segB[k]);
                    float w = 1f / Mathf.Pow(d * d + 0.0025f, 2f);
                    for (int s = 0; s < 4; s++)
                        if (w > best[s])
                        {
                            for (int t = 3; t > s; t--) { best[t] = best[t - 1]; bestIndex[t] = bestIndex[t - 1]; }
                            best[s] = w; bestIndex[s] = k; break;
                        }
                }
                float sum = best[0] + best[1] + best[2] + best[3];
                weights[v] = new BoneWeight
                {
                    boneIndex0 = bestIndex[0], weight0 = best[0] / sum, boneIndex1 = bestIndex[1], weight1 = best[1] / sum,
                    boneIndex2 = bestIndex[2], weight2 = best[2] / sum, boneIndex3 = bestIndex[3], weight3 = best[3] / sum,
                };
            }
            var boneTransforms = new Transform[bones.Count];
            var bindposes = new Matrix4x4[bones.Count];
            for (int k = 0; k < bones.Count; k++)
            {
                boneTransforms[k] = ragdoll.BoneOf(bones[k]);
                bindposes[k] = boneTransforms[k].worldToLocalMatrix * go.transform.localToWorldMatrix;
            }
            skinnedMesh = new Mesh { name = "BodyBag_Wrap_runtime" };
            if (n > 65000) skinnedMesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            skinnedMesh.vertices = vertices; skinnedMesh.uv = denseUv; skinnedMesh.triangles = denseTriangles;
            skinnedMesh.boneWeights = weights; skinnedMesh.bindposes = bindposes;
            skinnedMesh.RecalculateNormals(); skinnedMesh.RecalculateBounds();
            // Every character renderer goes, enabled or not yet (round 2: a body packed in the field is spawned this very
            // frame and its renderers are switched on by the network spawn afterwards: Fedya saw head and arms sticking out).
            foreach (var r in GetComponentsInChildren<Renderer>(true))
                if (r.gameObject != go) { r.enabled = false; hidden.Add(r); }
            skin = go.AddComponent<SkinnedMeshRenderer>();
            skin.sharedMesh = skinnedMesh; skin.bones = boneTransforms; skin.rootBone = ragdoll.BoneOf(pelvis);
            skin.sharedMaterial = SourceMaterial; skin.updateWhenOffscreen = true;
            skin.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
        }

        /// <summary>Stiff sack: arms locked inside, trunk/hips/knees/neck bend only a little.</summary>
        private void Stiffen()
        {
            var profile = ragdoll.Profile;
            for (int i = 0; i < profile.Parts.Length; i++)
            {
                var joint = ragdoll.JointOf(i);
                if (joint == null) continue;
                switch (profile.Parts[i].Kind)
                {
                    case NpcRagdollProfile.Kind.UpperArm:
                    case NpcRagdollProfile.Kind.ForeArm:
                        joint.angularXMotion = joint.angularYMotion = joint.angularZMotion = ConfigurableJointMotion.Locked; break;
                    case NpcRagdollProfile.Kind.Chest: Limit(joint, -8f, 14f, 6f); break;
                    case NpcRagdollProfile.Kind.Head: Limit(joint, -8f, 10f, 6f); break;
                    case NpcRagdollProfile.Kind.Thigh: Limit(joint, -5f, 16f, 4f); break;
                    case NpcRagdollProfile.Kind.Calf: Limit(joint, 0f, 14f, 3f); break;
                }
            }
        }

        private static void Limit(ConfigurableJoint joint, float low, float high, float side)
        {
            var l = joint.lowAngularXLimit; l.limit = Mathf.Max(l.limit, low); joint.lowAngularXLimit = l;
            var h = joint.highAngularXLimit; h.limit = Mathf.Min(h.limit, high); joint.highAngularXLimit = h;
            var y = joint.angularYLimit; y.limit = Mathf.Min(y.limit, side); joint.angularYLimit = y;
            var z = joint.angularZLimit; z.limit = Mathf.Min(z.limit, side); joint.angularZLimit = z;
        }

        private void OnDestroy() { if (skinnedMesh != null) Destroy(skinnedMesh); }

        /// <summary>The body inside stays hidden: anything that switches one of its renderers back on (a network spawn, an
        /// outfit or skin swap, a renderer added later) is undone before the frame is drawn.</summary>
        private void LateUpdate()
        {
            if (skin == null) return;
            if (Time.frameCount % 20 == 0)
                foreach (var r in GetComponentsInChildren<Renderer>(true))
                    if (r != skin && !hidden.Contains(r)) hidden.Add(r);
            foreach (var r in hidden) if (r != null && r.enabled) r.enabled = false;
        }

        /// <summary>Splits every source edge longer than MaxEdge (conforming: an edge is split for both its triangles),
        /// so the bag's long flat faces can bend along the body. Cached per source mesh.</summary>
        private static void Densify()
        {
            if (cachedSource == SourceMesh && densePositions != null) return;
            cachedSource = SourceMesh;
            var positions = new List<Vector3>(SourceMesh.vertices);
            var uv = new List<Vector2>(SourceMesh.uv.Length == positions.Count ? SourceMesh.uv : new Vector2[positions.Count]);
            var triangles = new List<int>(SourceMesh.triangles);
            for (int pass = 0; pass < 12; pass++)
            {
                var mid = new Dictionary<long, int>();
                int Mid(int a, int c)
                {
                    long key = a < c ? ((long)a << 32) | (uint)c : ((long)c << 32) | (uint)a;
                    if (mid.TryGetValue(key, out int m)) return m;
                    if ((positions[a] - positions[c]).magnitude <= MaxEdge) return -1;
                    m = positions.Count; positions.Add((positions[a] + positions[c]) * 0.5f); uv.Add((uv[a] + uv[c]) * 0.5f);
                    mid[key] = m; return m;
                }
                var next = new List<int>(triangles.Count * 2); bool split = false;
                for (int t = 0; t < triangles.Count; t += 3)
                {
                    int a = triangles[t], b = triangles[t + 1], c = triangles[t + 2];
                    int ab = Mid(a, b), bc = Mid(b, c), ca = Mid(c, a);
                    int count = (ab >= 0 ? 1 : 0) + (bc >= 0 ? 1 : 0) + (ca >= 0 ? 1 : 0);
                    if (count == 0) { next.Add(a); next.Add(b); next.Add(c); continue; }
                    split = true;
                    if (count == 3) { Add(next, a, ab, ca); Add(next, ab, b, bc); Add(next, ca, bc, c); Add(next, ab, bc, ca); continue; }
                    // Rotate so the split edges come first in a fixed order, then fan.
                    if (count == 1)
                    {
                        if (ab >= 0) { Add(next, a, ab, c); Add(next, ab, b, c); }
                        else if (bc >= 0) { Add(next, a, b, bc); Add(next, a, bc, c); }
                        else { Add(next, a, b, ca); Add(next, ca, b, c); }
                        continue;
                    }
                    if (ab < 0) { Add(next, a, b, bc); Add(next, a, bc, ca); Add(next, ca, bc, c); }
                    else if (bc < 0) { Add(next, a, ab, ca); Add(next, ab, b, ca); Add(next, ca, b, c); }
                    else { Add(next, a, ab, c); Add(next, ab, bc, c); Add(next, ab, b, bc); }
                }
                triangles = next;
                if (!split) break;
            }
            densePositions = positions.ToArray(); denseUv = uv.ToArray(); denseTriangles = triangles.ToArray();
        }
        private static void Add(List<int> list, int a, int b, int c) { list.Add(a); list.Add(b); list.Add(c); }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() { SourceMesh = null; SourceMaterial = null; cachedSource = null; densePositions = null; denseUv = null; denseTriangles = null; }
    }
}
