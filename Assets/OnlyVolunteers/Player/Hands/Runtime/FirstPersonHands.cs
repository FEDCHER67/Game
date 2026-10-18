using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>Local player's first-person arms (FP_HANDS_SPEC_2026-10-18_v01). Follows the view camera, adds sway,
    /// walk bob, wall retract and use/throw motion, blends hand poses by <see cref="HandPoseId"/>, places the held
    /// item's view-model proxy in the main hand and IKs both arms to their grip targets (pose, item socket or a
    /// world handle). Visual only: it never moves gameplay objects, owns no input and sends nothing over the network;
    /// gameplay calls <see cref="Hold"/>, <see cref="PlayUse"/>, <see cref="SetCharge"/>, <see cref="SetWorldTarget"/>
    /// and reads <see cref="NetState"/> for replication (hooks: spec §9).</summary>
    [DefaultExecutionOrder(1000)] // after KccFirstPersonInput has placed the camera this frame
    [DisallowMultipleComponent]
    public sealed class FirstPersonHands : MonoBehaviour
    {
        [Header("View")]
        [Tooltip("The player's world camera transform (KccFirstPersonInput.ViewCamera).")]
        public Transform viewCamera;
        public Camera worldCamera;
        [Tooltip("Optional URP overlay camera (child of the world camera) that draws only the view-model layer.")]
        public Camera viewModelCamera;
        [Range(20f, 100f)] public float viewModelFov = 55f;
        [Tooltip("Child of this object; carries sway/bob. Arms and item proxies live under it.")]
        public Transform viewRoot;
        [Tooltip("Layer for arms and proxies (e.g. FPViewModel); -1 leaves layers alone.")]
        public int viewModelLayer = -1;

        [Header("Rig")]
        public TwoBoneArm rightArm = new TwoBoneArm { poleLocal = new Vector3(0.7f, -0.9f, 0f) };
        public TwoBoneArm leftArm = new TwoBoneArm { poleLocal = new Vector3(-0.7f, -0.9f, 0f) };
        public HandPoseLibrary library;
        [Tooltip("Build capsule arms at runtime when no rig is assigned (greybox until the art exists).")]
        public bool buildGreyboxArms = true;

        [Header("Sway")]
        public float swayGain = 0.02f;
        public float swayMaxDegrees = 6f;
        public float swayRollGain = 0.012f;
        public float swayHalfLife = 0.07f;

        [Header("Bob")]
        public Vector2 bobAmplitude = new Vector2(0.012f, 0.008f);
        public float bobCyclesPerMeter = 0.45f;
        public float bobReferenceSpeed = 4.5f;
        public float bobHalfLife = 0.12f;

        [Header("Walls (no clipping is the overlay camera's job; this only reads better)")]
        [Tooltip("0 disables. Exclude the player's own layers.")]
        public LayerMask wallMask = 0;
        public float wallReach = 0.55f;
        public Vector3 wallRetractOffset = new Vector3(0f, -0.06f, -0.18f);
        public float wallHalfLife = 0.06f;

        [Header("Equip / reach")]
        public float equipDuration = 0.25f;
        public float equipDrop = 0.25f;
        public float reachHalfLife = 0.1f;
        public float throwRecoverBlend = 0.08f;

        private const int PoseCount = PoseBlender.Count;
        private readonly HandTarget[] poseRight = new HandTarget[PoseCount];
        private readonly HandTarget[] poseLeft = new HandTarget[PoseCount];
        private readonly bool[] poseOffSocket = new bool[PoseCount];
        private readonly float[] poseBlend = new float[PoseCount];
        private readonly float[] poseMotion = new float[PoseCount];
        private readonly Vector3[] poseUseOffset = new Vector3[PoseCount];
        private readonly Vector3[] poseUseEuler = new Vector3[PoseCount];
        private readonly float[] poseUseDuration = new float[PoseCount];
        private readonly Quaternion[] rotScratch = new Quaternion[PoseCount];

        private readonly PoseBlender blender = new PoseBlender();
        private readonly Dictionary<ItemGrip, ItemGrip> proxies = new Dictionary<ItemGrip, ItemGrip>();
        private readonly Transform[] worldTargets = new Transform[2];
        private readonly float[] reachWeights = new float[2];
        private readonly float[] reachVelocities = new float[2];

        private ItemGrip heldPrefab, heldProxy;
        private HandPoseId? poseOverride;
        private HandAction action;
        private byte actionSequence;
        private float charge01, useElapsed = float.MaxValue, equipElapsed = float.MaxValue;
        private Quaternion lastCameraRotation;
        private Vector3 lastCameraPosition;
        private bool haveLastCamera;
        private Vector3 sway, swayVelocity;
        private float bobPhase, bobWeight, bobWeightVelocity, wallRetract, wallVelocity;
        private bool visible = true;

        public ItemGrip HeldPrefab => heldPrefab;
        public ItemGrip HeldProxy => heldProxy;
        public HandPoseId CurrentPose => blender.Target;
        public bool TwoHanded => heldPrefab != null && heldPrefab.twoHanded;
        public HandsNetState NetState => new HandsNetState(blender.Target, action, actionSequence, charge01);

        /// <summary>Hide while driving, in menus, with the phone UI full-screen, etc.</summary>
        public bool Visible
        {
            get => visible;
            set { visible = value; if (viewRoot != null) viewRoot.gameObject.SetActive(value); }
        }

        // --- gameplay API ---

        /// <summary>Shows <paramref name="prefab"/> (an item visual with <see cref="ItemGrip"/>) in the hands; null
        /// empties them. Proxies are instantiated once per prefab under the view root and reused.</summary>
        public void Hold(ItemGrip prefab)
        {
            if (prefab == heldPrefab) return;
            if (heldProxy != null) heldProxy.gameObject.SetActive(false);
            heldPrefab = prefab;
            heldProxy = null;
            if (prefab != null)
            {
                if (!proxies.TryGetValue(prefab, out heldProxy) || heldProxy == null)
                {
                    heldProxy = Instantiate(prefab, viewRoot != null ? viewRoot : transform, false);
                    heldProxy.name = prefab.name + "_FP";
                    heldProxy.transform.localScale = Vector3.one * prefab.viewScale;
                    PrepareProxy(heldProxy.gameObject);
                    proxies[prefab] = heldProxy;
                }
                heldProxy.gameObject.SetActive(true);
            }
            equipElapsed = 0f;
            SetAction(HandAction.Equip);
            charge01 = 0f;
        }

        /// <summary>Forces a pose regardless of the held item (PushPull on a gurney, PhoneHold); null clears it.</summary>
        public void SetPoseOverride(HandPoseId? pose) => poseOverride = pose;

        /// <summary>One-shot use motion of the current pose (syringe press, scalpel stroke, zip-tie pull).</summary>
        public void PlayUse()
        {
            useElapsed = 0f;
            SetAction(HandAction.Use);
        }

        /// <summary>Charged throw: 0 cancels, &gt;0 pulls the main hand back into ThrowWindup by that amount.</summary>
        public void SetCharge(float charge)
        {
            charge01 = Mathf.Clamp01(charge);
            if (charge01 > 0f) action = HandAction.Charge;
            else if (action == HandAction.Charge) action = HandAction.None;
        }

        /// <summary>Release frame of a charged throw (the item itself is thrown by gameplay; call Hold(null) after).</summary>
        public void PlayThrow()
        {
            charge01 = 0f;
            useElapsed = 0f;
            SetAction(HandAction.Throw);
        }

        /// <summary>Reach a world handle with one hand (table tool at the cursor, gurney bar, door knob). The target's
        /// pose is the grip pose (ItemGrip axes); null releases. Blends in/out over reachHalfLife.</summary>
        public void SetWorldTarget(HandSide side, Transform target) => worldTargets[(int)side] = target;

        public void ClearWorldTargets() { worldTargets[0] = null; worldTargets[1] = null; }

        public void RebuildPoseCache()
        {
            for (int i = 0; i < PoseCount; i++)
            {
                var id = (HandPoseId)i;
                HandPose asset = library != null ? library.Find(id) : null;
                if (asset != null)
                {
                    poseRight[i] = asset.right; poseLeft[i] = asset.left; poseOffSocket[i] = asset.offHandUsesSocket;
                    poseBlend[i] = asset.blendTime; poseMotion[i] = asset.motionScale;
                    poseUseOffset[i] = asset.useOffset; poseUseEuler[i] = asset.useEuler; poseUseDuration[i] = asset.useDuration;
                }
                else
                {
                    HandPose.Defaults(id, out poseRight[i], out poseLeft[i], out poseOffSocket[i]);
                    poseBlend[i] = 0.15f; poseMotion[i] = 1f;
                    poseUseOffset[i] = new Vector3(0f, 0f, 0.06f); poseUseEuler[i] = Vector3.zero; poseUseDuration[i] = 0.25f;
                }
            }
        }

        // --- lifecycle ---

        private void Awake()
        {
            if (viewRoot == null)
            {
                viewRoot = new GameObject("FP_ViewRoot").transform;
                viewRoot.SetParent(transform, false);
            }
            if (buildGreyboxArms)
            {
                if (!rightArm.IsValid) BuildGreyboxArm(rightArm, HandSide.Right);
                if (!leftArm.IsValid) BuildGreyboxArm(leftArm, HandSide.Left);
            }
            rightArm.CacheRest();
            leftArm.CacheRest();
            if (viewModelLayer >= 0) SetLayer(viewRoot.gameObject, viewModelLayer);
            RebuildPoseCache();
        }

        private void OnValidate()
        {
            if (Application.isPlaying) RebuildPoseCache();
        }

        private void OnDisable() => haveLastCamera = false;

        private void LateUpdate()
        {
            if (viewCamera == null || !visible) return;
            float dt = Time.deltaTime;

            Vector3 camPos = viewCamera.position;
            Quaternion camRot = viewCamera.rotation;
            transform.SetPositionAndRotation(camPos, camRot);

            UpdateMotion(camPos, camRot, dt);
            UpdatePoseBlend(dt);
            if (viewModelCamera != null) viewModelCamera.fieldOfView = viewModelFov;

            float[] w = blender.Weights;
            float motion = 0f, offSocket = 0f;
            for (int i = 0; i < PoseCount; i++) { motion += w[i] * poseMotion[i]; offSocket += poseOffSocket[i] ? w[i] : 0f; }
            ApplyRootMotion(motion, dt);

            HandSide main = heldPrefab != null ? heldPrefab.mainHand : HandSide.Right;
            Pose root = new Pose(viewRoot.position, viewRoot.rotation);
            Pose mainLocal = BlendTarget(main == HandSide.Right ? poseRight : poseLeft, w, out Vector4 mainCurl, out float mainSpread);
            Pose offLocal = BlendTarget(main == HandSide.Right ? poseLeft : poseRight, w, out Vector4 offCurl, out float offSpread);

            if (heldPrefab != null) mainLocal = HandsMath.Multiply(mainLocal, heldPrefab.ViewTweak);
            ApplyUseKick(ref mainLocal);

            Pose mainGrip = ApplyReach(main, HandsMath.Multiply(root, mainLocal), dt);
            HandSide off = main == HandSide.Right ? HandSide.Left : HandSide.Right;
            Pose offGrip = HandsMath.Multiply(root, offLocal);

            if (heldProxy != null)
            {
                heldProxy.PlaceByMainGrip(mainGrip);
                if (offSocket > 0f && heldProxy.TryGetSocketWorld(off, out Pose socket))
                    offGrip = HandsMath.Lerp(offGrip, socket, offSocket);
            }
            offGrip = ApplyReach(off, offGrip, dt);

            TwoBoneArm mainArm = main == HandSide.Right ? rightArm : leftArm;
            TwoBoneArm offArm = main == HandSide.Right ? leftArm : rightArm;
            mainArm.SolveGrip(mainGrip, viewRoot, 1f);
            offArm.SolveGrip(offGrip, viewRoot, 1f);
            mainArm.ApplyFingers(mainCurl, mainSpread);
            offArm.ApplyFingers(offCurl, offSpread);

            if (action == HandAction.Use || action == HandAction.Throw || action == HandAction.Equip)
            {
                bool done = action == HandAction.Equip ? equipElapsed >= equipDuration
                    : useElapsed >= poseUseDuration[(int)blender.Target];
                if (done) action = charge01 > 0f ? HandAction.Charge : HandAction.None;
            }
            if (worldTargets[0] != null || worldTargets[1] != null)
            { if (action == HandAction.None) action = HandAction.Reach; }
            else if (action == HandAction.Reach) action = HandAction.None;
        }

        // --- internals ---

        private void SetAction(HandAction next)
        {
            action = next;
            actionSequence = (byte)((actionSequence + 1) & 0x3);
        }

        private HandPoseId BasePose() =>
            poseOverride ?? (heldPrefab != null ? heldPrefab.pose : HandPoseId.Empty);

        private void UpdatePoseBlend(float dt)
        {
            if (charge01 > 0f)
            {
                blender.SetTarget(HandPoseId.ThrowWindup);
                blender.Step(dt, poseBlend[(int)HandPoseId.ThrowWindup], charge01);
                return;
            }
            HandPoseId target = BasePose();
            blender.SetTarget(target);
            blender.Step(dt, action == HandAction.Throw ? throwRecoverBlend : poseBlend[(int)target]);
        }

        private void UpdateMotion(Vector3 camPos, Quaternion camRot, float dt)
        {
            if (!haveLastCamera || dt <= 0f)
            {
                lastCameraPosition = camPos; lastCameraRotation = camRot; haveLastCamera = true;
                return;
            }
            Vector3 delta = (Quaternion.Inverse(lastCameraRotation) * camRot).eulerAngles;
            var look = new Vector2(Mathf.DeltaAngle(0f, delta.y), Mathf.DeltaAngle(0f, delta.x)) / dt;
            Vector3 move = camPos - lastCameraPosition;
            move.y = 0f;
            float speed = move.magnitude / dt;
            if (speed > 20f) speed = 0f; // teleport / seat change
            lastCameraPosition = camPos; lastCameraRotation = camRot;

            float heft = heldPrefab != null ? heldPrefab.heft : 0f;
            Vector3 swayTarget = HandsMath.SwayAngles(look, swayGain * (1f + heft), swayMaxDegrees, swayRollGain);
            sway = HandsMath.SpringStep(sway, ref swayVelocity, swayTarget, swayHalfLife * (1f + heft), dt);

            float bobTarget = bobReferenceSpeed > 0f ? Mathf.Clamp01(speed / bobReferenceSpeed) : 0f;
            bobWeight = HandsMath.SpringStep(bobWeight, ref bobWeightVelocity, bobTarget, bobHalfLife, dt);
            bobPhase = HandsMath.AdvanceBobPhase(bobPhase, speed, bobCyclesPerMeter * (1f - 0.3f * heft), dt);

            float wallTarget = 0f;
            if (wallMask.value != 0 &&
                Physics.Raycast(camPos, camRot * Vector3.forward, out RaycastHit hit, wallReach, wallMask, QueryTriggerInteraction.Ignore))
                wallTarget = HandsMath.WallRetract(hit.distance, wallReach);
            wallRetract = HandsMath.SpringStep(wallRetract, ref wallVelocity, wallTarget, wallHalfLife, dt);

            if (useElapsed < float.MaxValue) useElapsed += dt;
            if (equipElapsed < float.MaxValue) equipElapsed += dt;
        }

        private void ApplyRootMotion(float motionScale, float dt)
        {
            float equip = equipElapsed < equipDuration ? 1f - equipElapsed / Mathf.Max(1e-3f, equipDuration) : 0f;
            Vector3 offset = HandsMath.BobOffset(bobPhase, bobWeight, bobAmplitude) * motionScale
                             + wallRetractOffset * wallRetract
                             + Vector3.down * (equipDrop * equip * equip);
            viewRoot.localPosition = offset;
            viewRoot.localRotation = Quaternion.Euler(sway * motionScale);
        }

        private Pose BlendTarget(HandTarget[] table, float[] w, out Vector4 curl, out float spread)
        {
            Vector3 pos = Vector3.zero;
            curl = Vector4.zero;
            spread = 0f;
            for (int i = 0; i < PoseCount; i++)
            {
                rotScratch[i] = Quaternion.Euler(table[i].gripEuler);
                if (w[i] <= 0f) continue;
                pos += table[i].gripPosition * w[i];
                curl += table[i].curl * w[i];
                spread += table[i].spread * w[i];
            }
            return new Pose(pos, HandsMath.BlendRotations(rotScratch, w, PoseCount));
        }

        private void ApplyUseKick(ref Pose mainLocal)
        {
            int p = (int)blender.Target;
            if (action != HandAction.Use && action != HandAction.Throw) return;
            float k = HandsMath.UseKick(useElapsed, poseUseDuration[p]);
            if (k <= 0f) return;
            Vector3 offset = action == HandAction.Throw ? new Vector3(0f, 0.02f, 0.18f) : poseUseOffset[p];
            mainLocal.position += offset * k;
            mainLocal.rotation *= Quaternion.Euler(poseUseEuler[p] * k);
        }

        private Pose ApplyReach(HandSide side, Pose grip, float dt)
        {
            int s = (int)side;
            Transform t = worldTargets[s];
            reachWeights[s] = Mathf.Clamp01(HandsMath.SpringStep(reachWeights[s], ref reachVelocities[s],
                t != null ? 1f : 0f, reachHalfLife, dt));
            if (t == null || reachWeights[s] <= 1e-3f) return grip;
            Vector3 target = t.position;
            if (viewModelCamera != null && worldCamera != null)
            {
                // The arms are drawn with the view-model FOV: move the target so it lands where the world shows it.
                Vector3 local = viewCamera.InverseTransformPoint(target);
                target = viewCamera.TransformPoint(HandsMath.WorldToViewModelSpace(local, worldCamera.fieldOfView, viewModelFov));
            }
            return HandsMath.Lerp(grip, new Pose(target, t.rotation), reachWeights[s]);
        }

        private void PrepareProxy(GameObject go)
        {
            // A view-model proxy is visual only: no physics, no network, no shadows into the world.
            foreach (var c in go.GetComponentsInChildren<Collider>(true)) c.enabled = false;
            foreach (var rb in go.GetComponentsInChildren<Rigidbody>(true)) rb.isKinematic = true;
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            if (viewModelLayer >= 0) SetLayer(go, viewModelLayer);
        }

        private static void SetLayer(GameObject go, int layer)
        {
            go.layer = layer;
            foreach (Transform c in go.transform) SetLayer(c.gameObject, layer);
        }

        private void BuildGreyboxArm(TwoBoneArm arm, HandSide side)
        {
            float sx = side == HandSide.Right ? 1f : -1f;
            string n = side == HandSide.Right ? "R" : "L";
            arm.upper = NewBone("Arm_" + n + "_Upper", viewRoot, new Vector3(0.24f * sx, -0.45f, -0.08f));
            arm.lower = NewBone("Arm_" + n + "_Lower", arm.upper, new Vector3(0f, 0f, 0.3f));
            arm.hand = NewBone("Hand_" + n, arm.lower, new Vector3(0f, 0f, 0.28f));
            arm.grip = NewBone("Hand_" + n + "_Grip", arm.hand, new Vector3(0f, 0f, 0.05f));
            AddShape(PrimitiveType.Capsule, arm.upper, 0.3f, 0.075f);
            AddShape(PrimitiveType.Capsule, arm.lower, 0.28f, 0.065f);
            AddShape(PrimitiveType.Sphere, arm.hand, 0.1f, 0.1f);
        }

        private static Transform NewBone(string name, Transform parent, Vector3 localPosition)
        {
            var t = new GameObject(name).transform;
            t.SetParent(parent, false);
            t.localPosition = localPosition;
            return t;
        }

        private static void AddShape(PrimitiveType type, Transform bone, float length, float thickness)
        {
            GameObject g = GameObject.CreatePrimitive(type);
            var col = g.GetComponent<Collider>();
            col.enabled = false;
            Destroy(col);
            g.name = bone.name + "_Greybox";
            g.transform.SetParent(bone, false);
            g.transform.localPosition = new Vector3(0f, 0f, length * 0.5f);
            g.transform.localRotation = type == PrimitiveType.Capsule ? Quaternion.Euler(90f, 0f, 0f) : Quaternion.identity;
            g.transform.localScale = type == PrimitiveType.Capsule
                ? new Vector3(thickness, length * 0.5f, thickness)
                : new Vector3(thickness, thickness * 0.8f, length);
            g.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        }
    }
}
