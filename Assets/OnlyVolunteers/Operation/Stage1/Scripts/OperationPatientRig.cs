using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Patient presentation and hit geometry on the approved PATIENT model (never modified): trigger colliders
    /// on the bones for the table cursor (head, neck, torso, shoulders, arms, legs), the face blend shapes, the
    /// animator contract (int OpState, trigger ShockDeath) and a small procedural layer for struggling limbs.</summary>
    public sealed class OperationPatientRig : MonoBehaviour
    {
        public const int StateTableAwake = 0, StateTableAsleep = 1, StateStruggle = 2, StatePanic = 3, StateDead = 4, StateEscapeFall = 5, StateKnockedOut = 6;
        private static readonly int OpStateId = Animator.StringToHash("OpState");
        private static readonly int ShockDeathId = Animator.StringToHash("ShockDeath");

        [SerializeField] private Animator animator;
        [SerializeField] private SkinnedMeshRenderer face;
        [SerializeField] private Collider physicsCollider;

        private readonly Dictionary<BodyPart, List<Collider>> parts = new();
        private Transform hips, spine, spine2, neck, head, headTop, armL, armR, foreL, foreR, handL, handR, upLegL, upLegR, legL, legR, footL, footR;
        private int blink = -1, blinkL = -1, blinkR = -1, worried = -1, surprised = -1, happy = -1;
        private float wBlink, wBlinkL, wBlinkR, wWorried, wSurprised, wHappy;
        private float tBlink, tBlinkL, tBlinkR, tWorried, tSurprised, tHappy;
        private int opState = -1;
        private bool built;

        /// <summary>0..1 flailing of unrestrained limbs (index: L arm, R arm, L leg, R leg, torso).</summary>
        public readonly float[] LimbMotion = new float[5];
        public float Twitch;
        public float HeadShake;
        public Transform Head => head;
        public Transform HeadTop => headTop != null ? headTop : head;
        public Animator Animator => animator;

        private void Awake() => Build();

        private Transform Bone(string name)
        {
            foreach (var t in GetComponentsInChildren<Transform>(true)) if (t.name == "mixamorig:" + name) return t;
            return null;
        }

        public void Build()
        {
            if (built) return;
            built = true;
            if (animator == null) animator = GetComponentInChildren<Animator>(true);
            if (face == null) foreach (var smr in GetComponentsInChildren<SkinnedMeshRenderer>(true)) if (smr.name == "Face") face = smr;
            if (face != null && face.sharedMesh != null)
            {
                var m = face.sharedMesh;
                blink = m.GetBlendShapeIndex("Blink"); blinkL = m.GetBlendShapeIndex("Blink_L"); blinkR = m.GetBlendShapeIndex("Blink_R");
                worried = m.GetBlendShapeIndex("Worried"); surprised = m.GetBlendShapeIndex("Surprised"); happy = m.GetBlendShapeIndex("Happy");
            }
            hips = Bone("Hips"); spine = Bone("Spine"); spine2 = Bone("Spine2"); neck = Bone("Neck"); head = Bone("Head"); headTop = Bone("HeadTop_End");
            armL = Bone("LeftArm"); armR = Bone("RightArm"); foreL = Bone("LeftForeArm"); foreR = Bone("RightForeArm"); handL = Bone("LeftHand"); handR = Bone("RightHand");
            upLegL = Bone("LeftUpLeg"); upLegR = Bone("RightUpLeg"); legL = Bone("LeftLeg"); legR = Bone("RightLeg"); footL = Bone("LeftFoot"); footR = Bone("RightFoot");
            if (hips == null || head == null) return;
            // Built in the prefab's bind pose (Awake runs before the first animator update).
            Sphere(BodyPart.Head, head, head.position + (HeadTop.position - head.position) * 0.3f, 0.135f);
            Capsule(BodyPart.Neck, neck, neck.position, head.position, 0.065f);
            Capsule(BodyPart.Torso, hips, hips.position - (spine2.position - hips.position) * 0.15f, spine2.position + (spine2.position - hips.position).normalized * 0.06f, 0.12f);
            Sphere(BodyPart.ShoulderL, armL, armL.position, 0.068f);
            Sphere(BodyPart.ShoulderR, armR, armR.position, 0.068f);
            Capsule(BodyPart.ArmL, armL, armL.position, foreL.position, 0.056f);
            Capsule(BodyPart.ArmL, foreL, foreL.position, handL.position, 0.052f);
            Sphere(BodyPart.ArmL, handL, handL.position + (handL.position - foreL.position).normalized * 0.05f, 0.06f);
            Capsule(BodyPart.ArmR, armR, armR.position, foreR.position, 0.056f);
            Capsule(BodyPart.ArmR, foreR, foreR.position, handR.position, 0.052f);
            Sphere(BodyPart.ArmR, handR, handR.position + (handR.position - foreR.position).normalized * 0.05f, 0.06f);
            if (upLegL != null && legL != null) Capsule(BodyPart.LegL, upLegL, upLegL.position, legL.position, 0.08f);
            if (legL != null && footL != null) Capsule(BodyPart.LegL, legL, legL.position, footL.position, 0.065f);
            if (upLegR != null && legR != null) Capsule(BodyPart.LegR, upLegR, upLegR.position, legR.position, 0.08f);
            if (legR != null && footR != null) Capsule(BodyPart.LegR, legR, legR.position, footR.position, 0.065f);
            if (animator != null) { animator.cullingMode = AnimatorCullingMode.AlwaysAnimate; animator.applyRootMotion = false; }
        }

        private GameObject PartObject(BodyPart part, Transform bone, Vector3 center, Quaternion rotation)
        {
            var go = new GameObject("Hit_" + part);
            go.transform.SetPositionAndRotation(center, rotation);
            go.transform.SetParent(bone, true);
            var tag = go.AddComponent<OperationTargetTag>();
            tag.kind = TargetKind.Body; tag.index = (int)part;
            return go;
        }
        private void Sphere(BodyPart part, Transform bone, Vector3 center, float radius)
        {
            if (bone == null) return;
            var go = PartObject(part, bone, center, Quaternion.identity);
            var c = go.AddComponent<SphereCollider>(); c.isTrigger = true; c.radius = radius / Mathf.Max(0.0001f, go.transform.lossyScale.x);
            Add(part, c);
        }
        private void Capsule(BodyPart part, Transform bone, Vector3 a, Vector3 b, float radius)
        {
            if (bone == null) return;
            Vector3 d = b - a;
            var go = PartObject(part, bone, (a + b) * 0.5f, Quaternion.FromToRotation(Vector3.up, d.sqrMagnitude > 1e-8f ? d.normalized : Vector3.up));
            float s = Mathf.Max(0.0001f, go.transform.lossyScale.x);
            var c = go.AddComponent<CapsuleCollider>(); c.isTrigger = true; c.direction = 1;
            c.radius = radius / s; c.height = (d.magnitude + radius * 2f) / s;
            Add(part, c);
        }
        private void Add(BodyPart part, Collider c)
        {
            if (!parts.TryGetValue(part, out var list)) parts[part] = list = new List<Collider>();
            list.Add(c);
        }

        /// <summary>Metres from a world point to the surface of a body part (0 inside). Server-side validation.</summary>
        public float DistanceToPart(BodyPart part, Vector3 world)
        {
            if (!parts.TryGetValue(part, out var list)) return 0f;
            float best = float.PositiveInfinity;
            foreach (var c in list)
            {
                if (c == null) continue;
                bool was = c.enabled; c.enabled = true;
                best = Mathf.Min(best, Vector3.Distance(c.ClosestPoint(world), world));
                c.enabled = was;
            }
            return best;
        }
        public Vector3 PartCenter(BodyPart part)
        {
            if (!parts.TryGetValue(part, out var list) || list.Count == 0) return transform.position;
            return list[0].bounds.center;
        }
        public IReadOnlyList<Collider> PartColliders(BodyPart part) => parts.TryGetValue(part, out var list) ? list : null;

        public void SetPhysicsCollider(bool enabled)
        {
            if (physicsCollider == null) physicsCollider = GetComponent<Collider>();
            if (physicsCollider != null) physicsCollider.enabled = enabled;
        }

        public void SetOpState(int state)
        {
            if (animator == null || animator.runtimeAnimatorController == null || state == opState) return;
            opState = state;
            animator.SetInteger(OpStateId, state);
        }
        public void ShockDeath() { if (animator != null && animator.runtimeAnimatorController != null) animator.SetTrigger(ShockDeathId); }

        /// <summary>Target face weights 0..100; blended smoothly each frame.</summary>
        public void Face(float blinkBoth, float worriedW, float surprisedW, float happyW, float blinkLeft = 0f, float blinkRight = 0f)
        {
            tBlink = blinkBoth; tWorried = worriedW; tSurprised = surprisedW; tHappy = happyW; tBlinkL = blinkLeft; tBlinkR = blinkRight;
        }

        private void LateUpdate()
        {
            float k = 1f - Mathf.Exp(-12f * Time.deltaTime);
            wBlink = Mathf.Lerp(wBlink, tBlink, k); wBlinkL = Mathf.Lerp(wBlinkL, tBlinkL, k); wBlinkR = Mathf.Lerp(wBlinkR, tBlinkR, k);
            wWorried = Mathf.Lerp(wWorried, tWorried, k); wSurprised = Mathf.Lerp(wSurprised, tSurprised, k); wHappy = Mathf.Lerp(wHappy, tHappy, k);
            if (face != null)
            {
                if (blink >= 0) face.SetBlendShapeWeight(blink, wBlink);
                if (blinkL >= 0) face.SetBlendShapeWeight(blinkL, wBlinkL);
                if (blinkR >= 0) face.SetBlendShapeWeight(blinkR, wBlinkR);
                if (worried >= 0) face.SetBlendShapeWeight(worried, wWorried);
                if (surprised >= 0) face.SetBlendShapeWeight(surprised, wSurprised);
                if (happy >= 0) face.SetBlendShapeWeight(happy, wHappy);
            }
            float time = Time.time;
            Vector3 up = transform.up, along = transform.forward;
            Swing(armL, LimbMotion[0], up, along, 22f, time * 7.1f, 0f);
            Swing(armR, LimbMotion[1], up, along, 22f, time * 6.6f, 1.7f);
            Swing(upLegL, LimbMotion[2], up, along, 12f, time * 5.3f, 0.6f);
            Swing(upLegR, LimbMotion[3], up, along, 12f, time * 5.9f, 2.4f);
            if (spine != null && (LimbMotion[4] > 0f || Twitch > 0f))
            {
                float a = Mathf.Sin(time * 4.3f) * 5f * LimbMotion[4] + (Mathf.PerlinNoise(time * 9f, 0.3f) - 0.5f) * 14f * Twitch;
                spine.rotation = Quaternion.AngleAxis(a, along) * spine.rotation;
            }
            if (head != null && HeadShake > 0f)
                head.rotation = Quaternion.AngleAxis(Mathf.Sin(time * 13f) * 18f * HeadShake, along) * head.rotation;
        }
        private static void Swing(Transform bone, float amount, Vector3 up, Vector3 along, float degrees, float phase, float offset)
        {
            if (bone == null || amount <= 0.001f) return;
            float a = Mathf.Sin(phase + offset) * degrees * amount;
            float lift = (Mathf.Sin(phase * 0.7f + offset) * 0.5f + 0.5f) * degrees * 0.6f * amount;
            bone.rotation = Quaternion.AngleAxis(a, up) * Quaternion.AngleAxis(lift, along) * bone.rotation;
        }
    }
}
