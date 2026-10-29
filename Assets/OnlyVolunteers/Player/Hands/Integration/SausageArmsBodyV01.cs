using System.Collections.Generic;
using OnlyVolunteers.Characters.Player;
using OnlyVolunteers.Session;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>
    /// One instance of the player sausage (PLAYER_SAUSAGE_W86_v01) used by the hands, in one of three roles:
    /// <list type="bullet">
    /// <item>FirstPerson: the local player's own arms in front of the camera. No Animator (bind pose + IK every frame), no
    /// LODs; only the hands, the bare-arm regions and the chosen top (whose sleeves are what shows; its torso stays below the
    /// view) are drawn, without shadows. Head, face, hair, hat, legs: never drawn, so the camera is never inside a head.</item>
    /// <item>ThirdPersonShadow: the local player's full body for his shadow only (ShadowsOnly), same arm IK.</item>
    /// <item>ThirdPersonVisible: how friends see a player: the full dressed sausage, walk/idle clips, the arm IK on top.</item>
    /// </list>
    /// Dressed by its own PlayerSausageAvatarV01 (skin tone, chosen top and its colours). No colliders, no rigidbodies:
    /// nothing here can ever touch physics or push anyone.
    /// </summary>
    public sealed class SausageArmsBodyV01
    {
        public enum Kind { FirstPerson, ThirdPersonShadow, ThirdPersonVisible }

        public readonly GameObject GameObject;
        public readonly Transform Transform;
        public readonly Kind Mode;
        public readonly PlayerSausageAvatarV01 Avatar;
        public readonly StretchArmRigV01 Rig;
        public readonly Animator Animator;
        public readonly ArmChannelV01[] Channels = { new ArmChannelV01(), new ArmChannelV01() };
        /// <summary>Middle of the two shoulder joints in the unscaled root space (first-person placement).</summary>
        public readonly Vector3 ShoulderMid;
        public readonly float[] StretchShown = { 1f, 1f };
        public readonly Quaternion[] HandShown = { Quaternion.identity, Quaternion.identity };
        public readonly bool[] HandShownSet = new bool[2];
        /// <summary>Punch (Q): the cue being played on this body (-1 none) and where the swinging wrist was when it began
        /// (this body's local space; first person: the anchor's).</summary>
        public int PunchKey = -1;
        public Vector3 PunchFrom;
        /// <summary>First person: both arms are parked out of the view (snapped there while not drawn).</summary>
        public bool Parked;

        private readonly List<Renderer> drawn = new List<Renderer>();
        private bool visible = true;
        private string playing;
        private Vector3 lastFeet;
        private bool hasFeet;
        private float speed;
        private bool nodSet;
        private Quaternion nodBase, nodWritten;

        /// <summary>FP: the renderers drawn (hands, arms, top).</summary>
        public IReadOnlyList<Renderer> Drawn => drawn;

        private SausageArmsBodyV01(GameObject go, Kind kind, StretchArmRigV01 rig)
        {
            GameObject = go; Transform = go.transform; Mode = kind; Rig = rig;
            Avatar = go.GetComponent<PlayerSausageAvatarV01>();
            Animator = go.GetComponent<Animator>();
            ShoulderMid = Transform.InverseTransformPoint((rig.ShoulderPosition(StretchArmRigV01.Side.Right) +
                                                           rig.ShoulderPosition(StretchArmRigV01.Side.Left)) * 0.5f);
            ShoulderMid = Vector3.Scale(ShoulderMid, Transform.localScale);
        }

        public static SausageArmsBodyV01 Create(GameObject prefab, Transform parent, Kind kind, string name, int layer, bool matte = true)
        {
            if (prefab == null) return null;
            var go = Object.Instantiate(prefab, parent, false);
            go.name = name;
            go.transform.localPosition = Vector3.zero;
            go.transform.localRotation = Quaternion.identity;
            go.transform.localScale = Vector3.one;
            // Presentation only: strip anything physical a future prefab revision might carry.
            foreach (var c in go.GetComponentsInChildren<Collider>(true)) Object.Destroy(c);
            foreach (var r in go.GetComponentsInChildren<Rigidbody>(true)) Object.Destroy(r);
            foreach (var t in go.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = layer;
            if (matte) SausageMatteV01.Apply(go); // Fedya 30.10: no shine on the player's skin or clothes
            var rig = StretchArmRigV01.Bind(go.transform);
            if (rig == null)
            {
                Debug.LogWarning("[OV Hands] the body prefab has no Mixamo arms (mixamorig:RightArm/ForeArm/Hand): hands off", prefab);
                Object.Destroy(go);
                return null;
            }
            var body = new SausageArmsBodyV01(go, kind, rig);
            // v02 cuffs: every top's sleeve rim rides the forearm, not the bending hand (no twisted, spiky cuffs).
            foreach (var smr in go.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                if (smr.name.StartsWith("Top_")) rig.BindCuffs(smr);
            body.Setup();
            return body;
        }

        private void Setup()
        {
            if (Mode == Kind.FirstPerson)
            {
                if (Animator != null) Animator.enabled = false;
                var lod = GameObject.GetComponent<LODGroup>();
                if (lod != null) Object.Destroy(lod);
                foreach (var r in GameObject.GetComponentsInChildren<Renderer>(true))
                {
                    bool arm = IsFirstPersonPart(r.name);
                    r.enabled = arm;
                    r.shadowCastingMode = ShadowCastingMode.Off;
                    r.receiveShadows = true;
                    r.lightProbeUsage = LightProbeUsage.BlendProbes;
                    if (r is SkinnedMeshRenderer smr)
                    {
                        smr.updateWhenOffscreen = arm; // the arms reach far out of the body's box
                        // v02: a top's torso never shows in first person (the viewmodel sits lower and farther since
                        // 30.10): its torso bones collapse into the shoulders, only the sleeves are drawn.
                        if (arm && r.name.StartsWith("Top_"))
                            SleevesOnlyV01.Apply(smr, Rig.RigRoot,
                                (Rig.ShoulderPosition(StretchArmRigV01.Side.Right) + Rig.ShoulderPosition(StretchArmRigV01.Side.Left)) * 0.5f);
                    }
                    if (arm) drawn.Add(r);
                }
                return;
            }
            if (Animator != null)
            {
                Animator.applyRootMotion = false;
                Animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
            }
            foreach (var r in GameObject.GetComponentsInChildren<Renderer>(true))
            {
                r.shadowCastingMode = Mode == Kind.ThirdPersonShadow ? ShadowCastingMode.ShadowsOnly : ShadowCastingMode.On;
                if (r is SkinnedMeshRenderer smr && smr.rootBone != null)
                {
                    // A stretched arm reaches metres out of the import box: a fixed box around the hips that holds it.
                    float unit = Mathf.Max(1e-6f, Mathf.Abs(smr.rootBone.lossyScale.x));
                    smr.localBounds = new Bounds(Vector3.zero, Vector3.one * (7f / unit));
                }
                drawn.Add(r);
            }
        }

        /// <summary>Hands, bare-arm regions and the tops (sleeves), LOD0 only.</summary>
        public static bool IsFirstPersonPart(string rendererName)
        {
            if (string.IsNullOrEmpty(rendererName) || !rendererName.EndsWith("_LOD0")) return false;
            return rendererName.StartsWith("Body_Hands") || rendererName.StartsWith("Body_ArmUpper") ||
                   rendererName.StartsWith("Body_ArmMid") || rendererName.StartsWith("Body_ArmLower") ||
                   rendererName.StartsWith("Top_");
        }

        public void Dress(PlayerAppearance look)
        {
            if (Avatar != null && look != null) Avatar.Apply(look);
        }

        public void SetVisible(bool on)
        {
            if (visible == on) return;
            visible = on;
            foreach (var r in drawn) if (r != null) r.enabled = on;
        }

        public void SetShadowCasting(ShadowCastingMode mode)
        {
            foreach (var r in drawn) if (r != null) r.shadowCastingMode = mode;
        }

        /// <summary>Third person: idle / walk / run by the speed the feet move (works for the owner and for a replicated
        /// copy alike). Crossfades take effect on the Animator's next update.</summary>
        public void TickAnimation(Vector3 feet, float dt, PlayerArmsTuningV01 tuning)
        {
            if (Animator == null || !Animator.isActiveAndEnabled || dt <= 0f) return;
            Vector3 delta = feet - lastFeet;
            delta.y = 0f;
            float v = hasFeet && delta.magnitude < 3f ? delta.magnitude / dt : 0f;
            lastFeet = feet; hasFeet = true;
            speed = Mathf.Lerp(speed, v, 1f - Mathf.Exp(-dt * 8f));
            string state = speed < 0.25f ? tuning.IdleState : speed > tuning.RunAbove ? tuning.RunState : tuning.WalkState;
            float rate = state == tuning.IdleState ? 1f
                : Mathf.Clamp(speed / Mathf.Max(0.1f, state == tuning.RunState ? tuning.RunClipSpeed : tuning.WalkClipSpeed), 0.4f, 2f);
            Animator.speed = rate;
            if (state == playing || string.IsNullOrEmpty(state)) return;
            if (!Animator.HasState(0, Animator.StringToHash(state))) return;
            Animator.CrossFadeInFixedTime(state, 0.18f);
            playing = state;
        }

        /// <summary>Third person: the head nods with a share of the view pitch, on top of the clip (also when the clip does not
        /// key the head, without piling up).</summary>
        public void Nod(float pitchDegrees, Vector3 bodyRight)
        {
            var head = Rig.Head;
            if (head == null || head.parent == null) return;
            Quaternion current = head.localRotation;
            Quaternion baseRotation = nodSet && Quaternion.Angle(current, nodWritten) < 0.01f ? nodBase : current;
            Quaternion world = Quaternion.AngleAxis(Mathf.Clamp(pitchDegrees, -70f, 70f), bodyRight) * (head.parent.rotation * baseRotation);
            head.rotation = world;
            nodBase = baseRotation;
            nodWritten = head.localRotation;
            nodSet = true;
        }

        public void Destroy()
        {
            if (GameObject != null) Object.Destroy(GameObject);
        }
    }
}
